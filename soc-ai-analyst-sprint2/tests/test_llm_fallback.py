import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from agent import llm
from agent.llm import GeminiProvider, ProviderUnavailable


def _response():
    return SimpleNamespace(
        text='{"items":[{"rank":1,"assessment":"weak",'
        '"explanation":"Needs review","cited_alert_ids":["a-1"]}]}'
    )


def _client(monkeypatch, outcomes):
    from google import genai

    client = Mock()
    client.models.generate_content.side_effect = outcomes
    monkeypatch.setattr(genai, "Client", Mock(return_value=client))
    return client


def _provider(**kwargs):
    return GeminiProvider("test-secret", sleep=lambda _: None, **kwargs)


def test_retries_retryable_503_before_success(monkeypatch):
    from google.genai.errors import ServerError
    from google.genai.types import ThinkingLevel

    client = _client(monkeypatch, [ServerError(503, {}), _response()])
    provider = _provider(model="primary", retry_attempts=2, thinking_level="high")
    output, _ = provider.review({"hypotheses": []})
    assert output["items"][0]["rank"] == 1
    assert [item["outcome"] for item in provider.last_attempts] == ["http_503", "ok"]
    calls = client.models.generate_content.call_args_list
    assert [call.kwargs["model"] for call in calls] == [
        "primary",
        "primary",
    ]
    assert client.models.generate_content.call_args.kwargs["config"][
        "thinking_config"
    ] == {"thinking_level": ThinkingLevel.HIGH}


def test_uses_fallback_after_primary_retry_budget(monkeypatch):
    from google.genai.errors import ServerError

    _client(monkeypatch, [ServerError(503, {}), _response()])
    provider = _provider(
        model="primary", fallback_models=["backup"], retry_attempts=0,
        thinking_level="high",
    )
    output, _ = provider.review({"hypotheses": []})
    assert output["items"]
    assert provider.last_model == "backup"
    assert [item["model"] for item in provider.last_attempts] == ["primary", "backup"]


def test_model_review_reports_fallback_model(monkeypatch):
    from google.genai.errors import ServerError

    _client(monkeypatch, [ServerError(503, {}), _response()])
    provider = _provider(
        model="primary", fallback_models=["backup"], retry_attempts=0,
        thinking_level="high",
    )
    monkeypatch.setattr(llm, "get_provider", lambda: provider)

    async def guard_call(name, payload):
        if name == "prepare_model_context":
            return {"hypotheses": [], "stats": {}}
        return {"items": [], "rejected": []}

    result = asyncio.run(llm.build_model_review([], [], guard_call))
    assert result["status"] == "ok"
    assert result["model"] == "backup"
    assert result["fallback_used"] is True
    assert result["primary_model"] == "primary"
    assert result["analyzed_at"].endswith("+00:00")
    assert result["fallback_reason"] == (
        "backup was used because the earlier model failed: "
        "primary: overloaded or unavailable (503) x1."
    )


def test_does_not_retry_non_retryable_400(monkeypatch):
    from google.genai.errors import ClientError

    client = _client(monkeypatch, [ClientError(400, {})])
    provider = _provider(model="primary", retry_attempts=2, thinking_level="high")
    with pytest.raises(ClientError):
        provider.review({"hypotheses": []})
    assert client.models.generate_content.call_count == 1
    assert provider.last_attempts[0]["outcome"] == "http_400"


def test_build_model_review_returns_all_failed_attempts_without_key(monkeypatch):
    from google.genai.errors import ServerError

    _client(monkeypatch, [ServerError(503, {}), ServerError(503, {})])
    provider = _provider(
        model="primary", fallback_models=["backup"], retry_attempts=0,
        thinking_level="high",
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")
    monkeypatch.setattr(llm, "get_provider", lambda: provider)

    async def guard_call(name, payload):
        if name == "prepare_model_context":
            return {"hypotheses": [], "stats": {}}
        return {"items": [], "rejected": []}

    result = asyncio.run(llm.build_model_review([], [], guard_call))
    assert result["status"] == "error"
    assert [item["outcome"] for item in result["attempts"]] == [
        "http_503",
        "http_503",
    ]
    assert "test-secret" not in str(result)
    assert result["fallback_used"] is False  # nothing answered, so no fallback was used


def test_get_provider_defaults_to_high_thinking(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_THINKING_LEVEL", raising=False)
    provider = llm.get_provider()
    assert provider.thinking_level == "high"


def test_review_has_no_output_cap_unless_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MAX_OUTPUT_TOKENS", raising=False)
    assert llm.get_provider().max_output_tokens is None
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "4096")
    assert llm.get_provider().max_output_tokens == 4096


def test_invalid_thinking_level_is_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "maximum")
    with pytest.raises(ProviderUnavailable, match="GEMINI_THINKING_LEVEL"):
        llm.get_provider()


