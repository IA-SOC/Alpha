import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

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
