from __future__ import annotations

from pathlib import Path


def test_readme_design_review_section_mentions_language_and_integrity() -> None:
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "Design Review Finale" in content
    assert "The response is rendered in three sections" in content
    assert "The design review must not alter the original deliverables" in content
    assert "mirrors the language of the initial prompt unless asked otherwise" in content
