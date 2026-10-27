# %% [markdown]
# # 13 Data science by taxonomy group, FY2016–2025
#
# Which kinds of data science do NIH projects do, and how is the mix changing? Splits substantive
# data science projects (label Y) into the taxonomy's 7 groups (Data infrastructure has 2 subgroups:
# computing and platforms, data management and sharing) and 28 categories.
#
# Input: notebook 10's `exporter_core_projects_labeled.parquet` and notebook 08's
# `exporter_applications.parquet`. Output:
# - `reports/results/ds_groups_by_fy.csv`: projects and extramural funding per group and fiscal year
# - `reports/results/ds_categories_by_fy.csv`: the same per category
# - `reports/results/ds_groups_by_ic.csv`: projects and funding per group and institute
# - `data/processed/ds_projects.parquet`: one row per substantive data science record, for the API
#   (`api/main.py`) and the dashboard
#
# **Groups**
# - Methods, split three ways: statistics and analytics, computational modeling, artificial intelligence
# - Software and tools; data infrastructure (subgroups: computing and platforms; data management and
#   sharing); responsible AI; workforce
#
# **Definitions**
# - Group projects = substantive data science records with at least one category in the group that
#   fiscal year. A record can be in several groups, so groups add up to more than the total.
# - Share of data science projects = group projects / all substantive data science records that year
# - Develops AI projects = group projects whose AI role is building new AI methods
# - Group funding = extramural attributed cost of those records (center funding counted once);
#   share of data science funding = group funding / extramural attributed cost of all substantive
#   data science records

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from settings import PRELIMINARY_FY, SETTINGS, admin_period  # noqa: E402  # pyright: ignore[reportMissingImports]
from taxonomy import load_categories  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT.mkdir(parents=True, exist_ok=True)

# Reporting units: 7 groups, plus 2 subgroups inside Data infrastructure. A record in either subgroup
# counts once in the parent. `level` says which is which; filter on it so a record isn't counted twice.
GROUP_LABELS = {
    "statistics_analytics": "Statistics and analytics",
    "computational_modeling": "Computational modeling",
    "artificial_intelligence": "Artificial intelligence",
    "software_tools": "Software and tools",
    "data_infrastructure": "Data infrastructure",
    "responsible_ai": "Responsible AI",
    "workforce": "Workforce",
    "computing_platforms": "Computing and platforms",       # subgroup of Data infrastructure
    "data_sharing": "Data management and sharing",          # subgroup of Data infrastructure
}
SUBGROUPS = {"computing_platforms": "data_infrastructure", "data_sharing": "data_infrastructure"}
GROUP_LEVEL = {g: ("Subgroup" if g in SUBGROUPS else "Group") for g in GROUP_LABELS}
GROUP_PARENT = {g: SUBGROUPS.get(g, g) for g in GROUP_LABELS}
cats = load_categories()
cats = cats[cats.dimension.isin(["methods", "software_tools", "data_infrastructure", "data_sharing",
                                 "responsible_ai", "workforce"])].copy()
# Subgroup (the categories.yaml dimension or methods group), then the reporting group above it
cats["ds_subgroup"] = (cats.group.where(cats.dimension == "methods", cats.dimension)
                       .replace({"data_infrastructure": "computing_platforms"}))
cats["ds_group"] = cats.ds_subgroup.map(GROUP_PARENT)
cats["group_label"] = cats.ds_group.map(GROUP_LABELS)
cats["subgroup_label"] = cats.ds_subgroup.where(cats.ds_subgroup.isin(SUBGROUPS)).map(GROUP_LABELS)
# Each category counts toward its group and, inside Data infrastructure, its subgroup
group_of = {r.category_id: sorted({r.ds_group, r.ds_subgroup}) for r in cats.itertuples()}
cats[["ds_group", "group_label", "subgroup_label", "category_id", "label"]]

