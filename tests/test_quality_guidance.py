import asyncio
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Pipe, Plan, Action  # noqa: E402
from open_webui.models.users import User  # noqa: E402


class StubPipe(Pipe):
    def __init__(self) -> None:
        super().__init__()
        self.action_prompts: list[list[dict[str, str]]] = []
        self.analysis_prompts: list[str] = []
        self.action_responses: list[str] = []
        self.analysis_responses: list[str] = []
        self.simulated_tool_call_sequence: list[list[str]] = []

        async def _noop_emit(_event):
            return None

        async def _noop_call(_event):
            return ""

        # Bypass event infrastructure during tests
        setattr(self, "__current_event_emitter__", _noop_emit)
        setattr(self, "__current_event_call__", _noop_call)
        setattr(self, "__request__", object())
        setattr(self, "__user__", User())
        self.user = {}

    async def get_completion(  # type: ignore[override]
        self,
        prompt,
        model: str | dict[str, object] = "",
        tools: dict[str, dict[object, object]] | None = None,
        format: dict[str, object] | None = None,
        action_results: dict[str, dict[str, str]] | None = None,
        action=None,
    ) -> str:
        if isinstance(prompt, list):
            self.action_prompts.append(prompt)  # type: ignore[arg-type]
            response = self.action_responses.pop(0)

            if self.simulated_tool_call_sequence and action is not None:
                calls_for_attempt = self.simulated_tool_call_sequence.pop(0)
                for call in calls_for_attempt:
                    if call not in action.tool_calls:
                        action.tool_calls.append(call)

            return response

        self.analysis_prompts.append(prompt)  # type: ignore[arg-type]
        return self.analysis_responses.pop(0)

    async def emit_status(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def emit_message(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def emit_full_state(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def emit_replace(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def emit_replace_mermaid(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def emit_action_summary(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        return

    async def handle_failed_action_with_exception(  # type: ignore[override]
        self, *_args, **_kwargs
    ) -> str:
        return "abort"

    async def handle_failed_action(self, *_args, **_kwargs) -> str:  # type: ignore[override]
        return "abort"

    async def handle_warning_action(  # type: ignore[override]
        self, *_args, **_kwargs
    ) -> str:
        return "approve"


def run_async(coro):
    return asyncio.run(coro)


def test_analyze_output_prompt_disables_tool_penalties() -> None:
    pipe = StubPipe()
    pipe.valves.ENABLE_TOOL_INTEGRATION = False

    plan = Plan(goal="Goal", actions=[])
    action = Action(
        id="step-1",
        type="text",
        description="Produce summary",
        tool_ids=["web_search"],
    )

    pipe.analysis_responses = [
        json.dumps(
            {
                "is_successful": True,
                "quality_score": 0.9,
                "issues": [],
                "suggestions": [],
            }
        )
    ]

    run_async(pipe.analyze_output(plan, action, "{\"primary_output\": \"\", \"supporting_details\": \"\"}"))

    assert pipe.analysis_prompts, "analysis prompt should be captured"
    prompt = pipe.analysis_prompts[0]

    assert "Tool integration is disabled" in prompt
    assert "Do not penalize the output for missing tool calls" in prompt
    assert "Expected Tool(s)" not in prompt
    assert "Tool Usage Verification" not in prompt


def test_retry_feedback_uses_previous_low_quality_reason() -> None:
    pipe = StubPipe()
    pipe.valves.ENABLE_TOOL_INTEGRATION = False

    action = Action(
        id="step-1",
        type="text",
        description="Draft the introduction",
    )
    plan = Plan(goal="Goal", actions=[action])

    pipe.action_responses = [
        json.dumps(
            {"primary_output": "Draft", "supporting_details": ""}
        ),
        json.dumps(
            {"primary_output": "Improved Draft", "supporting_details": ""}
        ),
    ]

    pipe.analysis_responses = [
        json.dumps(
            {
                "is_successful": False,
                "quality_score": 0.2,
                "issues": ["Missing introduction"],
                "suggestions": ["Add an engaging introduction."],
            }
        ),
        json.dumps(
            {
                "is_successful": True,
                "quality_score": 0.85,
                "issues": [],
                "suggestions": [],
            }
        ),
    ]

    run_async(pipe.execute_action(plan, action, {}, 1))

    assert len(pipe.action_prompts) >= 2, "Expected a retry attempt"

    retry_user_prompt = pipe.action_prompts[1][1]["content"]

    assert "Quality score last attempt: 0.20" in retry_user_prompt
    assert "Missing introduction" in retry_user_prompt
    assert "Add an engaging introduction." in retry_user_prompt


def test_retry_feedback_reports_previous_tool_usage() -> None:
    pipe = StubPipe()
    pipe.valves.ENABLE_TOOL_INTEGRATION = True

    action = Action(
        id="step-1",
        type="tool",
        description="Collect data",
        tool_ids=["search_tool"],
    )
    plan = Plan(goal="Goal", actions=[action])

    pipe.action_responses = [
        json.dumps(
            {"primary_output": "Draft", "supporting_details": ""}
        ),
        json.dumps(
            {"primary_output": "Improved Draft", "supporting_details": ""}
        ),
    ]

    pipe.simulated_tool_call_sequence = [["search_tool"], []]

    pipe.analysis_responses = [
        json.dumps(
            {
                "is_successful": False,
                "quality_score": 0.3,
                "issues": ["Data summary incomplete"],
                "suggestions": ["Incorporate search results into the primary output."],
            }
        ),
        json.dumps(
            {
                "is_successful": True,
                "quality_score": 0.8,
                "issues": [],
                "suggestions": [],
            }
        ),
    ]

    run_async(pipe.execute_action(plan, action, {}, 1))

    assert len(pipe.action_prompts) >= 2, "Expected a retry attempt"

    retry_user_prompt = pipe.action_prompts[1][1]["content"]

    assert "Tools previously called: search_tool" in retry_user_prompt
    assert "did not use any tools" not in retry_user_prompt.lower()
