# %% [markdown]
# # C5. Projecting the preliminary year: completeness vs. gradient boosting vs. quantile regression
#
# RePORTER keeps adding a fiscal year's records for months after it closes (Sept 30). Notebook 18
# projects the final count as to-date / completeness, where completeness is the share of the prior
# year's final records RePORTER had added by the same lag. This back-tests that against two models.
#
# - Unit: extramural grants, institute × activity family cell (R, U, P, K, T, F, other).
# - Lags (days after Sept 30): 24 (the FY2026 pull on Oct 24, 2026), 60, 90, 180.
# - Back-test years FY2021–FY2025. Each model trains only on earlier years (FY2020 onward).
# - Truth = the count as of the Oct 24, 2026 pull. FY2025 was 389 days past close then, nearly final.
#
# Methods
# - Completeness (current): projected = to_date / completeness in the prior year, same cell and lag;
#   cells with < 200 prior-year records use the all-NIH completeness.
# - Gradient boosting: predicts log(final / to_date) from lag, prior-year and two-years-back completeness
#   (cell and all NIH), log to_date, share added in the 14 days before the lag, institute, family.
# - Quantile regression: linear, same numeric features; 10th, 50th, 90th percentiles give an 80% range.
#
# Measures
# - Total error = projected all-NIH total / actual − 1
# - Cell error (WAPE) = Σ |projected − actual| / Σ actual, across cells
# - 80% coverage = share of cells whose actual falls inside the range (completeness range: min to max of
#   the prior two years' completeness, as in notebook 18)
#
# Run: python -u analyses/methods/fy_projection_backtest.py  (Python 3.12+; pandas, pyarrow, scikit-learn, matplotlib)
# Input: raw API pulls, data/nih/api/projects_FY*.jsonl.gz (FY2018 is incomplete and skipped)

# %%
import gzip
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import QuantileRegressor

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "mnt" / "data" / "nih" / "api"
CACHE = ROOT / "data" / "interim" / "reporter_date_added.parquet"
OUT = ROOT / "reports" / "methods"
FIG = ROOT / "reports" / "figures" / "methods"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

PULL = pd.Timestamp("2026-10-24")
YEARS = list(range(2019, 2027))
TEST_YEARS = list(range(2021, 2026))
LAGS = [24, 60, 90, 180]
MIN_CELL = 200
NIH = {"CA", "HL", "AI", "GM", "AG", "NS", "MH", "DK", "HD", "DA", "AA", "ES", "EY", "DC", "DE", "AR", "EB", "HG",
       "LM", "MD", "NR", "AT", "TR", "TW", "OD"}
FAMILIES = {"R", "U", "P", "K", "T", "F"}
FEATURES = ["lag", "c1", "c2", "c1_nih", "c2_nih", "log_to_date", "recent"]

# %% [markdown]
# ## Load date_added for every extramural grant

# %%
if CACHE.exists():
    raw = pd.read_parquet(CACHE)
else:
    parts = []
    for fy in YEARS:
        with gzip.open(RAW / f"projects_FY{fy}.jsonl.gz", "rt", encoding="utf-8") as fh:
            recs = [json.loads(line) for line in fh]
        parts.append(pd.DataFrame({
            "fy": fy, "date_added": [r.get("date_added") for r in recs],
            "award": [r.get("award_amount") or 0 for r in recs],
            "activity": [r.get("activity_code") or "" for r in recs],
            "ic": [(r.get("agency_ic_admin") or {}).get("code") for r in recs]}))
        print(f"FY{fy}: {len(recs):,}")
    raw = pd.concat(parts, ignore_index=True)
    raw["date_added"] = pd.to_datetime(raw.date_added, errors="coerce").dt.tz_localize(None)
    raw.to_parquet(CACHE, index=False)

d = raw[raw.ic.isin(NIH) & ~raw.activity.str[0].isin(["Z", "N", "Y"])].copy()
d["family"] = np.where(d.activity.str[0].isin(FAMILIES), d.activity.str[0], "Other")
d["lag_days"] = (d.date_added - pd.to_datetime(d.fy.astype(str) + "-09-30")).dt.days
print(f"{len(d):,} extramural grant records, FY{YEARS[0]}–FY{YEARS[-1]}")

# %% [markdown]
# ## Cell table: to-date and final counts by year, lag, institute, family

# %%
def cells(measure):
    w = np.ones(len(d)) if measure == "records" else d.award.values
    rows = []
    for lag in LAGS:
        early = (d.lag_days <= lag).values
        recent = ((d.lag_days > lag - 14) & (d.lag_days <= lag)).values
        g = pd.DataFrame({"fy": d.fy, "ic": d.ic, "family": d.family, "final": w, "to_date": w * early,
                          "recent": w * recent, "n": 1}).groupby(["fy", "ic", "family"]).sum().reset_index()
        rows.append(g.assign(lag=lag))
    c = pd.concat(rows, ignore_index=True)
    c["comp"] = c.to_date / c.final.replace(0, np.nan)
    nih = c.groupby(["fy", "lag"])[["to_date", "final"]].sum()
    nih = (nih.to_date / nih.final).rename("comp_nih").reset_index()
    c = c.merge(nih, on=["fy", "lag"])
    for k in (1, 2):
        prev = c[["fy", "ic", "family", "lag", "comp", "comp_nih", "n"]].assign(fy=lambda x: x.fy + k)
        c = c.merge(prev.rename(columns={"comp": f"c{k}", "comp_nih": f"c{k}_nih", "n": f"n{k}"}),
                    on=["fy", "ic", "family", "lag"], how="left")
    c["recent"] = c.recent / c.to_date.replace(0, np.nan)
    c["log_to_date"] = np.log1p(c.to_date)
    c["target"] = np.log((c.final + 1) / (c.to_date + 1))
    return c