# %%
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet")
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet")
key = ["core_project_number", "subproject_id"]
NIH_ICS = {"CA", "HL", "AI", "GM", "AG", "NS", "MH", "DK", "HD", "DA", "AA", "ES", "EY", "DC", "DE", "AR", "EB", "HG",
           "LM", "MD", "NR", "AT", "TR", "TW", "OD", "RR", "CL", "RM"}  # NIH only; drops CDC, AHRQ, FDA, NIOSH, VA
apps = apps[apps.administering_ic.isin(NIH_ICS)]
core = core.merge(apps[key].drop_duplicates(), on=key)
ds = core[core.ds_label == "Y"].copy()
ds["categories"] = ds.model_categories.fillna("").str.split("; ").map(lambda c: sorted(x for x in c if x in group_of))
ds["groups"] = ds.categories.map(lambda c: sorted({u for x in c for u in group_of[x]}))
print(f"{len(ds):,} substantive data science records; {(ds.groups.str.len() == 0).sum():,} with no group category")

# Drop any same-named columns from the applications file first, so the merge doesn't add _x/_y suffixes
apps = apps.drop(columns=[c for c in ["groups", "categories", "ai_role", "ai_label"] if c in apps.columns])
apps = apps.merge(ds[key + ["groups", "categories", "ai_role"]], on=key, how="inner")
print("applications columns:", list(apps.columns))
apps["record"] = apps.core_project_number + "|" + apps.subproject_id.fillna("")
apps["extramural"] = ~apps.activity.fillna("").str.startswith("Z")

# %% [markdown]
# ## By group and fiscal year

# %%
_stop = start("By group and fiscal year")
def by_fy(long: pd.DataFrame, col: str) -> pd.DataFrame:
    ext = long[long.extramural]
    out = pd.DataFrame({
        "projects": long.groupby(["fy", col]).record.nunique(),
        "extramural_cost": ext.groupby(["fy", col]).attributed_cost.sum(),
        "develops_ai_projects": long[long.ai_role == "develops_ai"].groupby(["fy", col]).record.nunique(),
    }).fillna(0).reset_index()
    totals = pd.DataFrame({"ds_projects": apps.groupby("fy").record.nunique(),
                           "ds_extramural_cost": apps[apps.extramural].groupby("fy").attributed_cost.sum()})
    out = out.merge(totals, left_on="fy", right_index=True)
    out["share_of_ds_projects"] = out.projects / out.ds_projects
    out["share_of_ds_funding"] = out.extramural_cost / out.ds_extramural_cost
    return out


g = by_fy(apps.explode("groups").dropna(subset=["groups"]).rename(columns={"groups": "ds_group"}), "ds_group")
g["group_label"] = g.ds_group.map(GROUP_LABELS)
g["level"], g["parent_group"] = g.ds_group.map(GROUP_LEVEL), g.ds_group.map(GROUP_PARENT).map(GROUP_LABELS)
g["preliminary"] = g.fy == PRELIMINARY_FY  # FY2026 is preliminary
g["admin_period"] = g.fy.map(admin_period)
g.to_csv(OUT / "ds_groups_by_fy.csv", index=False)

c = by_fy(apps.explode("categories").dropna(subset=["categories"]).rename(columns={"categories": "category_id"}),
          "category_id")
c = c.merge(cats[["category_id", "label", "ds_group", "group_label", "ds_subgroup", "subgroup_label"]], on="category_id")
c["preliminary"] = c.fy == PRELIMINARY_FY
c.to_csv(OUT / "ds_categories_by_fy.csv", index=False)
g.pivot(index="group_label", columns="fy", values="share_of_ds_projects").round(3)
_stop()
# %% [markdown]
# ## By group and institute (FY2016–2025)
# Projects = distinct records in the group with any application at the IC; share of IC data science =
# group projects / all substantive data science records at that IC.

