from uuid import uuid4

from fastapi.testclient import TestClient

from agent.investigation import build_blast_radius
from app.main import create_app


def test_blast_radius_deduplicates_entities_and_keeps_alert_evidence():
    alerts = [
        {
            "id": "a1",
            "host": "web-01",
            "user": "alice",
            "source_ip": "198.51.100.10",
            "dest_ip": "10.0.0.10",
            "rule_name": "rule-a",
        },
        {
            "id": "a2",
            "host": "web-01",
            "user": "alice",
            "source_ip": "198.51.100.10",
            "dest_ip": "10.0.0.10",
            "rule_name": "rule-b",
        },
    ]

    result = build_blast_radius(alerts, [])

    assert len(result["observed_assets"]) == 1
    assert result["observed_assets"][0]["basis_alert_ids"] == ["a1", "a2"]
    entities = {
        (item["entity_type"], item["entity"]): item["basis_alert_ids"]
        for item in result["observed_entities"]
    }
    assert entities == {
        ("host", "web-01"): ["a1", "a2"],
        ("user", "alice"): ["a1", "a2"],
        ("source_ip", "198.51.100.10"): ["a1", "a2"],
        ("destination_ip", "10.0.0.10"): ["a1", "a2"],
    }


def test_report_endpoint_exposes_persisted_dual_audience_sections(tmp_path):
    path = tmp_path / "cases.sqlite3"
    app = create_app(database_path=path)
    case_id = uuid4()
    result = {
        "case_id": str(case_id),
        "report": {
            "audience_sections": {
                "technical": {"title": "Technical findings"},
                "non_technical": {"title": "Non-technical summary"},
            }
        },
        "report_markdown": "report",
    }
    with TestClient(app) as client:
        app.state.investigation_service.store.save_investigation(case_id, result)
        response = client.get(f"/api/v1/cases/{case_id}/report")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": str(case_id),
        "report": result["report"],
        "audience_sections": result["report"]["audience_sections"],
        "report_markdown": "report",
    }
