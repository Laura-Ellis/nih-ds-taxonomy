"""Labeling prompts for the LLM review step.

The tuned prompts are private (prompts/labeling_prompts.yaml, git-ignored). Without them the code falls
back to config/prompts.example.yaml, which runs end to end but gives different labels. METHODOLOGY.md
describes what the prompts cover.
"""

import warnings
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "prompts" / "labeling_prompts.yaml"
EXAMPLE = ROOT / "config" / "prompts.example.yaml"


def load_prompts() -> dict:
    if PRIVATE.exists():
        return yaml.safe_load(PRIVATE.read_text(encoding="utf-8"))
    warnings.warn("prompts/labeling_prompts.yaml not found; using config/prompts.example.yaml (labels will differ "
                  "from the published results)", stacklevel=2)
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


PROMPTS = load_prompts()
