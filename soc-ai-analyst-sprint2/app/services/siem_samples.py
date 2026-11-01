"""Local sample-only Elastic/Wazuh adapter; no HTTP clients or credentials."""

import argparse
import json
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.schemas.case import IncidentCase
from app.services.case_service import native_identifier
from app.services.wazuh_enrichment import build_wazuh_case


@dataclass
class SampleMapping:
    case: IncidentCase
    records: list[dict]
    sources: list[dict]
    warnings: list[dict]


def _offset_path(value, offset):
    if isinstance(value, str) and value.startswith("/alerts/"):
        parts = value.split("/")
        parts[2] = str(int(parts[2]) + offset)
        return "/".join(parts)
    return value


def _offset_fields(items, offset):
    return [
        {
            key: _offset_path(value, offset)
            if key == "path" or key.endswith("_path")
            else value
            for key, value in item.items()
        }
        for item in items
    ]


def build_sample_case(
    *,
    case_id: str,
    submitted_at: str,
    elastic_alerts: list[dict] | None = None,
    wazuh_alerts: list[dict] | None = None,
) -> SampleMapping:
    """Wrap unchanged samples using the backend's active native-ID profile.

    Elastic precedes Wazuh; order within each input is retained. Wazuh provider
    mapping is delegated in one batch so selected parent references survive.
    Case metadata is caller-supplied, never inferred from an event timestamp.
    """
    elastic = [] if elastic_alerts is None else elastic_alerts
    wazuh = [] if wazuh_alerts is None else wazuh_alerts
    if not isinstance(elastic, list) or not isinstance(wazuh, list):
        raise ValueError("Samples must be JSON arrays")
    if len(elastic) + len(wazuh) > settings.max_alerts_per_case:
        raise ValueError("Combined selection exceeds MAX_ALERTS_PER_CASE")
    alerts = []
    for index, raw in enumerate(elastic):
        aid = native_identifier(raw, settings.elastic_alert_id_pointer)
        if not isinstance(raw, dict) or not isinstance(aid, str) or not aid.strip():
            raise ValueError(
                f"Elastic sample {index} requires the configured string ID"
            )
        alerts.append(
            {"alert_id": aid, "source_system": "elastic", "raw_alert": deepcopy(raw)}
        )
    offset = len(alerts)
    sources, warnings = [], []
    if wazuh:
        mapped = build_wazuh_case(wazuh, case_id=case_id, submitted_at=submitted_at)
        for alert in mapped.case.alerts:
            if (
                native_identifier(alert.raw_alert, settings.wazuh_alert_id_pointer)
                != alert.alert_id
            ):
                raise ValueError(
                    "Wazuh sample id conflicts with the backend ID profile"
                )
            alerts.append(alert.model_dump(exclude_unset=True))
        sources = _offset_fields(mapped.sources, offset)
        warnings = _offset_fields(mapped.warnings, offset)
        enrichments = [
            item.model_dump(exclude_unset=True) for item in mapped.case.enrichments
        ]
    else:
        enrichments = []
    ids = [alert["alert_id"] for alert in alerts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate native IDs across the combined selection")
    case = IncidentCase.model_validate(
        {
            "schema_version": "1.0",
            "case_id": case_id,
            "submitted_at": submitted_at,
            "alerts": alerts,
            "enrichments": enrichments,
        }
    )
    records = [
        {
            "source_system": alert.source_system,
            "sample_path": f"/{index if index < offset else index - offset}",
            "case_path": f"/alerts/{index}/raw_alert",
            "id_pointer": (
                settings.elastic_alert_id_pointer
                if alert.source_system == "elastic"
                else settings.wazuh_alert_id_pointer
            ),
        }
        for index, alert in enumerate(case.alerts)
    ]
    return SampleMapping(case, records, sources, warnings)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Non-finite numbers are not JSON")


def load_samples(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(
            stream, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("Sample file must contain an array of alert objects")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elastic", type=Path)
    parser.add_argument("--wazuh", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--submitted-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.elastic and not args.wazuh:
        parser.error("Provide at least one local sample file")
    audit_path = args.output.with_suffix(args.output.suffix + ".mapping.json")
    if args.output.exists() or audit_path.exists():
        parser.error("Output or sidecar exists; choose a new output")
    try:
        mapped = build_sample_case(
            case_id=args.case_id,
            submitted_at=args.submitted_at,
            elastic_alerts=load_samples(args.elastic) if args.elastic else [],
            wazuh_alerts=load_samples(args.wazuh) if args.wazuh else [],
        )
    except (ValueError, OSError) as exc:
        # Pydantic/JSON exceptions can contain raw input; emit no sample contents.
        parser.error(
            f"Invalid sample or metadata ({type(exc).__name__}); no output written"
        )
    audit = {
        "profile": "siem-samples-v1",
        "inputs": {
            key: str(path)
            for key, path in (("elastic", args.elastic), ("wazuh", args.wazuh))
            if path is not None
        },
        "records": mapped.records,
        "sources": mapped.sources,
        "warnings": mapped.warnings,
    }
    created = []
    try:
        with ExitStack() as stack:
            case_stream = stack.enter_context(args.output.open("x", encoding="utf-8"))
            created.append(args.output)
            audit_stream = stack.enter_context(audit_path.open("x", encoding="utf-8"))
            created.append(audit_path)
            case_stream.write(mapped.case.model_dump_json(exclude_unset=True, indent=2))
            json.dump(
                audit, audit_stream, ensure_ascii=False, indent=2, allow_nan=False
            )
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        parser.error("Cannot write output pair; no case is ready for submission")
    print(f"Mapped {len(mapped.case.alerts)} alerts; review the mapping sidecar.")


if __name__ == "__main__":
    main()
