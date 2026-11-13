from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agent.llm import ProviderUnavailable
from app.main import create_app
from app.services import chat_service
from tests.test_correlation_engine import case_for, event


@pytest.fixture
def chat(tmp_path, monkeypatch):
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    contexts = []

    class GeminiDouble:
        def chat(self, context):
            contexts.append(deepcopy(context))
            return {
                "answer": "Evidence requires analyst review",
                "evidence_refs": [next(iter(context["evidence"]))],
            }

    monkeypatch.setattr(chat_service, "get_provider", lambda *args: GeminiDouble())
    with TestClient(app) as client:
        ids = []
        for name in ("alpha", "beta"):
            case = case_for(event(name))
            case.case_id = name
            case_id = client.post(
                "/api/v1/cases", json=case.model_dump(exclude_unset=True)
            ).json()["case_id"]
            ids.append(case_id)
            app.state.investigation_service.store.save_investigation(
                UUID(case_id),
                {
                    "case_id": case_id,
                    "run_id": f"run-{name}",
                    "report": {
                        "hypotheses": [],
                        "timeline": [{"alert_id": name}],
                        "enrichment": {"items": [{"observable": name}]},
                    },
                },
            )
        yield client, app, ids, contexts


def send(client, case_id, **overrides):
    return client.post(
        f"/api/v1/cases/{case_id}/messages",
        headers={"X-Analyst-Id": "isabella"},
        json={"analyst_id": "isabella", "message": "Explain this case", **overrides},
    )


def test_multi_turn_and_case_isolation(chat):
    client, app, (a, b), contexts = chat
    assert send(client, a, message="First alpha question").status_code == 200
    assert send(client, a, message="Explain your previous answer").status_code == 200
    assert [m["role"] for m in contexts[1]["messages"]] == ["user", "assistant"]
    assert contexts[1]["messages"][0]["content"] == "First alpha question"
    assert send(client, b).status_code == 200
    assert contexts[-1]["messages"] == []
    assert contexts[-1]["case_id"] == b
    assert "alpha" not in str(contexts[-1])
    assert "beta" not in str(contexts[0])
    assert len(client.get(f"/api/v1/cases/{a}/messages").json()["messages"]) == 4
    assert len(client.get(f"/api/v1/cases/{b}/messages").json()["messages"]) == 2
    assert any(ref.startswith("mcp:") for ref in contexts[0]["evidence"])


@pytest.mark.parametrize(
    "reference", ["alert:beta", "alert:missing", "mcp:run-beta:timeline:0"]
)
def test_invalid_or_cross_case_input_refs_do_not_call_gemini(chat, reference):
    client, _, (a, _), contexts = chat
    assert send(client, a, evidence_refs=[reference]).status_code == 422
    assert contexts == []
    assert client.get(f"/api/v1/cases/{a}/messages").json()["messages"] == []


@pytest.mark.parametrize(
    "output",
    [
        {"answer": "made up", "evidence_refs": ["alert:beta"]},
        {"answer": "bad shape"},
        {"answer": "", "evidence_refs": []},
    ],
)
def test_invalid_model_output_is_not_saved(chat, monkeypatch, output):
    client, _, (a, _), _ = chat

    class BadProvider:
        def chat(self, context):
            return output

    monkeypatch.setattr(chat_service, "get_provider", lambda *args: BadProvider())
    assert send(client, a).status_code == 502
    assert client.get(f"/api/v1/cases/{a}/messages").json()["messages"] == []


@pytest.mark.parametrize(
    "error, expected",
    [
        (RuntimeError("secret"), 502),
        (TimeoutError("secret"), 504),
        (ProviderUnavailable("secret"), 503),
    ],
)
def test_provider_errors_do_not_leak_or_save_partial_turns(
    chat, monkeypatch, error, expected
):
    client, _, (a, _), _ = chat

    def fail(*args):
        raise error

    monkeypatch.setattr(chat_service, "get_provider", fail)
    response = send(client, a)
    assert response.status_code == expected
    assert "secret" not in response.text
    assert client.get(f"/api/v1/cases/{a}/messages").json()["messages"] == []


def test_contract_evidence_catalog_and_missing_cases(chat):
    client, app, (a, _), _ = chat
    evidence = client.get(f"/api/v1/cases/{a}/chat-evidence").json()["evidence"]
    assert "alert:alpha" in evidence
    assert "mcp:run-alpha:timeline:0" in evidence
    assert (
        send(client, a, evidence_refs=["mcp:run-alpha:timeline:0"]).status_code == 200
    )
    assert send(client, a, analyst_id="other").status_code == 403
    assert send(client, a, message=" ").status_code == 422
    assert send(client, str(uuid4())).status_code == 404
    case = case_for(event("pending"))
    case.case_id = "pending"
    pending = client.post(
        "/api/v1/cases", json=case.model_dump(exclude_unset=True)
    ).json()["case_id"]
    assert send(client, pending).status_code == 409


def test_history_survives_backend_restart(chat):
    client, app, (a, _), contexts = chat
    assert send(client, a).status_code == 200
    path = app.state.chat_service.store.path
    with TestClient(create_app(database_path=path)) as restarted:
        assert len(restarted.get(f"/api/v1/cases/{a}/messages").json()["messages"]) == 2
        assert send(restarted, a).status_code == 200
        assert len(contexts[-1]["messages"]) == 2


def test_concurrent_turns_are_serialized_per_case(chat):
    from concurrent.futures import ThreadPoolExecutor

    client, _, (a, _), contexts = chat
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda text: send(client, a, message=text), ["one", "two"])
        )
    assert all(result.status_code == 200 for result in results)
    assert sorted(len(context["messages"]) for context in contexts) == [0, 2]
    history = client.get(f"/api/v1/cases/{a}/messages").json()["messages"]
    assert [item["role"] for item in history] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_gemini_chat_uses_sdk_and_closes_client(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from google import genai

    from agent.llm import GeminiProvider

    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text='{"answer":"Insufficient evidence","evidence_refs":[]}'
    )
    constructor = Mock(return_value=client)
    monkeypatch.setattr(genai, "Client", constructor)
    provider = GeminiProvider("test-key", model="configured-model")
    result = provider.chat({"case_id": "a", "messages": [], "evidence": {}})
    assert result["evidence_refs"] == []
    args = client.models.generate_content.call_args.kwargs
    assert args["model"] == "configured-model"
    assert '"case_id": "a"' in args["contents"]
    assert args["config"]["response_mime_type"] == "application/json"
    constructor.assert_called_once()
    client.close.assert_called_once()


def test_large_case_keeps_mcp_evidence_in_default_context(chat):
    client, app, _, contexts = chat
    case = case_for(*(event(f"a-{i}") for i in range(35)))
    case.case_id = "large-case"
    case_id = client.post(
        "/api/v1/cases", json=case.model_dump(exclude_unset=True)
    ).json()["case_id"]
    app.state.investigation_service.store.save_investigation(
        UUID(case_id),
        {
            "case_id": case_id,
            "run_id": "large-run",
            "report": {"timeline": [{"alert_ids": ["a-0"]}]},
        },
    )
    assert send(client, case_id).status_code == 200
    assert "mcp:large-run:timeline:0" in contexts[-1]["evidence"]
