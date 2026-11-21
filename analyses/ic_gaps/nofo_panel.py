# %% [markdown]
# # Do more NOFOs that ask for data science lead to more data science projects?
#
# Panel: institute × taxonomy group × fiscal year, FY2016 to FY2024, all NIH institutes (results reported for the 10
# largest). Input from `nofo_asks.py`.
#
# **Measures**
# - Open asking NOFOs (exposure) = targeted NOFOs (RFA, PAR) whose Section I asks for data science in the group,
#   led by the institute, open in the fiscal year (open FY ≤ year ≤ expiration FY). Led by = the institute's code is in
#   the NOFO number (RFA-HL-20-015 = NHLBI) or it is the only participating institute. NIH-wide NOFOs that list 20+
#   institutes are left out: every institute would get them every year, so they can't show an effect.
# - Caveat: the NOFO list comes from NOFOs that funded at least one record, so NOFOs that funded nothing are missing, and
#   recent NOFOs (FY2024 on) are undercounted. The panel stops at FY2024 for the exposure.
# - New data science projects (outcome) = data science projects administered by the institute, in the group, whose first
#   fiscal year is the year. Modeled as log(1 + projects).
#
# **Models**
# 1. Lags with fixed effects (OLS): log(1 + new projects) in year t on open asking NOFOs in t−1 and t−2, with a fixed
#    effect for each institute × group (its usual level) and for each institute × year and group × year (budgets and
#    NIH-wide trends). Standard errors clustered by institute × group. A lead (NOFOs in t+1) is the reverse-causality
#    check: if next year's NOFOs "predict" this year's projects, NOFOs follow growth rather than cause it.
# 2. Event study (stacked difference-in-differences): an event = an institute × group gets a new asking NOFO after two
#    years with none. Comparison = the same group at institutes with no new asking NOFO from t−2 to t+2. Change in
#    log(1 + new projects) from year −1, event minus comparison, for years −3 to +3. 200 bootstraps over events.
#
# Outputs: `reports/internal/ic_gaps/nofo_panel_*.csv`.

# %%
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.iv.absorbing import AbsorbingLS

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "internal" / "ic_gaps"
FY_FIRST, FY_LAST = 2016, 2024
SEED, N_BOOT = 7, 200
IC = {"CA": "NCI", "GM": "NIGMS", "AG": "NIA", "AI": "NIAID", "HL": "NHLBI", "MH": "NIMH", "NS": "NINDS",
      "HD": "NICHD", "DK": "NIDDK", "DA": "NIDA", "EB": "NIBIB", "HG": "NHGRI", "ES": "NIEHS", "EY": "NEI",
      "AR": "NIAMS", "DC": "NIDCD", "LM": "NLM", "AA": "NIAAA", "TR": "NCATS", "MD": "NIMHD",
      "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH"}
GROUP = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
         "artificial_intelligence": "Artificial intelligence", "software_tools": "Software and tools",
         "data_infrastructure": "Data infrastructure", "data_sharing": "Data infrastructure",
         "computing_platforms": "Data infrastructure", "responsible_ai": "Responsible AI", "workforce": "Workforce"}
TOP10 = ["NCI", "NHLBI", "NIA", "NIAID", "NICHD", "NIDA", "NIDDK", "NIGMS", "NIMH", "NINDS"]

# %%
n = pd.read_csv(OUT / "nofo_asks.csv")
n = n[n.asks_ds & n.kind.isin(["RFA", "PAR"]) & n.groups.notna()].copy()
n["ic"] = n.issuer.map(IC)
solo = n.ic.isna() & ~n.participating_ics.fillna("").str.contains(";") & n.participating_ics.isin(IC.values())
n.loc[solo, "ic"] = n.loc[solo, "participating_ics"]
n["group"] = n.groups.str.split("; ")
n = n.dropna(subset=["ic"]).explode("group")
years = range(FY_FIRST - 3, FY_LAST + 2)
open_ = [(r.ic, r.group, y) for r in n.itertuples() for y in years if r.open_fy <= y <= r.expire_fy]
new_ = n.groupby(["ic", "group", "open_fy"]).nofo.nunique()

ds = pd.read_parquet(PROCESSED / "ds_projects.parquet", columns=["core_project_number", "subproject_id", "groups", "first_fy", "ic"])
ds["ic"] = ds.ic.map(IC)
ds["group"] = ds.groups.fillna("").str.split(";")
ds = ds.explode("group")
ds["group"] = ds.group.str.strip().map(GROUP)
ds = ds.dropna(subset=["ic", "group"]).drop_duplicates(["core_project_number", "subproject_id", "group"])
ds["first_fy"] = pd.to_numeric(ds.first_fy, errors="coerce")

idx = pd.MultiIndex.from_product([sorted(IC.values()), sorted(set(GROUP.values())), list(years)], names=["ic", "group", "fy"])
p = pd.DataFrame(index=idx)
p["new_projects"] = ds.groupby(["ic", "group", "first_fy"]).size().rename_axis(["ic", "group", "fy"]).reindex(idx).fillna(0)
p["open_nofos"] = pd.Series(1, index=pd.MultiIndex.from_tuples(open_, names=["ic", "group", "fy"])).groupby(level=[0, 1, 2]).sum() \
    .reindex(idx).fillna(0)
