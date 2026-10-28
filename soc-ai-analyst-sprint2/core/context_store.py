"""
Consultas de solo lectura al almacén de contexto: IoC pre-enriquecidos y casos anonimizados.

Contrato (S4-US3-T03):
- La base SQLite se abre con mode=ro; ninguna consulta escribe ni crea el archivo.
- No se hace enriquecimiento: solo se lee lo que ya está almacenado.
- Cada IoC conserva proveedor, veredicto y resultado crudos, y su referencia de origen.
- La base y sus datos sintéticos los crea el prototipo de S4-US3-T04 con SCHEMA.
"""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA = """
CREATE TABLE iocs (
    record_id TEXT PRIMARY KEY,
    observable_type TEXT NOT NULL,
    observable_value TEXT NOT NULL,
    provider TEXT NOT NULL,
    raw_verdict TEXT,
    raw_result TEXT,
    source_ref TEXT NOT NULL,
    enriched_at TEXT
);
CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    source_ref TEXT NOT NULL
);
CREATE TABLE case_iocs (
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    record_id TEXT NOT NULL REFERENCES iocs(record_id),
    PRIMARY KEY (case_id, record_id)
);
"""

# Bounds the payload sent back through MCP; a broader search needs pagination.
MAX_RECORDS = 100
IOC_COLUMNS = ("i.record_id, i.observable_type, i.observable_value, i.provider, "
               "i.raw_verdict, i.raw_result, i.source_ref, i.enriched_at")


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)


def _raw(value: Optional[str]) -> Any:
    try:
        return json.loads(value) if value else None
    except ValueError:
        return value


def _ioc(row: tuple, store: str) -> Dict[str, Any]:
    record_id, kind, value, provider, verdict, raw, source_ref, enriched_at = row
    return {"record_id": record_id, "observable": {"type": kind, "value": value},
            "provider": provider, "raw_verdict": verdict, "raw_result": _raw(raw),
            "enriched_at": enriched_at,
            "source": {"store": store, "table": "iocs", "record_id": record_id, "source_ref": source_ref}}


def _query(path: Path, run) -> Dict[str, Any]:
    if not Path(path).is_file():
        return {"status": "unavailable", "error": "Context database not found"}
    try:
        with closing(connect(path)) as connection:
            return run(connection, Path(path).name)
    except sqlite3.Error as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}


def lookup_iocs(path: Path, value: str, observable_type: Optional[str] = None) -> Dict[str, Any]:
    # shortcut: exact value match; add normalization (case, defang) if real data needs it.
    def run(connection, store):
        sql = f"SELECT {IOC_COLUMNS} FROM iocs i WHERE i.observable_value = ?"
        params = [value]
        if observable_type:
            sql += " AND i.observable_type = ?"
            params.append(observable_type)
        rows = connection.execute(sql + " ORDER BY i.record_id LIMIT ?", (*params, MAX_RECORDS)).fetchall()
        return {"status": "ok", "iocs": [_ioc(row, store) for row in rows]}
    return _query(path, run)


def lookup_case(path: Path, case_id: str) -> Dict[str, Any]:
    def run(connection, store):
        case = connection.execute(
            "SELECT case_id, title, summary, source_ref FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if case is None:
            return {"status": "not_found", "case": None, "iocs": []}
        rows = connection.execute(
            f"SELECT {IOC_COLUMNS} FROM iocs i JOIN case_iocs c ON c.record_id = i.record_id "
            "WHERE c.case_id = ? ORDER BY i.record_id LIMIT ?", (case_id, MAX_RECORDS)).fetchall()
        return {"status": "ok",
                "case": {"case_id": case[0], "title": case[1], "summary": case[2],
                         "source": {"store": store, "table": "cases", "record_id": case[0],
                                    "source_ref": case[3]}},
                "iocs": [_ioc(row, store) for row in rows]}
    return _query(path, run)
