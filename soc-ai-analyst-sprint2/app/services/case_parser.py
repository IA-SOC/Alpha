"""Incident case parsing and structural validation.

Sprint 2 contribution (Sprint 2 / US1).
This module provides a reusable boundary for converting Python dictionaries or
raw JSON into the canonical IncidentCase model. Validation rules remain
centralized in app.schemas.case so API and non-HTTP callers share one contract.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.schemas.case import IncidentCase


class IncidentCaseParser:
    """Parse incident-case input and apply the v1.0 structural contract."""

    @staticmethod
    def parse(payload: dict[str, Any]) -> IncidentCase:
        """Validate a decoded JSON object and return the canonical model."""
        return IncidentCase.model_validate(payload)

    @staticmethod
    def parse_json(payload: str | bytes | bytearray) -> IncidentCase:
        """Decode JSON and validate it as an incident case.

        ``json.JSONDecodeError`` is raised for malformed JSON and
        ``pydantic.ValidationError`` for a well-formed payload that violates
        the incident-case contract.
        """
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            # Reuse Pydantic so callers receive the same structural validation
            # semantics as when a non-object reaches the API boundary.
            return IncidentCase.model_validate(decoded)
        return IncidentCase.model_validate(decoded)


__all__ = ["IncidentCaseParser", "ValidationError"]
