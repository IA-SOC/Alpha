"""Submit the synthetic v1.0 case to a running FastAPI server and verify results.

    python demo/run_pipeline.py --base-url http://127.0.0.1:8000

Uses only the standard library. No SIEM, enrichment provider or LLM is contacted.
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def request(base_url, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=310) as response:
        return response.status, json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "demo" / "output")
    args = parser.parse_args()
    case = json.loads((ROOT / "examples/sprint2_demo.json").read_text(encoding="utf-8"))
    case["case_id"] = "SPRINT2-DEMO-" + uuid4().hex[:12]
    started = time.perf_counter()
    status, accepted = request(args.base_url, "/api/v1/cases", case)
    assert status == 201
    prefix = f"/api/v1/cases/{accepted['case_id']}"
    status, result = request(args.base_url, prefix + "/investigate", {})
    assert status == 200
    assert result["status"] == "pending_review"
    assert result["validation"]["ok"] and result["validation"]["traceability_ok"]
    pairs = result["correlation"]["relationships"]
    assert Counter(r["classification"] for r in pairs) == {
        "related": 1,
        "uncertain": 2,
        "unrelated": 3,
    }
    assert result["correlation"]["noise_alert_ids"] == ["ecs-noise-003"]
    assert result["report"]["enrichment"]["items"][0]["matched_alert_ids"] == [
        "ecs-auth-001",
        "wazuh-auth-002",
    ]
    assert result["investigation_context"]["original_case"] == case
    assert result["report"]["hypotheses"][0]["ioc_evidence"]
    elapsed = time.perf_counter() - started
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("submitted_case.json", case),
        ("accepted.json", accepted),
        ("investigation.json", result),
    ):
        (args.output_dir / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (args.output_dir / "report.md").write_text(
        result["report_markdown"], encoding="utf-8"
    )
    summary = {
        "case_id": accepted["case_id"],
        "elapsed_seconds": round(elapsed, 3),
        "pair_counts": dict(Counter(r["classification"] for r in pairs)),
        "noise_alert_ids": result["correlation"]["noise_alert_ids"],
        "ioc_count": len(result["report"]["enrichment"]["items"]),
        "status": result["status"],
        "validation": result["validation"],
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
