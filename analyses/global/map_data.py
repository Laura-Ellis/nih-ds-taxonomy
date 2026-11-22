# %% [markdown]
# # Analysis D: data for the interactive map
#
# Data science funding abroad by country, fiscal year, institute, taxonomy group and route, for the site map.
# Same filters as `direct_awards.py` and `subawards.py`:
#
# - Direct = attributed cost of data science records in the years their recipient was outside the U.S.
# - Subaward = reported first-tier subaward amounts to foreign partners on data science primes, by the report's
#   fiscal year. Reports larger than their prime award are dropped.
# - Taxonomy group = the record's `groups` in `ds_projects.parquet` (the prime's parent record for subawards). A
#   record can sit in several groups, so group rows add up to more than the "all" row.
#
# Output: `reports/results/global/map_country_fy.csv` (iso3, fy, ic, group, direct, subaward).

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
PROCESSED, INTERIM = ROOT / "data" / "processed", ROOT / "data" / "interim"
OUT = ROOT / "reports" / "results" / "global"
FY_FIRST, FY_LAST = 2016, 2026
sys.path.insert(0, str(ROOT / "analyses" / "global"))
from regions import iso3  # noqa: E402

key = ["core_project_number", "subproject_id"]
ds = pd.read_parquet(PROCESSED / "ds_projects.parquet", columns=key + ["ds_label", "groups"])
ds = ds[ds.ds_label.eq("Y")].copy()
ds["subproject_id"] = ds.subproject_id.fillna("").astype(str).str.strip()
ds["groups"] = ds.groups.fillna("").str.split("; ").map(lambda g: [x for x in g if x])
GROUPS = ds[key + ["groups"]]

# %% direct awards, by record-year
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "org_country", "administering_ic", "attributed_cost"])
a["fy"] = pd.to_numeric(a.fy, errors="coerce")
a["subproject_id"] = a.subproject_id.fillna("").astype(str).str.strip()
a = a[a.fy.between(FY_FIRST, FY_LAST) & a.org_country.notna() & a.org_country.ne("UNITED STATES")]
# data science = the record's own label, as in direct_awards.py; groups where the taxonomy has them
lbl = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label"])
lbl["subproject_id"] = lbl.subproject_id.fillna("").astype(str).str.strip()
a = a.merge(lbl[lbl.ds_label.eq("Y")][key], on=key, how="inner").merge(GROUPS, on=key, how="left")
a["groups"] = a.groups.map(lambda g: g if isinstance(g, list) else [])
direct = pd.DataFrame({"iso3": a.org_country.map(iso3), "fy": a.fy.astype(int), "ic": a.administering_ic,
                       "groups": a.groups, "amount": a.attributed_cost.fillna(0.0), "route": "direct"})

# %% subawards, by report
s = pd.read_parquet(INTERIM / "usaspending_subawards.parquet")
s = s[s.prime_award_funding_sub_agency_name.eq("National Institutes of Health")].copy()
s["fy"] = pd.to_numeric(s.subaward_action_date_fiscal_year, errors="coerce")
s = s[s.fy.between(FY_FIRST, FY_LAST)].copy()
s["amount"] = pd.to_numeric(s.subaward_amount, errors="coerce").fillna(0.0)
s = s[~(s.amount > pd.to_numeric(s.prime_award_amount, errors="coerce"))]
s["iso3"] = s.subawardee_country_name.map(iso3)
s = s[s.iso3.notna() & s.iso3.ne("USA")]
s["fain"] = s.prime_award_fain.str.strip().str.upper()
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["ds_label", "administering_ic"])
core["subproject_id"] = core.subproject_id.fillna("").astype(str).str.strip()
core["parent"] = core.subproject_id.eq("")
lab = core.sort_values("parent", ascending=False).drop_duplicates("core_project_number")
lab = lab[lab.ds_label.eq("Y")].merge(GROUPS, on=key, how="left")
lab["groups"] = lab.groups.map(lambda g: g if isinstance(g, list) else [])
s = s.merge(lab[["core_project_number", "administering_ic", "groups"]], left_on="fain",
            right_on="core_project_number", how="inner")
sub = pd.DataFrame({"iso3": s.iso3, "fy": s.fy.astype(int), "ic": s.administering_ic, "groups": s.groups,
                    "amount": s.amount, "route": "subaward"})

# %% long table: "all" once per row, then one row per group
x = pd.concat([direct, sub], ignore_index=True)
assert x.iso3.notna().all(), "country without an ISO3 code"
allrows = x.assign(group="all").drop(columns="groups")
grp = x.explode("groups").dropna(subset=["groups"]).rename(columns={"groups": "group"})
long = (pd.concat([allrows, grp]).groupby(["iso3", "fy", "ic", "group", "route"]).amount.sum()
        .unstack("route", fill_value=0.0).reset_index())
long.columns.name = None
long.to_csv(OUT / "map_country_fy.csv", index=False, float_format="%.0f")

tot = long[long.group.eq("all")][["direct", "subaward"]].sum()
print(f"Direct ${tot.direct / 1e6:,.1f}M, subaward ${tot.subaward / 1e6:,.1f}M, countries {long.iso3.nunique()}, rows {len(long):,}")
