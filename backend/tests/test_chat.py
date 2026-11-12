from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from app.models.chat import ChatThread
from app.services.chat import (
    HistoryMessage,
    TurnResult,
    reset_graph_for_tests,
    run_turn,
)


def test_chat_requires_auth(client: TestClient) -> None:
    assert client.get("/api/chat/threads").status_code == 401


def test_create_list_and_message_round_trip(user_client: TestClient) -> None:
    reset_graph_for_tests()
    r = user_client.post("/api/chat/threads", json={})
    assert r.status_code == 201
    thread = r.json()
    thread_id = thread["id"]

    r = user_client.get("/api/chat/threads")
    assert r.status_code == 200
    assert any(t["id"] == thread_id for t in r.json()["items"])

    with patch(
        "app.routers.chat.run_turn",
        return_value=TurnResult(
            content="Hello back",
            thinking="User greeted me; reply warmly.",
            tools_used=[],
        ),
    ) as mocked:
        r = user_client.post(
            f"/api/chat/threads/{thread_id}/messages",
            json={"content": "Hi there"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["user_message"]["role"] == "user"
        assert body["user_message"]["content"] == "Hi there"
        assert body["assistant_message"]["role"] == "assistant"
        assert body["assistant_message"]["content"] == "Hello back"
        assert body["assistant_message"]["thinking"] == "User greeted me; reply warmly."
        mocked.assert_called_once()
        history, user_text = mocked.call_args.args
        assert user_text == "Hi there"
        assert history == []

    r = user_client.get(f"/api/chat/threads/{thread_id}/messages")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert [m["role"] for m in items] == ["user", "assistant"]
    assert items[1]["thinking"] == "User greeted me; reply warmly."
    assert items[0]["thinking"] is None

    with patch(
        "app.routers.chat.run_turn",
        return_value=TurnResult(content="Still here", thinking="Recall prior greeting."),
    ) as mocked:
        r = user_client.post(
            f"/api/chat/threads/{thread_id}/messages",
            json={"content": "Remember me?"},
        )
        assert r.status_code == 200
        history, user_text = mocked.call_args.args
        assert user_text == "Remember me?"
        assert [(h.role, h.content) for h in history] == [
            ("user", "Hi there"),
            ("assistant", "Hello back"),
        ]
        assert r.json()["assistant_message"]["thinking"] == "Recall prior greeting."


def test_cannot_access_other_users_thread(
    user_client: TestClient,
    admin_client: TestClient,
    db_session: Session,
) -> None:
    r = user_client.post("/api/chat/threads", json={"title": "Mine"})
    assert r.status_code == 201
    thread_id = r.json()["id"]

    assert admin_client.get(f"/api/chat/threads/{thread_id}/messages").status_code == 404
    assert (
        admin_client.post(
            f"/api/chat/threads/{thread_id}/messages",
            json={"content": "Nope"},
        ).status_code
        == 404
    )
    assert admin_client.delete(f"/api/chat/threads/{thread_id}").status_code == 404

    # Owner can delete
    assert user_client.delete(f"/api/chat/threads/{thread_id}").status_code == 204
    assert db_session.get(ChatThread, UUID(thread_id)) is None


def test_missing_api_key_returns_503(user_client: TestClient, monkeypatch) -> None:
    reset_graph_for_tests()
    from app.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")
    r = user_client.post("/api/chat/threads", json={})
    assert r.status_code == 201
    thread_id = r.json()["id"]

    from app.services import chat as chat_service

    monkeypatch.setattr(chat_service, "_graph", None)
    r = user_client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"content": "Hello"},
    )
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_browse_web_tool_formats_results(monkeypatch) -> None:
    from app.services import chat as chat_service

    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query: str, max_results: int = 5):
            assert "bengaluru" in query.lower() or "weather" in query.lower()
            return [
                {
                    "title": "Bengaluru Weather",
                    "href": "https://example.com/blr",
                    "body": "Currently 28°C and partly cloudy.",
                }
            ]

    import ddgs as ddgs_mod

    monkeypatch.setattr(ddgs_mod, "DDGS", FakeDDGS)
    out = chat_service._duckduckgo_search("Bengaluru weather now")
    assert "28°C" in out
    assert "Bengaluru Weather" in out


def test_run_turn_invokes_graph_with_thinking(monkeypatch) -> None:
    reset_graph_for_tests()
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {
        "thinking": "Check history, then answer.",
        "messages": [
            HumanMessage(content="hi"),
            AIMessage(content="Hello!"),
        ],
    }
    monkeypatch.setattr("app.services.chat.get_graph", lambda: fake_graph)

    result = run_turn([HistoryMessage(role="user", content="earlier")], "hi")
    assert result.content == "Hello!"
    assert result.thinking == "Check history, then answer."
    assert result.tools_used == []
    fake_graph.invoke.assert_called_once()
    payload = fake_graph.invoke.call_args.args[0]
    assert payload["thinking"] == ""
    assert len(payload["messages"]) == 2