# %%
_stop = start("By group and institute (FY2016–2025)")
IC_SHORT = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}
gl = apps.explode("groups").dropna(subset=["groups"]).rename(columns={"groups": "ds_group"})
gl["ic"] = gl.administering_ic.map(IC_SHORT).fillna(gl.administering_ic)
apps["ic"] = apps.administering_ic.map(IC_SHORT).fillna(apps.administering_ic)
gic = pd.DataFrame({"projects": gl.groupby(["ds_group", "ic"]).record.nunique(),
                    "extramural_cost": gl[gl.extramural].groupby(["ds_group", "ic"]).attributed_cost.sum()}
                   ).fillna(0).reset_index()
gic = gic.merge(apps.groupby("ic").record.nunique().rename("ic_ds_projects"), left_on="ic", right_index=True)
gic["share_of_ic_ds_projects"] = gic.projects / gic.ic_ds_projects
gic["group_label"] = gic.ds_group.map(GROUP_LABELS)
gic["level"] = gic.ds_group.map(GROUP_LEVEL)
gic.sort_values(["ds_group", "projects"], ascending=[True, False]).to_csv(OUT / "ds_groups_by_ic.csv", index=False)
_stop()
# %% [markdown]
# ## Record-level table for the API

# %%
_stop = start("Record-level table for the API")
apps["ext_cost"] = apps.attributed_cost.where(apps.extramural, 0)
agg = {"first_fy": ("fy", "min"), "last_fy": ("fy", "max"), "extramural_cost": ("ext_cost", "sum")}
for out_col, src in [("project_title", "project_title"), ("ic", "administering_ic"), ("activity", "activity"),
                     ("org_name", "org_name"), ("org_state", "org_state")]:
    if src in apps.columns:
        agg[out_col] = (src, "last")
latest = apps.sort_values("fy").groupby(key).agg(**agg).reset_index()
nofo_cols = ["nofos"] if "nofos" in ds.columns else []
projects = ds[key + ["ds_label", "ai_label", "ai_role", "groups", "categories", *nofo_cols]].merge(latest, on=key)
projects["groups"] = projects.groups.str.join("; ")
projects["categories"] = projects.categories.str.join("; ")
projects.to_parquet(PROCESSED / "ds_projects.parquet", index=False)
print(f"{len(projects):,} records saved for the API")
projects.head()
_stop()
# %% [markdown]
# ## Data science by NOFO (notice of funding opportunity)
# Ties funding opportunities to the data science projects they funded. One row per NOFO number:
# all NIH records that responded to it, how many are substantive data science and AI, the share, and
# the groups most common among its data science records. Records can respond to different NOFOs in
# different years (for example a renewal), so a record counts under each NOFO it used.
# - ds_share = data science records under the NOFO / all records under it

# %%
_stop = start("Data science by NOFO (notice of funding opportunity)")
if "nofo" in apps.columns:
    allr = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                           columns=["administering_ic", "core_project_number", "subproject_id", "fy", "nofo"])
    allr = allr[allr.administering_ic.isin(NIH_ICS) & allr.nofo.notna() & (allr.nofo.astype(str).str.strip() != "")]
    allr["record"] = allr.core_project_number + "|" + allr.subproject_id.fillna("")
    ds_recs = set(apps.record)
    ai_recs = set((ds.loc[ds.ai_label == "Y", "core_project_number"] + "|" + ds.loc[ds.ai_label == "Y", "subproject_id"].fillna("")))
    n = allr.drop_duplicates(["nofo", "record"])
    by_nofo = n.groupby("nofo").agg(records=("record", "nunique"), first_fy=("fy", "min"), last_fy=("fy", "max"))
    by_nofo["ds_records"] = n[n.record.isin(ds_recs)].groupby("nofo").record.nunique()
    by_nofo["ai_records"] = n[n.record.isin(ai_recs)].groupby("nofo").record.nunique()
    by_nofo = by_nofo.fillna({"ds_records": 0, "ai_records": 0})
    by_nofo["ds_share"] = by_nofo.ds_records / by_nofo.records
    by_nofo["ai_share"] = by_nofo.ai_records / by_nofo.records
    rg = n[n.record.isin(ds_recs)].merge(apps[["record", "groups"]].drop_duplicates("record"), on="record").explode("groups")
    rg = rg[rg.groups.isin([g for g in GROUP_LABELS if GROUP_LEVEL[g] == "Group"])]
    top = (rg.groupby(["nofo", "groups"]).record.nunique().reset_index().sort_values("record", ascending=False)
           .groupby("nofo").head(3).assign(label=lambda d: d.groups.map(GROUP_LABELS))
           .groupby("nofo").label.agg("; ".join).rename("top_groups"))
    by_nofo = by_nofo.join(top).reset_index().sort_values("ds_records", ascending=False)
    by_nofo.to_csv(OUT / "ds_by_nofo.csv", index=False)
    print(f"{len(by_nofo):,} NOFOs; {(by_nofo.ds_records > 0).sum():,} funded at least one data science record")
    by_nofo.head(10)
