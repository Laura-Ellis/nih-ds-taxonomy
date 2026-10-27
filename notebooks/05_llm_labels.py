# %% [markdown]
# # 05 LLM review step (taxonomy v0.4)
#
# Keywords find candidate projects (high recall). An LLM then reads each title and abstract
# and decides, using the same rules as the hand coding:
#
# - **ds_related / ai_related:** Y (substantive), M (mention only), or N
# - **ai_role:** develops, applies, studies, or supports AI
# - **categories:** taxonomy category IDs for work the project itself does
#
# This notebook runs the LLM on the 150 coded projects and compares it with the codes.
#
# **Setup:** `pip install anthropic`, then set the `ANTHROPIC_API_KEY` environment variable.
# Results are cached in `data/interim/llm_labels.jsonl`, so reruns cost nothing.
#
# **Definitions**
# - Substantive = coded Y; any mention = coded Y or M
# - Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement)
# - Precision = flagged and coded / flagged; recall = flagged and coded / coded
# - Pipeline = keyword flag AND LLM says Y

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import llm_label as llm  # noqa: E402  # pyright: ignore[reportMissingImports]
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from coding import kappa, load_coded  # noqa: E402  # pyright: ignore[reportMissingImports]

REPORTS = ROOT / "reports"
CACHE = ROOT / "data" / "interim" / "llm_labels.jsonl"
MODEL = llm.DEFAULT_MODEL

sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
coded = load_coded(REPORTS)
val = sample[sample.appl_id.isin(coded.appl_id)]
kw = tx.label_projects(val)  # keyword labels for the coded projects only
print(f"{len(val)} coded projects to label with {MODEL}")

# %% [markdown]
# ## Run the LLM on the 150 coded projects
# About 2,500 input tokens and 150 output tokens per project; the instructions (about
# 1,900 tokens) are cached after the first call.

# %%
labels = llm.label_projects(val, CACHE, model=MODEL)
x = coded.merge(kw, on="appl_id").merge(labels, on="appl_id")
x.llm_ds_related.value_counts(), x.llm_ai_related.value_counts()

# %% [markdown]
# ## Agreement with the codes

# %%
rows = []
for label, kw_col, code_col, llm_col in [
        ("AI", "ai_related", "my_ai_related", "llm_ai_related"),
        ("Data science", "data_science_related", "my_ds_related", "llm_ds_related")]:
    truth = x[code_col].eq("Y")
    rows.append({"label": label, "method": "LLM (Y/M/N)", "kappa": kappa(x[llm_col], x[code_col]),
                 "precision": None, "recall": None})
    methods = [("Keywords", x[kw_col]), ("LLM", x[llm_col].eq("Y")),
               ("Pipeline: keywords + LLM", x[kw_col] & x[llm_col].eq("Y"))]
    if label == "AI":
        methods.insert(1, ("RCDC", x.rcdc_ml_ai.astype(bool)))
    for name, pred in methods:
        tp = (pred & truth).sum()
        rows.append({"label": label, "method": name, "kappa": kappa(pred, truth),
                     "precision": tp / pred.sum(), "recall": tp / truth.sum()})
agreement = pd.DataFrame(rows).round(2)
agreement.to_csv(REPORTS / "agreement_v0.4.csv", index=False)
agreement

# %%
print(pd.crosstab(x.my_ai_related, x.llm_ai_related, rownames=["coded AI"], colnames=["LLM AI"]))
print(pd.crosstab(x.my_ds_related, x.llm_ds_related, rownames=["coded DS"], colnames=["LLM DS"]))

# %% [markdown]
# ## Substantive AI: precision and recall by method

# %%
PRIMARY, HIGHLIGHT, INK, BG = "#596D69", "#B06F60", "#4F5152", "#F1EDE1"
ai = agreement[(agreement.label == "AI") & agreement.precision.notna()].set_index("method")
fig, ax = plt.subplots(figsize=(7, 3.2), facecolor=BG)
ax.set_facecolor(BG)
for i, (name, r) in enumerate(ai.iterrows()):
    color = HIGHLIGHT if name.startswith("Pipeline") else PRIMARY
    ax.plot([r.precision, r.recall], [i, i], color=color, alpha=0.4, lw=2)
    ax.scatter(r.precision, i, color=color, marker="o", s=60, zorder=3)
    ax.scatter(r.recall, i, color=color, marker="s", s=60, zorder=3)
ax.set_yticks(range(len(ai)), ai.index, color=INK)
ax.set_xlim(0.5, 1.02)
ax.set_xlabel("Share (circle = precision, square = recall)", color=INK)
ax.set_title("Substantive AI: precision and recall by method", loc="left", color=INK)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
plt.tight_layout()
fig.savefig(REPORTS / "llm_precision_recall.png", dpi=200)

# %% [markdown]
# ## Disagreements to review

# %%
dis = x[(x.my_ai_related != x.llm_ai_related) | (x.my_ds_related != x.llm_ds_related)]
dis[["appl_id", "project_title", "my_ds_related", "llm_ds_related", "my_ai_related",
     "llm_ai_related", "llm_ai_role", "llm_evidence"]].to_csv(REPORTS / "llm_disagreements.csv", index=False)
print(f"{len(dis)} disagreements saved to reports/llm_disagreements.csv")

# %% [markdown]
# ## Role of AI (no codes yet; review the evidence quotes)

# %%
x[x.llm_ai_related == "Y"].llm_ai_role.value_counts()

# %% [markdown]
# ## Category agreement (projects both sides call data science Y)
# The coded categories were drafted, not reviewed, so treat these as a rough check.

# %%
both = x[(x.my_ds_related == "Y") & (x.llm_ds_related == "Y")].copy()
both["mine"] = both.my_categories.fillna("").map(lambda v: {c.strip() for c in v.split(";") if c.strip()})
both["llm"] = both.llm_categories.map(set)
out = []
for c in sorted(set().union(*both.mine, *both.llm)):
    pred, truth = both.llm.map(lambda k, c=c: c in k), both.mine.map(lambda k, c=c: c in k)
    out.append({"category": c, "llm": pred.sum(), "coded": truth.sum(), "both": (pred & truth).sum()})
by_cat = pd.DataFrame(out)
by_cat["precision"] = (by_cat.both / by_cat.llm).round(2)
by_cat["recall"] = (by_cat.both / by_cat.coded).round(2)
by_cat.sort_values("coded", ascending=False)
