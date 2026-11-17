"""Cobertura de extremo a extremo para la segunda opinión del modelo."""
import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import llm  # noqa: E402
from agent.graph import investigate  # noqa: E402

CASE = json.loads(
    (ROOT / "data" / "sample_case_bruteforce.json").read_text(encoding="utf-8")
)


def run_case(case, thread_id):
    return asyncio.run(investigate(case, thread_id))


def test_primary_model_review_is_reported_without_fallback(monkeypatch):
    class GeminiDouble:
        name = "gemini"
        model = "primary"
        last_model = "primary"
        last_attempts = [{"model": "primary", "outcome": "ok", "latency_ms": 1}]

        def review(self, context):
            return llm.MockProvider().review(context)

    monkeypatch.setattr(llm, "get_provider", lambda *args: GeminiDouble())
    case = deepcopy(CASE)
    case["require_gemini"] = True

    state = run_case(case, "model-review-primary")
    review = state["report"]["model_review"]

    assert review["fallback_used"] is False
    assert not any("Se usó backup porque falló antes:" in item
                   for item in state["report"]["limitations"])
    assert "modelo ok (primary)" in state["audit_log"][-1]["detail"]
    assert state["validation"]["ok"] is True


def test_fallback_model_review_adds_spanish_limitation(monkeypatch):
    class GeminiDouble:
        name = "gemini"
        model = "primary"
        last_model = "backup"
        last_attempts = [
            {"model": "primary", "outcome": "http_503", "latency_ms": 1},
            {"model": "backup", "outcome": "ok", "latency_ms": 2},
        ]

        def review(self, context):
            return llm.MockProvider().review(context)

    monkeypatch.setattr(llm, "get_provider", lambda *args: GeminiDouble())
    case = deepcopy(CASE)
    case["require_gemini"] = True

    state = run_case(case, "model-review-fallback")
    report = state["report"]

    assert report["model_review"]["fallback_used"] is True
    assert report["model_review"]["model"] == "backup"
    assert report["model_review"]["primary_model"] == "primary"
    assert (
        "Se usó backup porque falló antes: primary: saturado o no disponible "
        "(503) x1." in report["limitations"]
    )
    assert "modelo ok (backup, respaldo)" in state["audit_log"][-1]["detail"]
    assert state["validation"]["ok"] is True


def test_unavailable_gemini_keeps_valid_report_without_model_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    case = deepcopy(CASE)
    case["require_gemini"] = True

    state = run_case(case, "model-review-unavailable")

    assert state["report"]["model_review"]["status"] == "unavailable"
    assert "model" not in state["report"]["model_review"]
    assert "modelo unavailable (None)" in state["audit_log"][-1]["detail"]
    assert state["validation"]["ok"] is True
