from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import Action, Pipe, Plan  # noqa: E402


class FinalSynthesisRenderingPipe(Pipe):
    def __init__(self) -> None:
        super().__init__()
        self.captured_messages: list[str] = []
        self.__current_event_emitter__ = self._capture_event  # type: ignore[assignment]
        self.__current_event_call__ = self._noop_event_call  # type: ignore[assignment]
        self.valves.SHOW_ACTION_SUMMARIES = False

    async def get_completion(  # type: ignore[override]
        self,
        prompt,
        model: str | dict[str, object] = "",
        tools: dict[str, dict[object, object]] | None = None,
        format: dict[str, object] | None = None,
        action_results: dict[str, dict[str, str]] | None = None,
        action=None,
    ) -> str:
        if not isinstance(prompt, str):
            raise AssertionError("Unexpected non-string prompt for design review")

        context_payload: dict[str, object] = {}
        if "Contexte:" in prompt:
            _, context_block = prompt.split("Contexte:\n", 1)
            try:
                context_payload = json.loads(context_block)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
                raise AssertionError(f"Invalid context payload: {exc}") from exc

        goal_text = str(context_payload.get("goal", "")) if context_payload else ""
        steps_payload = context_payload.get("steps", []) if isinstance(context_payload, dict) else []

        steps_response: list[dict[str, object]] = []
        priorities: list[str] = []

        if isinstance(steps_payload, list):
            for index, entry in enumerate(steps_payload, start=1):
                if not isinstance(entry, dict):
                    continue
                description = str(entry.get("description", "")).strip()
                action_id = str(entry.get("action_id", "")).strip()
                quality_summary = str(entry.get("quality_summary", "")).strip()

                suggestions = [
                    str(item).strip()
                    for item in (entry.get("suggestions") or [])
                    if str(item).strip()
                ]
                issues = [
                    str(item).strip()
                    for item in (entry.get("issues") or [])
                    if str(item).strip()
                ]

                overview = description or f"Étape {index}"
                strengths = [quality_summary] if quality_summary else ["Livrable conforme."]
                improvements = (
                    suggestions + issues
                    if suggestions
                    else (issues or ["Aucun axe d'amélioration identifié."])
                )

                if suggestions:
                    priorities.append(
                        f"Étape {index} – {overview} : {suggestions[0]}"
                    )

                steps_response.append(
                    {
                        "action_id": action_id,
                        "step_overview": overview,
                        "strengths": strengths,
                        "improvements": improvements,
                    }
                )

        if not priorities:
            priorities.append("Maintenir la qualité actuelle.")

        return json.dumps(
            {
                "request_summary": goal_text or "Synthèse du dispositif OptiScan.",
                "work_summary": "Les livrables des étapes ont été analysés et résumés.",
                "steps": steps_response,
                "priorities": priorities,
            }
        )

    async def _capture_event(self, event: dict[str, Any]) -> None:
        if event["type"] == "message":
            self.captured_messages.append(event["data"]["content"])
        # Other event types are not relevant for this test but must be absorbed.

    async def _noop_event_call(self, *_args: Any, **_kwargs: Any) -> str:
        return ""

    async def execute_action(  # type: ignore[override]
        self,
        plan: Plan,
        action: Action,
        context: dict[str, Any],
        step_number: int,
    ) -> dict[str, str]:
        outputs = {
            "executive_summary": {
                "primary_output": "Summary content with clear narrative.",
                "supporting_details": "Compiled from prior research.",
            },
            "product_objectives": {
                "primary_output": "```sql\nSELECT * FROM roadmap WHERE priority = 'high';\n```",
                "supporting_details": "Prioritized deliverables list.",
            },
        }

        quality_snapshots = {
            "executive_summary": {
                "quality_score": 0.92,
                "summary": "Narration complète et précise.",
                "issues": [],
                "suggestions": ["Valider le ton avec l'équipe produit."],
            },
            "product_objectives": {
                "quality_score": 0.68,
                "summary": "Liste pertinente mais encore perfectible.",
                "issues": ["Ajouter un objectif sur la scalabilité."],
                "suggestions": ["Clarifier les métriques d'impact attendues."],
            },
        }

        if action.id not in outputs:
            raise AssertionError(f"Unexpected action requested in test: {action.id}")

        result = outputs[action.id]
        action.output = result
        action.status = "completed"
        action.end_time = datetime.now().strftime("%H:%M:%S")

        plan.metadata.setdefault("raw_action_outputs", {})[action.id] = result
        plan.metadata.setdefault("action_quality", {})[action.id] = (
            quality_snapshots[action.id]
        )
        return result


def run_execute_plan(pipe: FinalSynthesisRenderingPipe, plan: Plan) -> None:
    asyncio.run(pipe.execute_plan(plan))


def test_final_synthesis_outputs_step_summaries_and_review() -> None:
    pipe = FinalSynthesisRenderingPipe()

    plan = Plan(
        goal="Validate final synthesis rendering",
        actions=[
            Action(
                id="executive_summary",
                type="text",
                description="Draft the executive summary",
            ),
            Action(
                id="product_objectives",
                type="text",
                description="List the key objectives",
            ),
            Action(
                id="final_synthesis",
                type="text",
                description=(
                    "Final Deliverable: OptiScan IR – Portable Ocular Pre-Diagnosis Device\n"
                    "Executive Summary\n{{executive_summary}}\n\n"
                    "Product Objectives\n{{product_objectives}}"
                ),
                dependencies=["executive_summary", "product_objectives"],
            ),
        ],
    )

    run_execute_plan(pipe, plan)

    final_action = next(a for a in plan.actions if a.id == "final_synthesis")
    assert final_action.output is not None

    primary_output = final_action.output.get("primary_output", "")
    assert primary_output, "Final synthesis output should not be empty"
    assert "## Résultats par étape" in primary_output
    assert "Étape 1 · Draft the executive summary" in primary_output
    assert "Score qualité : 0.92" in primary_output
    assert "Commentaires qualité : Narration complète et précise." in primary_output
    assert "Summary content with clear narrative." in primary_output
    assert "Étape 2 · List the key objectives" in primary_output
    assert "Score qualité : 0.68" in primary_output
    assert "```sql\nSELECT * FROM roadmap WHERE priority = 'high';\n```" in primary_output
    assert "Ajouter un objectif sur la scalabilité." in primary_output

    review_output = final_action.output.get("supporting_details", "")
    assert "### Points forts" in review_output
    assert "Draft the executive summary" in review_output
    assert "### Axes d'amélioration" in review_output
    assert "Ajouter un objectif sur la scalabilité." in review_output
    assert "### Priorités" in review_output
    assert "Clarifier les métriques d'impact attendues." in review_output
    assert "```sql\nSELECT * FROM roadmap WHERE priority = 'high';\n```" not in review_output

    final_metadata = plan.metadata.get("final_synthesis", {})
    assert final_metadata.get("stepwise_summary") == primary_output

    raw_outputs = plan.metadata.get("raw_action_outputs", {})
    assert raw_outputs.get("executive_summary", {}).get(
        "primary_output"
    ) == "Summary content with clear narrative."
    assert raw_outputs.get("product_objectives", {}).get("primary_output") == (
        "```sql\nSELECT * FROM roadmap WHERE priority = 'high';\n```"
    )