def test_httpx_read_timeout_is_retried_and_logged_as_timeout(monkeypatch):
    client = _client(monkeypatch, [httpx.ReadTimeout("slow"), _response()])
    provider = _provider(model="primary", retry_attempts=1)
    output, _ = provider.review({"hypotheses": []})
    assert output["items"]
    assert client.models.generate_content.call_count == 2
    assert [a["outcome"] for a in provider.last_attempts] == ["timeout", "ok"]


def test_httpx_connect_error_moves_to_the_fallback_model(monkeypatch):
    _client(monkeypatch, [httpx.ConnectError("down"), _response()])
    provider = _provider(model="primary", fallback_models=["backup"], retry_attempts=0)
    provider.review({"hypotheses": []})
    assert provider.last_model == "backup"
    assert [a["outcome"] for a in provider.last_attempts] == ["connection", "ok"]


def test_chat_retries_and_has_no_output_cap_by_default(monkeypatch):
    from google.genai.errors import ServerError

    answer = SimpleNamespace(text='{"answer":"ok","evidence_refs":[]}')
    client = _client(monkeypatch, [ServerError(503, {}), answer])
    provider = _provider(model="primary", retry_attempts=1)
    assert provider.chat({"current_message": "hi"})["answer"] == "ok"
    config = client.models.generate_content.call_args.kwargs["config"]
    assert config["max_output_tokens"] is None


def test_fallback_reason_is_none_when_the_first_model_answers():
    attempts = [{"model": "primary", "outcome": "ok", "latency_ms": 5}]
    assert llm.fallback_reason(attempts, "primary") is None
    assert llm.fallback_reason([], None) is None


def test_fallback_reason_in_spanish_groups_repeated_failures():
    attempts = [
        {"model": "primary", "outcome": "http_503", "latency_ms": 1},
        {"model": "primary", "outcome": "http_504", "latency_ms": 2},
        {"model": "backup", "outcome": "ok", "latency_ms": 3},
    ]
    reason = llm.fallback_reason(attempts, "backup", "es")
    assert reason == (
        "Se usó backup porque falló antes: primary: saturado o no disponible (503), "
        "no respondió a tiempo (504) x2."
    )


def test_failed_review_records_when_and_primary_model_but_no_fallback(monkeypatch):
    from google.genai.errors import ServerError

    _client(monkeypatch, [ServerError(503, {})])
    provider = _provider(model="primary", retry_attempts=0)
    monkeypatch.setattr(llm, "get_provider", lambda: provider)

    async def guard_call(name, payload):
        return {"hypotheses": [], "stats": {}}

    result = asyncio.run(llm.build_model_review([], [], guard_call))
    assert result["status"] == "error" and result["primary_model"] == "primary"
    assert result["fallback_used"] is False and result["fallback_reason"] is None
    assert result["analyzed_at"]


async def _guard_call(name, payload):
    if name == "prepare_model_context":
        return {"hypotheses": [], "stats": {}}
    return {"items": [], "rejected": []}


