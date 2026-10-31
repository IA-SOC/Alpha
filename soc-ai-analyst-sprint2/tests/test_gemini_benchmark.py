"""Offline benchmark, accounting and credential-boundary regressions (#68)."""

import asyncio
import json
import os
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.llm import GeminiProvider
from benchmarks import gemini_compare as bench


@pytest.fixture
def context():
    return {
        "hypotheses": [
            {
                "rank": 1,
                "evidence_for_ids": ["a"],
                "evidence_against_ids": [],
                "alerts": [{"id": "a"}],
            }
        ]
    }


@pytest.fixture
def output():
    return {
        "items": [
            {
                "rank": 1,
                "assessment": "weak",
                "explanation": "Incomplete evidence",
                "cited_alert_ids": ["a"],
            }
        ]
    }


def test_cost_includes_thinking_and_discounted_cached_input():
    usage = {
        "input_tokens": 1000,
        "cached_input_tokens": 100,
        "output_tokens": 200,
        "thinking_tokens": 300,
    }
    assert bench.estimate_cost(usage) == pytest.approx(0.0025575)


@pytest.mark.parametrize(
    "change",
    [
        {"input_tokens": None},
        {"output_tokens": None},
        {"thinking_tokens": -1},
        {"cached_input_tokens": 2000},
        {"input_tokens": True},
    ],
)
def test_missing_or_invalid_usage_is_unknown_not_free(change):
    usage = {
        "input_tokens": 1000,
        "cached_input_tokens": 0,
        "output_tokens": 200,
        "thinking_tokens": 0,
        **change,
    }
    assert bench.estimate_cost(usage) is None


@pytest.mark.parametrize(
    "change",
    [
        {"rank": True},
        {"rank": 99},
        {"cited_alert_ids": ["not-supplied"]},
        {"explanation": ""},
        {"assessment": "confirmed"},
    ],
)
def test_invalid_or_unsupported_model_output_does_not_pass_quality(
    context, output, change
):
    output["items"][0].update(change)
    assert not bench.review_quality(output, context)["complete_coverage"]


def test_duplicate_missing_and_unsent_citations_are_not_complete(context, output):
    assert bench.review_quality(output, context)["complete_coverage"]
    assert not bench.review_quality({"items": []}, context)["complete_coverage"]
    output["items"].append(deepcopy(output["items"][0]))
    assert not bench.review_quality(output, context)["complete_coverage"]
    context["hypotheses"][0]["alerts"] = []
    assert bench.review_quality(output, context)["unseen_alert_citations"] == 2


def test_errors_never_store_exception_messages_or_claim_zero_cost(context):
    provider = Mock()
    provider.review.side_effect = RuntimeError("fake-secret-in-provider-exception")
    measured = bench.measure_review(provider, context, True)
    assert measured["status"] == "error"
    assert measured["estimated_api_cost_usd"] is None
    assert "fake-secret" not in json.dumps(measured)


def test_sdk_endpoint_budget_usage_and_client_cleanup(monkeypatch, context, output):
    from google import genai

    response = SimpleNamespace(
        text=json.dumps(output),
        usage_metadata=SimpleNamespace(
            prompt_token_count=10,
            candidates_token_count=20,
            thoughts_token_count=30,
            cached_content_token_count=0,
            total_token_count=60,
        ),
    )
    client = Mock()
    client.models.generate_content.return_value = response
    constructor = Mock(return_value=client)
    monkeypatch.setattr(genai, "Client", constructor)
    provider = GeminiProvider(
        "fake-test-key", model=bench.MODEL, max_output_tokens=2048, retry_attempts=1
    )
    actual, usage = provider.review(context)
    assert actual == output
    assert usage["thinking_tokens"] == 30 and usage["total_tokens"] == 60
    kwargs = constructor.call_args.kwargs
    assert kwargs["vertexai"] is False
    assert kwargs["http_options"] == {
        "base_url": "https://generativelanguage.googleapis.com",
        "retry_options": {"attempts": 1},
    }
    config = client.models.generate_content.call_args.kwargs["config"]
    assert config["max_output_tokens"] == 2048
    assert "fake-test-key" not in json.dumps(config)
    client.close.assert_called_once()
    client.models.generate_content.side_effect = TimeoutError("fake-test-key")
    with pytest.raises(TimeoutError):
        provider.review(context)
    assert client.close.call_count == 2


