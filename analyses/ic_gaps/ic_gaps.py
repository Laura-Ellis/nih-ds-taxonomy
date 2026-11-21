# %% [markdown]
# # Where data science is thin at each of the 10 largest institutes
#
# Internal gap analysis (full results git-ignored in `reports/internal/ic_gaps/`). The 10 institutes with the most
# data science projects, in alphabetical order. Three lenses, FY2016 to FY2025 (FY2026 preliminary, left out):
#
# 1. **Vs. the rest of NIH (methods mix).** Location quotient for each taxonomy category:
#    LQ = (IC data science projects in the category ÷ IC data science projects)
#       ÷ (rest-of-NIH data science projects in the category ÷ rest-of-NIH data science projects).
#    LQ = 1: same mix as the rest of NIH; LQ < 0.5 (and the category is at least 2% of the rest of NIH's
#    data science projects) = gap.
#    Application areas (neuroscience, imaging, ...) and AI roles are left out: they describe the domain, not the method.
# 2. **Vs. its own mission areas.** For each RCDC category with at least 300 IC projects and 2% of IC funding
#    (method categories left out):
#    gap points = area data science funding share at the IC − IC data science funding share overall.
#    Negative = data science is thinner in that area than across the IC. The rest of NIH's data science share
#    in the same area is shown as a benchmark. Gap = at least 5 points below the IC's own share and below the rest of NIH.
# 3. **Vs. disease burden.** For each GBD level 3 cause (RCDC to GBD crosswalk, `analyses/topics`) where the IC spends at
#    least $50M and 10% of NIH's funding in the cause (low-confidence crosswalk matches left out): IC data science intensity = IC data science funding ÷ IC funding in the cause, compared with the
#    rest of NIH's intensity in the same cause, next to U.S. DALYs. A burden gap = a cause in the top half of DALYs
#    among the IC's causes with intensity at least 2 points below the rest of NIH's.
#
# Plus NOFO links (`reports/results/nofo_links.csv`): share of the IC's data science projects that came in under a
# broad NOFO with a weak fit, by taxonomy group (the best-fitting NOFO, not necessarily the funding one).
#
# Funding = attributed cost (centers counted once). Data science = `ds_label` = Y.
# Outputs: `reports/internal/ic_gaps/<ic>/lens*.csv`, `reports/internal/ic_gaps/summary.csv`.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
PROCESSED, RESULTS = ROOT / "data" / "processed", ROOT / "reports" / "results"
TOPICS = ROOT / "analyses" / "topics"
OUT = ROOT / "reports" / "internal" / "ic_gaps"
OUT.mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST = 2016, 2025
TOP_N = 10
MIN_AREA, MIN_CAUSE_COST, MIN_CAT_SHARE, LQ_GAP = 300, 50e6, 0.02, 0.5
IC = {"CA": "NCI", "GM": "NIGMS", "AG": "NIA", "AI": "NIAID", "HL": "NHLBI", "MH": "NIMH", "NS": "NINDS",
      "HD": "NICHD", "DK": "NIDDK", "DA": "NIDA", "EB": "NIBIB", "HG": "NHGRI", "ES": "NIEHS", "EY": "NEI",
      "AR": "NIAMS", "OD": "OD", "DC": "NIDCD", "LM": "NLM", "AA": "NIAAA", "TR": "NCATS", "MD": "NIMHD",
      "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH"}
import yaml  # noqa: E402
_tax = yaml.safe_load((ROOT / "taxonomy" / "categories.yaml").read_text(encoding="utf-8"))
# application areas and AI roles describe where or how AI is used, not a data science method, so lens 1 leaves them out
CAT_LABEL = {c["id"]: c["label"] for dim in _tax["dimensions"] for c in dim.get("categories", [])
             if dim["id"] not in ("application_area", "ai_role")}
GROUP_LABEL = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
               "artificial_intelligence": "Artificial intelligence", "software_tools": "Software and tools",
               "data_infrastructure": "Data infrastructure", "responsible_ai": "Responsible AI", "workforce": "Workforce"}
MIN_AREA_COST_SHARE, MIN_CAUSE_IC_SHARE, AREA_GAP, CAUSE_GAP = 0.02, 0.10, -5, -2
METHOD_AREAS = {"Data Science", "Networking and Information Technology R&D (NITRD)", "Networking and Information Technology R&D",
                "Machine Learning and Artificial Intelligence", "Bioengineering", "Biotechnology"}

# %%
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "administering_ic", "nih_spending_cats", "attributed_cost"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label", "categories"])
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy, errors="coerce")
a = a[a.fy.between(FY_FIRST, FY_LAST)].copy()
a["ic"] = a.administering_ic.map(IC)
a = a[a.ic.notna()].copy()
a["record"] = a.core_project_number + "|" + a.subproject_id.fillna("").astype(str)
a["ds"] = a.ds_label.eq("Y")
a["cost"] = a.attributed_cost.fillna(0.0)
a["cats"] = a.nih_spending_cats.fillna("").str.split(";").map(lambda xs: {x.strip() for x in xs if x.strip()})

