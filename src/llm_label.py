"""LLM review step for the NIH Data Science Taxonomy (v0.4).

For each project, an LLM reads the title and abstract and returns:
- ds_related and ai_related: Y (substantive), M (mention only), or N
- ai_role: develops_ai, applies_ai, studies_ai, or supports_ai (AI projects only)
- categories: taxonomy category IDs for work the project itself does
- evidence: a short quote supporting the call

Keywords find candidates (recall); this step decides substantive vs. mention (precision).
Results are cached to a JSON Lines file, one line per project, so reruns only call the
API for new projects.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-sonnet-5-5"
PROMPT_VERSION = "0.4.0"

from prompts import PROMPTS  # noqa: E402  (tuned prompts are private; see src/prompts.py)

RULES = PROMPTS["llm_rules"]


def load_definitions(path: Path | None = None) -> dict:
    """Return {"roles": [...], "categories": [...]} with id, label, definition, dimension."""
    path = path or ROOT / "taxonomy" / "categories.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    roles, cats = [], []

    def walk(dim, items, group=None):
        for item in items:
            if "categories" in item:  # a group inside a dimension
                walk(dim, item["categories"], item["id"])
            else:
                rec = {"id": item["id"], "label": item["label"],
                       "definition": item.get("definition", ""), "dimension": dim["id"]}
                (roles if dim.get("method") == "llm" else cats).append(rec)

    for dim in doc["dimensions"]:
        walk(dim, dim.get("categories", []) or dim.get("groups", []))
    return {"roles": roles, "categories": cats}


def build_system_prompt(defs: dict) -> str:
    roles = "\n".join(f"  {r['id']}: {r['definition']}" for r in defs["roles"])
    cats, last = [], None
    for c in defs["categories"]:
        if c["dimension"] != last:
            cats.append(f"  [{c['dimension']}]")
            last = c["dimension"]
        cats.append(f"    {c['id']}: {c['label']}. {c['definition']}")
    return RULES.format(roles=roles, categories="\n".join(cats))


def build_tool(defs: dict) -> dict:
    yn = {"type": "string", "enum": ["Y", "M", "N"]}
    return {
        "name": "record_labels",
        "description": "Record the taxonomy labels for one project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ds_related": yn,
                "ai_related": yn,
                "ai_role": {"type": ["string", "null"], "enum": [r["id"] for r in defs["roles"]] + [None]},
                "categories": {"type": "array",
                               "items": {"type": "string", "enum": [c["id"] for c in defs["categories"]]}},
                "evidence": {"type": "string"},
            },
            "required": ["ds_related", "ai_related", "ai_role", "categories", "evidence"],
        },
    }


def clean(labels: dict, defs: dict) -> dict:
    """Enforce the rules the model can get wrong: AI needs DS, roles need AI, categories need DS."""
    out = dict(labels)
    if out["ds_related"] == "N":
        out["ai_related"] = "N"
    if out["ai_related"] == "N":
        out["ai_role"] = None
    valid = {c["id"] for c in defs["categories"]}
    out["categories"] = [c for c in out.get("categories", []) if c in valid] if out["ds_related"] == "Y" else []
    return out


def label_project(client, title: str, abstract: str, defs: dict, model: str = DEFAULT_MODEL) -> dict:
    """One API call. The system prompt is cached, so only the abstract is billed at full rate after the first call.

    Some models do not accept a forced tool call, so the model chooses the tool (tool_choice auto);
    if it answers in text instead, it is asked once more to call record_labels.
    """
    messages = [{"role": "user", "content": f"Title: {title}\n\nAbstract:\n{abstract}"}]
    for _ in range(2):
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            system=[{"type": "text", "text": build_system_prompt(defs), "cache_control": {"type": "ephemeral"}}],
            tools=[build_tool(defs)],
            tool_choice={"type": "auto"},
            messages=messages,
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        if block is not None:
            return clean(block.input, defs)
        parsed = _json_from_text(resp.content)  # labels written as JSON text instead of a tool call
        if parsed is not None:
            return clean(parsed, defs)
        messages = messages + [{"role": "assistant", "content": resp.content},
                               {"role": "user", "content": "Call the record_labels tool with your labels."}]
    raise RuntimeError(f"No labels returned (stop_reason={resp.stop_reason}) for: {title[:60]}")


def _json_from_text(content) -> dict | None:
    import re
    text = " ".join(getattr(b, "text", "") for b in content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return d if {"ds_related", "ai_related"} <= d.keys() else None


def get_key(env_var: str, keys_heading: str) -> str:
    """Find an API key: environment variable, then .env at the repo root, then the
    "**Key:** `...`" line under a "### <keys_heading>" heading in ~/KEYS.md (or $KEYS_FILE)."""
    import os
    import re

    if os.environ.get(env_var):
        return os.environ[env_var]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == env_var and value.strip():
                return value.strip().strip('"').strip("'")
    keys_file = Path(os.environ.get("KEYS_FILE", Path.home() / "KEYS.md"))
    detail = f"{keys_file} not found"
    if keys_file.exists():
        text = keys_file.read_text(encoding="utf-8-sig")
        # Heading: any markdown heading level, case-insensitive, words in any spacing
        words = r"\s+".join(map(re.escape, keys_heading.split()))
        section = re.search(rf"^#+[^\n]*{words}.*?(?=^#+\s|\Z)", text, re.S | re.M | re.I)
        if not section:
            detail = f"no heading containing '{keys_heading}' in {keys_file}"
        else:
            # Key line: "**Key:** `abc`", "**Key:** abc", or "Key: abc"
            for line in section.group(0).splitlines():
                m = re.match(r"^[\s*-]*Key\b(.*)$", line, re.I)
                if m:
                    value = m.group(1).strip().strip(":*` \t").strip()
                    if value:
                        return value.split()[0].strip("`")
            detail = f"heading '{keys_heading}' found in {keys_file}, but its Key line is empty or not readable"
    raise RuntimeError(f"No {env_var} found: {detail}. You can also set the {env_var} environment variable.")


def make_client():
    """Anthropic client; the key comes from get_key (environment, .env, or KEYS.md)."""
    import anthropic

    return anthropic.Anthropic(api_key=get_key("ANTHROPIC_API_KEY", "Anthropic"))


def label_projects(df: pd.DataFrame, cache: Path, client=None, model: str = DEFAULT_MODEL,
                   workers: int = 4) -> pd.DataFrame:
    """Label every row of df (needs appl_id, project_title, abstract_text), using and extending the cache."""
    defs = load_definitions()
    cache = Path(cache)
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("model") == model and rec.get("prompt_version") == PROMPT_VERSION:
                done[rec["appl_id"]] = rec
    todo = df[~df.appl_id.isin(done)]
    if len(todo):
        if client is None:
            client = make_client()
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(label_project, client, r.project_title, str(r.abstract_text or ""),
                                   defs, model): r.appl_id for r in todo.itertuples()}
            failed = []
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as e:  # one bad response should not stop the run
                    failed.append((futures[fut], str(e)[:120]))
                    continue
                rec = {"appl_id": futures[fut], "model": model, "prompt_version": PROMPT_VERSION, **result}
                f.write(json.dumps(rec) + "\n")
                f.flush()
                done[rec["appl_id"]] = rec
        print(f"Labeled {len(todo) - len(failed)} new projects; {len(df) - len(todo)} from cache")
        for appl_id, err in failed:
            print(f"  Failed {appl_id}: {err}")
        if failed:
            print(f"{len(failed)} failed; rerun to retry them (the rest are cached)")
    out = pd.DataFrame([done[a] for a in df.appl_id if a in done])
    return out.rename(columns={c: f"llm_{c}" for c in out.columns if c not in ("appl_id",)})
