import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Action, Pipe


@pytest.fixture
def pipe() -> Pipe:
    return Pipe()


@pytest.fixture
def sample_action() -> Action:
    return Action(
        id="a-1",
        type="text",
        description="Generate documentation",
    )


def test_format_action_output_unwraps_markdown_block(
    pipe: Pipe, sample_action: Action
) -> None:
    output = {
        "primary_output": "```markdown\n# Heading\n\nParagraph text.\n```",
    }

    rendered = pipe.format_action_output(sample_action, output)

    assert "```markdown" not in rendered
    assert "# Heading" in rendered


def test_format_action_output_unwraps_generic_code_block(
    pipe: Pipe, sample_action: Action
) -> None:
    output = {
        "primary_output": "```\n## Section\n- Item 1\n- Item 2\n```",
    }

    rendered = pipe.format_action_output(sample_action, output)

    assert rendered.count("```") == 0
    assert "## Section" in rendered


def test_format_action_output_preserves_code_blocks_for_languages(
    pipe: Pipe, sample_action: Action
) -> None:
    output = {
        "primary_output": "```python\nprint(\"Hello\")\n```",
    }

    rendered = pipe.format_action_output(sample_action, output)

    assert "```python" in rendered


def test_clean_nested_markdown_unwraps_mermaid_wrapped_in_image(
    pipe: Pipe, sample_action: Action
) -> None:
    output = {
        "primary_output": "![Measurement Process Diagram](```mermaid\n"
        "graph TD\n    A-->B\n```)",
    }

    rendered = pipe.format_action_output(sample_action, output)

    assert "![Measurement Process Diagram]" not in rendered
    assert "```mermaid\ngraph TD\n    A-->B\n```" in rendered


def test_supporting_details_unwraps_markdown_block(
    pipe: Pipe, sample_action: Action
) -> None:
    output = {
        "primary_output": "",
        "supporting_details": "```markdown\n### Notes\n- Detail\n```",
    }

    rendered = pipe.format_action_output(sample_action, output)

    assert "```markdown" not in rendered
    assert "### Notes" in rendered
    assert "<details>" in rendered
