# %% [markdown]
# # 10 Resolve uncertain Jev calls with ChatGPT and finalize labels
#
# Input: notebook 09's Jev labels (`data/interim/jev_labels_exporter.jsonl`) and notebook 08's
# `exporter_flagged_text.parquet`, `exporter_core_projects.parquet`, and `exporter_applications.parquet`.
#
# 1. **ChatGPT (GPT-6 Luna)** relabels the calls where Jev is less than 90% confident, AI or data
#    science. It came within 0.02 κ of Claude on both labels at about one-twentieth of the cost
#    (METHODOLOGY.md, section 4). `src/claude_batch.py` keeps a Claude Batch API option.
# 2. Final labels are joined back to every project record, and counts are summarized by year.
#
# Results are cached, so the notebook is safe to stop and rerun.
#
# **Definitions**
# - Substantive = Y (in an aim or the approach); mention = M; none = N
# - Uncertain = Jev's top answer has probability < `CUTOFF`
# - Final label = ChatGPT's answer for uncertain calls, otherwise Jev's
# - Records the keywords did not flag are N for both (keywords miss an estimated 2–6%)

# %%
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import gateway_label as gw  # noqa: E402  # pyright: ignore[reportMissingImports]
import jev_label as jev  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, REPORTS = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports"
JEV_MODEL = jev.DEFAULT_MODEL  # "typesafe-ai/jev" (version 1.14.0 at the time of the run)
CUTOFF = 0.90
RESOLVE = "ai_or_ds"  # "ai": resolver only for uncertain AI calls; "ai_or_ds": uncertain AI or data science
RESOLVER_ROUTE, RESOLVER_MODEL = "gateway", "openai/gpt-6-luna"  # as tested in notebook 19
RESOLVER_PER_PROJECT = 0.00029  # measured in notebook 19: ~2,400 input and ~100 output tokens per abstract
MAX_RESOLVER_SPEND = 25  # USD; the notebook stops before resolving if the estimate is above this

import pyarrow.parquet as pq  # noqa: E402

if "attributed_cost" not in pq.read_schema(PROCESSED / "exporter_applications.parquet").names:
    raise RuntimeError("exporter_applications.parquet has no attributed_cost; rerun notebook 08 (fast: labels are cached)")
flagged = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet")
texts = (flagged.drop_duplicates("text_hash")
         .assign(appl_id=lambda d: d.text_hash)[["appl_id", "project_title", "abstract_text"]])
length_factor = max(1.0, texts.abstract_text.str.len().mean() / 2_800)
print(f"{len(flagged):,} flagged records; {len(texts):,} unique texts; "
      f"average text is {length_factor:.1f}x a single abstract")


# Jev labels from notebook 09 (read from the cache; texts Jev could not label count as uncertain)
JEV_CACHE = INTERIM / "jev_labels_exporter.jsonl"
CHUNK = 2_000
jl = jev.label_projects(texts, JEV_CACHE, model=JEV_MODEL)
print(f"Jev labels for {len(jl):,} of {len(texts):,} texts")

# %% [markdown]
# ## 1. ChatGPT on uncertain calls

# %%
_stop = start("1. ChatGPT on uncertain calls")
def confidence(probs) -> float:
    return max(probs.values()) if isinstance(probs, dict) and probs else 0.0


x = texts.merge(jl, on="appl_id", how="left")  # texts Jev failed on count as uncertain
x["jev_ai_conf"], x["jev_ds_conf"] = x.jev_ai_probs.map(confidence), x.jev_ds_probs.map(confidence)
x["uncertain"] = x.jev_ai_conf < CUTOFF
if RESOLVE == "ai_or_ds":
    x["uncertain"] |= x.jev_ds_conf < CUTOFF
to_resolve = x[x.uncertain]
# Only texts not already in the resolver's saved labels cost anything
RESOLVER_CACHE = INTERIM / f"{RESOLVER_MODEL.replace('/', '_')}_labels_exporter.jsonl"
cached = ({json.loads(line)["appl_id"] for line in RESOLVER_CACHE.read_text(encoding="utf-8").splitlines() if line.strip()}
          if RESOLVER_CACHE.exists() else set())
new_texts = int((~to_resolve.appl_id.isin(cached)).sum())
estimate = new_texts * RESOLVER_PER_PROJECT * length_factor
print(f"{len(to_resolve):,} uncertain texts ({x.uncertain.mean():.1%}) to {RESOLVER_MODEL}; "
      f"{len(to_resolve) - new_texts:,} already labeled, {new_texts:,} new; estimated cost ${estimate:.2f}")
if estimate > MAX_RESOLVER_SPEND:
    raise RuntimeError(f"Estimated ${estimate:.2f} is above MAX_RESOLVER_SPEND (${MAX_RESOLVER_SPEND}). "
                       'Raise the limit or set RESOLVE = "ai".')
