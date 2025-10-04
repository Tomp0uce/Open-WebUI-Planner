from __future__ import annotations

import asyncio
from typing import Any

import pytest

from planner import Pipe, Request, Users


def test_get_completion_omits_temperature_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    pipe = Pipe()
    pipe.__request__ = Request()  # type: ignore[attr-defined]
    pipe.__user__ = Users.get_user_by_id("stub")  # type: ignore[attr-defined]

    captured_payload: dict[str, Any] = {}

    async def fake_generate_chat_completion(_request: Any, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        nonlocal captured_payload
        captured_payload = payload
        return {"choices": [{"message": {"content": ""}}]}

    monkeypatch.setattr("planner.generate_chat_completion", fake_generate_chat_completion)

    asyncio.run(pipe.get_completion("hello"))

    assert "temperature" not in captured_payload


def test_temperature_valves_are_unavailable() -> None:
    pipe = Pipe()

    for field_name in [
        "ACTION_TEMPERATURE",
        "WRITER_TEMPERATURE",
        "CODER_TEMPERATURE",
        "PLANNING_TEMPERATURE",
        "ANALYSIS_TEMPERATURE",
    ]:
        assert not hasattr(pipe.valves, field_name)
