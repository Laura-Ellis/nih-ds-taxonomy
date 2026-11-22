# %% [markdown]
# # Where NIH funds data science abroad: direct awards
#
# Analysis D, part 1. Projects whose recipient organization is outside the United States (RePORTER `org_country`),
# FY2016 to FY2026 (FY2026 preliminary). A project = a record (core project number + subproject id), the same unit
# as the other analyses. Data science = `ds_label` = Y; AI = `ai_label` = Y. Funding = attributed cost (centers
# counted once).
#
# - Data science share = data science records ÷ all records, with a 95% Wilson interval.
# - Regions: WHO regions (`regions.py`).
# - Administration periods: Obama (FY2016), Trump 1 (FY2017–2020), Biden (FY2021–2024), Trump 2 (FY2025–2026).
# - DS-I Africa: projects under the Common Fund NOFOs RFA-RM-20-015 to -018, RFA-RM-22-022 and RFA-RM-22-023.
#
# Outputs in `reports/results/global/`.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "results" / "global"
OUT.mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST = 2016, 2026
DSI_AFRICA = {"RFA-RM-20-015", "RFA-RM-20-016", "RFA-RM-20-017", "RFA-RM-20-018", "RFA-RM-22-022", "RFA-RM-22-023"}

sys.path.insert(0, str(ROOT / "analyses" / "global"))
from regions import iso3, who_region  # noqa: E402

REGION_OF = lambda country: who_region(iso3(country))  # noqa: E731
# display names for the RePORTER spellings that need one
NAME = {"BURKINA": "Burkina Faso", "CONGO DEM REP": "DR Congo", "TANZANIA U REP": "Tanzania",
        "ST KITTS/NEVIS": "St. Kitts and Nevis", "TRINIDAD/TOBA": "Trinidad and Tobago"}


def period(fy):
    return "Obama" if fy <= 2016 else "Trump 1" if fy <= 2020 else "Biden" if fy <= 2024 else "Trump 2"


def wilson(k, n, z=1.96):
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = np.where(n > 0, k / np.maximum(n, 1), np.nan)
    d = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return mid - half, mid + half


def shares(g, k="ds", n="records"):
    lo, hi = wilson(g[k], g[n])
    return g.assign(**{f"{k}_share": g[k] / g[n], f"{k}_lo": lo, f"{k}_hi": hi})


# %%
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "org_country", "org_name", "administering_ic", "activity", "nofo", "attributed_cost"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label", "ai_label"])
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy, errors="coerce")
a = a[a.fy.between(FY_FIRST, FY_LAST)].copy()
a["record"] = a.core_project_number + "|" + a.subproject_id.fillna("").astype(str)
a["foreign"] = a.org_country.notna() & a.org_country.ne("UNITED STATES")
a["ds"], a["ai"] = a.ds_label.eq("Y"), a.ai_label.eq("Y")
a["cost"] = a.attributed_cost.fillna(0.0)
a["dsi_africa"] = a.nofo.isin(DSI_AFRICA)
a["period"] = a.fy.map(period)
assert a.loc[a.foreign, "org_country"].map(REGION_OF).notna().all(), "country without a region"

# one row per record: labels, total funding, and recipient of the latest year
def records(df):
    r = (df.sort_values("fy").groupby("record")
         .agg(country=("org_country", "last"), org=("org_name", "last"), ic=("administering_ic", "last"),
              ds=("ds", "max"), ai=("ai", "max"), dsi_africa=("dsi_africa", "max"), cost=("cost", "sum"))
         .reset_index())
    r["region"] = r.country.map(REGION_OF)
    r["ds_cost"] = r.cost.where(r.ds, 0.0)
    return r


rec = records(a)
# a few records moved between a U.S. and a foreign recipient: count only their foreign years here
f = records(a[a.foreign])
# record-level tables for institute cuts (data/interim is git-ignored)
rec.assign(foreign=rec.record.isin(f.record))[["record", "ic", "ds", "ai", "cost", "foreign"]].to_parquet(
    ROOT / "data" / "interim" / "global_all_records.parquet", index=False)
f.to_parquet(ROOT / "data" / "interim" / "global_direct_records.parquet", index=False)
a[["record", "fy", "period", "administering_ic", "foreign", "ds", "dsi_africa"]].to_parquet(
    ROOT / "data" / "interim" / "global_record_years.parquet", index=False)