_stop()
# %% [markdown]
# ## Tableau extract: filter by group, IC, fiscal year, activity code, state, and AI role
# One row per record × fiscal year × group. In Tableau, count projects with COUNTD([record]) and sum
# [extramural_cost] only after filtering to one group, since a record appears once per group it is in.
# `ic_totals_by_fy.csv` gives the denominators (all records and all extramural funding per IC and year)
# for shares.

# %%
_stop = start("Tableau extract: filter by group, IC, fiscal year, activity code, state, and AI role")
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC"}
extra = [c for c in ["org_state"] if c in apps.columns]
tab = (apps.merge(ds[key + ["ai_label"]], on=key)
       .explode("groups").dropna(subset=["groups"]).rename(columns={"groups": "ds_group"}))
tab["group_label"] = tab.ds_group.map(GROUP_LABELS)
tab["level"] = tab.ds_group.map(GROUP_LEVEL)          # Group or Subgroup: filter to one level per view
tab["parent_group"] = tab.ds_group.map(GROUP_PARENT).map(GROUP_LABELS)
tab["ic"] = tab.administering_ic.map(IC_NAMES).fillna(tab.administering_ic)
tab["extramural_cost"] = tab.attributed_cost.where(tab.extramural)
extra += [c for c in ["nofo"] if c in tab.columns]  # funding opportunity (NOFO) behind each application
tab = tab[["record", "fy", "ic", "activity", *extra, "ds_group", "group_label", "level", "parent_group", "ai_label", "ai_role",
           "extramural", "extramural_cost"]]
tab["preliminary"] = tab.fy == PRELIMINARY_FY
tab["admin_period"] = tab.fy.map(admin_period)
tab.to_csv(OUT / "tableau_ds_groups.csv", index=False)

all_apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                           columns=["fy", "administering_ic", "activity", "core_project_number", "subproject_id",
                                    "attributed_cost"])
all_apps = all_apps[all_apps.administering_ic.isin(NIH_ICS)]
all_apps["record"] = all_apps.core_project_number + "|" + all_apps.subproject_id.fillna("")
all_apps["ic"] = all_apps.administering_ic.map(IC_NAMES).fillna(all_apps.administering_ic)
ext = all_apps[~all_apps.activity.fillna("").str.startswith("Z")]
totals = pd.DataFrame({"all_projects": all_apps.groupby(["fy", "ic"]).record.nunique(),
                       "all_extramural_cost": ext.groupby(["fy", "ic"]).attributed_cost.sum()}).fillna(0).reset_index()
