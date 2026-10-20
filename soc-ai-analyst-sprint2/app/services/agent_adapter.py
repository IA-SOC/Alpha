"""Adapt accepted records only; intake validation stays in the original service."""

from copy import deepcopy

from app.services.correlation import correlate
from app.services.evidence import SIGNAL_PATHS, extract_events, read_field
from app.services.ioc_integration import integrate_iocs
from app.storage.case_store import AcceptedCase


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
