"""#67 acceptance: audience claims -> canonical report -> original case evidence.

Reuse the real API/MCP fixture and source cases already exercised by Sprint 3.
Formatter unit tests cover projection mechanics; these check source-grounded
content and the backend's rejection of altered audience views.
"""

import json
from copy import deepcopy

import pytest

from app.services.traceability import _resolve_pointer, verify_traceability
from core.report_contract import serialize_report
from tests.helpers import investigate, tagged
from tests.sprint3.cases import EXPECTATIONS, load_case

CASES = (
    "us6_ambiguous",
    "us7_nested_custom",
    "us7_conflicting_providers",
    "us7_missing",
)
SUMMARY_FIELDS = (
    "brief",
    "observations",
    "hypotheses",
    "potential_impact",
    "proposed_actions",
    "limitations",
    "review",
)


def assert_original_fields(node, source):
    """Check source IDs, alert ownership and raw values behind a projected claim."""
    indexes = {alert["alert_id"]: i for i, alert in enumerate(source["alerts"])}
    if isinstance(node, dict):
        if "source_fields" in node:
            for field in node["source_fields"]:
                aid = field["alert_id"]
                assert aid in indexes
                assert field["path"].startswith(f"/alerts/{indexes[aid]}/raw_alert/")
                exists, original = _resolve_pointer(source, field["path"])
                assert exists and original == field["value"]
                if "alert_id" in node:
                    assert aid == node["alert_id"]
        for value in node.values():
            assert_original_fields(value, source)
    elif isinstance(node, list):
        for value in node:
            assert_original_fields(value, source)


@pytest.mark.parametrize("name", CASES)
def test_both_audiences_have_required_source_grounded_information(name, sprint3_result):
    result, source = sprint3_result(name), load_case(name)
    report = result["report"]
    sections = report["audience_sections"]
    technical, summary = sections["technical"], sections["non_technical"]
    assert technical["title"] == "Technical findings"
    assert summary["title"] == "Non-technical summary"
    for key in SUMMARY_FIELDS:
        claims = summary[key] if isinstance(summary[key], list) else [summary[key]]
        assert claims
        for claim in claims:
            assert claim["text"].strip() and claim["report_paths"]
            for path in claim["report_paths"]:
                exists, canonical = _resolve_pointer(report, path)
                assert exists, path
                assert_original_fields(canonical, source)
    data = technical["data"]
    for key in (
        "input",
        "timeline",
        "attack_mapping",
        "hypotheses",
        "blast_radius",
        "enrichment",
        "recommended_actions",
        "limitations",
        "review",
    ):
        assert key in data
    known_ids = {alert["alert_id"] for alert in source["alerts"]}
    assert {
        aid for entry in data["timeline"] for aid in entry["alert_ids"]
    } == known_ids
    assert data["input"]["alert_count"] == len(source["alerts"])
    assert (
        f"processed {len(source['alerts'])} of {len(source['alerts'])}"
        in (summary["observations"][0]["text"])
    )
    assert_original_fields(data, source)
    for hypothesis in data["hypotheses"]:
        assert hypothesis["evidence_for"]
        for evidence in hypothesis["evidence_for"] + hypothesis["evidence_against"]:
            assert evidence["alert_id"] in known_ids
            assert evidence["source_fields"]  # prevent vacuous pointer checks
    verify_traceability(result["investigation_context"], report)
    assert json.loads(serialize_report(report)) == report  # #84/#87 compatibility


def test_both_audiences_keep_support_contradictions_and_uncertainty(sprint3_result):
    result = sprint3_result("us6_ambiguous")
    sections = result["report"]["audience_sections"]
    expected = EXPECTATIONS["us6_ambiguous"]
    hypothesis = sections["technical"]["data"]["hypotheses"][0]
    assert {e["alert_id"] for e in hypothesis["evidence_for"]} == set(
        expected["support_ids"]
    )
    assert {e["alert_id"] for e in hypothesis["evidence_against"]} == set(
        expected["against_ids"]
    )
    finding = sections["technical"]["findings"][0]["text"]
    for aid in expected["support_ids"] + expected["against_ids"]:
        assert aid in finding
    summary = sections["non_technical"]
    text = summary["hypotheses"][0]["text"]
    assert "Supporting references: 2; contradicting references: 1" in text
    assert "Reported confidence: low" in text
    assert "This remains a hypothesis" in text
    assert "Nothing has been confirmed" in summary["brief"][0]["text"]
    assert "not automatically compromised" in summary["potential_impact"][0]["text"]
    assert not sections["technical"]["data"]["blast_radius"]["confirmed_assets"]
    assert all(
        "Pending analyst approval" in a["text"] for a in summary["proposed_actions"]
    )


