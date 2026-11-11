"""Prepare reproducible, stratified Wazuh coverage cases from local exports."""

import argparse
import hashlib
import heapq
import json
import os
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.services.wazuh_enrichment import build_wazuh_case
from app.services.wazuh_import import iter_wazuh_records

PROFILE = "wazuh-representative-cases-v1"
FIELDS = {
    "decoder": "decoder.name",
    "rule_id": "rule.id",
    "level": "rule.level",
    "channel": "data.win.system.channel",
    "event_id": "data.win.system.eventID",
    "integration": "data.integration",
    "vt_found": "data.virustotal.found",
    "vt_error": "data.virustotal.error",
    "misp_found": "data.misp_file_hashes.found",
    "misp_error": "data.misp_file_hashes.error",
    "file_event": "syscheck.event",
}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def _source_integrity(source):
    with source.open("rb") as stream:
        fingerprint = _digest(stream)
    verified = []
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("ZIP contains duplicate member names")
            for sums in sorted(n for n in names if Path(n).name == "SHA256SUMS"):
                parent = sums.rpartition("/")[0]
                for line in archive.read(sums).decode("utf-8").splitlines():
                    if not line.strip():
                        continue
                    digest, filename = line.split(maxsplit=1)
                    member = "/".join(filter(None, [parent, filename.lstrip("*")]))
                    with archive.open(member) as stream:
                        actual = _digest(stream)
                    if actual != digest.lower():
                        raise ValueError(f"Checksum mismatch for {member}")
                    verified.append({"member": member, "sha256": actual})
    return {"name": source.name, "sha256": fingerprint, "verified_members": verified}


def _stratum(record):
    """Use the timestamp's stated local date; retain undated alerts explicitly."""
    try:
        timestamp = datetime.fromisoformat(record.get("timestamp", ""))
        day = timestamp.date().isoformat() if timestamp.tzinfo else "undated"
    except (ValueError, TypeError):
        day = "undated"
    fields = {"day": day}
    for name, path in FIELDS.items():
        value = record
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        # Structured provider errors contribute their presence, not free text.
        if name.endswith("_error"):
            value = value is not None
        fields[name] = value
    return fields


