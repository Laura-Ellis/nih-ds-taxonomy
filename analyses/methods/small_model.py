# %% [markdown]
# # C4. A small, free labeling model
#
# Can TF-IDF + logistic regression stand in for Jev + ChatGPT?
#
# - Train: pipeline labels (keywords → Jev → ChatGPT) on keyword-flagged records, FY2016–2026.
#   Records that contain any of the 150 coded projects are dropped, so nothing leaks into the test.
# - Test: the 150 hand-coded projects (substantive = Y). Same rule as the pipeline: a project
#   must be flagged by keywords before the model can call it Y.
# - Second check: agreement with the pipeline on a 20% holdout of flagged records.
#
# Measures: precision = TP / predicted Y; recall = TP / coded Y;
# Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement).
#
# Run: python -u analyses/methods/small_model.py  (Python 3.12+; pandas, pyarrow, scikit-learn, openpyxl, matplotlib)

# %%
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from coding import kappa, load_coded  # noqa: E402  # pyright: ignore[reportMissingImports]

OUT = ROOT / "reports" / "methods"
FIG = ROOT / "reports" / "figures" / "methods"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LABELS = [("AI", "ai", "ai_related", "my_ai_related"), ("Data science", "ds", "data_science_related", "my_ds_related")]


def text(title, abstract):
    return title.fillna("") + ". " + abstract.fillna("")


def scores(pred, truth):
    pred, truth = pd.Series(pred).astype(bool).values, pd.Series(truth).astype(bool).values
    tp = (pred & truth).sum()
    return {"precision": round(tp / max(pred.sum(), 1), 2), "recall": round(tp / truth.sum(), 2),
            "kappa": round(kappa(pred, truth), 2)}


# %% [markdown]
# ## Test set: the 150 coded projects

# %%
coded = load_coded(ROOT / "reports")
sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
val = sample[sample.appl_id.isin(coded.appl_id)]
test = coded.merge(tx.label_projects(val).drop(columns=["project_title", "abstract_text"], errors="ignore"), on="appl_id").merge(
    val[["appl_id", "project_title", "abstract_text"]], on="appl_id")
test["text"] = text(test.project_title, test.abstract_text)
print(f"test: {len(test)} coded projects")

# %% [markdown]
# ## Training set: pipeline labels on flagged records

# %%
lab = pd.read_parquet(ROOT / "data" / "processed" / "exporter_core_projects_labeled.parquet")
lab = lab[lab.ds_flag | lab.ai_flag]
txt = pd.read_parquet(ROOT / "data" / "processed" / "exporter_flagged_text.parquet",
                      columns=["text_hash", "project_title", "abstract_text"]).drop_duplicates("text_hash")
train = lab.merge(txt, on="text_hash")
coded_ids = set(coded.appl_id.astype(str))
leak = train.application_ids.astype(str).str.split(r"[,;\s]+").map(lambda ids: bool(coded_ids & set(ids)))
train = train[~leak].reset_index(drop=True)
train["text"] = text(train.project_title, train.abstract_text)
print(f"train: {len(train):,} flagged records ({leak.sum()} dropped because they hold a coded project)")

# %% [markdown]
# ## Fit and score

# %%
rows, timing = [], {}
for label, short, kw_col, code_col in LABELS:
    y = train[f"{short}_label"].eq("Y")
    tr, ho = train_test_split(train.index, test_size=0.2, random_state=42, stratify=y)
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=5, max_df=0.5, sublinear_tf=True, stop_words="english"),
        LogisticRegression(max_iter=3000, C=4, class_weight="balanced"))
    t0 = time.perf_counter()
    model.fit(train.loc[tr, "text"], y[tr])
    timing[f"{label} fit (s)"] = round(time.perf_counter() - t0, 1)

    t0 = time.perf_counter()
    p_ho = model.predict_proba(train.loc[ho, "text"])[:, 1]
    timing[f"{label} seconds per 10,000 texts"] = round((time.perf_counter() - t0) / len(ho) * 10_000, 1)

    rows.append({"label": label, "test": "Pipeline holdout (20%)", "method": "TF-IDF + LR",
                 **scores(p_ho >= 0.5, y[ho])})
    p = model.predict_proba(test.text)[:, 1]
    truth = test[code_col].eq("Y")
    kw = test[kw_col].astype(bool)
    rows.append({"label": label, "test": "150 coded", "method": "Keywords", **scores(kw, truth)})
    rows.append({"label": label, "test": "150 coded", "method": "Keywords → TF-IDF + LR", **scores(kw & (p >= 0.5), truth)})
    test[f"lr_{short}_p"] = p

res = pd.DataFrame(rows)
res.to_csv(OUT / "small_model_comparison.csv", index=False)
print(res.to_string(index=False))
print(timing)

# %% [markdown]
# ## Next to the pipeline (from notebooks/19_pipeline_compare.py)

# %%
pipe = pd.read_csv(ROOT / "reports" / "pipeline_comparison_v0.4.csv")
keep = ["Keywords → Jev", "Keywords → Jev → ChatGPT", "Keywords → Jev → Claude", "Claude alone"]
both = pd.concat([pipe[pipe.method.isin(keep)][["label", "method", "precision", "recall", "kappa"]],
                  res[res.method.eq("Keywords → TF-IDF + LR")][["label", "method", "precision", "recall", "kappa"]]])
both.to_csv(OUT / "small_model_vs_pipeline.csv", index=False)
print(both.pivot(index="method", columns="label", values="kappa"))

# %%
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharex=True)
for ax, (label, *_) in zip(axes, LABELS):
    d = both[both.label.eq(label)].sort_values("kappa")
    colors = ["#c8553d" if "TF-IDF" in m else "#9aa5b1" for m in d.method]
    ax.barh(d.method, d.kappa, color=colors)
    for i, k in enumerate(d.kappa):
        ax.text(k + 0.01, i, f"{k:.2f}", va="center", fontfamily="Arial", fontsize=9)
    ax.set_title(label, loc="left", fontfamily="Arial", fontsize=11)
    ax.set_xlim(0, 1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
axes[0].set_xlabel("Cohen's κ vs. 150 hand-coded projects", fontfamily="Arial", fontsize=9)
fig.suptitle("A free local model next to the paid pipeline", x=0.01, ha="left", fontfamily="Arial", fontsize=12)
fig.text(0.01, -0.04, "κ = (observed − chance agreement) / (1 − chance). LR = logistic regression. "
         "Source: NIH RePORTER; 150 coded projects, ±0.1 sampling error.", fontsize=8, fontfamily="Arial", color="#555")
fig.tight_layout()
fig.savefig(FIG / "small_model_kappa.png", dpi=200, bbox_inches="tight")
