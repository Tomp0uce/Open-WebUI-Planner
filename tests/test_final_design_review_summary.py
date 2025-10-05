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
    assert "Analyse initiale" in primary_output
    assert "Prototype fonctionnel" in primary_output
    assert "Planifier une session de relecture croisée." in primary_output
    first_step_index = primary_output.index("### Étape 1 · Analyse initiale")
    second_step_index = primary_output.index("### Étape 2 · Prototype fonctionnel")
    assert first_step_index < second_step_index
    inter_steps = primary_output[first_step_index:second_step_index]
    assert "\n---\n" in inter_steps
