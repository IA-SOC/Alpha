"""Explicit SIEM export adapter; does not change the v1.0 intake contract."""

import re
from copy import deepcopy
from dataclasses import dataclass

from app.schemas.case import IncidentCase

HASH_LENGTHS = {"sha256": 64, "sha1": 40, "md5": 32}


@dataclass
class WazuhMapping:
    case: IncidentCase
    sources: list[dict]
    warnings: list[dict]


def _hash(kind, value):
    return (
        isinstance(kind, str)
        and kind in HASH_LENGTHS
        and isinstance(value, str)
        and re.fullmatch(r"[a-fA-F0-9]{%d}" % HASH_LENGTHS[kind], value) is not None
    )


def build_wazuh_case(
    raw_alerts: list[dict], *, case_id: str, submitted_at: str
) -> WazuhMapping:
    """Map selected Wazuh alerts and embedded VT/MISP data without enrichment calls.

    raw_result is the complete provider object. sources is a sidecar mapping of
    its original location, not extra fields in the frozen input contract.
    Unsupported/error-only results remain in raw_alert and produce diagnostics.
    """
    alerts = []
    seen = set()
    for raw in raw_alerts:
        aid = raw.get("id") if isinstance(raw, dict) else None
        if not isinstance(aid, str) or not aid.strip():
            raise ValueError("Each Wazuh alert requires a nonblank string id")
        if aid in seen:
            raise ValueError("Duplicate Wazuh alert id in selection")
        seen.add(aid)
        alerts.append(
            {"alert_id": aid, "source_system": "wazuh", "raw_alert": deepcopy(raw)}
        )
    # Validate case size and metadata before doing any mapping.
    case = IncidentCase.model_validate(
        {
            "schema_version": "1.0",
            "case_id": case_id,
            "submitted_at": submitted_at,
            "alerts": alerts,
        }
    )
    enrichments, sources, warnings = [], [], []
    for index, alert in enumerate(case.alerts):
        data = alert.raw_alert.get("data")
        if not isinstance(data, dict):
            continue
        integration = data.get("integration")
        if integration not in ("virustotal", "misp_file_hashes"):
            continue
        base = f"/alerts/{index}/raw_alert/data/{integration}"

        def warn(code):
            warnings.append({"alert_id": alert.alert_id, "code": code, "path": base})

        result = data.get(integration)
        if not isinstance(result, dict):
            warn("invalid_provider_object")
            continue
        source = result.get("source")
        source = source if isinstance(source, dict) else {}
        if integration == "virustotal":
            candidates = [(k, source.get(k)) for k in HASH_LENGTHS]
            observable = next(((k, v) for k, v in candidates if _hash(k, v)), None)
            value_path = f"{base}/source/{observable[0]}" if observable else None
        else:
            kind, value = result.get("type"), result.get("value")
            observable = (kind, value) if _hash(kind, value) else None
            value_path = f"{base}/value"
        if observable is None:
            warn("no_supported_observable")
            continue
        # Containment is an explicit association, never an observable match.
        related = [alert.alert_id]
        parent = source.get("alert_id")
        if isinstance(parent, str) and parent in seen:
            if parent not in related:
                related.append(parent)
        elif parent is not None:
            warn("source_alert_not_in_case")
        position = len(enrichments)
        enrichments.append(
            {
                "provider": "virustotal" if integration == "virustotal" else "misp",
                "observable": {"type": observable[0], "value": observable[1]},
                "related_alert_ids": related,
                "raw_result": deepcopy(result),
            }
        )
        sources.append(
            {
                "enrichment_path": f"/enrichments/{position}",
                "raw_result_path": base,
                "observable_value_path": value_path,
                "provider_path": f"/alerts/{index}/raw_alert/data/integration",
            }
        )
    payload = case.model_dump(exclude_unset=True)
    payload["enrichments"] = enrichments
    return WazuhMapping(IncidentCase.model_validate(payload), sources, warnings)
