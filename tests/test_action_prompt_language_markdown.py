from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Action, Plan, Pipe


class CapturingPipe(Pipe):
    def __init__(self) -> None:
        super().__init__()


def test_action_prompt_enforces_language_and_markdown() -> None:
    plan = Plan(
        goal="Créer cinq invites",  # French goal triggers French requirement
        actions=[
            Action(
                id="step1",
                type="text",
                description="Rédiger un prompt pour un mammifère spécifique",
            ),
        ],
    )

    pipe = CapturingPipe()

    prompt = pipe._build_full_context_prompt(
        plan=plan,
        action=plan.actions[0],
        step_number=1,
        context_for_prompt={},
        requirements=pipe.valves.ACTION_PROMPT_REQUIREMENTS_TEMPLATE,
        user_guidance_text="",
    )

    assert "LANGUAGE CONSISTENCY" in prompt
    assert "same language" in prompt
    assert "Format the whole response using Markdown" in prompt

    lightweight_prompt = pipe._build_lightweight_prompt(
        plan=plan,
        action=plan.actions[0],
        step_number=1,
        context_metadata={},
        requirements=pipe.valves.ACTION_PROMPT_REQUIREMENTS_TEMPLATE,
        user_guidance_text="",
    )

    assert "LANGUAGE CONSISTENCY" in lightweight_prompt
    assert "Markdown" in lightweight_prompt