totals["preliminary"] = totals.fy == PRELIMINARY_FY
totals.to_csv(OUT / "ic_totals_by_fy.csv", index=False)
print(f"Tableau extract: {len(tab):,} rows; IC totals: {len(totals):,} rows")
_stop()
# %% [markdown]
# ## RCDC categories (NIH's own spending categories)
# RCDC = Research, Condition, and Disease Categorization. Each application lists its RCDC categories
# in `nih_spending_cats` (semicolon-separated). A record has an RCDC category if any of its
# applications lists it.
#
# Outputs
# - `rcdc_by_group.csv`: for all data science, each group, and AI, the RCDC categories with the most
#   projects, FY2016–2025 (top 25 per scope); share = projects with the category / projects in the scope
# - `tableau_rcdc_bridge.csv`: record × fiscal year × RCDC category, for an RCDC filter in Tableau
#   (relate it to `tableau_ds_groups.csv` on record and fy)
# - `rcdc_ai_comparison.csv`: taxonomy AI vs. RCDC "Machine Learning and Artificial Intelligence" by
#   fiscal year: both, taxonomy only, RCDC only

# %%
_stop = start("RCDC categories (NIH's own spending categories)")
RCDC_COL = "nih_spending_cats"
RCDC_AI = "Machine Learning and Artificial Intelligence"


def rcdc_long(df: pd.DataFrame) -> pd.DataFrame:
    """One row per record × fiscal year × RCDC category."""
    r = df[["record", "fy", RCDC_COL]].dropna(subset=[RCDC_COL]).copy()
    r["rcdc"] = r[RCDC_COL].astype(str).str.split(";")
    r = r.explode("rcdc")
    r["rcdc"] = r.rcdc.str.strip()
    return r[r.rcdc != ""][["record", "fy", "rcdc"]].drop_duplicates()


ds_rcdc = rcdc_long(apps)
ds_rcdc.to_csv(OUT / "tableau_rcdc_bridge.csv", index=False)

rec_groups = apps[["record", "groups"]].drop_duplicates("record").explode("groups").dropna()
rec_rcdc = ds_rcdc[["record", "rcdc"]].drop_duplicates()
cost = apps[apps.extramural].groupby("record").attributed_cost.sum()
scopes = [("all_data_science", "All data science", set(apps.record))]
scopes += [(g, GROUP_LABELS[g], set(rec_groups.loc[rec_groups.groups == g, "record"])) for g in GROUP_LABELS]
rows = []
for sid, label, recs in scopes:
    r = rec_rcdc[rec_rcdc.record.isin(recs)]
    top = (r.groupby("rcdc").record.nunique().rename("projects").reset_index()
           .assign(extramural_cost=lambda d: d.rcdc.map(
               r.assign(c=r.record.map(cost).fillna(0)).groupby("rcdc").c.sum())))
    top["share_of_scope_projects"] = top.projects / len(recs)
    top = top.sort_values("projects", ascending=False).head(25)
    top.insert(0, "scope", sid)
    top.insert(1, "scope_label", label)
    top["rank"] = range(1, len(top) + 1)
    rows.append(top)
rcdc_by_group = pd.concat(rows, ignore_index=True)
rcdc_by_group.to_csv(OUT / "rcdc_by_group.csv", index=False)
print(rcdc_by_group[rcdc_by_group["rank"] <= 5][["scope_label", "rank", "rcdc", "projects",
                                                  "share_of_scope_projects"]].to_string(index=False))
_stop()

# %% Taxonomy AI vs. RCDC AI, all NIH records by fiscal year
full = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["fy", "administering_ic", "core_project_number", "subproject_id", RCDC_COL])
full = full[full.administering_ic.isin(NIH_ICS)]
full["record"] = full.core_project_number + "|" + full.subproject_id.fillna("")
full["rcdc_ai"] = full[RCDC_COL].fillna("").str.contains(RCDC_AI, regex=False)
tax_ai = set((core.loc[core.ai_label == "Y", "core_project_number"] + "|" +
              core.loc[core.ai_label == "Y", "subproject_id"].fillna("")))
