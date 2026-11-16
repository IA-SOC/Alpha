import json
from copy import deepcopy
from uuid import UUID

import pytest

from app.services.export_redaction import REDACTED, redact_export
from tests.test_correlation_engine import case_for, event


@pytest.mark.parametrize(
    "field",
    [
        "password",
        "client_secret",
        "apiKey",
        "http.request.headers.Authorization",
        "Cookie",
        "Set-Cookie",
        "credentials",
        "private_key",
        "refresh-token",
    ],
)
def test_nested_restricted_fields_and_copies(field):
    original = {
        "alerts": [{field: "synthetic-secret-151"}],
        "notes": "Copied synthetic-secret-151",
        "confidence": "low",
    }
    before = deepcopy(original)
    exported = redact_export(original)
    assert "synthetic-secret-151" not in json.dumps(exported)
    assert exported["alerts"][0][field] == REDACTED
    assert exported["confidence"] == "low"
    assert original == before


@pytest.mark.parametrize(
    "field", ["apiToken", "api_token", "clientToken", "bearerToken", "dbPassword"]
)
def test_suffix_restricted_fields(field):
    result = redact_export(
        {"data": {field: "synthetic-secret-176"}, "confidence": "high"}
    )
    assert result["data"][field] == REDACTED
    assert result["confidence"] == "high"
    assert redact_export({"terminalSessionId": "safe"})["terminalSessionId"] == "safe"


def test_short_restricted_secret_does_not_corrupt_copied_text():
    result = redact_export({"x": {"password": "a"}, "msg": "a cat sat"})
    assert result == {"x": {"password": REDACTED}, "msg": "a cat sat"}


def test_long_restricted_secret_redacts_copies_without_corrupting_short_text():
    result = redact_export(
        {"data": {"apiToken": "abcd1234secret", "note": "pwd=ab then abc"}}
    )
    assert "abcd1234secret" not in json.dumps(result)
    assert result["data"]["note"] == "pwd=" + REDACTED + " then abc"


@pytest.mark.parametrize(
    "text",
    [
        "password=synthetic-secret-151",
        "api_key='synthetic-secret-151'",
        "Bearer synthetic-secret-151",
        "Basic synthetic-secret-151",
        "https://user:synthetic-secret-151@example.org/path",
        "-----BEGIN RSA PRIVATE KEY-----\nsynthetic-secret-151\n"
        "-----END RSA PRIVATE KEY-----",
        '{"password": "synthetic-secret-151"}',
    ],
)
def test_credentials_in_free_text(text):
    assert "synthetic-secret-151" not in redact_export({"notes": text})["notes"]


def test_evidence_pointer_value_is_redacted():
    original = {
        "source_fields": [{"pointer": "/raw_alert/password", "value": "secret-151"}]
    }
    result = redact_export(original)
    assert result["source_fields"][0] == {
        "pointer": "/raw_alert/password",
        "value": REDACTED,
    }


def test_export_redacts_stored_legacy_result_without_changing_storage(
    client, application
):
    payload = case_for(event("a")).model_dump(exclude_unset=True)
    payload["alerts"][0]["raw_alert"]["password"] = "secret-151"
    cid = client.post("/api/v1/cases", json=payload).json()["case_id"]
    result = {
        "case_id": cid,
        "report": {"review": {"status": "validated", "notes": "secret-151"}},
        "investigation_context": {"original_case": payload},
        "report_markdown": "Copied credential secret-151",
    }
    store = application.state.investigation_service.store
    store.save_investigation(UUID(cid), result)
    for _ in range(2):
        response = client.get(f"/api/v1/cases/{cid}/export")
        assert response.status_code == 200
        assert "secret-151" not in response.text
        assert response.json()["report"]["review"]["status"] == "validated"
        assert "attachment" in response.headers["content-disposition"]
    assert store.get_investigation(UUID(cid)) == result
    assert client.get(f"/api/v1/cases/{cid}").json()["submitted_case"] == payload
