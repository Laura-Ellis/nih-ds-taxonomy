# %% [markdown]
# # Targeted vs. researcher-initiated outputs, and levers, for each of the 10 largest institutes
#
# Same cohort, outcomes, and AIPW as `analyses/topics/impact_levers.py` (15,729 data science projects that started
# FY2016 to FY2020; highly cited papers = top quarter of mean RCR, any patent, any clinical trial).
#
# - **Targeted vs. researcher-initiated:** the "Targeted NOFO" lever (any application answered an RFA or PAR) vs. a
#   broad NOFO. NIH-wide adjusted for size, grant type, and institute; within an institute for size and grant type.
# - **Levers:** every lever in `impact_levers.py`, within each institute.
# AIPW = augmented inverse probability weighting: a model of who gets the lever and a model of the outcome, combined so
# the estimate holds if either model is right. 100 bootstraps for the 95% interval. Lever shares under 3% or over 97%
# in an institute are skipped (too few projects to compare).
#
# Output: `reports/internal/ic_gaps/ic_outputs.csv`. Runtime: about 10 minutes.

# %%
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
HERE = ROOT / "analyses" / "topics"
OUT = ROOT / "reports" / "internal" / "ic_gaps"
os.environ.setdefault("IMPACT_LEVER_BOOT", "100")
IC = {"CA": "NCI", "HL": "NHLBI", "AG": "NIA", "AI": "NIAID", "HD": "NICHD", "DA": "NIDA", "DK": "NIDDK", "GM": "NIGMS",
      "MH": "NIMH", "NS": "NINDS"}

# Run impact_levers.py up to its levers section: cohort, outcomes, new details, and the aipw() function
_src = (HERE / "impact_levers.py").read_text(encoding="utf-8")
_g = {"__file__": str(HERE / "impact_levers.py"), "__name__": "ic_outputs"}
head, levers_cell = _src.split("# ## Do the new details help predict?")[0], _src.split("# ## Levers, made alike")[1]
exec(head, _g)
exec("#" + levers_cell.split("rows = []")[0], _g)   # defines aipw() and LEVERS
d, STRUCT_NUM, OUTCOMES, SEED, aipw, LEVERS, N_BOOT = (_g[k] for k in ("d", "STRUCT_NUM", "OUTCOMES", "SEED", "aipw", "LEVERS", "N_BOOT"))

# %%
rows = []
scopes = [("NIH", d)] + [(name, d[d.administering_ic == code]) for code, name in sorted(IC.items(), key=lambda x: x[1])]
for scope, sub in scopes:
    struct = pd.get_dummies(sub[["family"]], prefix=["type"], dtype=int)
    if scope == "NIH":
        struct = pd.get_dummies(sub[["ic", "family"]], prefix=["ic", "type"], dtype=int)
    for k, lv in enumerate(LEVERS):
        t = sub[lv].to_numpy()
        if t.mean() < 0.03 or t.mean() > 0.97:
            continue
        W = pd.concat([sub[[c for c in STRUCT_NUM if not (lv == "Multi-PI" and c == "n_pis")]], struct], axis=1).astype(float).to_numpy()
        rng = np.random.default_rng(SEED + k)
        for o in OUTCOMES:
            y = sub[o].to_numpy()
            if y.sum() < 10:
                continue
            est = aipw(t, y, W)
            boot = [aipw(t, y, W, rng.integers(0, len(t), len(t))) for _ in range(N_BOOT)]
            rows.append({"scope": scope, "lever": lv, "share_with": t.mean(), "outcome": OUTCOMES[o],
                         "with": y[t == 1].mean(), "without": y[t == 0].mean(), "aipw_gap": est,
                         "low": np.percentile(boot, 2.5), "high": np.percentile(boot, 97.5), "projects": len(t)})
    print(scope, "done", flush=True)
res = pd.DataFrame(rows)
res.to_csv(OUT / "ic_outputs.csv", index=False)
show = res.assign(**{c: res[c] * 100 for c in ("share_with", "with", "without", "aipw_gap", "low", "high")}).round(1)
print(show[show.lever == "Targeted NOFO"].to_string(index=False))
