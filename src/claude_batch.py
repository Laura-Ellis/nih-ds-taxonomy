"""Claude labels through the Message Batches API (half the standard price, results within 24 hours).

Same prompt, tool, and rules as llm_label.label_project. Batch IDs are saved to a state file, so a
rerun picks up a batch already submitted instead of paying for it again. Results are written to the
same JSON Lines cache format as llm_label (keyed by `appl_id`, here the project's text hash).
Docs: https://docs.claude.com/en/docs/build-with-claude/batch-processing
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from llm_label import (DEFAULT_MODEL, PROMPT_VERSION, _json_from_text, build_system_prompt, build_tool, clean,
                       load_definitions, make_client)

MAX_PER_BATCH = 50_000  # API limit is 100,000 requests or 256 MB per batch


def build_request(custom_id: str, title: str, abstract: str, defs: dict, model: str = DEFAULT_MODEL) -> dict:
    return {"custom_id": custom_id,
            "params": {"model": model, "max_tokens": 4000,
                       "system": [{"type": "text", "text": build_system_prompt(defs),
                                   "cache_control": {"type": "ephemeral"}}],
                       "tools": [build_tool(defs)], "tool_choice": {"type": "auto"},
                       "messages": [{"role": "user", "content": f"Title: {title}\n\nAbstract:\n{abstract}"}]}}


def parse_result(result, defs: dict) -> tuple[dict | None, str]:
    """(labels or None, status). Status: ok, no_labels, refusal, errored, canceled, expired."""
    if result.type != "succeeded":
        return None, result.type
    msg = result.message
    block = next((b for b in msg.content if b.type == "tool_use"), None)
    if block is not None:
        return clean(block.input, defs), "ok"
    parsed = _json_from_text(msg.content)
    if parsed is not None:
        return clean(parsed, defs), "ok"
    return None, "refusal" if msg.stop_reason == "refusal" else "no_labels"


def cached_ids(cache: Path, model: str = DEFAULT_MODEL) -> set:
    if not Path(cache).exists():
        return set()
    recs = (json.loads(line) for line in Path(cache).read_text(encoding="utf-8").splitlines())
    return {r["appl_id"] for r in recs if r.get("model") == model and r.get("prompt_version") == PROMPT_VERSION}


def label_batch(df: pd.DataFrame, cache: Path, state: Path, model: str = DEFAULT_MODEL, client=None,
                poll_seconds: int = 60) -> pd.DataFrame:
    """Label df rows (appl_id, project_title, abstract_text) not yet in the cache, via batches.

    Blocks until every batch ends (usually under an hour; at most 24 hours). Safe to stop and rerun.
    """
    defs = load_definitions()
    cache, state = Path(cache), Path(state)
    client = client or make_client()
    saved = json.loads(state.read_text()) if state.exists() else {"batches": [], "failed": {}}
    done = cached_ids(cache, model)
    pending_in_batches = {cid for b in saved["batches"] if not b.get("collected") for cid in b["ids"]}
    todo = df[~df.appl_id.isin(done | pending_in_batches | set(saved["failed"]))]

    # Submit new work
    for i in range(0, len(todo), MAX_PER_BATCH):
        part = todo.iloc[i:i + MAX_PER_BATCH]
        reqs = [build_request(str(r.appl_id), r.project_title, str(r.abstract_text or ""), defs, model)
                for r in part.itertuples()]
        batch = client.messages.batches.create(requests=reqs)
        saved["batches"].append({"id": batch.id, "ids": [str(a) for a in part.appl_id], "collected": False})
        state.write_text(json.dumps(saved))
        print(f"Submitted batch {batch.id} with {len(reqs):,} requests")

    # Wait for and collect each batch
    for b in saved["batches"]:
        if b["collected"]:
            continue
        while True:
            info = client.messages.batches.retrieve(b["id"])
            if info.processing_status == "ended":
                break
            c = info.request_counts
            print(f"  {b['id']}: {c.succeeded + c.errored:,} of {len(b['ids']):,} done; checking again in "
                  f"{poll_seconds}s (safe to stop and rerun)")
            time.sleep(poll_seconds)
        n_ok = 0
        with cache.open("a", encoding="utf-8") as f:
            for r in client.messages.batches.results(b["id"]):
                labels, status = parse_result(r.result, defs)
                if labels is None:
                    saved["failed"][r.custom_id] = status
                    continue
                f.write(json.dumps({"appl_id": r.custom_id, "model": model, "prompt_version": PROMPT_VERSION,
                                    "via": "batch", **labels}) + "\n")
                n_ok += 1
        b["collected"] = True
        state.write_text(json.dumps(saved))
        print(f"Collected {b['id']}: {n_ok:,} labeled, {len(b['ids']) - n_ok:,} without labels")

    if saved["failed"]:
        print(f"{len(saved['failed']):,} requests without labels: "
              f"{pd.Series(saved['failed']).value_counts().to_dict()}; those keep their Jev labels")
    recs = [json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines()] if cache.exists() else []
    out = pd.DataFrame([r for r in recs if r.get("model") == model and r.get("prompt_version") == PROMPT_VERSION])
    out = out[out.appl_id.isin(set(df.appl_id.astype(str)))].drop_duplicates("appl_id", keep="last")
    return out.rename(columns={c: f"llm_{c}" for c in out.columns if c != "appl_id"})