def wape(p, a):
    return np.abs(p - a).sum() / a.sum()


results, fy26 = [], []
for measure in ["records", "funding"]:
    c = cells(measure)
    # Completeness: prior-year cell completeness, all-NIH when the cell is small or empty
    use_cell = (c.n1 >= MIN_CELL) & (c.c1 > 0)
    c["comp_use"] = np.where(use_cell, c.c1, c.c1_nih)
    c["p_comp"] = c.to_date / c.comp_use
    lo_c = np.where(use_cell, np.fmax(c.c1, c.c2.fillna(c.c1)), np.fmax(c.c1_nih, c.c2_nih.fillna(c.c1_nih)))
    hi_c = np.where(use_cell, np.fmin(c.c1, c.c2.fillna(c.c1)), np.fmin(c.c1_nih, c.c2_nih.fillna(c.c1_nih)))
    c["lo_comp"], c["hi_comp"] = c.to_date / lo_c, c.to_date / hi_c
    c[FEATURES] = c[FEATURES].fillna(c[FEATURES].median(numeric_only=True))
    X = pd.get_dummies(c[FEATURES + ["ic", "family"]], columns=["ic", "family"], dtype=float)

    for test_fy in TEST_YEARS + [2026]:
        tr = (c.fy >= 2020) & (c.fy < test_fy) & (c.fy < 2026)
        te = c.fy.eq(test_fy) & (c.to_date > 0)
        gb = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=10, random_state=0)
        gb.fit(X[tr], c.target[tr])
        c.loc[te, "p_gb"] = (c.to_date[te] + 1) * np.exp(gb.predict(X[te])) - 1
        Xq = c[FEATURES]
        for q, col in [(0.1, "lo_qr"), (0.5, "p_qr"), (0.9, "hi_qr")]:
            qr = QuantileRegressor(quantile=q, alpha=0.0005, solver="highs").fit(Xq[tr], c.target[tr])
            c.loc[te, col] = (c.to_date[te] + 1) * np.exp(qr.predict(Xq[te])) - 1

        for lag in LAGS:
            x = c[te & c.lag.eq(lag)]
            if test_fy == 2026:
                if lag == 24:
                    fy26.append({"measure": measure, "to_date": x.to_date.sum(),
                                 **{m: x[f"p_{k}"].sum() for m, k in
                                    [("Completeness", "comp"), ("Gradient boosting", "gb"), ("Quantile regression", "qr")]},
                                 "qr_low": x.lo_qr.sum(), "qr_high": x.hi_qr.sum(),
                                 "comp_low": x.lo_comp.sum(), "comp_high": x.hi_comp.sum()})
                continue
            for name, k, rng in [("Completeness", "comp", ("lo_comp", "hi_comp")), ("Gradient boosting", "gb", None),
                                 ("Quantile regression", "qr", ("lo_qr", "hi_qr"))]:
                cov = ((x.final >= x[rng[0]]) & (x.final <= x[rng[1]])).mean() if rng else np.nan
                results.append({"measure": measure, "fy": test_fy, "lag": lag, "method": name,
                                "total_error": x[f"p_{k}"].sum() / x.final.sum() - 1,
                                "cell_wape": wape(x[f"p_{k}"], x.final), "coverage_80": cov,
                                "to_date_share": x.to_date.sum() / x.final.sum()})

res = pd.DataFrame(results)
res.to_csv(OUT / "fy_projection_backtest.csv", index=False)
summ = (res.groupby(["measure", "lag", "method"])
        .agg(mean_abs_total_error=("total_error", lambda s: s.abs().mean()), cell_wape=("cell_wape", "mean"),
             coverage_80=("coverage_80", "mean")).round(3).reset_index())
summ.to_csv(OUT / "fy_projection_backtest_summary.csv", index=False)
fy26 = pd.DataFrame(fy26)
fy26.to_csv(OUT / "fy2026_projection_by_method.csv", index=False)
print(summ.to_string(index=False))
print(fy26.round(0).to_string(index=False))

# %%
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
colors = {"Completeness": "#9aa5b1", "Gradient boosting": "#c8553d", "Quantile regression": "#2f6690"}
for ax, measure in zip(axes, ["records", "funding"]):
    s = summ[summ.measure.eq(measure)]
    for m, g in s.groupby("method"):
        ax.plot(g.lag, g.cell_wape * 100, marker="o", color=colors[m], label=m)
    ax.set_title(f"Grant {measure}", loc="left", fontsize=11)
    ax.set_xticks(LAGS)
    ax.set_xlabel("Days after the fiscal year closes", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Cell error, WAPE (%)", fontsize=9)
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle("Back-test, FY2021–FY2025: error in projecting final counts by institute and activity family",
             x=0.01, ha="left", fontsize=12)
fig.text(0.01, -0.04, "WAPE = Σ|projected − actual| / Σ actual across institute × activity family cells. "
         "Source: NIH RePORTER API, pulled Oct 24, 2026.", fontsize=8, color="#555")
fig.tight_layout()
fig.savefig(FIG / "fy_projection_backtest.png", dpi=200, bbox_inches="tight")
