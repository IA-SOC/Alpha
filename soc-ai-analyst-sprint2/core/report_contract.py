"""Shared structural validation and lossless JSON serialization for reports.

The skill validator additionally resolves case references; backend traceability
checks original values and pointers. Neither check proves an inference true.
"""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills/soc-case-investigator/references/report-schema.json"
)
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
SCHEMA_ID = SCHEMA["$id"]
_VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def report_errors(report: Any) -> list[str]:
    """Return schema errors with JSON paths, including confidence requirements."""
    return [
        f"{error.json_path}: {error.message}"
        for error in _VALIDATOR.iter_errors(report)
    ]


def validate_report(report: Any) -> None:
    errors = report_errors(report)
    if errors:
        raise ValueError("Report contract validation failed: " + "; ".join(errors))


def serialize_report(report: dict) -> str:
    """Validate before emitting strict JSON; retain all evidence and extensions."""
    validate_report(report)
    return json.dumps(report, ensure_ascii=False, allow_nan=False)