def prepare_cases(
    source: Path,
    output: Path,
    *,
    submitted_at: str,
    samples_per_stratum: int = 2,
    max_alerts: int = 50,
    seed: str = "0",
):
    """Scan the complete source and publish cases plus provenance atomically."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if not 1 <= max_alerts <= min(50, settings.max_alerts_per_case):
        raise ValueError("max_alerts must be 1..50 and within MAX_ALERTS_PER_CASE")
    if samples_per_stratum < 1:
        raise ValueError("samples_per_stratum must be positive")
    if output.exists():
        raise FileExistsError("Output already exists; choose a new directory")
    before = source.stat()
    integrity = _source_integrity(source)
    counts, members = Counter(), Counter()
    samples = defaultdict(list)
    total = 0
    for record, location in iter_wazuh_records(source):
        aid = record.get("id")
        if not isinstance(aid, str) or not aid.strip():
            raise ValueError(f"Missing string alert id at {_json(location)}")
        key = _json(_stratum(record))
        rank = int(
            hashlib.sha256(_json([seed, location, aid]).encode()).hexdigest(), 16
        )
        # Keep the k smallest hashes for each stratum, independent of scan order.
        item = (-rank, location["member"], location["line"], record)
        heap = samples[key]
        if len(heap) < samples_per_stratum:
            heapq.heappush(heap, item)
        elif item[:3] > heap[0][:3]:
            heapq.heapreplace(heap, item)
        counts[key] += 1
        members[location["member"]] += 1
        total += 1
        if total % 100000 == 0:
            print(f"Scanned {total} alerts across {len(counts)} strata", flush=True)
    if not total:
        raise ValueError("Input contains no Wazuh records")
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed during preparation; retry with a stable input")

    days = defaultdict(list)
    strata = []
    selected_ids = set()
    for key in sorted(samples):
        fields = json.loads(key)
        stratum_id = hashlib.sha256(key.encode()).hexdigest()
        strata.append(
            {
                "id": stratum_id,
                "criteria": fields,
                "population": counts[key],
                "selected": len(samples[key]),
            }
        )
        for rank, member, line, record in sorted(samples[key], reverse=True):
            if record["id"] in selected_ids:
                raise ValueError(
                    "Selected native alert IDs repeat; disambiguate the source"
                )
            selected_ids.add(record["id"])
            days[fields["day"]].append(
                (
                    record,
                    {
                        "member": member,
                        "line": line,
                        "alert_id": record["id"],
                        "stratum_id": stratum_id,
                        "selection_hash": f"{-rank:064x}",
                    },
                )
            )
    policy = {
        "profile": PROFILE,
        "seed": seed,
        "samples_per_stratum": samples_per_stratum,
        "max_alerts": max_alerts,
        "stratification": {
            "day": "timestamp local date with explicit timezone",
            **FIELDS,
        },
        "selection": "Smallest SHA256 of JSON [seed, source location, native alert id]",
        "packing": (
            "Sorted strata and selection hashes within each date; split at max_alerts"
        ),
    }
    identity = hashlib.sha256(
        _json([integrity["sha256"], policy]).encode()
    ).hexdigest()[:20]
    manifest = {
        **policy,
        "source": integrity,
        "submitted_at": submitted_at,
        "scanned": total,
        "selected": len(selected_ids),
        "members": dict(sorted(members.items())),
        "strata": strata,
        "cases": [],
        "limitations": [
            "Coverage sampling changes the frequencies of the source population.",
            "Grouping does not establish a related incident or a known attack outcome.",
            "Source anonymization and confidentiality restrictions still apply.",
            "Missing or invalid timezone-aware timestamps are grouped as undated.",
            "Provider source alerts outside the sample remain mapping warnings.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".wazuh-cases-", dir=output.parent) as temp:
        stage = Path(temp) / "cases"
        stage.mkdir()
        for day, records in sorted(days.items()):
            for offset in range(0, len(records), max_alerts):
                batch = records[offset : offset + max_alerts]
                case_id = f"wazuh-{identity}-{day}-{offset // max_alerts + 1:04d}"
                mapped = build_wazuh_case(
                    [raw for raw, _ in batch],
                    case_id=case_id,
                    submitted_at=submitted_at,
                )
                filename = f"{case_id}.json"
                (stage / filename).write_text(
                    mapped.case.model_dump_json(exclude_unset=True, indent=2),
                    encoding="utf-8",
                )
                mapping = {
                    "profile": PROFILE,
                    "source_sha256": integrity["sha256"],
                    "records": [
                        {**location, "case_pointer": f"/alerts/{i}/raw_alert"}
                        for i, (_, location) in enumerate(batch)
                    ],
                    "sources": mapped.sources,
                    "warnings": mapped.warnings,
                }
                (stage / f"{filename}.mapping.json").write_text(
                    json.dumps(mapping, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                manifest["cases"].append(
                    {
                        "file": filename,
                        "mapping": f"{filename}.mapping.json",
                        "day": day,
                        "alert_count": len(batch),
                        "enrichment_count": len(mapped.sources),
                        "warning_count": len(mapped.warnings),
                    }
                )
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # A failed scan or mapping never publishes a partially prepared dataset.
        if output.exists():
            raise FileExistsError("Output was created by another process")
        os.rename(stage, output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--submitted-at", required=True)
    parser.add_argument("--samples-per-stratum", type=int, default=2)
    parser.add_argument("--max-alerts", type=int, default=50)
    parser.add_argument("--seed", default="0")
    args = parser.parse_args()
    try:
        manifest = prepare_cases(
            args.input,
            args.output,
            submitted_at=args.submitted_at,
            samples_per_stratum=args.samples_per_stratum,
            max_alerts=args.max_alerts,
            seed=args.seed,
        )
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(
        f"Prepared {len(manifest['cases'])} cases with {manifest['selected']} alerts "
        f"from {manifest['scanned']} records. See manifest.json."
    )


if __name__ == "__main__":
    main()
