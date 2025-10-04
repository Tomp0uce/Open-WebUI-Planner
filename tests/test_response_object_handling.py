from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Sequence

import pytest

from planner import Pipe, Request, Users


@dataclass
class DummyMessage:
    content: str
    tool_calls: Sequence[dict[str, Any]] | None = None


@dataclass
class DummyChoice:
    message: DummyMessage


@dataclass
class DummyResponse:
    choices: Sequence[DummyChoice]


def _setup_pipe() -> Pipe:
    pipe = Pipe()
    pipe.__request__ = Request()  # type: ignore[attr-defined]
    pipe.__user__ = Users.get_user_by_id("stub")  # type: ignore[attr-defined]
    return pipe


def test_get_completion_supports_response_object(monkeypatch: pytest.MonkeyPatch) -> None:
    pipe = _setup_pipe()

    dummy_response = DummyResponse(choices=[DummyChoice(DummyMessage("All good"))])

    async def fake_generate_chat_completion(_request: Any, _payload: dict[str, Any], **_kwargs: Any) -> DummyResponse:
        return dummy_response

    monkeypatch.setattr("planner.generate_chat_completion", fake_generate_chat_completion)

    result = asyncio.run(pipe.get_completion("ping"))

    assert result == "All good"


def test_pipe_short_circuit_supports_response_object(monkeypatch: pytest.MonkeyPatch) -> None:
    pipe = _setup_pipe()

    dummy_response = DummyResponse(choices=[DummyChoice(DummyMessage("Task handled"))])

    async def fake_generate_chat_completion(_request: Any, _payload: dict[str, Any], **_kwargs: Any) -> DummyResponse:
        return dummy_response

    monkeypatch.setattr("planner.generate_chat_completion", fake_generate_chat_completion)

    async def fake_event_emitter(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def fake_event_call(*_args: Any, **_kwargs: Any) -> None:
        return None

    result = asyncio.run(
        pipe.pipe(
            body={"messages": [{"role": "user", "content": "hi"}]},
            __user__={"id": "stub"},
            __request__=Request(),
            __event_emitter__=fake_event_emitter,
            __event_call__=fake_event_call,
            __task__="non-default",
        )
    )

    assert result == "Planner: Task handled"
