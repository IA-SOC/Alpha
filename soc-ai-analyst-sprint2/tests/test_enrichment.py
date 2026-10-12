"""Sprint 2 - Sprint 2 US3: cases with and without enrichment information."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples" / "test_cases"
URL = "/api/v1/cases"


def sample(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def test_case_with_enrichment_is_accepted_and_preserved(client, application):
    payload = sample("with_enrichment.json")
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    stored = application.state.case_service.store.get(payload["case_id"])
    assert stored.submitted_case.enrichments is not None
    enrichment = stored.submitted_case.enrichments[0]
    assert enrichment.provider == "virustotal"
    assert enrichment.related_alert_ids == ["elastic-ioc-001"]
    assert enrichment.raw_result["reputation"] == "malicious"


def test_case_without_enrichment_is_accepted(client, application):
    payload = sample("without_enrichment.json")
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    stored = application.state.case_service.store.get(payload["case_id"])
    assert stored.submitted_case.enrichments is None
