"""Sprint 2 - Sprint 2 US2: related-event and unrelated-noise test data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "test_cases" / "valid_related_with_noise.json"
URL = "/api/v1/cases"


def test_related_and_noise_sample_is_accepted(client, application):
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text

    stored = application.state.case_service.store.get(payload["case_id"])
    alerts = stored.submitted_case.alerts
    assert len(alerts) == 3

    # Two events intentionally share the same IP/user/host and represent the
    # related activity; the third uses a different IP/host and is test noise.
    first, second, noise = [alert.raw_alert for alert in alerts]
    assert first["source"]["ip"] == second["source"]["ip"]
    assert first["user"]["name"] == second["user"]["name"]
    assert first["host"]["name"] == second["host"]["name"]
    assert noise["source"]["ip"] != first["source"]["ip"]
    assert noise["host"]["name"] != first["host"]["name"]
