"""Check shipped examples against the original schema and the intake API."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["elastic", "wazuh", "mixed"])
def test_specification_examples_match_schema_and_backend(client, application, name):
    schema = json.loads(
        (ROOT / "docs/incident-case-input-v1.0.schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    payload = json.loads((ROOT / f"examples/{name}.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201, response.text
    saved = application.state.case_service.store.get(payload["case_id"])
    assert saved.submitted_case.model_dump(exclude_unset=True) == payload


def test_shipped_invalid_example_has_actionable_error(client, id_factory):
    payload = json.loads((ROOT / "examples/invalid_missing_case_id.json").read_text())
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "rule": "VR-03",
                "loc": ["body", "case_id"],
                "msg": "Field required",
                "type": "missing",
            }
        ]
    }
    id_factory.assert_not_called()
