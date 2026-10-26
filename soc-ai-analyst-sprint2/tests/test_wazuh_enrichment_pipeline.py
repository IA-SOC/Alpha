"""Synthetic CI and opt-in local customer compatibility through the real API."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.traceability import _resolve_pointer, verify_traceability
from app.services.wazuh_import import iter_wazuh_records
from tests.test_wazuh_enrichment import map_alerts, provider_alert


def check_pipeline(raw_alerts, tmp_path):
    mapped = map_alerts(*raw_alerts)
    payload = mapped.case.model_dump(exclude_unset=True)
    database = tmp_path / "us3.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        accepted = client.post("/api/v1/cases", json=payload)
        assert accepted.status_code == 201
        cid = accepted.json()["case_id"]
        result = client.post(f"/api/v1/cases/{cid}/investigate")
        assert result.status_code == 200
        result = result.json()
        assert result["status"] == "pending_review"
        assert result["validation"]["ok"]
        assert result["validation"]["traceability_ok"]
        verify_traceability(result["investigation_context"], result["report"])
        items = result["report"]["enrichment"]["items"]
        assert len(items) == len(mapped.case.enrichments)
        for item, original in zip(items, payload["enrichments"], strict=True):
            assert item["raw_result"] == original["raw_result"]
        for source in mapped.sources:
            _, enrichment = _resolve_pointer(payload, source["enrichment_path"])
            _, raw_result = _resolve_pointer(payload, source["raw_result_path"])
            assert enrichment["raw_result"] == raw_result
    with TestClient(create_app(database_path=database)) as restarted:
        stored = restarted.get(f"/api/v1/cases/{cid}").json()["submitted_case"]
        assert stored == payload
        saved = restarted.get(f"/api/v1/cases/{cid}/investigation").json()
        assert saved["report"]["enrichment"]["items"] == items
    return mapped


def test_synthetic_siem_enrichment_survives_investigation_and_restart(tmp_path):
    parent = {
        "id": "original",
        "timestamp": "2026-08-10T00:00:00.000-0500",
        "syscheck": {"sha1_after": "a" * 40},
    }
    check_pipeline(
        [parent, provider_alert(), provider_alert("misp_file_hashes", "provider-2")],
        tmp_path,
    )


@pytest.mark.skipif(
    not os.getenv("ALIGO_WAZUH_ZIP"), reason="Customer ZIP is local and opt-in"
)
def test_customer_sample_compatibility(tmp_path):
    # Select by provider outcome, not by verdict or assumed incident label.
    samples = {}
    locations = {}
    path = Path(os.environ["ALIGO_WAZUH_ZIP"])
    for raw, location in iter_wazuh_records(path):
        data = raw.get("data", {})
        vt = data.get("virustotal", {})
        category = None
        if data.get("integration") == "virustotal":
            if "error" in vt:
                category = "vt_error"
            elif vt.get("found") == "0":
                category = "vt_not_found"
            elif vt.get("found") == "1":
                category = "vt_found"
        elif data.get("integration") == "misp_file_hashes":
            category = "misp"
        if category and category not in samples:
            samples[category] = raw
            locations[category] = location
        if len(samples) == 4:
            break
    assert set(samples) == {"vt_error", "vt_not_found", "vt_found", "misp"}
    # Include available parent alerts so native references are tested as well.
    parent_ids = set()
    for raw in samples.values():
        data = raw["data"]
        parent = data[data["integration"]].get("source", {}).get("alert_id")
        if isinstance(parent, str):
            parent_ids.add(parent)
    parents = []
    for raw, _ in iter_wazuh_records(path):
        if raw.get("id") in parent_ids:
            parents.append(raw)
            parent_ids.remove(raw["id"])
        if not parent_ids:
            break
    mapped = check_pipeline(parents + list(samples.values()), tmp_path)
    assert len(mapped.case.enrichments) == 3
    assert any(w["code"] == "no_supported_observable" for w in mapped.warnings)
    # Output only source locations/counts, never customer alert contents.
    print(
        {
            "sample_locations": locations,
            "parent_alerts": len(parents),
            "enrichments": len(mapped.case.enrichments),
            "warning_codes": [w["code"] for w in mapped.warnings],
        }
    )
