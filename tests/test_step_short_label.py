from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from planner import _build_step_short_label


def test_short_label_focuses_on_prompt_subject() -> None:
    description = (
        "Rédiger un prompt pour un mammifère spécifique, en mentionnant des caractéristiques"
        " détaillées comme l'environnement et le style artistique."
    )
    assert _build_step_short_label(description) == "Prompt mammifère spécifique"


def test_short_label_trims_trailing_stopwords() -> None:
    description = "Create a prompt for a tropical bird with rainforest context and lighting."
    assert _build_step_short_label(description) == "Prompt tropical bird"
