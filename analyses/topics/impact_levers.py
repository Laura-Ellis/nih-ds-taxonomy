# %% [markdown]
# # B5b. What goes with more outputs: levers and other project details
#
# Follow-up to `impact_models.py` (slides 9 and 10). Same cohort and outcomes: 15,729 data science projects that started
# FY2016 to FY2020; highly cited papers (top quarter of mean RCR), any patent, any clinical trial.
#
# **Questions**
# 1. Do details beyond size, type, and research area help predict outputs? Compare 5-fold cross-validated AUC for
#    gradient boosting with (a) project structure, (b) + taxonomy and themes (slide 9), (c) + the new details below.
# 2. Which levers an institute controls go with more outputs once projects are made alike (AIPW, as in slide 9)?
#    NIH-wide and NIAID-only.
#
# **New details** (from ExPORTER applications and PI profiles)
# - Targeted NOFO: any application answered an RFA or PAR (vs. a broad NOFO, researcher-initiated).
# - Multi-PI: 2 or more PIs. Applies AI: the taxonomy's "applies AI" role.
# - Co-funded: 2 or more institutes paid for the project in some year.
# - Large research organization: the organization is among the 50 with the most NIH projects, FY2016 to FY2026.
# - Established PI: a PI on the project had an earlier NIH project (visible from FY2016 only).
# - Clinical research: NIH's RCDC tags include "Clinical Research".
# - Renewed: the project won a competing renewal. Successful projects are more likely to be renewed, so this one
#   runs both ways; it is reported but not treated as a lever.
#
# Outputs: `reports/results/impact_levers_auc.csv`, `impact_levers_importance.csv`, `impact_levers.csv`.
# Runtime: a few minutes. Reuses the cohort and outcome cells of `impact_models.py`.

# %%
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
HERE = ROOT / "analyses" / "topics"
sys.path.insert(0, str(ROOT / "src"))
from progress import say  # noqa: E402  # pyright: ignore[reportMissingImports]

# Same cohort and outcomes as impact_models.py: run its first cells (projects, traits, outcomes)
_src = (HERE / "impact_models.py").read_text(encoding="utf-8")
_g = {"__file__": str(HERE / "impact_models.py"), "__name__": "impact_cells"}
exec(_src.split("# ## Model comparison")[0], _g)
d, STRUCT_NUM, OUTCOMES, SEED, OUT, PROCESSED = (_g[k] for k in ("d", "STRUCT_NUM", "OUTCOMES", "SEED", "OUT", "PROCESSED"))
N_BOOT = int(os.environ.get("IMPACT_LEVER_BOOT", 100))

# %% [markdown]
# ## New project details

# %%
say("new project details")
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["core_project_number", "nofo", "funding_ics", "nih_spending_cats", "org_name", "pi_ids",
                                "application_type", "fy"])
apps["nofo"] = apps.nofo.fillna("").astype(str).str.upper()
apps["n_funders"] = apps.funding_ics.fillna("").astype(str).str.count(":")
top_orgs = apps.groupby("org_name").core_project_number.nunique().nlargest(50).index
pis = apps.assign(pi=apps.pi_ids.fillna("").astype(str).str.split(";")).explode("pi")
pis["pi"] = pis.pi.str.extract(r"(\d+)")[0]
pi_first = pis.dropna(subset=["pi"]).groupby("pi").fy.min()
pis["pi_first_fy"] = pis.pi.map(pi_first)
cp = apps[apps.core_project_number.isin(d.core_project_number)].groupby("core_project_number")
det = pd.DataFrame({
    "Targeted NOFO": cp.nofo.agg(lambda s: s.str.match(r"^(RFA|PAR)-").any()),
    "Co-funded (2+ institutes)": cp.n_funders.max() >= 2,
    "Large research organization": cp.org_name.agg(lambda s: s.isin(top_orgs).any()),
    "Clinical research": cp.nih_spending_cats.agg(lambda s: s.fillna("").str.contains("Clinical Research").any()),
    "Renewed": cp.application_type.agg(lambda s: s.astype(str).eq("2").any()),
}).astype(int)
first_fy = cp.fy.min()
pp = pis[pis.core_project_number.isin(d.core_project_number)]
det["Established PI"] = (pp.assign(start=pp.core_project_number.map(first_fy))
                         .assign(earlier=lambda x: x.pi_first_fy < x.start).groupby("core_project_number").earlier.any()
                         .reindex(det.index).fillna(False).astype(int))
d = d.join(det, on="core_project_number")
d["Multi-PI"] = (d.n_pis >= 2).astype(int)
d["Applies AI"] = d["tax: AI role applies"]
NEW = list(det.columns) + ["Multi-PI"]
d[NEW] = d[NEW].fillna(0).astype(int)
say("shares: " + ", ".join(f"{c} {d[c].mean():.0%}" for c in NEW))

