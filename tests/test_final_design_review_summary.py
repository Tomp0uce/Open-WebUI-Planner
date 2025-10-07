from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Action, Plan, Pipe


class ReviewPipe(Pipe):
    def __init__(self) -> None:
        super().__init__()

    async def emit_status(self, level: str, message: str, done: bool):  # type: ignore[override]
        return None


async def _run_review(plan: Plan, assembled_output: str) -> dict[str, str]:
    pipe = ReviewPipe()
    return await pipe.review_final_deliverable(plan, assembled_output)


def test_final_review_appends_global_summary() -> None:
    plan = Plan(
        goal="Valider le livrable",
        actions=[
            Action(id="etape1", type="text", description="Analyse initiale"),
            Action(id="etape2", type="text", description="Prototype fonctionnel"),
            Action(id="final_synthesis", type="text", description="{{etape1}}\n{{etape2}}"),
        ],
    )

    plan.metadata.setdefault("action_quality", {})["etape1"] = {
        "quality_score": 0.9,
        "summary": "Travail très abouti.",
        "issues": ["Vérifier la cohérence des données."],
        "suggestions": ["Documenter les hypothèses clés."],
    }
    plan.metadata.setdefault("action_quality", {})["etape2"] = {
        "quality_score": 0.6,
        "summary": "Résultat partiel nécessitant des retouches.",
        "issues": ["Compléter les tests unitaires."],
        "suggestions": ["Planifier une session de relecture croisée."],
    }

    plan.metadata.setdefault("raw_action_outputs", {})["etape1"] = {
        "primary_output": "Livrable de l'étape 1 : rapport détaillé.",
        "supporting_details": "Synthèse et analyse des données.",
    }
    plan.metadata.setdefault("raw_action_outputs", {})["etape2"] = {
        "primary_output": "Livrable de l'étape 2 : prototype fonctionnel.",
        "supporting_details": "Tests manquants sur les cas limites.",
    }

    pipe = ReviewPipe()

    completed_results = {
        "etape1": {"primary_output": "Livrable de l'étape 1"},
        "etape2": {"primary_output": "Livrable de l'étape 2"},
    }

    assembled_output = pipe._build_stepwise_execution_summary(
        plan, completed_results
    )

    result = asyncio.run(_run_review(plan, assembled_output))

    primary_output = result["primary_output"]

    assert primary_output.startswith(assembled_output)
    assert "## Synthèse globale de la design review" in primary_output

    global_section = primary_output.split("## Synthèse globale de la design review", maxsplit=1)[
        1
    ]

    assert "Section 1 : Résumé rapide" in global_section
    section1_content = global_section.split("Section 2 :", maxsplit=1)[0]
    summary_lines = [
        line.strip()
        for line in section1_content.splitlines()
        if line.strip().startswith("-")
    ]
    assert any("Portée" in line for line in summary_lines)
    assert any(
        "Livrables traités" in line
        and "Étape 1 – Analyse initiale" in line
        and "Étape 2 – Prototype fonctionnel" in line
        for line in summary_lines
    )
    assert any("Points forts" in line for line in summary_lines)
    assert any("Axes de vigilance" in line for line in summary_lines)

    table_header = "| Étape | Score | Points forts | Axes d'amélioration |"
    assert table_header in global_section

    table_rows = [
        line
        for line in global_section.splitlines()
        if line.startswith("| Étape") and "Points" not in line
    ]
    assert table_rows, "La table doit contenir au moins une ligne d'étape."

    for row in table_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        assert len(cells) == 4
        step_label = cells[0]
        assert step_label.startswith("Étape ")
        assert "–" in step_label
        summary_text = step_label.split("–", maxsplit=1)[1].strip()
        summary_words = summary_text.split()
        assert 2 <= len(summary_words) <= 6
        assert summary_words[-1].lower() not in {"un", "une", "des", "pour", "avec"}
        score_cell = cells[1]
        assert score_cell.replace(",", ".").replace(" ", "").startswith("0.") or score_cell in {"0,60", "0,90"}
        assert "Contenu :" not in cells[2]
        assert "Contenu :" not in cells[3]
        assert "rapport détaillé" not in cells[2]
        assert "rapport détaillé" not in cells[3]

    assert "Section 3 : Prochaines étapes prioritaires" in global_section
    section3_content = global_section.split("Section 3 : Prochaines étapes prioritaires", maxsplit=1)[
        1
    ]
    section3_lines = [line for line in section3_content.splitlines() if line.strip()]
    assert section3_lines[0].startswith("Analyse globale"), (
        "La section 3 doit commencer par une analyse globale du contenu."
    )
    assert "Objectif" in section3_lines[0]
    assert "Analyse initiale" in section3_lines[0]
    next_steps_lines = [line for line in section3_lines if line.strip().startswith("- Étape")]
    assert next_steps_lines, "Les prochaines étapes doivent être listées sous forme de puces."
