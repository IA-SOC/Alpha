
import argparse
import gzip
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from app.services.wazuh_enrichment import build_wazuh_case


def prepare(source: Path, output: Path):

    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "profile": "client-wazuh-v1",
        "days": [],
        "total": 0,
        "limitations": [
            "Unlabelled alerts; no incident accuracy score.",
            "Pseudonymous public IPs cannot support IP reputation.",
            "Samples are compatibility cases, not proven attacks.",
        ],
    }
    with zipfile.ZipFile(source) as archive:
        sums_name = next(n for n in archive.namelist() if n.endswith("/SHA256SUMS"))
        expected = {}
        for line in archive.read(sums_name).decode().splitlines():
            digest, name = line.split(maxsplit=1)
            expected[Path(name.lstrip("*")).name] = digest
        for name in sorted(n for n in archive.namelist() if n.endswith(".json.gz")):
            sha = hashlib.sha256()
            with archive.open(name) as raw:
                for chunk in iter(lambda: raw.read(1024 * 1024), b""):
                    sha.update(chunk)
            if sha.hexdigest() != expected.get(Path(name).name):
                raise ValueError(f"Checksum mismatch: {name}")
            levels, decoders = Counter(), Counter()
            samples, locations, seen_decoders = [], [], set()
            count = 0
            with (
                archive.open(name) as raw,
                gzip.open(raw, "rt", encoding="utf-8") as stream,
            ):
                for line_no, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                        raise ValueError(f"Invalid alert: {name}:{line_no}")
                    count += 1
                    decoder = row.get("decoder", {}).get("name", "(missing)")
                    levels[str(row.get("rule", {}).get("level"))] += 1
                    decoders[decoder] += 1

                    if decoder not in seen_decoders and len(samples) < 12:
                        seen_decoders.add(decoder)
                        samples.append(row)
                        locations.append(
                            {"member": name, "line": line_no, "alert_id": row["id"]}
                        )
            day = Path(name).name.removeprefix("ossec-alerts-").split(".")[0]
            mapped = build_wazuh_case(
                samples,
                case_id=f"aligo-2026-08-{day}-compat",
                submitted_at="2026-10-27T00:00:00Z",
            )
            case_name = f"client-day-{day}.json"
            (output / case_name).write_text(
                mapped.case.model_dump_json(exclude_unset=True, indent=2),
                encoding="utf-8",
            )
            mapping = {
                "source_sha256": sha.hexdigest(),
                "records": locations,
                "sources": mapped.sources,
                "warnings": mapped.warnings,
            }
            (output / f"{case_name}.mapping.json").write_text(
                json.dumps(mapping, indent=2), encoding="utf-8"
            )
            summary["days"].append(
                {
                    "member": name,
                    "count": count,
                    "sha256_ok": True,
                    "levels": dict(levels),
                    "decoders": dict(decoders),
                    "sample_case": case_name,
                    "sample_size": len(samples),
                }
            )
            summary["total"] += count
            print(f"{Path(name).name}: {count} valid records, checksum OK", flush=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
