"""LLM labels from Gemini, ChatGPT, or any model on the Vercel AI Gateway.

Same prompt, rules, and output as llm_label.py (Claude), through OpenAI-compatible chat APIs, so
models can be swapped and compared. Routes (key looked up in ~/KEYS.md by heading):
- "openai": OpenAI API directly ("### OpenAI")
- "gemini": Google Gemini API directly, OpenAI-compatible endpoint ("### Google (Gemini)")
- "gateway": Vercel AI Gateway, any provider with one key ("### Vercel AI Gateway")
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from llm_label import PROMPT_VERSION, build_system_prompt, build_tool, clean, get_key, load_definitions

BASE_URL = "https://ai-gateway.vercel.sh/v1"
ROUTES = {  # route: (base URL, environment variable, KEYS.md heading)
    "gateway": (BASE_URL, "AI_GATEWAY_API_KEY", "Vercel AI Gateway"),
    "openai": (None, "OPENAI_API_KEY", "OpenAI"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "Gemini"),
}


def make_client(route: str = "gateway"):
    from openai import OpenAI

    base_url, env_var, heading = ROUTES[route]
    return OpenAI(api_key=get_key(env_var, heading), base_url=base_url)


def available_models(client, prefixes=("google/", "openai/", "anthropic/", "gemini", "gpt", "o")) -> list[str]:
    """Model IDs the client can use, to check a name before a run ('models/' prefix removed)."""
    ids = (m.id.removeprefix("models/") for m in client.models.list().data)
    return sorted(i for i in ids if i.startswith(prefixes))


def _tool(defs: dict) -> dict:
    t = build_tool(defs)
    return {"type": "function",
            "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}


def _parse(message) -> dict | None:
    calls = getattr(message, "tool_calls", None) or []
    for c in calls:
        if c.function.name == "record_labels":
            return json.loads(c.function.arguments)
    m = re.search(r"\{.*\}", message.content or "", re.S)  # labels written as JSON text instead
    if m:
        try:
            d = json.loads(m.group(0))
            return d if {"ds_related", "ai_related"} <= d.keys() else None
        except json.JSONDecodeError:
            return None
    return None


def label_project(client, title: str, abstract: str, defs: dict, model: str) -> dict:
    messages = [{"role": "system", "content": build_system_prompt(defs)},
                {"role": "user", "content": f"Title: {title}\n\nAbstract:\n{abstract}"}]
    for _ in range(2):
        resp = client.chat.completions.create(model=model, messages=messages, tools=[_tool(defs)],
                                              tool_choice="auto", max_tokens=1500)
        msg = resp.choices[0].message
        labels = _parse(msg)
        if labels is not None:
            out = clean({"ai_role": None, "categories": [], "evidence": "", **labels}, defs)
            usage = getattr(resp, "usage", None)
            out["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", None),
                            "output_tokens": getattr(usage, "completion_tokens", None)}
            return out
        messages = messages + [{"role": "assistant", "content": msg.content or ""},
                               {"role": "user", "content": "Call the record_labels tool with your labels."}]
    raise RuntimeError(f"No labels returned (finish_reason={resp.choices[0].finish_reason}) for: {title[:60]}")


def label_projects(df: pd.DataFrame, cache: Path, model: str, prefix: str, client=None,
                   route: str = "gateway", workers: int = 4) -> pd.DataFrame:
    """Label rows of df (appl_id, project_title, abstract_text); columns are named <prefix>_*."""
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
        client = client or make_client(route)
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(label_project, client, r.project_title, str(r.abstract_text or ""),
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
        print(f"{model}: labeled {len(todo) - len(failed)} new projects; {len(df) - len(todo)} from cache")
        for appl_id, err in failed[:5]:
            print(f"  Failed {appl_id}: {err}")
    out = pd.DataFrame([done[a] for a in df.appl_id if a in done])
    if out.empty:
        raise RuntimeError(f"No projects labeled with {model}; see the errors above")
    return out.rename(columns={c: f"{prefix}_{c}" for c in out.columns if c != "appl_id"})
