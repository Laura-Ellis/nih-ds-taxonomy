"""Jev (Typesafe System One model) labels through the Vercel AI Gateway.

Jev answers typed questions about a piece of text ("state") and returns a calibrated
probability for each answer. Each project becomes one request with:
- ds_related, ai_related: choice of Y / M / N (same rules as the coded sample and Claude)
- ai_role: choice of develops_ai / applies_ai / studies_ai / supports_ai / none
- cat_<id>: yes/no ("noul") probability for each taxonomy category

Output matches llm_label.label_projects (llm_* columns), plus probabilities, so notebooks
can compare the two directly. API docs: https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from llm_label import clean, get_key, load_definitions

URL = "https://ai-gateway.vercel.sh/typesafe/v1/systemone"
DEFAULT_MODEL = "typesafe-ai/jev"  # alias; resolved to jev-1.14.0 for the FY2016–2025 run (cached labels use this name)
PROMPT_VERSION = "0.4.0-jev"
CATEGORY_THRESHOLD = 0.5  # P(true) needed to assign a category

from prompts import PROMPTS  # noqa: E402  (tuned prompts are private; see src/prompts.py)

DS_INSTRUCTIONS = PROMPTS["jev_ds_instructions"]
AI_INSTRUCTIONS = PROMPTS["jev_ai_instructions"]
YMN = PROMPTS["jev_ymn"]


def build_questions(defs: dict) -> dict:
    roles = {r["id"]: r["definition"] for r in defs["roles"]}
    roles["none"] = "The project does not use or build AI."
    q = {
        "ds_related": {"type": "choice", "instructions": DS_INSTRUCTIONS, "criteria": YMN},
        "ai_related": {"type": "choice", "instructions": AI_INSTRUCTIONS, "criteria": YMN},
        "ai_role": {"type": "choice", "instructions": "What role does AI play in this project?", "criteria": roles},
    }
    for c in defs["categories"]:
        q[f"cat_{c['id']}"] = {
            "type": "noul",
            "instructions": f"Does the project itself do work in this area ({c['label']}): {c['definition']} "
                            "Count only work the project does, not background.",
        }
    return q


def _choice(answer: dict) -> tuple[str | None, dict]:
    """Return (chosen label, probabilities) from a choice answer, whatever the field name."""
    probs = answer.get("probabilities") or {}
    for key in ("choice", "value", "answer", "selected"):
        if isinstance(answer.get(key), str):
            return answer[key], probs
    return (max(probs, key=probs.get) if probs else None), probs


def parse(answers: dict, defs: dict) -> dict:
    ds, ds_p = _choice(answers["ds_related"])
    ai, ai_p = _choice(answers["ai_related"])
    role, _ = _choice(answers.get("ai_role", {}))
    cat_p = {k[4:]: a.get("noul", 0.0) for k, a in answers.items() if k.startswith("cat_")}
    out = clean({"ds_related": ds, "ai_related": ai, "ai_role": None if role == "none" else role,
                 "categories": [c for c, p in cat_p.items() if p >= CATEGORY_THRESHOLD], "evidence": ""}, defs)
    out.update({"ds_probs": ds_p, "ai_probs": ai_p, "category_probs": cat_p})
    return out


def label_project(session, title: str, abstract: str, defs: dict, model: str = DEFAULT_MODEL) -> dict:
    resp = session.post(URL, json={"model": model, "state": f"Title: {title}\n\nAbstract:\n{abstract}",
                                   "questions": build_questions(defs)}, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    out = parse(body["answers"], defs)
    cost = body.get("provider_metadata", {}).get("gateway", {}).get("cost")
    out.update({"usage": body.get("usage", {}), "cost": float(cost) if cost else None})
    return out


def make_session():
    import requests

    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {get_key('AI_GATEWAY_API_KEY', 'Vercel AI Gateway')}",
                      "Content-Type": "application/json"})
    return s


def label_projects(df: pd.DataFrame, cache: Path, session=None, model: str = DEFAULT_MODEL,
                   workers: int = 8) -> pd.DataFrame:
    """Label every row of df (appl_id, project_title, abstract_text), using and extending the cache."""
    defs = load_definitions()
    cache = Path(cache)
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("model") == model and rec.get("prompt_version") == PROMPT_VERSION:
                done[rec["appl_id"]] = rec
    todo = df[~df.appl_id.isin(done)]
    failed = []
    if len(todo):
        session = session or make_session()
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(label_project, session, r.project_title, str(r.abstract_text or ""),
                                   defs, model): r.appl_id for r in todo.itertuples()}
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as e:  # one bad response should not stop the run
                    failed.append((futures[fut], str(e)[:200]))
                    continue
                rec = {"appl_id": futures[fut], "model": model, "prompt_version": PROMPT_VERSION, **result}
                f.write(json.dumps(rec) + "\n")
                f.flush()
                done[rec["appl_id"]] = rec
        print(f"Labeled {len(todo) - len(failed)} new projects; {len(df) - len(todo)} from cache")
        for appl_id, err in failed[:5]:
            print(f"  Failed {appl_id}: {err}")
        if failed:
            print(f"{len(failed)} failed; rerun to retry them")
    out = pd.DataFrame([done[a] for a in df.appl_id if a in done])
    if out.empty:
        raise RuntimeError("No projects labeled; see the errors above")
    return out.rename(columns={c: f"jev_{c}" for c in out.columns if c != "appl_id"})
