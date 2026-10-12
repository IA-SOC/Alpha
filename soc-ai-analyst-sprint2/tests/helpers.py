"""Synthetic fixtures; no customer-export layout is asserted."""

from typing import Any


def make_case(
    source: str = "elastic", count: int = 1, case_id: str = "INC-TEST-001"
) -> dict[str, Any]:
    alerts = []
    for index in range(count):
        alert_id = f"native-{index}"
        raw = {"event": {"id": alert_id}} if source == "elastic" else {"id": alert_id}
        alerts.append({"alert_id": alert_id, "source_system": source, "raw_alert": raw})
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "submitted_at": "2026-09-29T20:30:00Z",
        "alerts": alerts,
    }


def add_enrichment(case: dict[str, Any]) -> None:
    case["enrichments"] = [
        {
            "provider": "virustotal",
            "observable": {"type": "ip", "value": "192.0.2.10"},
            "related_alert_ids": [case["alerts"][0]["alert_id"]],
            "raw_result": {"custom": {"nested": [True, None, 3.1]}},
        }
    ]


def assert_rejected(response, id_factory, rule: str, status_code: int = 422) -> None:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert "case_id" not in body
    assert "submitted_case_id" not in body
    assert body["detail"]
    assert any(error["rule"] == rule for error in body["detail"]), body
    assert all(
        error["loc"] and error["msg"] and error["type"] for error in body["detail"]
    )
    id_factory.assert_not_called()
