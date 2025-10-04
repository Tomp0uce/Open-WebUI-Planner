from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Pipe


class PipeForPlanStructureTest(Pipe):
    def __init__(self) -> None:
        super().__init__()
        self.captured_prompt: list[dict[str, str]] | None = None

    async def get_completion(  # type: ignore[override]
        self,
        prompt,
        model: str | dict[str, object] = "",
        tools: dict[str, dict[object, object]] | None = None,
        format: dict[str, object] | None = None,
        action_results: dict[str, dict[str, str]] | None = None,
        action=None,
    ) -> str:
        self.captured_prompt = prompt  # type: ignore[assignment]
        return (
            "{" "\"goal\": \"stub goal\", "
            "\"actions\": [{"
            "\"id\": \"final_synthesis\", "
            "\"type\": \"text\", "
            "\"description\": \"Summary\", "
            "\"tool_ids\": [], "
            "\"dependencies\": [], "
            "\"model\": \"WRITER_MODEL\"" "}]" "}"
        )

    async def emit_status(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def validate_and_fix_tool_actions(  # type: ignore[override]
        self, _plan
    ) -> None:
        return

    async def validate_and_enhance_template(  # type: ignore[override]
        self, _plan
    ) -> None:
        return

    async def validate_and_flag_lightweight_context(  # type: ignore[override]
        self, _plan
    ) -> None:
        return


def run_create_plan(pipe: PipeForPlanStructureTest, goal: str) -> None:
    asyncio.run(pipe.create_plan(goal))


def test_plan_structure_section_has_leading_newline_with_tools() -> None:
    pipe = PipeForPlanStructureTest()
    pipe.valves.ENABLE_TOOL_INTEGRATION = True

    run_create_plan(pipe, "Test goal with tools")

    assert pipe.captured_prompt is not None
    system_prompt = pipe.captured_prompt[0]["content"]
    expected_line = (
        "\n- Your output must be a JSON object with a \"goal\" and a list of \"actions\". "
        "Each action must follow this schema:"
    )
    assert expected_line in system_prompt


def test_plan_structure_section_has_leading_newline_without_tools() -> None:
    pipe = PipeForPlanStructureTest()
    pipe.valves.ENABLE_TOOL_INTEGRATION = False

    run_create_plan(pipe, "Test goal without tools")

    assert pipe.captured_prompt is not None
    system_prompt = pipe.captured_prompt[0]["content"]
    expected_line = (
        "\n- tool_ids: Provide an empty array [] because external tools cannot be used."
    )
    assert expected_line in system_prompt
