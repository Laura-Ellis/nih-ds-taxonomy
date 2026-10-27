# %% [markdown]
# # 07 Jev vs. Claude vs. keywords
#
# Runs Jev (Typesafe, through the Vercel AI Gateway) on the 150 coded projects and compares
# it with keywords and Claude (notebook 05). Adoption bar from `reports/method_comparison.md`:
# κ ≥ 0.90 on substantive AI.
#
# **Setup:** add your AI Gateway key under "### Vercel AI Gateway" in ~/KEYS.md (or set
# `AI_GATEWAY_API_KEY`). Results are cached in `data/interim/jev_labels.jsonl`.
#
# **Definitions**
# - Substantive = coded Y; precision = flagged and coded / flagged; recall = flagged and coded / coded
# - Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement)
# - Jev returns P(answer) for each label; categories are assigned when P(true) ≥ 0.5

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import jev_label as jev  # noqa: E402  # pyright: ignore[reportMissingImports]
import llm_label as llm  # noqa: E402  # pyright: ignore[reportMissingImports]
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from coding import kappa, load_coded  # noqa: E402  # pyright: ignore[reportMissingImports]

REPORTS = ROOT / "reports"
INTERIM = ROOT / "data" / "interim"
sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
coded = load_coded(REPORTS)
val = sample[sample.appl_id.isin(coded.appl_id)]

# %% [markdown]
# ## Try one project first

# %%
first = jev.label_projects(val.head(1), INTERIM / "jev_labels.jsonl")
first.T

# %% [markdown]
# ## Label the 150 coded projects

# %%
jl = jev.label_projects(val, INTERIM / "jev_labels.jsonl")
cl = llm.label_projects(val, INTERIM / "llm_labels.jsonl")  # Claude, from cache
x = coded.merge(tx.label_projects(val), on="appl_id").merge(jl, on="appl_id").merge(cl, on="appl_id")  # Claude refused 1
print(f"{len(x)} projects; Jev cost ${x.jev_cost.sum():.4f}")

# %%
rows = []
for label, kw_col, code_col in [("AI", "ai_related", "my_ai_related"),
                                ("Data science", "data_science_related", "my_ds_related")]:
    truth = x[code_col].eq("Y")
    short = "ai" if label == "AI" else "ds"
    methods = [("Keywords", x[kw_col]), ("Keywords, evidence rule", x[f"{short}_likely"]),
               ("Claude", x[f"llm_{short}_related"].eq("Y")), ("Jev", x[f"jev_{short}_related"].eq("Y"))]
    for name, pred in methods:
        tp = (pred & truth).sum()
        rows.append({"label": label, "method": name, "kappa": round(kappa(pred, truth), 2),
                     "precision": round(tp / max(pred.sum(), 1), 2), "recall": round(tp / truth.sum(), 2)})
    rows.append({"label": label, "method": "Jev vs. Claude (Y/M/N)",
                 "kappa": round(kappa(x[f"jev_{short}_related"], x[f"llm_{short}_related"]), 2)})
comparison = pd.DataFrame(rows)
comparison.to_csv(REPORTS / "jev_comparison_v0.4.csv", index=False)
comparison

# %% [markdown]
# ## Does Jev's confidence help?
# If low-confidence answers are the wrong ones, a cutoff can send only those to Claude.

# %%
x["jev_ai_conf"] = x.jev_ai_probs.map(lambda p: max(p.values()) if p else None)
x["jev_ai_right"] = x.jev_ai_related.eq("Y") == x.my_ai_related.eq("Y")
x.groupby(pd.cut(x.jev_ai_conf, [0, 0.6, 0.8, 0.9, 1.0])).jev_ai_right.agg(["count", "mean"])

# %%
print(pd.crosstab(x.my_ai_related, x.jev_ai_related, rownames=["coded AI"], colnames=["Jev AI"]))

# %% [markdown]
# ## Hybrid: Jev, with Claude for answers below 90% confidence

# %%
CUTOFF = 0.90
hybrid = []
for label, short, code_col in [("AI", "ai", "my_ai_related"), ("Data science", "ds", "my_ds_related")]:
    conf = x[f"jev_{short}_probs"].map(lambda p: max(p.values()) if p else 0)
    final = x[f"jev_{short}_related"].where(conf >= CUTOFF, x[f"llm_{short}_related"])
    truth, pred = x[code_col].eq("Y"), final.eq("Y")
    tp = (pred & truth).sum()
    hybrid.append({"label": label, "sent_to_claude": int((conf < CUTOFF).sum()),
                   "kappa": round(kappa(pred, truth), 2), "precision": round(tp / pred.sum(), 2),
                   "recall": round(tp / truth.sum(), 2)})
pd.DataFrame(hybrid)
