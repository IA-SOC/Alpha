"""Safe writer for the SQLite context database consumed by the read-only MCP."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from core.context_store import SCHEMA


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _records(value: Any, key: str, path: Path) -> list[dict[str, Any]]:
    records = value.get(key) if isinstance(value, dict) else value
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError(f"{path}: expected an array of {key}")
    return records


def _required_text(record: dict[str, Any], field: str, location: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}.{field}: expected non-empty string")
    return value


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _ioc_rows(records: Iterable[dict[str, Any]], source: Path):
    rows = []
    for index, record in enumerate(records):
        location = f"{source}#ioc[{index}]"
        record_id = _required_text(record, "record_id", location)
        observable = record.get("observable")
        if not isinstance(observable, dict):
            raise ValueError(f"{location}.observable: expected object")
        observable_type = _required_text(observable, "type", location + ".observable")
        observable_value = _required_text(observable, "value", location + ".observable")
        provider = _required_text(record, "provider", location)
        source_ref = record.get("source_ref", location)
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError(f"{location}.source_ref: expected non-empty string")
        rows.append(
            (
                record_id,
                observable_type,
                observable_value,
                provider,
                record.get("raw_verdict"),
                _json_text(record.get("raw_result")),
                source_ref,
                record.get("enriched_at"),
            )
        )
    return rows


def _case_rows(records: Iterable[dict[str, Any]], source: Path):
    cases, links = [], []
    for index, record in enumerate(records):
        location = f"{source}#case[{index}]"
        case_id = _required_text(record, "case_id", location)
        source_ref = record.get("source_ref", location)
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError(f"{location}.source_ref: expected non-empty string")
        cases.append(
            (case_id, record.get("title"), record.get("summary"), source_ref)
        )
        record_ids = record.get("ioc_record_ids", [])
        if not isinstance(record_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in record_ids
        ):
            raise ValueError(f"{location}.ioc_record_ids: expected string array")
        links.extend((case_id, record_id) for record_id in record_ids)
    return cases, links


def import_context(
    database: Path,
    *,
    iocs_file: Path,
    cases_file: Path,
) -> dict[str, int]:
    """Validate both files fully, then atomically create and populate the database."""
    iocs = _records(_load(iocs_file), "iocs", iocs_file)
    cases = _records(_load(cases_file), "cases", cases_file)
    ioc_rows = _ioc_rows(iocs, iocs_file)
    case_rows, links = _case_rows(cases, cases_file)
    ioc_ids = {row[0] for row in ioc_rows}
    case_ids = {row[0] for row in case_rows}
    if len(ioc_ids) != len(ioc_rows):
        raise ValueError("Duplicate IoC record_id")
    if len(case_ids) != len(case_rows):
        raise ValueError("Duplicate case_id")
    if any(record_id not in ioc_ids for _, record_id in links):
        raise ValueError("case_iocs references an unknown IoC record_id")
    if len(set(links)) != len(links):
        raise ValueError("Duplicate case_iocs relationship")

    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        try:
            connection.executemany(
                "INSERT INTO iocs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ioc_rows
            )
            connection.executemany(
                "INSERT INTO cases VALUES (?, ?, ?, ?)", case_rows
            )
            connection.executemany("INSERT INTO case_iocs VALUES (?, ?)", links)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Context database already contains imported IDs: {exc}") from exc
    return {"iocs": len(ioc_rows), "cases": len(case_rows), "case_iocs": len(links)}
