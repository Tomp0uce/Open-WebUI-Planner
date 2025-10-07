from __future__ import annotations

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Action, Plan, Pipe


class ReviewPipe(Pipe):
    def __init__(self, ai_payload: Any) -> None:
        super().__init__()
        self._ai_payload = ai_payload
        self.calls = 0
        self.captured_prompt: str | None = None
        self.captured_format: Any = None

    async def emit_status(self, level: str, message: str, done: bool):  # type: ignore[override]
        return None

    async def get_completion(  # type: ignore[override]
        self,
        prompt: str,
        format: Any | None = None,
        action_results: dict[str, Any] | None = None,
        action: Action | None = None,
    ) -> str:
        self.calls += 1
        self.captured_prompt = prompt
        self.captured_format = format
        if isinstance(self._ai_payload, Exception):
            raise self._ai_payload
        return json.dumps(self._ai_payload)


def _build_plan() -> Plan:
    plan = Plan(
        goal="Générer cinq prompts illustratifs pour différents animaux.",
        actions=[
            Action(id="etape1", type="text", description="Lister cinq animaux distincts"),
            Action(id="etape2", type="text", description="Produire des prompts détaillés"),
            Action(id="final_synthesis", type="text", description="{{etape1}}\n{{etape2}}"),
        ],
    )

    plan.metadata.setdefault("action_quality", {})["etape1"] = {
        "quality_score": 0.95,
        "summary": "Liste cohérente et pertinente.",
        "issues": [],
        "suggestions": ["Ajouter plus de diversité géographique."],
    }
    plan.metadata.setdefault("action_quality", {})["etape2"] = {
        "quality_score": 0.95,
        "summary": "Prompts riches en détails.",
        "issues": [],
        "suggestions": ["Introduire des animaux moins communs."],
    }

    plan.metadata.setdefault("raw_action_outputs", {})["etape1"] = {
        "primary_output": "Lion\nChimpanzé\nColibri\nDauphin\nKangourou",
        "supporting_details": "Animaux sélectionnés",
    }
    plan.metadata.setdefault("raw_action_outputs", {})["etape2"] = {
        "primary_output": "Prompts créatifs pour chaque animal.",
        "supporting_details": "Descriptions immersives.",
    }

    return plan


def test_design_review_uses_ai_sections() -> None:
    ai_response = {
        "request_summary": "Créer cinq prompts d'illustration couvrant différents animaux.",
        "work_summary": "Deux étapes ont fourni une liste d'animaux et des descriptions immersives pour chaque prompt.",
        "steps": [
            {
                "action_id": "etape1",
                "step_overview": "Sélection de cinq espèces variées",
                "strengths": ["Animaux emblématiques clairement listés."],
                "improvements": ["Explorer des espèces plus inattendues."],
            },
            {
                "action_id": "etape2",
                "step_overview": "Prompts descriptifs pour chaque animal",
                "strengths": ["Descriptions vivantes adaptées à la génération d'images."],
                "improvements": ["Souligner davantage la diversité géographique."],
            },
        ],
        "priorities": [
            "Introduire des animaux moins courants pour enrichir la variété des prompts.",
            "Ajouter des contextes géographiques plus contrastés dans les descriptions.",
        ],
    }

    pipe = ReviewPipe(ai_payload=ai_response)
    plan = _build_plan()

    completed_results = {
        "etape1": {"primary_output": "Lion\nChimpanzé\nColibri\nDauphin\nKangourou"},
        "etape2": {"primary_output": "Prompts immersifs détaillés"},
    }

    assembled_output = pipe._build_stepwise_execution_summary(plan, completed_results)

    result = asyncio.run(pipe.review_final_deliverable(plan, assembled_output))

    assert pipe.calls == 1
    assert pipe.captured_prompt is not None

    primary_output = result["primary_output"]
    assert primary_output.startswith(assembled_output)
    assert "## Synthèse globale de la design review" in primary_output
    assert "Section 1 : Résumé de la demande et du travail réalisé" in primary_output
    assert "- Résumé de la demande : Créer cinq prompts d'illustration" in primary_output
    assert "- Résumé du travail réalisé : Deux étapes ont fourni" in primary_output

    table_header = "| Étape | Score | Points forts | Axes d'amélioration |"
    assert table_header in primary_output
    assert "Étape 1 – Sélection de cinq espèces variées" in primary_output
    assert "Animaux emblématiques clairement listés." in primary_output
    assert "Explorer des espèces plus inattendues." in primary_output
    assert "Étape 2 – Prompts descriptifs pour chaque animal" in primary_output
    assert "Descriptions vivantes adaptées à la génération d'images." in primary_output
    assert "| 0.95 |" in primary_output

    assert "Section 3 : Prochaines étapes prioritaires" in primary_output
    assert (
        "- Introduire des animaux moins courants pour enrichir la variété des prompts." in primary_output
    )
    assert (
        "- Ajouter des contextes géographiques plus contrastés dans les descriptions." in primary_output
    )

    supporting_details = result["supporting_details"]
    assert "Points forts" in supporting_details
    assert "Axes d'amélioration" in supporting_details


def test_design_review_rollback_when_ai_fails() -> None:
    pipe = ReviewPipe(ai_payload=RuntimeError("token limit exceeded"))
    plan = _build_plan()

    completed_results = {
        "etape1": {"primary_output": "Lion\nChimpanzé\nColibri\nDauphin\nKangourou"},
        "etape2": {"primary_output": "Prompts immersifs détaillés"},
    }

    assembled_output = pipe._build_stepwise_execution_summary(plan, completed_results)

    result = asyncio.run(pipe.review_final_deliverable(plan, assembled_output))

    assert result["primary_output"] == assembled_output
    assert "Synthèse globale de la design review" not in result["primary_output"]
    assert "Design review indisponible" in result["supporting_details"]