full["tax_ai"] = full.record.isin(tax_ai)
per = full.groupby(["fy", "record"]).agg(rcdc_ai=("rcdc_ai", "any"), tax_ai=("tax_ai", "any")).reset_index()
cmp_ = per.groupby("fy").apply(lambda d: pd.Series({
    "both": int((d.rcdc_ai & d.tax_ai).sum()), "taxonomy_only": int((~d.rcdc_ai & d.tax_ai).sum()),
    "rcdc_only": int((d.rcdc_ai & ~d.tax_ai).sum()), "rcdc_ai": int(d.rcdc_ai.sum()),
    "taxonomy_ai": int(d.tax_ai.sum())}), include_groups=False).reset_index()
cmp_["rcdc_recall"] = cmp_.both / cmp_.rcdc_ai.where(cmp_.rcdc_ai > 0)  # share of RCDC AI the taxonomy also calls AI
cmp_["preliminary"] = cmp_.fy == PRELIMINARY_FY
cmp_.to_csv(OUT / "rcdc_ai_comparison.csv", index=False)
cmp_

# %% [markdown]
# ## RCDC coverage by IC: how much of each RCDC category is data science, AI, or each group
# For every IC, fiscal year, and RCDC category: all NIH records with the category (`rcdc_projects`)
# and, for each scope (Data science, AI, the 7 groups, and the 2 Data infrastructure subgroups), how many are in it.
# - share = records in the category and the scope / all records in the category (same IC and year)
# One row per fiscal year × IC × RCDC category × scope, so Tableau can filter on any of them.

# %%
_stop = start("RCDC coverage by IC: how much of each RCDC category is data science, AI, or each group")
tax_ds = set((core.loc[core.ds_label == "Y", "core_project_number"] + "|" +
              core.loc[core.ds_label == "Y", "subproject_id"].fillna("")))
scopes_cov = {"Data science": tax_ds, "AI": tax_ai}
scopes_cov.update({GROUP_LABELS[g]: set(rec_groups.loc[rec_groups.groups == g, "record"]) for g in GROUP_LABELS})
full["ic"] = full.administering_ic.map(IC_NAMES).fillna(full.administering_ic)
fr = rcdc_long(full.drop_duplicates(["record", "fy"]))
fr = fr.merge(full[["record", "fy", "ic"]].drop_duplicates(["record", "fy"]), on=["record", "fy"])
base = fr.groupby(["fy", "ic", "rcdc"]).record.nunique().rename("rcdc_projects")
parts = []
for scope, recs in scopes_cov.items():
    n = fr[fr.record.isin(recs)].groupby(["fy", "ic", "rcdc"]).record.nunique().rename("scope_projects")
    parts.append(pd.concat([base, n], axis=1).fillna({"scope_projects": 0}).reset_index().assign(scope=scope))
cov = pd.concat(parts, ignore_index=True)
cov["scope_projects"] = cov.scope_projects.astype(int)
cov["share"] = cov.scope_projects / cov.rcdc_projects
cov["preliminary"] = cov.fy == PRELIMINARY_FY
cov.to_csv(OUT / "rcdc_ic_coverage.csv", index=False)
print(f"RCDC coverage: {len(cov):,} rows ({cov.rcdc.nunique()} RCDC categories, {cov.ic.nunique()} ICs, "
      f"{cov.scope.nunique()} scopes)")
last_full = cov.fy.max() - (1 if PRELIMINARY_FY == cov.fy.max() else 0)
FOCUS_IC = SETTINGS.get("focus_ic")  # preview one IC (config/local.yaml); the saved table covers every IC
if FOCUS_IC:
    print(f"Preview: RCDC coverage for {FOCUS_IC}, FY{last_full}")
    print(cov[(cov.ic == FOCUS_IC) & (cov.fy == last_full) & (cov.scope.isin(["Data science", "AI"]))]
          .pivot_table(index="rcdc", columns="scope", values="share").join(
              base.loc[last_full].loc[FOCUS_IC]).sort_values("rcdc_projects", ascending=False).head(10).round(3))
else:
    print("Set focus_ic in config/local.yaml to preview one institute here")
_stop()
