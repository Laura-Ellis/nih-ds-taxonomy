# %% [markdown]
# # 02 Test the taxonomy on the sample
#
# 1. Label the sample with the keyword baseline (`src/taxonomy.py`).
# 2. Compare `ai_related` with the RCDC category "Machine Learning and Artificial Intelligence".
# 3. Show how often each category fires, by stratum.
# 4. Export a review workbook to hand-code a random subset.
#
# **Definitions**
# - RCDC = Research, Condition, and Disease Categorization (NIH's spending categories)
# - Agreement = share of projects where the keyword label and RCDC agree
# - Precision = keyword AI projects that RCDC also flags / all keyword AI projects
# - Recall = keyword AI projects that RCDC also flags / all RCDC AI projects

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "config"))
import taxonomy as tx  # noqa: E402

RAW, PROCESSED, REPORTS = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "reports"
PROCESSED.mkdir(parents=True, exist_ok=True)

sample_file = sorted(RAW.glob("reporter_sample_2*.csv"))[-1]
sample = pd.read_csv(sample_file)
print(f"{len(sample):,} projects from {sample_file.name}")

# %%
labeled = tx.label_projects(sample)
labeled.to_csv(PROCESSED / "sample_labeled.csv", index=False)

# %% [markdown]
# ## Keyword `ai_related` vs. RCDC "Machine Learning and Artificial Intelligence"

# %%
ct = pd.crosstab(labeled.ai_related, labeled.rcdc_ml_ai, margins=True)
tp = ((labeled.ai_related) & (labeled.rcdc_ml_ai)).sum()
precision = tp / labeled.ai_related.sum()
recall = tp / labeled.rcdc_ml_ai.sum()
agreement = (labeled.ai_related == labeled.rcdc_ml_ai).mean()
print(f"Agreement {agreement:.1%} · Precision {precision:.1%} · Recall {recall:.1%}")
ct

# %% [markdown]
# ## How often each category fires, by stratum

# %%
cats = tx.load_categories()
long = labeled[["appl_id", "stratum", "categories"]].explode("categories").dropna()
share = (long.groupby(["categories", "stratum"]).appl_id.nunique()
         .div(labeled.groupby("stratum").appl_id.nunique(), level="stratum")
         .unstack(fill_value=0).reindex(cats.category_id).fillna(0))
share.index = cats.set_index("category_id").label.reindex(share.index)

fig, ax = plt.subplots(figsize=(9, 10))
share.sort_values("ai_search").plot.barh(ax=ax, color=["#596D69", "#CDC4B7", "#B06F60"], width=0.8)
ax.set_xlabel("Share of sampled projects with the category")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_title("Most categories fire in the AI search stratum, few in general projects", loc="left")
ax.legend(title="Stratum", frameon=False)
fig.tight_layout()
fig.savefig(REPORTS / "category_share_by_stratum.png", dpi=200)
plt.show()

# %% [markdown]
# ## Review workbook
#
# A random 150 projects (50 per stratum). For each, read the abstract and fill in:
# `my_ds_related` (Y/N), `my_ai_related` (Y/N), `my_categories` (category IDs, separated by ;), `missed_terms`,
# `false_positive_terms`, and `notes`. These become the hand-coded validation set.

# %%
review = pd.concat(g.sample(min(50, len(g)), random_state=20261023)
                   for _, g in labeled.groupby("stratum"))
review = review[["appl_id", "project_num", "fiscal_year", "ic", "activity_code", "stratum",
                 "project_title", "abstract_text", "rcdc_ml_ai", "data_science_related", "ai_related",
                 "categories", "matched_terms"]].copy()
review["categories"] = review.categories.map("; ".join)
for col in ["my_ds_related", "my_ai_related", "my_categories", "missed_terms", "false_positive_terms", "notes"]:
    review[col] = ""

with pd.ExcelWriter(REPORTS / "taxonomy_review_sample.xlsx") as xw:
    review.to_excel(xw, sheet_name="Review", index=False)
    cats.to_excel(xw, sheet_name="Category IDs", index=False)
print(f"Saved {len(review)} projects to reports/taxonomy_review_sample.xlsx")
