"""Adapt accepted records only; intake validation stays in the original service."""

import re
from copy import deepcopy

from pydantic import ValidationError

from app.schemas.case import IncidentCase
from app.services.correlation import correlate
from app.services.evidence import SIGNAL_PATHS, extract_events, read_field
from app.services.ioc_integration import integrate_iocs
from app.storage.case_store import AcceptedCase


def _unwrap_pointers(value):
    """/alerts/i/raw_alert/... -> /alerts/i/...: the direct case has no wrapper."""
    if isinstance(value, dict):
        return {
            k: (
                re.sub(r"^(/alerts/\d+)/raw_alert(?=/|$)", r"\1", v)
                if k == "path" and isinstance(v, str)
                else _unwrap_pointers(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_unwrap_pointers(v) for v in value]
    return value


def correlate_direct(case: dict, alerts: list[dict], window_seconds: int = 300):
    """Correlate a case that did not come through intake, or None if it can't be.

    Alerts are wrapped in the v1.0 contract only to reuse the correlation
    engine; evidence pointers are rewritten to point into the case as given.
    """
    raw_alerts = case.get("alerts")
    ids = [a["id"] for a in alerts]
    if (
        not isinstance(raw_alerts, list)
        or len(raw_alerts) != len(alerts)
        or len(set(ids)) != len(ids)
    ):
        return None
    try:
        wrapped = IncidentCase.model_validate(
            {
                "schema_version": "1.0",
                "case_id": str(case.get("case_id") or "direct"),
                # Required by the contract; correlation never uses it as event time.
                "submitted_at": "1970-01-01T00:00:00Z",
                "alerts": [
                    {
                        "alert_id": a["id"],
                        "source_system": (
                            "wazuh" if a["source_format"] == "wazuh" else "elastic"
                        ),
                        "raw_alert": a["raw"],
                    }
                    for a in alerts
                ],
            }
        )
    except ValidationError:
        return None
    result = correlate(extract_events(wrapped), window_seconds).model_dump()
    return _unwrap_pointers(result)


def adapt_case(accepted: AcceptedCase, window_seconds: int = 300) -> dict:
    case = accepted.submitted_case
    events = extract_events(case)
    correlation = correlate(events, window_seconds)
    iocs = integrate_iocs(case, events)
    alerts, signal_evidence = [], {}
    for index, wrapper in enumerate(case.alerts):
        raw = wrapper.raw_alert
        # Export metadata and any collisions remain intact in original_case.
        view = deepcopy(
            raw.get("_source") if isinstance(raw.get("_source"), dict) else raw
        )
        view["alert_id"] = wrapper.alert_id
        alerts.append(view)
        fields = []
        for path in SIGNAL_PATHS:
            for pointer, value in read_field(raw, path, f"/alerts/{index}/raw_alert"):
                if isinstance(value, str) or isinstance(value, list):
                    fields.append(
                        {
                            "alert_id": wrapper.alert_id,
                            "path": pointer,
                            "value": deepcopy(value),
                        }
                    )
        signal_evidence[wrapper.alert_id] = fields
    context = {
        "adapter_version": "backend-v1",
        "case_id": str(accepted.case_id),
        "submitted_case_id": case.case_id,
        "original_case": case.model_dump(exclude_unset=True),
        "events": [e.model_dump() for e in events],
        "signal_evidence": signal_evidence,
        "correlation": correlation.model_dump(),
        "ioc_evidence": iocs,
    }
    return {
        "case_id": str(accepted.case_id),
        "submitted_case_id": case.case_id,
        "schema_version": case.schema_version,
        "alerts": alerts,
        "enrichment": deepcopy(iocs),
        "investigation_context": context,
    }