def test_provider_verdicts_remain_quoted_evidence_not_summary_facts(sprint3_result):
    sections = sprint3_result("us7_conflicting_providers")["report"][
        "audience_sections"
    ]
    source = load_case("us7_conflicting_providers")
    data = sections["technical"]["data"]
    for item, supplied in zip(
        data["enrichment"]["items"], source["enrichments"], strict=True
    ):
        assert item["raw_result"] == supplied["raw_result"]
        exists, original = _resolve_pointer(source, item["source_path"])
        assert exists and original == supplied
    linked = data["hypotheses"][0]["ioc_evidence"]
    assert {e["evidence_id"] for e in linked} == {
        item["evidence_id"] for item in data["enrichment"]["items"]
    }
    summary_text = json.dumps(sections["non_technical"])
    assert "malicious" not in summary_text and "benign" not in summary_text
    assert "do not independently confirm compromise" in summary_text
    assert data["hypotheses"][0]["confidence"] == "baja"


def test_real_insufficient_evidence_case_is_uncertain_in_both_audiences(client):
    result = investigate(
        client, tagged("isolated", ["brute_force"], time="2026-10-09T12:00:00")
    )
    report = result["report"]
    sections = report["audience_sections"]
    hypothesis = sections["technical"]["data"]["hypotheses"][0]
    assert hypothesis["confidence"] == "insuficiente"
    assert hypothesis["confidence_basis"] and hypothesis["unknowns"]
    assert [e["alert_id"] for e in hypothesis["evidence_for"]] == ["isolated"]
    assert (
        "Confidence: insufficient (ordinal)"
        in sections["technical"]["findings"][0]["text"]
    )
    summary = sections["non_technical"]
    assert "insufficient confidence" in summary["brief"][0]["text"]
    assert "Reported confidence: insufficient" in summary["hypotheses"][0]["text"]
    assert "This remains a hypothesis" in summary["hypotheses"][0]["text"]
    assert "Nothing has been confirmed" in summary["brief"][0]["text"]
    assert report["recommended_actions"] == []
    assert "No response actions" in summary["proposed_actions"][0]["text"]
    assert "insufficient" in result["report_markdown"]
    verify_traceability(result["investigation_context"], report)


@pytest.mark.parametrize(
    "section,key",
    [
        ("technical", "data"),
        ("technical", "findings"),
        *(("non_technical", key) for key in SUMMARY_FIELDS),
    ],
)
def test_missing_audience_content_is_rejected(section, key, sprint3_result):
    result = sprint3_result("us7_nested_custom")
    del result["report"]["audience_sections"][section][key]
    with pytest.raises(ValueError, match="Audience sections differ"):
        verify_traceability(result["investigation_context"], result["report"])


@pytest.mark.parametrize(
    "section,key",
    [
        ("technical", "findings"),
        ("non_technical", "brief"),
        ("non_technical", "hypotheses"),
        ("non_technical", "potential_impact"),
        ("non_technical", "proposed_actions"),
    ],
)
def test_unsupported_audience_conclusions_are_rejected(section, key, sprint3_result):
    result = sprint3_result("us7_nested_custom")
    report = deepcopy(result["report"])
    claim = report["audience_sections"][section][key][0]
    # Even a resolvable reference cannot justify changing a candidate into fact.
    assert all(_resolve_pointer(report, p)[0] for p in claim["report_paths"])
    claim["text"] = (
        "Confirmed compromise; all hosts are infected and isolation is complete."
    )
    with pytest.raises(ValueError, match="Audience sections differ"):
        verify_traceability(result["investigation_context"], report)
