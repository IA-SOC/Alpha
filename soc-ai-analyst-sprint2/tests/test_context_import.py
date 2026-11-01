import json

import pytest

from app.services.context_import import import_context
from core import context_store


def write_inputs(tmp_path):
    iocs = tmp_path / "iocs.json"
    cases = tmp_path / "cases.json"
    iocs.write_text(
        json.dumps(
            {
                "iocs": [
                    {
                        "record_id": "ioc-1",
                        "observable": {"type": "ip", "value": "203.0.113.10"},
                        "provider": "synthetic-provider",
                        "raw_verdict": "not found",
                        "raw_result": {"error": "provider unavailable"},
                        "source_ref": "input/iocs.json#0",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cases.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case-1",
                        "title": "Synthetic case",
                        "summary": "Anonymized",
                        "source_ref": "input/cases.json#0",
                        "ioc_record_ids": ["ioc-1"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return iocs, cases


def test_import_matches_read_only_mcp_schema_and_preserves_sources(tmp_path):
    iocs, cases = write_inputs(tmp_path)
    database = tmp_path / "context.sqlite3"

    assert import_context(database, iocs_file=iocs, cases_file=cases) == {
        "iocs": 1,
        "cases": 1,
        "case_iocs": 1,
    }
    assert context_store.lookup_case(database, "case-1")["iocs"][0]["raw_verdict"] == (
        "not found"
    )
    assert context_store.lookup_case(database, "case-1")["case"]["source"][
        "source_ref"
    ] == "input/cases.json#0"


def test_import_validates_before_writing(tmp_path):
    iocs, cases = write_inputs(tmp_path)
    cases.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case-1",
                        "source_ref": "input/cases.json#0",
                        "ioc_record_ids": ["missing"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown IoC"):
        import_context(tmp_path / "context.sqlite3", iocs_file=iocs, cases_file=cases)
    assert not (tmp_path / "context.sqlite3").exists()


def test_import_rejects_duplicate_ids_without_partial_write(tmp_path):
    iocs, cases = write_inputs(tmp_path)
    payload = json.loads(iocs.read_text(encoding="utf-8"))
    payload["iocs"].append(payload["iocs"][0])
    iocs.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate IoC"):
        import_context(tmp_path / "context.sqlite3", iocs_file=iocs, cases_file=cases)
    assert not (tmp_path / "context.sqlite3").exists()