# %% [markdown]
# ## Headline numbers

# %%
head = pd.DataFrame({
    "group": ["Foreign recipients", "All NIH"],
    "records": [len(f), len(rec)], "ds": [f.ds.sum(), rec.ds.sum()], "ai": [f.ai.sum(), rec.ai.sum()],
    "countries": [f.country.nunique(), np.nan], "cost": [f.cost.sum(), rec.cost.sum()],
    "ds_cost": [f.ds_cost.sum(), rec.ds_cost.sum()]})
head = shares(shares(head), "ai")
head["ds_cost_share"] = head.ds_cost / head.cost
head.to_csv(OUT / "headline.csv", index=False)
print(head.round(3).to_string(index=False))

# %% [markdown]
# ## Countries and regions

# %%
def by(df, col):
    g = df.groupby(col).agg(records=("record", "size"), ds=("ds", "sum"), ai=("ai", "sum"),
                            dsi_africa=("dsi_africa", "sum"), cost=("cost", "sum"), ds_cost=("ds_cost", "sum"))
    return shares(g.reset_index()).sort_values("records", ascending=False)


countries = by(f, "country").assign(region=lambda d: d.country.map(REGION_OF),
                                    name=lambda d: d.country.map(NAME).fillna(d.country.str.title()))
countries.to_csv(OUT / "countries.csv", index=False)
regions = by(f, "region")
regions.to_csv(OUT / "regions.csv", index=False)
print(countries.head(12)[["name", "records", "ds", "ds_share", "ds_lo", "ds_hi", "cost"]].round(3).to_string(index=False))
print(regions[["region", "records", "ds", "ds_share", "ds_lo", "ds_hi", "cost"]].round(3).to_string(index=False))

# %%
inst = (f.groupby(["org", "country"]).agg(records=("record", "size"), ds=("ds", "sum"), ds_cost=("ds_cost", "sum"))
        .reset_index().sort_values(["ds", "ds_cost"], ascending=False))
inst.to_csv(OUT / "institutions.csv", index=False)
print(inst.head(12).to_string(index=False))

# %% [markdown]
# ## Trend by administration period
#
# A record counts in every period it was funded in.

# %%
pr = (a.groupby(["period", "record"]).agg(foreign=("foreign", "max"), ds=("ds", "max"), dsi=("dsi_africa", "max"))
      .reset_index())
trend = []
for grp, sub in [("Foreign recipients", pr[pr.foreign]), ("Foreign, without DS-I Africa", pr[pr.foreign & ~pr.dsi]),
                 ("All NIH", pr)]:
    g = sub.groupby("period").agg(records=("record", "size"), ds=("ds", "sum")).reset_index().assign(group=grp)
    trend.append(g)
trend = shares(pd.concat(trend))
order = ["Obama", "Trump 1", "Biden", "Trump 2"]
trend["period"] = pd.Categorical(trend.period, order, ordered=True)
trend = trend.sort_values(["group", "period"])
trend.to_csv(OUT / "trend_period.csv", index=False)
print(trend.round(3).to_string(index=False))

# %% [markdown]
# ## DS-I Africa's part

# %%
fd = f[f.ds]
dsi = pd.DataFrame({
    "measure": ["Foreign data science records", "Foreign data science funding",
                "African data science records", "African data science funding"],
    "dsi_africa": [fd.dsi_africa.sum(), fd.loc[fd.dsi_africa, "cost"].sum(),
                   fd[fd.region.eq("African Region")].dsi_africa.sum(),
                   fd.loc[fd.dsi_africa & fd.region.eq("African Region"), "cost"].sum()],
    "total": [len(fd), fd.cost.sum(), fd.region.eq("African Region").sum(),
              fd.loc[fd.region.eq("African Region"), "cost"].sum()]})
dsi["share"] = dsi.dsi_africa / dsi.total
no_dsi = f[~f.dsi_africa]
lo, hi = wilson(no_dsi.ds.sum(), len(no_dsi))
print(dsi.round(3).to_string(index=False))
print(f"Foreign data science share without DS-I Africa: {no_dsi.ds.mean():.3f} (95% CI {lo:.3f}–{hi:.3f})")
dsi.to_csv(OUT / "dsi_africa.csv", index=False)
