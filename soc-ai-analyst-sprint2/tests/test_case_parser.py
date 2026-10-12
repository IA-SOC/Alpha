"""Sprint 2 - Sprint 2 US1: incident case parser/validator tests."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.case_parser import IncidentCaseParser

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples" / "test_cases"


def load(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def test_parser_accepts_valid_case_with_related_and_noise_events():
    parsed = IncidentCaseParser.parse(load("valid_related_with_noise.json"))
    assert parsed.case_id == "INC-SPRINT2-RELATED-001"
    assert len(parsed.alerts) == 3
    assert parsed.correlation is not None


def test_parser_accepts_raw_json():
    raw = (SAMPLES / "without_enrichment.json").read_text(encoding="utf-8")
    parsed = IncidentCaseParser.parse_json(raw)
    assert parsed.alerts[0].source_system == "wazuh"


def test_parser_rejects_missing_required_alerts():
    with pytest.raises(ValidationError) as error:
        IncidentCaseParser.parse(load("invalid_missing_alerts.json"))
    assert any(item["loc"] == ("alerts",) for item in error.value.errors())


def test_parser_rejects_malformed_json():
    with pytest.raises(json.JSONDecodeError):
        IncidentCaseParser.parse_json('{"schema_version": "1.0"')
