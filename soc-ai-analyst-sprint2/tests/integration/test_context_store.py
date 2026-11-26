import asyncio
import json
import sqlite3
from contextlib import AsyncExitStack, closing

import pytest

from core import context_store
from orchestrator.client import SERVERS, McpToolClient

RAW = {"malicious": 7, "harmless": 60, "vendor_note": "seen in phishing kit"}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "context.sqlite3"
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(context_store.SCHEMA)
        connection.executemany(
            "INSERT INTO iocs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "ioc-1",
                    "ip",
                    "203.0.113.10",
                    "virustotal",
                    "malicious",
                    json.dumps(RAW),
                    "synthetic/export-01.json#0",
                    "2026-10-20T10:00:00Z",
                ),
                (
                    "ioc-2",
                    "ip",
                    "203.0.113.10",
                    "abuseipdb",
                    "84",
                    "not json",
                    "synthetic/export-02.json#3",
                    None,
                ),
                (
                    "ioc-3",
                    "domain",
                    "203.0.113.10",
                    "virustotal",
                    "harmless",
                    None,
                    "synthetic/export-01.json#1",
                    None,
                ),
                (
                    "ioc-4",
                    "domain",
                    "login.example.test",
                    "virustotal",
                    "suspicious",
                    None,
                    "synthetic/export-01.json#2",
                    None,
                ),
            ],
        )
        connection.execute(
            "INSERT INTO cases VALUES (?, ?, ?, ?)",
            ("case-anon-1", "Phishing", "Anonymized summary", "synthetic/cases.json#0"),
        )
        connection.executemany(
            "INSERT INTO case_iocs VALUES (?, ?)",
            [("case-anon-1", "ioc-4"), ("case-anon-1", "ioc-1")],
        )
    return path


def test_lookup_by_observable_preserves_provider_raw_verdict_and_source(db):
    result = context_store.lookup_iocs(db, "203.0.113.10", "ip")
    assert result["status"] == "ok"
    assert [item["record_id"] for item in result["iocs"]] == ["ioc-1", "ioc-2"]
    first, second = result["iocs"]
    assert first["provider"] == "virustotal" and first["raw_verdict"] == "malicious"
    assert first["raw_result"] == RAW
    assert first["source"] == {
        "store": "context.sqlite3",
        "table": "iocs",
        "record_id": "ioc-1",
        "source_ref": "synthetic/export-01.json#0",
    }
    assert second["raw_verdict"] == "84" and second["raw_result"] == "not json"


def test_lookup_without_type_returns_every_type(db):
    result = context_store.lookup_iocs(db, "203.0.113.10")
    assert [item["record_id"] for item in result["iocs"]] == ["ioc-1", "ioc-2", "ioc-3"]
    assert context_store.lookup_iocs(db, "198.51.100.1") == {"status": "ok", "iocs": []}


def test_lookup_by_case_returns_metadata_and_linked_iocs(db):
    result = context_store.lookup_case(db, "case-anon-1")
    assert result["status"] == "ok"
    assert result["case"]["source"]["source_ref"] == "synthetic/cases.json#0"
    assert [item["record_id"] for item in result["iocs"]] == ["ioc-1", "ioc-4"]
    assert context_store.lookup_case(db, "missing") == {
        "status": "not_found",
        "case": None,
        "iocs": [],
    }


def test_connection_is_read_only(db):
    with closing(context_store.connect(db)) as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM iocs")
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM iocs").fetchone()[0] == 4


def test_missing_or_foreign_database_is_unavailable_and_never_created(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    assert context_store.lookup_iocs(missing, "x")["status"] == "unavailable"
    assert not missing.exists()
    other = tmp_path / "other.sqlite3"
    with closing(sqlite3.connect(other)) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER)")
    result = context_store.lookup_case(other, "case-anon-1")
    assert result["status"] == "unavailable" and "no such table" in result["error"]


def test_mcp_server_reads_the_configured_database(db, monkeypatch):
    monkeypatch.setenv("CONTEXT_DB_PATH", str(db))

    async def call():
        async with AsyncExitStack() as stack:
            return await McpToolClient(SERVERS["context"]).call(
                stack,
                "lookup_iocs",
                {"value": "login.example.test", "observable_type": "domain"},
            )

    result = asyncio.run(call())
    assert result["status"] == "ok"
    assert [item["record_id"] for item in result["iocs"]] == ["ioc-4"]