ds_n = a[a.ds].groupby("ic").record.nunique().sort_values(ascending=False)
ICS = sorted(ds_n.head(TOP_N).index)
print("Top", TOP_N, "by data science projects (alphabetical):", ", ".join(ICS))

# %% [markdown]
# ## Lens 1: methods mix vs. the rest of NIH (location quotient)

# %%
dsp = a[a.ds].drop_duplicates("record")[["record", "ic", "categories"]]
tax = dsp.assign(cat=dsp.categories.fillna("").str.split(";")).explode("cat")
tax["cat"] = tax.cat.str.strip()
tax = tax[tax.cat.isin(CAT_LABEL)]
tax_n = tax.groupby(["ic", "cat"]).record.nunique().unstack(fill_value=0)
ds_tot = dsp.groupby("ic").record.nunique()


def lens1(ic):
    ic_n, rest_n = tax_n.loc[ic], tax_n.drop(index=ic).sum()
    ic_t, rest_t = ds_tot[ic], ds_tot.drop(ic).sum()
    d = pd.DataFrame({"ic_projects": ic_n, "ic_share": ic_n / ic_t, "rest_share": rest_n / rest_t})
    d["lq"] = d.ic_share / d.rest_share
    d["gap"] = (d.lq < LQ_GAP) & (d.rest_share >= MIN_CAT_SHARE)
    d["label"] = d.index.map(CAT_LABEL)
    return d[d.rest_share >= MIN_CAT_SHARE].sort_values("lq").rename_axis("category").reset_index()

# %% [markdown]
# ## Lens 2: own mission areas

# %%
cl = a[["ic", "record", "ds", "cost", "cats"]].explode("cats").dropna(subset=["cats"])
cl["ds_cost"] = cl.cost.where(cl.ds, 0.0)
area = cl.groupby(["ic", "cats"]).agg(projects=("record", "nunique"), cost=("cost", "sum"), ds_cost=("ds_cost", "sum"))
ic_cost = a.groupby("ic").cost.sum()
ic_ds_cost = a[a.ds].groupby("ic").cost.sum()


def lens2(ic):
    d = area.loc[ic].copy()
    rest = area.drop(index=ic, level="ic").groupby(level="cats")[["cost", "ds_cost"]].sum()
    d = d[(d.projects >= MIN_AREA) & ~d.index.isin(METHOD_AREAS) & (d.cost / ic_cost[ic] >= MIN_AREA_COST_SHARE)]
    d["ic_area_ds_share"] = d.ds_cost / d.cost
    d["ic_overall_ds_share"] = ic_ds_cost[ic] / ic_cost[ic]
    d["rest_area_ds_share"] = (rest.ds_cost / rest.cost).reindex(d.index)
    d["gap_points"] = 100 * (d.ic_area_ds_share - d.ic_overall_ds_share)
    d["vs_rest_points"] = 100 * (d.ic_area_ds_share - d.rest_area_ds_share)
    d["ic_cost_share"] = d.cost / ic_cost[ic]
    d["gap"] = (d.gap_points <= AREA_GAP) & (d.vs_rest_points < 0)
    return d.sort_values("gap_points").rename_axis("area").reset_index()

# %% [markdown]
# ## Lens 3: disease burden

# %%
g = pd.read_csv(next((ROOT / "data" / "raw" / "gbd").glob("*.csv")))
g = g[g.measure_name.str.startswith("DALYs") & g.metric_name.eq("Number") & g.sex_name.eq("Both")
      & g.age_name.eq("All ages") & g.year.between(FY_FIRST, FY_LAST) & g.location_name.eq("United States of America")]
dalys = g.groupby("cause_name").val.mean()
cw = pd.read_csv(TOPICS / "rcdc_gbd_crosswalk.csv")
cw = cw[cw.gbd_level == 3]
cw["rcdc"] = cw.rcdc_categories.str.split(";").map(lambda xs: {x.strip() for x in xs})
rows = []
for r in cw.itertuples():
    m = a.cats.map(lambda cs, want=r.rcdc: bool(cs & want))
    sub = a[m]
    by = sub.groupby("ic").cost.sum().rename("cost").to_frame().join(sub[sub.ds].groupby("ic").cost.sum().rename("ds_cost"))
    by = by.fillna(0.0).assign(cause=r.gbd_cause, confidence=r.confidence)
    rows.append(by.reset_index())
cause = pd.concat(rows, ignore_index=True)
cause["dalys"] = cause.cause.map(dalys)


def lens3(ic):
    d = cause[cause.ic == ic].set_index("cause")
    rest = cause[cause.ic != ic].groupby("cause")[["cost", "ds_cost"]].sum()
    d["nih_cost_share"] = d.cost / (d.cost + rest.cost.reindex(d.index))
    d = d[(d.cost >= MIN_CAUSE_COST) & (d.nih_cost_share >= MIN_CAUSE_IC_SHARE) & d.confidence.ne("low")].copy()
    d["ic_intensity"] = d.ds_cost / d.cost
    d["rest_intensity"] = (rest.ds_cost / rest.cost).reindex(d.index)
    d["gap_points"] = 100 * (d.ic_intensity - d.rest_intensity)
    d["high_burden"] = d.dalys >= d.dalys.median()
    d["gap"] = d.high_burden & (d.gap_points <= CAUSE_GAP)
    d["uncertain_match"] = d.confidence.ne("high")
    return d.drop(columns="ic").sort_values("dalys", ascending=False).reset_index()

