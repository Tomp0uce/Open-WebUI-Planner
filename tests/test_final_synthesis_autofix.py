from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Pipe  # noqa: E402


class PipeWithoutFinalSynthesis(Pipe):
    def __init__(self) -> None:
        super().__init__()
        self.emitted_statuses: list[tuple[str, str]] = []
        self.valves.WRITER_MODEL = "writer-model"
        self.valves.ACTION_MODEL = "action-model"
        self.valves.ENABLE_TOOL_INTEGRATION = False

    async def get_completion(  # type: ignore[override]
        self,
        prompt,
        model: str | dict[str, object] = "",
        tools: dict[str, dict[object, object]] | None = None,
        format: dict[str, object] | None = None,
        action_results: dict[str, dict[str, str]] | None = None,
        action=None,
    ) -> str:
        return (
            "{" "\"goal\": \"stub goal\", "
            "\"actions\": [{"
            "\"id\": \"research_topic\", "
            "\"type\": \"text\", "
            "\"description\": \"Research the topic\", "
            "\"tool_ids\": [], "
            "\"dependencies\": [], "
            "\"model\": \"WRITER_MODEL\"" "}, {"
            "\"id\": \"write_summary\", "
            "\"type\": \"text\", "
            "\"description\": \"Write the summary\", "
            "\"tool_ids\": [], "
            "\"dependencies\": [\"research_topic\"], "
            "\"model\": \"WRITER_MODEL\"" "}]" "}"
        )

    async def emit_status(self, level: str, message: str, *_args, **_kwargs) -> None:  # type: ignore[override]
        self.emitted_statuses.append((level, message))

    async def validate_and_fix_tool_actions(self, _plan):  # type: ignore[override]
        return

    async def validate_and_enhance_template(self, _plan):  # type: ignore[override]
        return

    async def validate_and_flag_lightweight_context(self, _plan):  # type: ignore[override]
        return


def run_create_plan(pipe: PipeWithoutFinalSynthesis, goal: str):
    return asyncio.run(pipe.create_plan(goal))


def test_final_synthesis_added_when_missing() -> None:
    pipe = PipeWithoutFinalSynthesis()

    plan = run_create_plan(pipe, "Goal without final synthesis")

    assert plan.actions[-1].id == "final_synthesis"
    assert plan.actions[-1].dependencies == ["research_topic", "write_summary"]
    assert "{{research_topic}}" in plan.actions[-1].description
    assert "{{write_summary}}" in plan.actions[-1].description
    assert plan.actions[-1].model == "writer-model"
    assert any("final_synthesis" in message for _, message in pipe.emitted_statuses)


class PipeEmptyPlan(PipeWithoutFinalSynthesis):
    async def get_completion(  # type: ignore[override]
        self,
        prompt,
        model: str | dict[str, object] = "",
        tools: dict[str, dict[object, object]] | None = None,
        format: dict[str, object] | None = None,
        action_results: dict[str, dict[str, str]] | None = None,
        action=None,
    ) -> str:
        return "{\"goal\": \"stub goal\", \"actions\": []}"


def test_final_synthesis_added_for_empty_plan() -> None:
    pipe = PipeEmptyPlan()

    plan = run_create_plan(pipe, "Goal with empty plan")

    assert plan.actions[-1].id == "final_synthesis"
    assert plan.actions[-1].dependencies == []
    assert "{{" not in plan.actions[-1].description
    assert "Final Deliverable" in plan.actions[-1].description