# %% [markdown]
# ## Do the new details help predict? (5-fold cross-validated AUC)

# %%
say("prediction")
STRUCT = pd.get_dummies(d[["ic", "family"]], prefix=["ic", "type"], dtype=int)
TRAITS = [c for c in d.columns if c.startswith(("tax: ", "theme: "))]
sets = {"Structure": pd.concat([d[STRUCT_NUM], STRUCT], axis=1),
        "+ taxonomy and themes (slide 9)": pd.concat([d[STRUCT_NUM], STRUCT, d[TRAITS]], axis=1),
        "+ new details": pd.concat([d[STRUCT_NUM], STRUCT, d[TRAITS], d[NEW]], axis=1)}
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
auc = []
for o in OUTCOMES:
    y = d[o].to_numpy()
    for name, X in sets.items():
        p = cross_val_predict(HistGradientBoostingClassifier(random_state=SEED), X.astype(float), y, cv=cv, method="predict_proba")[:, 1]
        auc.append({"outcome": OUTCOMES[o], "features": name, "auc": roc_auc_score(y, p)})
auc = pd.DataFrame(auc)
auc.to_csv(OUT / "impact_levers_auc.csv", index=False)
print(auc.pivot(index="features", columns="outcome", values="auc").round(3).to_string())

# permutation importance of each detail in the full model, on a held-out quarter
X = sets["+ new details"].astype(float)
imp = []
for o in OUTCOMES:
    y = d[o].to_numpy()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
    m = HistGradientBoostingClassifier(random_state=SEED).fit(Xtr, ytr)
    pi_ = permutation_importance(m, Xte, yte, scoring="roc_auc", n_repeats=10, random_state=SEED)
    imp += [{"outcome": OUTCOMES[o], "feature": f, "auc_drop": v} for f, v in zip(X.columns, pi_.importances_mean)]
imp = pd.DataFrame(imp)
imp.to_csv(OUT / "impact_levers_importance.csv", index=False)
for o in OUTCOMES.values():
    print(o, imp[imp.outcome == o].nlargest(8, "auc_drop")[["feature", "auc_drop"]].round(4).to_string(index=False))

# %% [markdown]
# ## Levers, made alike (AIPW), NIH-wide and NIAID

# %%
say("levers")


def aipw(t, y, W, idx=None):
    if idx is not None:
        t, y, W = t[idx], y[idx], W[idx]
    Ws = StandardScaler().fit_transform(W)
    e = LogisticRegression(max_iter=3000).fit(Ws, t).predict_proba(Ws)[:, 1].clip(0.02, 0.98)
    om = LogisticRegression(max_iter=3000).fit(np.c_[Ws, t], y)
    m1 = om.predict_proba(np.c_[Ws, np.ones_like(t)])[:, 1]
    m0 = om.predict_proba(np.c_[Ws, np.zeros_like(t)])[:, 1]
    return np.mean(m1 - m0 + t * (y - m1) / e - (1 - t) * (y - m0) / (1 - e))


LEVERS = ["Targeted NOFO", "Multi-PI", "Applies AI", "Co-funded (2+ institutes)", "Large research organization",
          "Established PI", "Renewed"]
rows = []
for scope, sub in [("NIH", d), ("NIAID", d[d.administering_ic == "AI"])]:
    struct = pd.get_dummies(sub[["family"]], prefix=["type"], dtype=int) if scope == "NIAID" else STRUCT.loc[sub.index]
    for k, lv in enumerate(LEVERS):
        t = sub[lv].to_numpy()
        if t.mean() < 0.03 or t.mean() > 0.97:
            continue
        W = pd.concat([sub[[c for c in STRUCT_NUM if not (lv == "Multi-PI" and c == "n_pis")]], struct], axis=1).astype(float).to_numpy()
        rng = np.random.default_rng(SEED + k)
        for o in OUTCOMES:
            y = sub[o].to_numpy()
            est = aipw(t, y, W)
            boot = [aipw(t, y, W, rng.integers(0, len(t), len(t))) for _ in range(N_BOOT)]
            rows.append({"scope": scope, "lever": lv, "share_with": t.mean(), "outcome": OUTCOMES[o],
                         "with": y[t == 1].mean(), "without": y[t == 0].mean(), "aipw_gap": est,
                         "low": np.percentile(boot, 2.5), "high": np.percentile(boot, 97.5), "projects": len(t)})
    say(f"  {scope} done")
lev = pd.DataFrame(rows)
lev.to_csv(OUT / "impact_levers.csv", index=False)
print(lev.assign(**{c: lev[c] * 100 for c in ("share_with", "with", "without", "aipw_gap", "low", "high")}).round(1).to_string(index=False))