_stop()

# %%
RESOLVER_CACHE = INTERIM / f"{RESOLVER_MODEL.replace('/', '_')}_labels_exporter.jsonl"
client = gw.make_client(RESOLVER_ROUTE)
for i in range(0, len(to_resolve), CHUNK):
    gw.label_projects(to_resolve.iloc[i:i + CHUNK], RESOLVER_CACHE, model=RESOLVER_MODEL, prefix="llm",
                      client=client, workers=8)
    say(f"Resolver: {min(i + CHUNK, len(to_resolve)):,} of {len(to_resolve):,}")
cl = (gw.label_projects(to_resolve, RESOLVER_CACHE, model=RESOLVER_MODEL, prefix="llm", client=client)
      if len(to_resolve) else pd.DataFrame(columns=["appl_id", "llm_ds_related", "llm_ai_related",
                                                    "llm_ai_role", "llm_categories"]))
cl = cl.drop(columns=[c for c in ("llm_usage", "llm_model", "llm_prompt_version") if c in cl])
print(f"Resolver labeled {len(cl):,} of {len(to_resolve):,} uncertain texts")

# %% [markdown]
# ## 2. Final labels

# %%
_stop = start("2. Final labels")
x = x.merge(cl, on="appl_id", how="left")
resolved = x.uncertain & x.llm_ai_related.notna()
for short in ("ds", "ai"):
    x[f"{short}_label"] = x[f"llm_{short}_related"].where(resolved, x[f"jev_{short}_related"]).fillna("N")
x["ai_role"] = x.llm_ai_role.where(resolved, x.jev_ai_role).where(x.ai_label != "N")
x["model_categories"] = x.llm_categories.where(resolved, x.jev_categories).map(
    lambda c: "; ".join(c) if isinstance(c, list) else "")
x["label_source"] = "jev"
x.loc[resolved, "label_source"] = RESOLVER_MODEL
x.loc[x.uncertain & ~resolved, "label_source"] = "jev (resolver unavailable)"
x.loc[x.jev_ai_related.isna() & ~resolved, "label_source"] = "none"
print(x.label_source.value_counts().to_dict())

labels = x[["appl_id", "ds_label", "ai_label", "ai_role", "model_categories", "label_source",
            "jev_ai_conf", "jev_ds_conf"]].rename(columns={"appl_id": "text_hash"})

core = pd.read_parquet(PROCESSED / "exporter_core_projects.parquet").merge(labels, on="text_hash", how="left")
not_flagged = ~core.ds_flag.fillna(False).astype(bool)
core.loc[not_flagged, ["ds_label", "ai_label"]] = "N"
core.loc[not_flagged, "label_source"] = "keywords (not flagged)"
core.to_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", index=False)
pd.crosstab(core.ds_label, core.ai_label, margins=True)
_stop()
# %% [markdown]
# ## Summary by fiscal year: substantive (Y) vs. any mention (Y or M)
# Funding uses `attributed_cost` from notebook 08, so center funding counts once.

# %%
_stop = start("Summary by fiscal year: substantive (Y) vs. any mention (Y or M)")
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["application_id", "fy", "core_project_number", "subproject_id", "attributed_cost"])
key = ["core_project_number", "subproject_id"]
apps = apps.merge(core[key + ["ds_label", "ai_label", "ai_role"]], on=key, how="left")
apps["record"] = apps.core_project_number + "|" + apps.subproject_id
summary = pd.DataFrame({
    "projects": apps.groupby("fy").record.nunique(),
    "ds_substantive": apps[apps.ds_label == "Y"].groupby("fy").record.nunique(),
    "ds_any": apps[apps.ds_label.isin(["Y", "M"])].groupby("fy").record.nunique(),
    "ai_substantive": apps[apps.ai_label == "Y"].groupby("fy").record.nunique(),
    "ai_any": apps[apps.ai_label.isin(["Y", "M"])].groupby("fy").record.nunique(),
}).fillna(0).astype(int)
summary["total_cost"] = apps.groupby("fy").attributed_cost.sum()
summary["ds_substantive_cost"] = apps[apps.ds_label == "Y"].groupby("fy").attributed_cost.sum()
summary["ai_substantive_cost"] = apps[apps.ai_label == "Y"].groupby("fy").attributed_cost.sum()
summary = summary.fillna(0).reset_index()
for c in ("ds_substantive", "ai_substantive"):
    summary[f"{c}_share"] = (summary[c] / summary.projects).round(3)
roles = apps[apps.ai_label == "Y"].groupby(["fy", "ai_role"]).record.nunique().unstack(fill_value=0)
summary = summary.merge(roles.add_prefix("ai_role_").reset_index(), on="fy", how="left")
summary.to_csv(REPORTS / "exporter_summary_labeled.csv", index=False)
summary
_stop()
