"""Compare the deterministic agent with its optional Gemini second opinion.

Offline by default. Live mode permits four fixed synthetic files, one generation
per case, no retries, no tools, and at most 2048 output tokens per generation.
Provider prose, exception messages, credentials and raw cases are never saved.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from agent.llm import GeminiProvider, MockProvider
from core.llm_guard import build_model_context, check_model_output

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gemini-3.8-flash"
CASES = {
    "phishing_ecs": {"T1566"},
    "bruteforce_wazuh": {"T1110", "T1021"},
    "exfiltration": {"T1041"},
    "pre_ransomware": {"T1021", "T1569.002", "T1490", "T1486"},
}
PRICING = {
    "model": MODEL,
    "currency": "USD",
    "per_tokens": 1_000_000,
    "input": 0.75,
    "cached_input": 0.075,
    "output_including_thinking": 3.75,
    "source": "https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash",
    "verified_date": "2026-10-31",
    "valid_through": "2026-12-31",
    "basis": "Standard paid-tier estimate; not invoice/free-tier billing",
}
PRICINGS = {
    MODEL: PRICING,
    "gemini-2.5-flash": {
        **PRICING,
        "model": "gemini-2.5-flash",
        "input": 0.30,
        "cached_input": 0.03,
        "output_including_thinking": 2.50,
        "source": "https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash",
        "valid_through": None,
    },
    "gemini-2.5-flash-lite": {
        **PRICING,
        "model": "gemini-2.5-flash-lite",
        "input": 0.10,
        "cached_input": 0.01,
        "output_including_thinking": 0.40,
        "source": "https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite",
        "valid_through": None,
    },
}


class ReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    rank: StrictInt = Field(ge=1)
    assessment: Literal["supports", "weak", "contradicts"]
    explanation: str = Field(min_length=1, max_length=600, pattern=r"\S")
    cited_alert_ids: list[str] = Field(min_length=1)


class ReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[ReviewItem]


@contextmanager
def environment(**values):
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def estimate_cost(usage, pricing=PRICING):
    names = ("input_tokens", "output_tokens", "thinking_tokens", "cached_input_tokens")
    if any(type(usage.get(key)) is not int or usage[key] < 0 for key in names):
        return None
    if usage["cached_input_tokens"] > usage["input_tokens"]:
        return None
    return round(
        (
            (usage["input_tokens"] - usage["cached_input_tokens"]) * pricing["input"]
            + usage["cached_input_tokens"] * pricing["cached_input"]
            + (usage["output_tokens"] + usage["thinking_tokens"])
            * pricing["output_including_thinking"]
        )
        / 1_000_000,
        9,
    )


def review_quality(output, context):
    """Structural/evidence quality proxies, not semantic security accuracy."""
    try:
        ReviewOutput.model_validate(output)
        schema_valid = True
    except ValidationError:
        schema_valid = False
    if not schema_valid:
        return {"schema_valid": False, "accepted_items": 0, "complete_coverage": False}
    checked = check_model_output(output, context)
    expected = {h["rank"] for h in context["hypotheses"]}
    sent = {h["rank"]: {a["id"] for a in h["alerts"]} for h in context["hypotheses"]}
    unseen = sum(
        ref not in sent.get(item["rank"], set())
        for item in output["items"]
        for ref in item["cited_alert_ids"]
    )
    ranks = {item["rank"] for item in checked["items"]}
    return {
        "schema_valid": True,
        "accepted_items": len(checked["items"]),
        "rejected_items": len(checked["rejected"]),
        "unseen_alert_citations": unseen,
        "complete_coverage": ranks == expected
        and not checked["rejected"]
        and not unseen,
        # Only accepted fixed vocabulary is persisted, never provider prose/IDs.
        "assessments": [
            {"rank": item["rank"], "assessment": item["assessment"]}
            for item in checked["items"]
        ],
    }


def source_quality(case, report):
    from app.services.traceability import _resolve_pointer

    checked = 0
    errors = 0

    def visit(node):
        nonlocal checked, errors
        if isinstance(node, dict):
            for field in node.get("source_fields", []):
                checked += 1
                exists, original = _resolve_pointer(case, field["path"])
                errors += not exists or original != field["value"]
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(report)
    return {"original_fields_checked": checked, "original_field_errors": errors}


def measure_review(provider, context, live, pricing=PRICING):
    started = time.perf_counter()
    try:
        output, usage = provider.review(context)
        result = {
            "status": "executed" if live else "offline_mock",
            "quality": review_quality(output, context),
            "usage": usage,
            "estimated_api_cost_usd": estimate_cost(usage, pricing) if live else 0.0,
            "returned_model_version": getattr(provider, "last_model_version", None),
        }
    except Exception as exc:
        # Never serialize provider exception text, request bodies or headers.
        result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "http_status": (
                getattr(exc, "code", None)
                if type(getattr(exc, "code", None)) is int
                else None
            ),
            "usage": None,
            "estimated_api_cost_usd": None,
        }
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


async def benchmark(names, live=False, key_file=None, model=MODEL):
    from agent.graph import investigate

    if not names or len(names) > 4 or len(set(names)) != len(names):
        raise ValueError("Choose one to four distinct registered synthetic cases")
    if any(name not in CASES for name in names):
        raise ValueError("Only registered synthetic cases are permitted")
    if model not in PRICINGS:
        raise ValueError("Model requires a verified pricing snapshot")
    key = None
    if live:
        if key_file is None or ROOT.parent in Path(key_file).resolve().parents:
            raise ValueError("Live mode requires a key file outside the repository")
        key = Path(key_file).read_text(encoding="utf-8-sig").strip()
        if not key or any(ch.isspace() for ch in key):
            raise ValueError("Invalid credential file")
    rows = []
    stopped = False
    for name in names:
        raw = (ROOT / f"data/synthetic/{name}.json").read_bytes()
        case = json.loads(raw)
        if case.get("synthetic") is not True:
            raise ValueError("Case must explicitly declare synthetic=true")
        started = time.perf_counter()
        # Key is absent while the agent starts local MCP subprocesses.
        with environment(LLM_PROVIDER="none", GEMINI_API_KEY=None):
            state = await investigate(case, thread_id=f"benchmark-{name}")
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        report = state["report"]
        context = build_model_context(state["alerts"], state["hypotheses"])
        baseline = {
            "latency_ms": elapsed,
            "schema_valid": state["validation"]["ok"],
            "api_tokens": 0,
            "estimated_api_cost_usd": 0.0,
            "expected_catalog_match": {
                m["technique_id"] for m in report["attack_mapping"]
            }
            == CASES[name],
            **source_quality(case, report),
        }
        if not baseline["schema_valid"]:
            raise ValueError("Baseline report invalid; no remote call made")
        if stopped:
            review = {"status": "not_executed_after_error"}
        else:
            provider = (
                GeminiProvider(
                    key,
                    model=model,
                    max_output_tokens=2048,
                    retry_attempts=1,
                    thinking_level="low" if model == MODEL else None,
                    thinking_budget=0 if model != MODEL else None,
                )
                if live
                else MockProvider()
            )
            with environment(GEMINI_API_KEY=key):
                review = await asyncio.to_thread(
                    measure_review, provider, context, live, PRICINGS[model]
                )
            stopped = review["status"] == "error"
        rows.append(
            {
                "case": name,
                "fixture_sha256": hashlib.sha256(raw).hexdigest(),
                "context_sha256": hashlib.sha256(
                    json.dumps(context, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
                "alert_count": len(state["alerts"]),
                "hypothesis_count": len(report["hypotheses"]),
                "baseline": baseline,
                "gemini_second_opinion": review,
            }
        )
    return {
        "benchmark_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "mode": "live" if live else "offline_mock",
        "model": model,
        "pricing": PRICINGS[model],
        "limits": {
            "max_requests": len(names),
            "retry_attempts": 1,
            "max_output_tokens_per_request": 2048,
            "thinking": "low" if model == MODEL else "budget=0",
        },
        "comparison": "deterministic full report vs incremental Gemini second opinion",
        "rows": rows,
    }, key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--model", choices=PRICINGS, default=MODEL)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, key = asyncio.run(
            benchmark(args.cases, args.live, args.key_file, args.model)
        )
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if key and key in serialized:
            raise ValueError("Credential detected; refusing output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        # Summary contains only statuses/counts, never provider output/errors.
        print(
            json.dumps(
                {
                    "mode": result["mode"],
                    "cases": [
                        {
                            "case": row["case"],
                            "status": row["gemini_second_opinion"]["status"],
                        }
                        for row in result["rows"]
                    ],
                }
            )
        )
        return int(
            any(r["gemini_second_opinion"]["status"] == "error" for r in result["rows"])
        )
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