# %% [markdown]
# ## NOFO links

# %%
# Route of each data science project: targeted (any application answered an RFA or PAR), no NOFO by design
# (intramural Z, VA I, contracts N/Y, other transactions OT), else broad (strong or weak fit from nofo_links.csv)
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=key + ["nofo", "activity", "fy"])
apps["fy"] = pd.to_numeric(apps.fy, errors="coerce")
apps = apps[apps.fy.between(FY_FIRST, FY_LAST)]
apps["record"] = apps.core_project_number + "|" + apps.subproject_id.fillna("").astype(str)
pr = apps.groupby("record").agg(targeted=("nofo", lambda s: s.fillna("").astype(str).str.upper().str.match(r"^(RFA|PAR)-").any()),
                                activity=("activity", "first"))
links = pd.read_csv(RESULTS / "nofo_links.csv", low_memory=False)
links["record"] = links.core_project_number + "|" + links.subproject_id.fillna("").astype(str)
fit = links.drop_duplicates("record").set_index("record").fit
dsx = pd.read_parquet(PROCESSED / "ds_projects.parquet", columns=key + ["groups", "ic"])
dsx["record"] = dsx.core_project_number + "|" + dsx.subproject_id.fillna("").astype(str)
dsx["ic"] = dsx.ic.map(IC)
dsx = dsx.join(pr, on="record")
act = dsx.activity.fillna("").astype(str)
dsx["route"] = np.select(
    [dsx.targeted.fillna(False).astype(bool), act.str.match(r"^(Z|I|N|Y|OT)"), dsx.record.map(fit).eq("Strong fit")],
    ["Targeted NOFO", "No NOFO (intramural, VA, contract)", "Broad NOFO, strong fit"], "Broad NOFO, weak fit")
dsx["group"] = dsx.groups.fillna("").str.split(";")
dsx = dsx.explode("group").reset_index(drop=True)
dsx["group"] = dsx.group.str.strip().map(lambda g: "Data infrastructure" if g in ("data_infrastructure", "data_sharing", "computing_platforms") else GROUP_LABEL.get(g))
ROUTE_ORDER = ["Targeted NOFO", "Broad NOFO, strong fit", "Broad NOFO, weak fit", "No NOFO (intramural, VA, contract)"]


def lens4(ic):
    s = dsx[(dsx.ic == ic) & dsx.group.notna()].drop_duplicates(["record", "group"])
    t = pd.crosstab(s.group.to_numpy(), s.route.to_numpy(), normalize="index").mul(100).reindex(columns=ROUTE_ORDER, fill_value=0)
    t["projects"] = s.group.value_counts()
    t.index.name = "group"
    allp = dsx[dsx.ic == ic].drop_duplicates("record").route.value_counts(normalize=True).mul(100).reindex(ROUTE_ORDER, fill_value=0)
    t.loc["All data science"] = list(allp) + [dsx[dsx.ic == ic].record.nunique()]
    return t.sort_values("Broad NOFO, weak fit", ascending=False).rename_axis("group").reset_index()

# %% [markdown]
# ## Run

# %%
summ = []
for ic in ICS:
    o = OUT / ic.lower()
    o.mkdir(exist_ok=True)
    l1, l2, l3, l4 = lens1(ic), lens2(ic), lens3(ic), lens4(ic)
    l1.to_csv(o / "lens1_methods_lq.csv", index=False)
    l2.to_csv(o / "lens2_mission_areas.csv", index=False)
    l3.to_csv(o / "lens3_burden.csv", index=False)
    l4.to_csv(o / "lens4_nofo_links.csv", index=False)
    s = l4.set_index("group").loc["All data science"] / 100
    summ.append({"ic": ic, "ds_projects": int(ds_n[ic]), "ds_funding_share": ic_ds_cost[ic] / ic_cost[ic],
                 "methods_gaps": int(l1.gap.sum()), "lowest_lq_category": l1.category.iloc[0], "lowest_lq": l1.lq.iloc[0],
                 "mission_gaps": int(l2.gap.sum()), "weakest_area": l2.area.iloc[0],
                 "weakest_area_points": l2.gap_points.iloc[0], "burden_gaps": int(l3.gap.sum()),
                 "top_burden_gap": l3[l3.gap].cause.iloc[0] if l3.gap.any() else "",
                 "targeted_share": s["Targeted NOFO"], "weak_fit_share": s["Broad NOFO, weak fit"]})
    print(f"{ic}: {int(l1.gap.sum())} methods gaps, {int(l2.gap.sum())} mission gaps, weakest area {l2.area.iloc[0]} ({l2.gap_points.iloc[0]:.1f} pts), "
          f"{int(l3.gap.sum())} burden gaps")
pd.DataFrame(summ).to_csv(OUT / "summary.csv", index=False)
