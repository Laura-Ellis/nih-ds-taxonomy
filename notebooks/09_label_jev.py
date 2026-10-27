# %% [markdown]
# # 09 Label the keyword-flagged projects with Jev
#
# Input: `data/processed/exporter_flagged_text.parquet` from notebook 08.
#
# Jev (Typesafe, through the Vercel AI Gateway) labels every flagged text: data science and AI
# (Y, M, or N) with a probability for each answer, the AI role, and category probabilities.
# Each unique text is labeled once (identical texts share labels). Results are cached in
# `data/interim/jev_labels_exporter.jsonl`, so the notebook is safe to stop and rerun.
# Next: notebook 10 sends the uncertain calls to ChatGPT.
#
# **Definitions**
# - Substantive = Y (in an aim or the approach); mention = M; none = N
# - Uncertain = Jev's top answer has probability < `CUTOFF`; those go to ChatGPT in notebook 10

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import jev_label as jev  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, REPORTS = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports"
JEV_MODEL = jev.DEFAULT_MODEL  # "typesafe-ai/jev" (version 1.14.0 at the time of the run)
CUTOFF = 0.90

flagged = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet")
texts = (flagged.drop_duplicates("text_hash")
         .assign(appl_id=lambda d: d.text_hash)[["appl_id", "project_title", "abstract_text"]])
length_factor = max(1.0, texts.abstract_text.str.len().mean() / 2_800)
print(f"{len(flagged):,} flagged records; {len(texts):,} unique texts; "
      f"average text is {length_factor:.1f}x a single abstract")

# %% [markdown]
# ## 1. Jev on every flagged text
# About $0.0002 per text at list price; progress prints every 2,000.

# %%
_stop = start("1. Jev on every flagged text")
JEV_CACHE = INTERIM / "jev_labels_exporter.jsonl"
CHUNK = 2_000
for i in range(0, len(texts), CHUNK):
    jev.label_projects(texts.iloc[i:i + CHUNK], JEV_CACHE, model=JEV_MODEL)
    say(f"Jev: {min(i + CHUNK, len(texts)):,} of {len(texts):,}")
jl = jev.label_projects(texts, JEV_CACHE, model=JEV_MODEL)
print(f"Jev labeled {len(jl):,} texts; cost ${jl.jev_cost.sum():.2f}")
_stop()
# %% [markdown]
# ## Jev results

# %%
_stop = start("Jev results")
def confidence(probs) -> float:
    return max(probs.values()) if isinstance(probs, dict) and probs else 0.0


jl["ai_conf"], jl["ds_conf"] = jl.jev_ai_probs.map(confidence), jl.jev_ds_probs.map(confidence)
print("Data science:", jl.jev_ds_related.value_counts(normalize=True).round(3).to_dict())
print("AI:", jl.jev_ai_related.value_counts(normalize=True).round(3).to_dict())
print("AI role (AI = Y):", jl[jl.jev_ai_related == "Y"].jev_ai_role.value_counts(normalize=True).round(3).to_dict())
unc_ai = (jl.ai_conf < CUTOFF).mean()
unc_any = ((jl.ai_conf < CUTOFF) | (jl.ds_conf < CUTOFF)).mean()
missing = len(texts) - len(jl)
print(f"Uncertain (< {CUTOFF}): AI {unc_ai:.1%}; AI or data science {unc_any:.1%}; "
      f"{missing:,} texts without Jev labels (also go to ChatGPT)")
print(f"Notebook 10: ~{unc_any * len(jl) + missing:,.0f} uncertain texts go to ChatGPT; at most "
      f"~${(unc_any * len(jl) + missing) * 0.00029 * length_factor:.2f} if none are saved yet "
      "(notebook 10 prints the cost of new texts only)")
_stop()
