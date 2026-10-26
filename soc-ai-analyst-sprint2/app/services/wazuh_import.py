"""Local, explicit selection from NDJSON/gzip/ZIP; no SIEM or provider access."""

import argparse
import gzip
import json
import zipfile
from pathlib import Path

from app.core.config import settings
from app.services.wazuh_enrichment import build_wazuh_case


def _records(stream, member):
    for number, line in enumerate(stream, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Invalid JSON in {member}, line {number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Expected an object in {member}, line {number}")
        yield record, {"member": member, "line": number}


def iter_wazuh_records(path: Path):
    """Stream archives in place; never extract paths from an untrusted ZIP."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if member.endswith(".json.gz"):
                    with archive.open(member) as compressed:
                        with gzip.open(compressed, "rt", encoding="utf-8") as stream:
                            yield from _records(stream, member)
    else:
        opener = gzip.open if path.suffix.lower() == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as stream:
            yield from _records(stream, path.name)


def select_alerts(path: Path, ids: list[str]):
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Select distinct alert IDs")
    if len(ids) > settings.max_alerts_per_case:
        raise ValueError("Selection exceeds MAX_ALERTS_PER_CASE")
    wanted = set(ids)
    records, locations = [], []
    # Scan the complete input to detect repeated native IDs; do not silently pick.
    for record, location in iter_wazuh_records(path):
        aid = record.get("id")
        if isinstance(aid, str) and aid in wanted:
            records.append(record)
            locations.append(location)
            if sum(r["id"] == aid for r in records) > 1:
                raise ValueError("Selected alert ID occurs more than once in input")
    if {r["id"] for r in records} != wanted:
        raise ValueError("Some selected alert IDs were not found")
    return records, locations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--alert-id", action="append", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--submitted-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit_path = args.output.with_suffix(args.output.suffix + ".mapping.json")
    if args.output.exists() or audit_path.exists():
        parser.error("Output or mapping sidecar already exists; choose a new output")
    try:
        alerts, locations = select_alerts(args.input, args.alert_id)
        mapped = build_wazuh_case(
            alerts, case_id=args.case_id, submitted_at=args.submitted_at
        )
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    audit = {
        "profile": "wazuh-siem-vt-misp-v1",
        "input": str(args.input),
        "records": locations,
        "sources": mapped.sources,
        "warnings": mapped.warnings,
    }
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(mapped.case.model_dump_json(exclude_unset=True, indent=2))
    with audit_path.open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, indent=2)
    print(
        f"Mapped {len(alerts)} alerts, {len(mapped.sources)} enrichments, "
        f"{len(mapped.warnings)} warnings. Review the mapping sidecar."
    )


if __name__ == "__main__":
    main()
