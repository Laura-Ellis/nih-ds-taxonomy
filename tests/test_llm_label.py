import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import llm_label as llm  # noqa: E402
from coding import kappa  # noqa: E402

DEFS = llm.load_definitions()


class FakeClient:
    """Stands in for anthropic.Anthropic; returns a fixed tool call and records requests."""

    def __init__(self, labels):
        self.labels, self.calls = labels, []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=dict(self.labels))])


def test_definitions_split_roles_from_categories():
    assert [r["id"] for r in DEFS["roles"]] == ["develops_ai", "applies_ai", "studies_ai", "supports_ai"]
    ids = {c["id"] for c in DEFS["categories"]}
    assert {"deep_learning", "omics", "training_education"} <= ids and "applies_ai" not in ids


def test_prompt_lists_every_category_and_rule():
    p = llm.build_system_prompt(DEFS)
    assert all(c["id"] in p for c in DEFS["categories"])
    assert "Standard sequencing analysis" in p and "is not AI" in p


def test_clean_enforces_rules():
    out = llm.clean({"ds_related": "N", "ai_related": "Y", "ai_role": "applies_ai",
                     "categories": ["deep_learning"], "evidence": ""}, DEFS)
    assert out["ai_related"] == "N" and out["ai_role"] is None and out["categories"] == []
    out = llm.clean({"ds_related": "Y", "ai_related": "M", "ai_role": "applies_ai",
                     "categories": ["deep_learning", "not_a_category"], "evidence": "x"}, DEFS)
    assert out["categories"] == ["deep_learning"] and out["ai_role"] == "applies_ai"


def test_label_projects_caches(tmp_path):
    client = FakeClient({"ds_related": "Y", "ai_related": "Y", "ai_role": "applies_ai",
                         "categories": ["machine_learning"], "evidence": "we will train a model"})
    df = pd.DataFrame({"appl_id": [1, 2], "project_title": ["a", "b"], "abstract_text": ["x", None]})
    cache = tmp_path / "labels.jsonl"
    out = llm.label_projects(df, cache, client=client)
    assert len(client.calls) == 2 and out.llm_ai_related.tolist() == ["Y", "Y"]
    assert client.calls[0]["tool_choice"]["name"] == "record_labels"
    llm.label_projects(df, cache, client=client)  # second run: all cached
    assert len(client.calls) == 2


def test_kappa():
    assert kappa(["Y", "N", "M"], ["Y", "N", "M"]) == 1
    assert round(kappa([True, True, False, False], [True, False, True, False]), 2) == 0
