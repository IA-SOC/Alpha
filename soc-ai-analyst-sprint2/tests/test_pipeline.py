import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app.main import create_app
from app.services.report_formatter import format_report
from app.services.traceability import verify_traceability
from core.report_contract import SCHEMA_ID, serialize_report
from tests.test_correlation_engine import case_for, event
from tests.test_ioc_integration import ioc

URL = "/api/v1/cases"
ROOT = Path(__file__).resolve().parents[1]


def submit(client, case):
    response = client.post(URL, json=case.model_dump(exclude_unset=True))
    assert response.status_code == 201, response.text
    return response.json()["case_id"]


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    path = tmp_path_factory.mktemp("pipeline") / "cases.sqlite3"
    app = create_app(database_path=path)
    a, b = event("a"), event("b", source="wazuh")
    for alert in (a, b):
        alert["raw_alert"]["tags"] = ["brute_force"]
        alert["raw_alert"]["customer_extra"] = {"a": [True, None, 1]}
    payload = case_for(
        a,
        b,
        event("noise", ip="198.51.100.8", host="dns-02", user="backup"),
        enrichments=[
            ioc(raw_result={"reputation": "malicious", "custom": 10}),
            ioc("203.0.113.9", related_alert_ids=["a"]),
        ],
    )
    with TestClient(app) as client:
        case_id = submit(client, payload)
        response = client.post(f"{URL}/{case_id}/investigate")
        assert response.status_code == 200, response.text
        yield client, app, path, case_id, payload, response.json()


def test_full_api_pipeline_reaches_real_langgraph_and_mcp(real_run):
    client, app, path, cid, payload, result = real_run
    assert result["status"] == "pending_review"
    assert result["validation"]["ok"] and result["validation"]["traceability_ok"]
    assert result["correlation"]["noise_alert_ids"] == ["noise"]
    assert result["report"]["enrichment"]["items"][0]["matched_alert_ids"] == ["a", "b"]
    assert [a["phase"] for a in result["audit_log"]] == [1, 2, 3, 4, 5]
    assert result["report"]["review"]["status"] == "pending"
    assert result["report"]["input"]["source_format"] == "mixed"
    assert result["report"]["input"]["schema_version"] == "1.0"
    assert result["report"]["methodology"]["report_schema"] == SCHEMA_ID
    assert json.loads(serialize_report(result["report"])) == result["report"]
    assert result["report"]["audience_sections"] == format_report(result["report"])
    assert result["report"]["audience_sections"]["language"] == "en"
    assert "## Non-technical summary" in result["report_markdown"]
    assert "## Technical findings" in result["report_markdown"]
    assert client.get(f"{URL}/{cid}").json()["submitted_case"] == payload.model_dump(
        exclude_unset=True
    )
    assert client.get(f"{URL}/{cid}/context").json() == result["investigation_context"]
    assert client.get(f"{URL}/{cid}/investigation").json() == result
    schema = json.loads(
        (
            ROOT / "skills/soc-case-investigator/references/report-schema.json"
        ).read_text()
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        result["report"]
    )


@pytest.mark.parametrize("corruption", ["percentage", "unsupported", "section"])
def test_backend_rechecks_contract_even_if_agent_validation_was_ok(
    real_run, corruption
):
    _, app, _, cid, _, result = real_run
    report = deepcopy(result["report"])
    if corruption == "percentage":
        report["hypotheses"][0]["confidence"] = "99%"
    elif corruption == "unsupported":
        report["hypotheses"][0]["evidence_for"] = []
    else:
        del report["timeline"]
    state = {
        "validation": {"ok": True},
        "case": {"investigation_context": result["investigation_context"]},
        "report": report,
    }
    with pytest.raises(ValueError, match="Report contract"):
        app.state.investigation_service._result(cid, result["run_id"], state)


def test_findings_reference_real_ioc_evidence_without_increasing_confidence(real_run):
    result = real_run[-1]
    hypothesis = result["report"]["hypotheses"][0]
    assert hypothesis["confidence"] == "media"
    assert {e["evidence_id"] for e in hypothesis["ioc_evidence"]} == {
        "ioc-0001",
        "ioc-0002",
    }
    assert {e["alert_id"] for e in hypothesis["ioc_evidence"]} == {"a", "b"}
    for e in hypothesis["evidence_for"]:
        assert e["source_fields"]
    verify_traceability(result["investigation_context"], result["report"])
    broken = deepcopy(result["report"])
    broken["hypotheses"][0]["ioc_evidence"][0]["alert_id"] = "noise"
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], broken)


@pytest.mark.parametrize(
    "section, mutate",
    [
        (
            "timeline",
            lambda report: report["timeline"][0]["alert_ids"].__setitem__(
                0, "not-submitted"
            ),
        ),
        (
            "attack_mapping",
            lambda report: report["attack_mapping"][0]["evidence"][0][
                "source_fields"
            ][0].__setitem__("path", "/alerts/0/raw_alert/not_present"),
        ),
        (
            "blast_radius",
            lambda report: report["blast_radius"]["observed_assets"][0][
                "basis_alert_ids"
            ].__setitem__(0, "not-submitted"),
        ),
        (
            "recommended_actions",
            lambda report: report["recommended_actions"][0]["evidence_ids"].__setitem__(
                0, "not-submitted"
            ),
        ),
        (
            "hypothesis_ioc",
            lambda report: report["hypotheses"][0]["ioc_evidence"][0].__setitem__(
                "source_path", "/enrichments/999"
            ),
        ),
    ],
)
def test_traceability_rejects_broken_references_and_paths(real_run, section, mutate):
    result = real_run[-1]
    broken = deepcopy(result["report"])
    mutate(broken)
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], broken)


