# %% [markdown]
# # 03 Agreement with hand coding
#
# Compares the keyword labels and NIH's RCDC category with the hand-coded review sample
# (`reports/taxonomy_review_coded.xlsx`).
#
# - Substantive = coded Y; any mention = coded Y or M
# - Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement); 1 = perfect, 0 = chance
# - Precision = labeled and coded / labeled; recall = labeled and coded / coded

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]

from coding import load_coded  # noqa: E402  # pyright: ignore[reportMissingImports]

REPORTS = ROOT / "reports"
version = "v0.3b"  # reviewed codes (spot check and recode) applied
sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
x = load_coded(REPORTS).merge(tx.label_projects(sample), on="appl_id")
print(f"{len(x)} coded projects")


# %%
def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe)


def precision_recall(pred, truth):
    pred, truth = np.asarray(pred, bool), np.asarray(truth, bool)
    tp = (pred & truth).sum()
    return tp / pred.sum(), tp / truth.sum()


rows = []
for label, kw, coded_col in [("AI", "ai_related", "my_ai_related"),
                             ("Data science", "data_science_related", "my_ds_related")]:
    for rule, truth in [("substantive (Y)", x[coded_col] == "Y"),
                        ("any mention (Y or M)", x[coded_col].isin(["Y", "M"]))]:
        methods = [("Keywords", x[kw])] + ([("RCDC", x.rcdc_ml_ai)] if label == "AI" else [])
        for name, pred in methods:
            p, r = precision_recall(pred, truth)
            rows.append({"label": label, "method": name, "coding": rule,
                         "kappa": kappa(pred, truth), "precision": p, "recall": r})
agreement = pd.DataFrame(rows).round(2)
agreement.to_csv(REPORTS / f"agreement_{version}.csv", index=False)
agreement

# %% [markdown]
# ## Category agreement (projects coded Y for data science)

# %%
ds = x[x.my_ds_related == "Y"].copy()
ds["mine"] = ds.my_categories.fillna("").map(lambda v: {c.strip() for c in v.split(";") if c.strip()})
cats = tx.load_categories()
out = []
for c in cats.loc[cats.method != "llm", "category_id"]:
    pred = ds.categories.map(lambda k, c=c: c in k)
    truth = ds.mine.map(lambda k, c=c: c in k)
    if pred.any() or truth.any():
        out.append({"category": c, "keyword": pred.sum(), "coded": truth.sum(), "both": (pred & truth).sum()})
by_cat = pd.DataFrame(out)
by_cat["precision"] = (by_cat.both / by_cat.keyword).round(2)
by_cat["recall"] = (by_cat.both / by_cat.coded).round(2)
by_cat.sort_values("coded", ascending=False)
