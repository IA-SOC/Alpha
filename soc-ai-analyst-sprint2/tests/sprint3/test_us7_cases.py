from copy import deepcopy

import pytest

from app.services.case_service import native_identifier
from app.services.traceability import verify_traceability
from tests.sprint3.cases import EXPECTATIONS, load_case

CASES = ["us7_nested_custom", "us7_missing", "us7_conflicting_providers"]


@pytest.mark.parametrize("name", CASES)
def test_original_evidence_survives_the_full_api_pipeline(name, sprint3_result):
    payload = load_case(name)
    result = sprint3_result(name)
    context = result["investigation_context"]
    assert context["original_case"] == payload
    verify_traceability(context, result["report"])
    for pointer, expected in EXPECTATIONS[name]["original_pointers"].items():
        assert native_identifier(context["original_case"], pointer) == expected

    def check_pointers(node):
        if isinstance(node, dict):
            if {"alert_id", "path", "value"} <= node.keys():
                assert native_identifier(payload, node["path"]) == node["value"]
                assert node["alert_id"] in {a["alert_id"] for a in payload["alerts"]}
            for value in node.values():
                check_pointers(value)
        elif isinstance(node, list):
            for value in node:
                check_pointers(value)


    check_pointers(result["report"])


def test_missing_values_do_not_become_invented_evidence(sprint3_result):
    result = sprint3_result("us7_missing")
    assert result["report"]["attack_mapping"] == []
    assert result["report"]["hypotheses"] == []
    assert all(not t["timestamp_utc"] for t in result["report"]["timeline"])
    assert all(not e["attributes"] for e in result["investigation_context"]["events"])
    assert all(e["warnings"] for e in result["investigation_context"]["events"])


def test_provider_disagreement_stays_separate_and_does_not_raise_confidence(
    sprint3_result,
):
    result = sprint3_result("us7_conflicting_providers")
    payload = load_case("us7_conflicting_providers")
    items = result["report"]["enrichment"]["items"]
    assert [item["provider"] for item in items] == EXPECTATIONS[
        "us7_conflicting_providers"
    ]["providers"]
    assert len({item["evidence_id"] for item in items}) == 2
    for index, (item, original) in enumerate(zip(items, payload["enrichments"])):
        for key, value in original.items():
            assert item[key] == value
        assert item["source_path"] == f"/enrichments/{index}"
        assert "verdict" not in item
    hypothesis = result["report"]["hypotheses"][0]
    assert hypothesis["confidence"] == "baja"
    assert {e["evidence_id"] for e in hypothesis["ioc_evidence"]} == {
        item["evidence_id"] for item in items
    }
    assert all(e["role"] == "context" for e in hypothesis["ioc_evidence"])


@pytest.mark.parametrize("corruption", ["unknown_alert", "wrong_path", "wrong_value"])
def test_tampered_source_reference_is_rejected(corruption, sprint3_result):
    result = sprint3_result("us7_nested_custom")
    report = deepcopy(result["report"])
    field = report["hypotheses"][0]["evidence_for"][0]["source_fields"][0]
    if corruption == "unknown_alert":
        field["alert_id"] = "not-submitted"
    elif corruption == "wrong_path":
        field["path"] = "/alerts/999/raw_alert/tags"
    else:
        field["value"] = "tampered"
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], report)


def test_changed_provider_result_is_rejected(sprint3_result):
    result = sprint3_result("us7_conflicting_providers")
    result["report"]["enrichment"]["items"][0]["raw_result"]["score"] = 0
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], result["report"])