def test_evidence_survives_restart_but_live_review_checkpoint_is_explicitly_temporary(
    real_run,
):
    _, _, path, cid, payload, result = real_run
    with TestClient(create_app(database_path=path)) as restarted:
        saved = restarted.get(f"{URL}/{cid}/investigation").json()
        assert saved["report"]["audience_sections"] == (
            result["report"]["audience_sections"]
        )
        assert saved == result
        assert saved["report"]["timeline"] == result["report"]["timeline"]
        assert saved["report"]["attack_mapping"] == result["report"]["attack_mapping"]
        assert all(
            mapping["technique_id"]
            and mapping["tactic"]
            and mapping["source_version"]
            and mapping["evidence"]
            for mapping in saved["report"]["attack_mapping"]
        )
        assert saved["report"]["hypotheses"] == result["report"]["hypotheses"]
        assert all(
            hypothesis["evidence_for"]
            for hypothesis in saved["report"]["hypotheses"]
        )
        assert any(
            hypothesis["ioc_evidence"]
            for hypothesis in saved["report"]["hypotheses"]
        )
        assert (
            saved["report"]["enrichment"]["items"]
            == result["report"]["enrichment"]["items"]
        )
        assert restarted.get(f"{URL}/{cid}").json()["submitted_case"] == (
            payload.model_dump(exclude_unset=True)
        )
        assert (
            restarted.post(
                f"{URL}/{cid}/review",
                json={"status": "validated", "analyst": "test", "notes": "checked"},
            ).status_code
            == 409
        )


@pytest.mark.parametrize("source", ["elastic", "wazuh"])
def test_valid_case_without_enrichment_uses_original_workflow(client, source):
    cid = submit(client, case_for(event("a", source=source)))
    result = client.post(f"{URL}/{cid}/investigate").json()
    assert result["validation"]["ok"]
    assert result["report"]["enrichment"]["status"] == "no_disponible"
    assert result["report"]["timeline"][0]["alert_ids"] == ["a"]


def test_unrelated_same_mitre_technique_does_not_pool_confidence(client):
    a, b = event("a"), event("b", ip="198.51.100.3", host="other", user="other")
    for alert in (a, b):
        alert["raw_alert"]["tags"] = ["brute_force"]
    cid = submit(client, case_for(a, b))
    result = client.post(f"{URL}/{cid}/investigate").json()
    assert len(result["report"]["hypotheses"]) == 2
    assert all(h["confidence"] == "baja" for h in result["report"]["hypotheses"])
    assert all(len(h["evidence_for"]) == 1 for h in result["report"]["hypotheses"])


def test_untyped_custom_native_fields_cannot_crash_agent(client):
    alert = event("a", time={"custom": "not a timestamp"}, host=["x"], user={"id": 7})
    cid = submit(client, case_for(alert))
    response = client.post(f"{URL}/{cid}/investigate")
    assert response.status_code == 200, response.text
    assert response.json()["report"]["timeline"][0]["timestamp_original"] is None


def test_missing_cases_invalid_ids_and_missing_investigation(client):
    cid = uuid4()
    for suffix in ("", "/context", "/investigation"):
        assert client.get(f"{URL}/{cid}{suffix}").status_code == 404
    assert client.post(f"{URL}/{cid}/investigate").status_code == 404
    assert client.get(f"{URL}/not-a-uuid/context").status_code == 422


def test_failure_retains_accepted_evidence_and_allows_retry(client, monkeypatch):
    import app.services.investigation_service as module

    original = module.investigate

    async def fail(*args, **kwargs):
        raise RuntimeError("simulated MCP failure")

    payload = case_for(event("a"))
    cid = submit(client, payload)
    monkeypatch.setattr(module, "investigate", fail)
    assert client.post(f"{URL}/{cid}/investigate").status_code == 502
    accepted = client.get(f"{URL}/{cid}")
    assert accepted.status_code == 200
    assert accepted.json()["submitted_case"] == payload.model_dump(exclude_unset=True)
    assert client.get(f"{URL}/{cid}/investigation").status_code == 404
    monkeypatch.setattr(module, "investigate", original)
    assert client.post(f"{URL}/{cid}/investigate").status_code == 200


def test_review_resumes_existing_graph_and_persists_decision(real_run):
    client, app, path, cid, _, _ = real_run
    assert (
        client.post(
            f"{URL}/{cid}/review",
            json={"status": "closed", "analyst": "test", "notes": "x"},
        ).status_code
        == 422
    )
    decision = {
        "status": "corrected",
        "analyst": "test-analyst",
        "notes": "Requires additional evidence.",
    }
    response = client.post(f"{URL}/{cid}/review", json=decision)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["report"]["review"]["status"] == "corrected"
    assert result["report"]["audience_sections"] == format_report(result["report"])
    assert "Human review status: corrected" in result["report_markdown"]
    assert len(result["audit_log"]) == 6
    assert client.get(f"{URL}/{cid}/investigation").json() == result
    assert client.post(f"{URL}/{cid}/review", json=decision).status_code == 409
