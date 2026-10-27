import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import jev_label as jev  # noqa: E402
import llm_label as llm  # noqa: E402

DEFS = llm.load_definitions()


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, json, timeout):
        self.calls.append(json)
        answers = {"ds_related": {"type": "choice", "choice": "Y", "probabilities": {"Y": 0.9, "M": 0.08, "N": 0.02}},
                   "ai_related": {"type": "choice", "probabilities": {"Y": 0.7, "M": 0.2, "N": 0.1}},
                   "ai_role": {"type": "choice", "choice": "applies_ai"}}
        answers.update({k: {"type": "noul", "noul": 0.9 if k == "cat_machine_learning" else 0.1}
                        for k in json["questions"] if k.startswith("cat_")})
        body = {"answers": answers, "usage": {"input_tokens": 900},
                "provider_metadata": {"gateway": {"cost": "0.00004"}}}
        return SimpleNamespace(status_code=200, json=lambda: body, text="")


def test_questions_cover_labels_and_categories():
    q = jev.build_questions(DEFS)
    assert {"ds_related", "ai_related", "ai_role"} <= q.keys()
    assert sum(k.startswith("cat_") for k in q) == len(DEFS["categories"])
    assert set(q["ai_related"]["criteria"]) == {"Y", "M", "N"}


def test_label_projects_parses_and_caches(tmp_path):
    s = FakeSession()
    df = pd.DataFrame({"appl_id": [1], "project_title": ["t"], "abstract_text": ["a"]})
    out = jev.label_projects(df, tmp_path / "j.jsonl", session=s)
    r = out.iloc[0]
    assert r.jev_ds_related == "Y" and r.jev_ai_related == "Y"  # argmax when no choice field
    assert r.jev_ai_role == "applies_ai" and r.jev_categories == ["machine_learning"]
    assert abs(r.jev_cost - 0.00004) < 1e-12
    jev.label_projects(df, tmp_path / "j.jsonl", session=s)
    assert len(s.calls) == 1


def test_get_key_reads_keys_file(tmp_path, monkeypatch):
    f = tmp_path / "KEYS.md"
    f.write_text("### Anthropic\n- **Key:** `a1`\n\n### Vercel AI Gateway (Jev)\n- **Key:** `v2`\n")
    monkeypatch.setenv("KEYS_FILE", str(f))
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    assert llm.get_key("AI_GATEWAY_API_KEY", "Vercel AI Gateway") == "v2"