def fake_state():
    return {
        "report": {"attack_mapping": [{"technique_id": "T1566"}], "hypotheses": []},
        "validation": {"ok": True},
        "hypotheses": [],
        "alerts": [],
    }


def test_live_key_scope_failure_stop_and_restoration(monkeypatch, tmp_path):
    from agent import graph

    key_file = tmp_path / "credential.txt"
    key_file.write_text("fake-benchmark-key", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "previous-test-value")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    calls = []

    async def baseline(*args, **kwargs):
        assert "GEMINI_API_KEY" not in os.environ
        assert os.environ["LLM_PROVIDER"] == "none"
        return fake_state()

    class FailingProvider:
        def __init__(self, key, **kwargs):
            assert key == "fake-benchmark-key"

        def review(self, context):
            assert os.environ["GEMINI_API_KEY"] == "fake-benchmark-key"
            calls.append(1)
            raise RuntimeError("fake-benchmark-key")

    monkeypatch.setattr(graph, "investigate", baseline)
    monkeypatch.setattr(bench, "GeminiProvider", FailingProvider)
    result, _ = asyncio.run(bench.benchmark(list(bench.CASES), True, key_file))
    assert len(calls) == 1
    assert (
        result["rows"][1]["gemini_second_opinion"]["status"]
        == "not_executed_after_error"
    )
    assert "fake-benchmark-key" not in json.dumps(result)
    assert os.environ["GEMINI_API_KEY"] == "previous-test-value"
    assert os.environ["LLM_PROVIDER"] == "mock"
    assert key_file.read_text() == "fake-benchmark-key"


@pytest.mark.parametrize("names", [[], ["customer"], ["phishing_ecs"] * 5])
def test_unregistered_or_excess_cases_fail_before_provider_calls(names):
    with pytest.raises(ValueError):
        asyncio.run(bench.benchmark(names))


def test_offline_never_reads_a_key_or_labels_mock_as_gemini(monkeypatch):
    from agent import graph

    async def baseline(*args, **kwargs):
        return fake_state()

    monkeypatch.setattr(graph, "investigate", baseline)
    result, key = asyncio.run(bench.benchmark(["phishing_ecs"], key_file="not-a-file"))
    assert key is None and result["mode"] == "offline_mock"
    assert result["rows"][0]["gemini_second_opinion"]["status"] == "offline_mock"


def test_key_inside_repository_is_rejected():
    with pytest.raises(ValueError, match="outside"):
        asyncio.run(
            bench.benchmark(["phishing_ecs"], True, bench.ROOT.parent / "key.txt")
        )


def test_cli_refuses_credential_overwrite(monkeypatch, tmp_path, capsys):
    key_file = tmp_path / "credential.txt"
    key_file.write_text("fake-key-must-stay", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["benchmark", "--live", "--key-file", str(key_file), "--output", str(key_file)],
    )
    assert bench.main() == 1
    assert key_file.read_text() == "fake-key-must-stay"
    assert "fake-key-must-stay" not in capsys.readouterr().out


def test_fallback_cost_uses_its_own_snapshot():
    usage = {
        "input_tokens": 1000,
        "output_tokens": 1000,
        "thinking_tokens": 0,
        "cached_input_tokens": 0,
    }
    assert bench.estimate_cost(usage, bench.PRICINGS["gemini-2.5-flash"]) == 0.0028
    assert bench.estimate_cost(usage, bench.PRICINGS["gemini-2.5-flash-lite"]) == 0.0005


def test_cli_blocks_credentials_in_generated_result(monkeypatch, tmp_path, capsys):
    async def fake_benchmark(*args):
        return {"unexpected": "fake-echoed-key"}, "fake-echoed-key"

    output_path = tmp_path / "result.json"
    monkeypatch.setattr(bench, "benchmark", fake_benchmark)
    monkeypatch.setattr("sys.argv", ["benchmark", "--output", str(output_path)])
    assert bench.main() == 1
    assert not output_path.exists()
    assert "fake-echoed-key" not in capsys.readouterr().out