p["new_nofos"] = new_.rename_axis(["ic", "group", "fy"]).reindex(idx).fillna(0)
p = p.reset_index()
p["unit"] = p.ic + " | " + p.group
p["y"] = np.log1p(p.new_projects)
g = p.groupby("unit")
for k in (1, 2):
    p[f"open_lag{k}"] = g.open_nofos.shift(k)
p["open_lead1"] = g.open_nofos.shift(-1)
p["ic_fy"], p["group_fy"] = p.ic + "_" + p.fy.astype(str), p.group + "_" + p.fy.astype(str)
panel = p[p.fy.between(FY_FIRST, FY_LAST)].copy()
panel.to_csv(OUT / "nofo_panel_data.csv", index=False)
print(f"{panel.unit.nunique()} institute × group units, {len(panel):,} unit-years; "
      f"mean open asking NOFOs {panel.open_nofos.mean():.1f}, mean new projects {panel.new_projects.mean():.1f}")

# %% [markdown]
# ## 1. Lags with fixed effects

# %%
rows = []
for name, rhs in [("Lags", "open_lag1 + open_lag2"), ("Lags + lead (check)", "open_lag1 + open_lag2 + open_lead1"),
                  ("Same year", "open_nofos")]:
    d = panel.dropna(subset=[c for c in ("open_lag1", "open_lag2", "open_lead1") if c in rhs] or ["y"])
    X = d[[t.strip() for t in rhs.split("+")]]
    absorb = d[["unit", "ic_fy", "group_fy"]].astype("category")
    m = AbsorbingLS(d.y, X, absorb=absorb).fit(cov_type="clustered", clusters=d.unit.astype("category").cat.codes)
    ci = m.conf_int()
    for v in X.columns:
        rows.append({"model": name, "term": v, "coef": m.params[v], "low": ci.loc[v, "lower"], "high": ci.loc[v, "upper"],
                     "p": m.pvalues[v], "pct_per_nofo": 100 * (np.exp(m.params[v]) - 1), "n": int(m.nobs)})
fe = pd.DataFrame(rows)
fe.to_csv(OUT / "nofo_panel_fe.csv", index=False)
print(fe.round(4).to_string(index=False))

# %% [markdown]
# ## 2. Event study (stacked)

# %%
pi = p.set_index(["unit", "fy"])
K = range(-3, 4)
events = []
for (unit, fy), r in pi.iterrows():
    if not (FY_FIRST <= fy <= FY_LAST - 1) or r.new_nofos == 0:
        continue
    prior = [pi.new_nofos.get((unit, fy - j), 0) for j in (1, 2)]
    if sum(prior) == 0:
        events.append((unit, fy, r.ic, r.group))
ev = pd.DataFrame(events, columns=["unit", "fy", "ic", "group"])
newn = p.pivot_table(index="unit", columns="fy", values="new_nofos", fill_value=0)
yv = p.pivot_table(index="unit", columns="fy", values="y")
unit_group = p.drop_duplicates("unit").set_index("unit").group


def event_path(e):
    ctrl = [u for u in unit_group[unit_group == e.group].index if u != e.unit
            and newn.loc[u, [c for c in range(e.fy - 2, e.fy + 3) if c in newn.columns]].sum() == 0]
    if not ctrl:
        return None
    out = {}
    for k in K:
        y0, yk = e.fy - 1, e.fy + k
        if yk not in yv.columns or y0 not in yv.columns or yk > FY_LAST:
            continue
        out[k] = (yv.at[e.unit, yk] - yv.at[e.unit, y0]) - (yv.loc[ctrl, yk] - yv.loc[ctrl, y0]).mean()
    return out


paths = pd.DataFrame([event_path(e) or {} for e in ev.itertuples()], index=ev.index).reindex(columns=list(K))
ev = ev.join(paths)
rng = np.random.default_rng(SEED)
res = []
for k in K:
    v = ev[k].dropna().to_numpy()
    boot = [rng.choice(v, len(v)).mean() for _ in range(N_BOOT)]
    res.append({"event_year": k, "effect": v.mean(), "low": np.percentile(boot, 2.5), "high": np.percentile(boot, 97.5),
                "pct": 100 * (np.exp(v.mean()) - 1), "events": len(v)})
es = pd.DataFrame(res)
es.to_csv(OUT / "nofo_panel_event_study.csv", index=False)
ev.to_csv(OUT / "nofo_panel_events.csv", index=False)
print(f"{len(ev)} events"); print(es.round(3).to_string(index=False))

# %% [markdown]
# ## By institute (top 10): events and the average change 1 to 2 years after

# %%
by = []
for ic in TOP10:
    e = ev[ev.ic == ic]
    after = e[[1, 2]].mean(axis=1).dropna()
    before = e[[-3, -2]].mean(axis=1).dropna()
    by.append({"ic": ic, "events": len(e), "after_effect": after.mean() if len(after) else np.nan,
               "after_pct": 100 * (np.exp(after.mean()) - 1) if len(after) else np.nan,
               "before_effect": before.mean() if len(before) else np.nan,
               "open_nofos_mean": panel[panel.ic == ic].open_nofos.mean(),
               "new_projects_mean": panel[panel.ic == ic].new_projects.mean()})
by = pd.DataFrame(by)
by.to_csv(OUT / "nofo_panel_by_ic.csv", index=False)
print(by.round(3).to_string(index=False))