def test_hung_primary_leaves_time_for_the_fallback(monkeypatch):
    import time

    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "90")
    now = [0.0]
    monkeypatch.setattr(llm, "time", SimpleNamespace(
        monotonic=lambda: now[0], perf_counter=time.perf_counter,
    ))
    timeouts = []

    def generate(model, contents, config):
        timeouts.append(config["http_options"]["timeout"])
        if model == "primary":
            now[0] += timeouts[-1] / 1000  # hangs for its whole share
            raise httpx.ReadTimeout("hung")
        return _response()

    _client(monkeypatch, generate)
    provider = _provider(model="primary", fallback_models=["backup"], retry_attempts=0)
    monkeypatch.setattr(llm, "get_provider", lambda: provider)
    result = asyncio.run(llm.build_model_review([], [], _guard_call))
    assert timeouts == [45000, 45000]
    assert result["status"] == "ok" and result["fallback_used"] is True
    assert result["attempts"] is not provider.last_attempts


def test_internal_deadline_beats_outer_wait_for(monkeypatch):
    import time

    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")

    def generate(model, contents, config):
        time.sleep(config["http_options"]["timeout"] / 1000)
        raise httpx.ReadTimeout("slow")

    _client(monkeypatch, generate)
    provider = _provider(model="primary", retry_attempts=0)
    monkeypatch.setattr(llm, "get_provider", lambda: provider)
    result = asyncio.run(llm.build_model_review([], [], _guard_call))
    assert result["status"] == "error" and result["error"].startswith("ReadTimeout")
    assert [a["outcome"] for a in result["attempts"]] == ["timeout"]
    assert result["attempts"] is not provider.last_attempts


def test_408_and_502_are_retried_and_explained():
    from google.genai.errors import ServerError

    assert GeminiProvider._retryable(ServerError(502, {}))
    assert GeminiProvider._retryable(SimpleNamespace(code=408))
    attempts = [
        {"model": "primary", "outcome": "http_408", "latency_ms": 1},
        {"model": "primary", "outcome": "http_502", "latency_ms": 1},
        {"model": "backup", "outcome": "ok", "latency_ms": 1},
    ]
    assert llm.fallback_reason(attempts, "backup", "es") == (
        "Se usó backup porque falló antes: primary: tiempo de espera de la "
        "solicitud (408), puerta de enlace incorrecta (502) x2."
    )
    assert "bad gateway (502)" in llm.fallback_reason(attempts, "backup")


def test_invalid_answer_moves_to_the_fallback_model(monkeypatch):
    _client(monkeypatch, [SimpleNamespace(text="not json"), _response()])
    provider = _provider(model="primary", fallback_models=["backup"], retry_attempts=0)
    output, _ = provider.review({"hypotheses": []})
    assert output["items"] and provider.last_model == "backup"
    assert [a["outcome"] for a in provider.last_attempts] == ["invalid_response", "ok"]
    assert "empty or invalid answer" in llm.fallback_reason(
        provider.last_attempts, "backup"
    )


def test_duplicate_fallback_models_are_not_retried(monkeypatch):
    from google.genai.errors import ServerError

    monkeypatch.setenv("GEMINI_MODEL", "same")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "same, other ,same")
    assert llm._gemini_models() == ["same", "other"]
    client = _client(monkeypatch, [ServerError(503, {})])
    provider = _provider(model="same", fallback_models=["same"], retry_attempts=0)
    with pytest.raises(ServerError):
        provider.review({"hypotheses": []})
    assert client.models.generate_content.call_count == 1


def test_failed_review_reports_the_model_that_failed_last(monkeypatch):
    from google.genai.errors import ClientError, ServerError

    _client(monkeypatch, [ServerError(503, {}), ClientError(400, {})])
    provider = _provider(model="primary", fallback_models=["backup"], retry_attempts=0)
    monkeypatch.setattr(llm, "get_provider", lambda: provider)
    result = asyncio.run(llm.build_model_review([], [], _guard_call))
    assert result["status"] == "error"
    assert result["model"] == "backup" and result["primary_model"] == "primary"


def test_invalid_answer_skips_to_the_next_model_without_same_model_retry(monkeypatch):
    client = _client(monkeypatch, [SimpleNamespace(text="not json"), _response()])
    provider = _provider(model="primary", fallback_models=["backup"], retry_attempts=2)
    provider.review({"hypotheses": []})
    assert client.models.generate_content.call_count == 2
    assert [a["outcome"] for a in provider.last_attempts] == ["invalid_response", "ok"]
    assert provider.last_model == "backup"
