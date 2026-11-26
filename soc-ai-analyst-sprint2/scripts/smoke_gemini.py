"""Opt-in live Gemini smoke check using only the bundled synthetic cases."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import create_app

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "sprint3"
SCENARIOS = (("us6_attack.json", True), ("us6_benign.json", False))
TIMEOUT_SECONDS = 90
CALL_BUDGET = 4  # Two automatic investigations and two chat turns.


def record(event, **details):
    print(json.dumps({"event": event, **details}), flush=True)


def investigate(client, filename, has_hypotheses):
    payload = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    payload["case_id"] = f"live-smoke-{uuid4()}"
    valid_alert_ids = {alert["alert_id"] for alert in payload["alerts"]}

    accepted = client.post("/api/v1/cases", json=payload)
    assert accepted.status_code == 201, f"{filename}: synthetic case was rejected"
    case_id = accepted.json()["case_id"]
    base = f"/api/v1/cases/{case_id}"

    deadline = time.monotonic() + TIMEOUT_SECONDS + 30
    while time.monotonic() < deadline:
        status = client.get(base + "/analysis-status").json()
        if status["status"] in {"completed", "error"}:
            break
        time.sleep(0.25)
    else:
        raise AssertionError(f"{filename}: automatic investigation did not finish")

    assert status["status"] == "completed", f"{filename}: {status['status']}"
    response = client.get(base + "/investigation")
    assert response.status_code == 200, f"{filename}: no saved investigation"
    saved = response.json()
    report = saved["report"]
    review = report.get("model_review") or {}
    attempts = review.get("attempts", [])
    candidates = review.get("candidate_hypotheses", [])
    record(
        "investigation",
        fixture=filename,
        case_id=case_id,
        status=review.get("status"),
        model=review.get("model"),
        attempts=attempts,
        usage=review.get("usage"),
        hypotheses=len(report["hypotheses"]),
        candidates=len(candidates),
        rejected_candidates=review.get("candidate_hypotheses_rejected"),
    )
    assert saved["validation"]["ok"]
    assert bool(report["hypotheses"]) == has_hypotheses
    assert review.get("status") == "ok" and review.get("provider") == "gemini"
    assert len(attempts) == 1 and attempts[0]["outcome"] == "ok"
    assessment = review.get("initial_assessment")
    assert assessment and assessment["assessment"], (
        f"{filename}: no validated assessment"
    )
    assert set(assessment["cited_alert_ids"]) <= valid_alert_ids
    for item in (*review["items"], *candidates):
        assert set(item["cited_alert_ids"]) <= valid_alert_ids
    for candidate in candidates:
        assert candidate["status"] == "candidate" and candidate["source"] == "model"
    return base, sorted(valid_alert_ids)[0], len(candidates)


def chat(client, base, alert_id):
    catalog = client.get(base + "/chat-evidence").json()["evidence"]
    evidence_ref = f"alert:{alert_id}"
    for turn, message in enumerate(
        (
            f"What does alert {alert_id} show? Cite its evidence.",
            "What evidence is missing to confirm your previous answer?",
        ),
        start=1,
    ):
        response = client.post(
            base + "/messages",
            headers={"X-Analyst-Id": "smoke"},
            json={
                "analyst_id": "smoke",
                "message": message,
                "evidence_refs": [evidence_ref],
            },
        )
        record("chat", turn=turn, http_status=response.status_code)
        assert response.status_code == 200, (
            f"Chat turn {turn}: HTTP {response.status_code}"
        )
        answer = response.json()["message"]
        refs = set(answer["evidence_refs"])
        assert answer["content"].strip() and refs <= catalog.keys()
        if turn == 1:
            assert evidence_ref in refs, "First answer did not cite the selected alert"
    history = client.get(base + "/messages").json()["messages"]
    assert [message["role"] for message in history] == ["user", "assistant"] * 2
    return history


def main():
    if not all(
        os.getenv(name, "").strip() for name in ("GEMINI_API_KEY", "GEMINI_MODEL")
    ):
        raise SystemExit(
            "Set GEMINI_API_KEY and GEMINI_MODEL in your environment first"
        )
    # The script owns this process and uses a fresh SQLite database for each run.
    os.environ.update(
        SOC_AUTO_INVESTIGATE="true",
        LLM_PROVIDER="gemini",
        GEMINI_FALLBACK_MODELS="",
        GEMINI_RETRY_ATTEMPTS="0",
        LLM_TIMEOUT_SECONDS=str(TIMEOUT_SECONDS),
    )
    record("start", call_budget=CALL_BUDGET, model=os.environ["GEMINI_MODEL"])
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "smoke.sqlite3"
        with TestClient(create_app(database_path=database)) as client:
            with_hypotheses, without_hypotheses = [
                investigate(client, filename, expected)
                for filename, expected in SCENARIOS
            ]
            base, alert_id, candidates_a = with_hypotheses
            other_base, _, candidates_b = without_hypotheses
            history = chat(client, base, alert_id)
        with TestClient(create_app(database_path=database)) as reopened:
            assert reopened.get(base + "/messages").json()["messages"] == history
            assert reopened.get(other_base + "/messages").json()["messages"] == []
    assert candidates_a + candidates_b > 0, "No Gemini candidate labels were exercised"
    record("pass", successful_calls=CALL_BUDGET)


if __name__ == "__main__":
    main()
