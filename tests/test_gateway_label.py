import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import gateway_label as gw  # noqa: E402
import llm_label as llm  # noqa: E402

DEFS = llm.load_definitions()
LABELS = {"ds_related": "Y", "ai_related": "M", "ai_role": "applies_ai", "categories": ["machine_learning"],
          "evidence": "q"}


class FakeClient:
    """Stands in for the OpenAI client on the AI Gateway."""

    def __init__(self, first_text=False):
        self.calls, self.first_text = [], first_text
        self.chat = NS(completions=NS(create=self.create))
        self.models = NS(list=lambda: NS(data=[NS(id="google/gemini-x"), NS(id="openai/gpt-y"), NS(id="xai/z")]))

    def create(self, **kw):
        self.calls.append(kw)
        if self.first_text and len(self.calls) == 1:
            msg = NS(content="thinking...", tool_calls=None)
        else:
            msg = NS(content=None, tool_calls=[NS(function=NS(name="record_labels", arguments=json.dumps(LABELS)))])
        return NS(choices=[NS(message=msg, finish_reason="stop")], usage=NS(prompt_tokens=4000, completion_tokens=120))


def test_tool_call_parsed_and_cached(tmp_path):
    c = FakeClient()
    df = pd.DataFrame({"appl_id": [1, 2], "project_title": ["a", "b"], "abstract_text": ["x", None]})
    out = gw.label_projects(df, tmp_path / "g.jsonl", model="google/gemini-x", prefix="gemini", client=c)
    assert out.gemini_ai_related.tolist() == ["M", "M"] and out.gemini_categories.iloc[0] == ["machine_learning"]
    assert out.gemini_usage.iloc[0]["input_tokens"] == 4000
    assert c.calls[0]["tools"][0]["function"]["name"] == "record_labels"
    gw.label_projects(df, tmp_path / "g.jsonl", model="google/gemini-x", prefix="gemini", client=c)
    assert len(c.calls) == 2  # second run from cache


def test_retry_when_text_answer():
    c = FakeClient(first_text=True)
    out = gw.label_project(c, "t", "a", DEFS, "openai/gpt-y")
    assert out["ds_related"] == "Y" and len(c.calls) == 2


def test_available_models_filters():
    assert gw.available_models(FakeClient()) == ["google/gemini-x", "openai/gpt-y"]
