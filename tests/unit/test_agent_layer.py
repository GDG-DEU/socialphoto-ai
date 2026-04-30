from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.agent.agent_service import AgentService
from src.services.agent.tool_executor import ToolExecutor
from src.services.agent.tools.sim_search_tool import SimSearchTool
from src.services.agent.tools.user_context_tool import UserContextTool


def _response_with_text(text: str) -> SimpleNamespace:
    part = SimpleNamespace(text=text)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(candidates=[candidate])


def _response_with_function_call(name: str, args: dict) -> SimpleNamespace:
    function_call = SimpleNamespace(name=name, args=args)
    part = SimpleNamespace(function_call=function_call)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(candidates=[candidate])


@pytest.mark.asyncio
async def test_tool_executor_returns_error_for_unknown_tool() -> None:
    executor = ToolExecutor(tools=[])

    result = await executor.execute("missing_tool", {})

    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_tool_executor_wraps_non_dict_result() -> None:
    tool = SimpleNamespace(name="demo_tool", execute=AsyncMock(return_value="ok"))
    executor = ToolExecutor(tools=[tool])

    result = await executor.execute("demo_tool", {"x": 1})

    assert result == {"result": "ok"}
    tool.execute.assert_awaited_once_with(x=1)


@pytest.mark.asyncio
async def test_sim_search_tool_uses_existing_service_contract() -> None:
    mock_service = SimpleNamespace(search=AsyncMock(return_value=[{"sim_score": 0.9}]))
    tool = SimSearchTool(mock_service)

    result = await tool.execute(
        query_text="sunset beach",
        cloudinary_public_id="samples/img1",
        top_k=3,
    )

    assert result == {"results": [{"sim_score": 0.9}]}
    mock_service.search.assert_awaited_once_with(
        query_text="sunset beach",
        image_url="samples/img1",
        top_k=3,
    )


@pytest.mark.asyncio
async def test_user_context_tool_calls_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = UserContextTool()

    monkeypatch.setenv("BACKEND_URL", "http://backend:3000")
    monkeypatch.setenv("API_KEY", "internal-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"profile": {"id": "u1"}}

    class FakeClient:
        def __init__(self, timeout: float):
            self.timeout = timeout
            self.called_url = ""
            self.called_headers: dict[str, str] = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
            self.called_url = url
            self.called_headers = headers
            assert url == "http://backend:3000/internal/users/u1/context"
            assert headers["X-API-Key"] == "internal-key"
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    result = await tool.execute(user_id="u1")
    assert result == {"profile": {"id": "u1"}}


@pytest.mark.asyncio
async def test_agent_service_returns_text_without_tool_call() -> None:
    gemini_client = SimpleNamespace(generate=AsyncMock(return_value=_response_with_text("Hello from model")))
    executor = SimpleNamespace(execute=AsyncMock())
    service = AgentService(gemini_client, executor)

    result = await service.run(user_id="u1", message="hello", history=[])

    assert result.reply == "Hello from model"
    assert result.actions is None
    executor.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_service_runs_tool_then_returns_text() -> None:
    gemini_client = SimpleNamespace(
        generate=AsyncMock(
            side_effect=[
                _response_with_function_call("get_user_context", {}),
                _response_with_text("Here is your context summary."),
            ]
        )
    )
    executor = SimpleNamespace(execute=AsyncMock(return_value={"profile": {"id": "u1"}}))
    service = AgentService(gemini_client, executor)

    result = await service.run(user_id="u1", message="summarize me", history=[])

    assert result.reply == "Here is your context summary."
    executor.execute.assert_awaited_once_with(
        tool_name="get_user_context",
        tool_args={"user_id": "u1"},
    )


@pytest.mark.asyncio
async def test_agent_service_returns_fallback_after_max_rounds() -> None:
    gemini_client = SimpleNamespace(
        generate=AsyncMock(return_value=_response_with_function_call("search_similar_images", {"top_k": 3}))
    )
    executor = SimpleNamespace(execute=AsyncMock(return_value={"results": []}))
    service = AgentService(gemini_client, executor)

    result = await service.run(user_id="u1", message="keep going", history=[])

    assert result.reply == "I'm having trouble completing your request. Please try again."
    assert executor.execute.await_count == 5


@pytest.mark.asyncio
async def test_agent_service_separates_cloudinary_ids_into_actions() -> None:
    gemini_client = SimpleNamespace(
        generate=AsyncMock(
            side_effect=[
                _response_with_function_call("search_similar_images", {"query_text": "sunset"}),
                _response_with_text("I found images including chat-temp/abc123."),
            ]
        )
    )
    executor = SimpleNamespace(
        execute=AsyncMock(
            return_value={
                "results": [
                    {"cloudinary_public_id": "chat-temp/abc123", "sim_score": 0.98},
                    {"cloudinary_public_id": "gallery/def456", "sim_score": 0.91},
                ]
            }
        )
    )
    service = AgentService(gemini_client, executor)

    result = await service.run(user_id="u1", message="find sunset images", history=[])

    assert "chat-temp/abc123" not in result.reply
    assert result.actions is not None
    assert result.actions[0].type == "search_similar_images_result"
    assert result.actions[0].parameters["cloudinary_public_ids"] == [
        "chat-temp/abc123",
        "gallery/def456",
    ]


@pytest.mark.asyncio
async def test_agent_service_builds_history_and_current_turn_with_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gemini_client = SimpleNamespace(generate=AsyncMock(return_value=_response_with_text("ok")))
    executor = SimpleNamespace(execute=AsyncMock())
    service = AgentService(gemini_client, executor)

    async def fake_fetch(_: str) -> str:
        return "ZmFrZS1pbWFnZQ=="

    monkeypatch.setattr(service, "_fetch_image_as_b64", fake_fetch)

    history = [
        {
            "role": "USER",
            "content": "look at this",
            "tool_calls": {"cloudinary_public_id": "chat-temp/abc"},
        }
    ]

    messages = await service._build_messages(history)
    current_turn = await service._build_current_turn("new message", "chat-temp/current")

    assert messages[0]["role"] == "user"
    assert messages[0]["parts"][0]["inline_data"]["mime_type"] == "image/jpeg"
    assert messages[0]["parts"][1]["text"] == "look at this"

    assert current_turn["role"] == "user"
    assert current_turn["parts"][0]["inline_data"]["data"] == "ZmFrZS1pbWFnZQ=="
    assert current_turn["parts"][1]["text"] == "new message"
