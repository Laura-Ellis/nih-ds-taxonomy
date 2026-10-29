# %% [markdown]
# # 11 Results: where data science and AI appear in NIH projects, FY2016–2025
#
# Input: notebook 10's `exporter_core_projects_labeled.parquet`, notebook 08's
# `exporter_applications.parquet`, and ExPORTER publication links (`combined/pub_links`).
# Output: tidy tables in `reports/results/` for the deck, site pages, and KPI dashboard.
#
# **Scope**
# - Counts cover all NIH project records (parent projects and subprojects), each counted once per
#   fiscal year it has an application.
# - Funding covers extramural awards only (activity codes not starting with Z). Intramural annual
#   reports describe whole lab programs, and one, NCBI operations (ZIHLM200888, about $340M a year),
#   would otherwise be about 13% of all AI funding. `attributed_cost` counts center funding once.
# - AI = substantive AI (label Y). Charts split it by role: develops, applies, studies, or supports AI.
# - NIH only: ExPORTER also lists other funders (CDC centers, AHRQ, FDA, NIOSH, VA), about 2.8% of
#   extramural funding. Their records are dropped from every count, share, and comparison.
#
# **Definitions**
# - Substantive = data science or AI in an aim or the stated approach (Y); mention = M
# - Share of projects = records with label Y / all records active that fiscal year
# - Share of funding = extramural attributed cost of Y records / all extramural attributed cost
# - Matched comparison: AI projects vs. non-AI projects in the same IC, activity code, and first
#   fiscal year, with non-AI projects weighted to the AI projects' count in each group

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from settings import FISCAL_YEARS, PRELIMINARY_FY, admin_period, source  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT.mkdir(parents=True, exist_ok=True)

# One-institute mode (internal): with the environment variable ONLY_IC set (for example ONLY_IC=NIAID), the same
# tables are built for that administering institute only and written to reports/internal/ic_<name>/ instead.
import os  # noqa: E402
ONLY_IC = os.environ.get("ONLY_IC")
if ONLY_IC:
    OUT = ROOT / "reports" / "internal" / f"ic_{ONLY_IC.lower()}"
    OUT.mkdir(parents=True, exist_ok=True)
# Latest complete fiscal year: snapshot comparisons use it, so a preliminary year doesn't skew shares
LATEST_FULL_FY = FISCAL_YEARS[-1] - 1 if PRELIMINARY_FY == FISCAL_YEARS[-1] else FISCAL_YEARS[-1]

IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}
NIH_ICS = set(IC_NAMES)  # administering IC codes for NIH institutes and centers
METHODS = {"machine_learning": "Machine learning", "deep_learning": "Deep learning", "nlp": "NLP",
           "computer_vision": "Computer vision", "generative_ai": "Generative AI and LLMs"}
AREAS = {"medical_imaging": "Imaging", "omics": "Genomics and omics", "clinical_care": "Clinical care and EHR",
         "neuroscience": "Neuroscience", "mental_behavioral": "Mental and behavioral health",
         "population_health": "Population health", "drug_discovery": "Drug discovery",
         "sensors_wearables": "Sensors and wearables"}

core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet")
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["application_id", "fy", "administering_ic", "activity", "core_project_number",
                                "subproject_id", "attributed_cost"])
key = ["core_project_number", "subproject_id"]
non_nih = ~apps.administering_ic.isin(NIH_ICS)
print(f"Dropping {non_nih.sum():,} non-NIH applications ({sorted(apps.loc[non_nih, 'administering_ic'].dropna().unique())})")
apps = apps[~non_nih]
if ONLY_IC:
    apps = apps[apps.administering_ic.map(IC_NAMES) == ONLY_IC]
    print(f"One-institute mode: {ONLY_IC}, {len(apps):,} applications")
core = core.merge(apps[key].drop_duplicates(), on=key)  # keep NIH records only
apps = apps.merge(core[key + ["ds_label", "ai_label", "ai_role", "model_categories"]], on=key, how="left")
apps["record"] = apps.core_project_number + "|" + apps.subproject_id
apps["extramural"] = ~apps.activity.fillna("").str.startswith("Z")
apps["ic"] = apps.administering_ic.map(IC_NAMES).fillna(apps.administering_ic)
ext = apps[apps.extramural]
cats = core.model_categories.fillna("").str.split("; ")
core["cat_set"] = cats.map(set)
print(f"{core.shape[0]:,} records; {apps.shape[0]:,} applications; extramural share of funding "
      f"{ext.attributed_cost.sum() / apps.attributed_cost.sum():.1%}")

# %% [markdown]
# ## Over time

# %%
def per_fy(df, mask=None):
    d = df if mask is None else df[mask]
    return d.groupby("fy").record.nunique()


trend = pd.DataFrame({
    "projects": per_fy(apps),
    "ds_substantive": per_fy(apps, apps.ds_label == "Y"),
    "ai_substantive": per_fy(apps, apps.ai_label == "Y"),
    "ai_any": per_fy(apps, apps.ai_label.isin(["Y", "M"])),
    "extramural_cost": ext.groupby("fy").attributed_cost.sum(),
    "ds_cost": ext[ext.ds_label == "Y"].groupby("fy").attributed_cost.sum(),
    "ai_cost": ext[ext.ai_label == "Y"].groupby("fy").attributed_cost.sum(),
}).fillna(0)
for role in ["applies_ai", "develops_ai", "supports_ai", "studies_ai"]:
    trend[f"ai_{role}"] = per_fy(apps, (apps.ai_label == "Y") & (apps.ai_role == role))
    trend[f"ai_cost_{role}"] = ext[(ext.ai_label == "Y") & (ext.ai_role == role)].groupby("fy").attributed_cost.sum()
trend = trend.fillna(0)
trend["ds_share"] = trend.ds_substantive / trend.projects
trend["ai_share"] = trend.ai_substantive / trend.projects
trend["ai_cost_share"] = trend.ai_cost / trend.extramural_cost
trend["ds_cost_share"] = trend.ds_cost / trend.extramural_cost
trend = trend.reset_index()
trend["preliminary"] = trend.fy == PRELIMINARY_FY  # FY2026 is preliminary
trend["admin_period"] = trend.fy.map(admin_period)
trend.to_csv(OUT / "trend_by_fy.csv", index=False)

# Growth within each administration period: average annual change in AI and data science shares
# (percentage points per year, least-squares slope over the period's fiscal years; FY2026 preliminary)
import numpy as np  # noqa: E402
per = []
for name, g in trend[trend.fy.notna()].groupby("admin_period", sort=False):
    row = {"admin_period": name, "first_fy": int(g.fy.min()), "last_fy": int(g.fy.max()), "years": len(g)}
    for col in ["ds_share", "ai_share", "ai_cost_share", "ds_cost_share"]:
        row[f"{col}_start"], row[f"{col}_end"] = g[col].iloc[0], g[col].iloc[-1]
        row[f"{col}_pp_per_year"] = (np.polyfit(g.fy, g[col] * 100, 1)[0] if len(g) > 1 else np.nan)
    per.append(row)
pd.DataFrame(per).to_csv(OUT / "trend_by_admin_period.csv", index=False)
trend[["fy", "projects", "ds_share", "ai_substantive", "ai_share", "ai_cost", "ai_cost_share"]].round(3)

# %% [markdown]
# ## By institute (extramural, all fiscal years; snapshot columns use the latest complete fiscal year)
# In one-institute mode the rows are activity codes instead (column still named `ic` so readers work unchanged).

# %%
UNIT = "activity" if ONLY_IC else "ic"
ic = pd.DataFrame({
    "ai_cost": ext[ext.ai_label == "Y"].groupby(UNIT).attributed_cost.sum(),
    "extramural_cost": ext.groupby(UNIT).attributed_cost.sum(),
    "ai_projects": ext[ext.ai_label == "Y"].groupby(UNIT).record.nunique(),
    "ai_cost_latest": ext[(ext.ai_label == "Y") & (ext.fy == LATEST_FULL_FY)].groupby(UNIT).attributed_cost.sum(),
    "extramural_cost_latest": ext[ext.fy == LATEST_FULL_FY].groupby(UNIT).attributed_cost.sum(),
}).fillna(0)
# Develops AI: projects building new AI methods, the subset of AI most tied to NIH's AI goals
dev = ext[(ext.ai_label == "Y") & (ext.ai_role == "develops_ai")]
ic["develops_ai_cost"] = dev.groupby(UNIT).attributed_cost.sum()
ic["develops_ai_projects"] = dev.groupby(UNIT).record.nunique()
ic = ic.fillna(0)
ic["develops_share_of_ai_cost"] = ic.develops_ai_cost / ic.ai_cost
ic["ai_share"] = ic.ai_cost / ic.extramural_cost
ic["ai_share_latest"] = ic.ai_cost_latest / ic.extramural_cost_latest
ic["latest_full_fy"] = LATEST_FULL_FY
ic = ic.sort_values("ai_cost", ascending=False).reset_index().rename(columns={UNIT: "ic"})
ic.to_csv(OUT / "ai_by_institute.csv", index=False)
ic.head(10).round(3)

# %% [markdown]
# ## Method × research area (substantive AI projects)

# %%
ai_core = core[core.ai_label == "Y"]
grid = pd.DataFrame({AREAS[a]: {METHODS[m]: int(ai_core.cat_set.map(lambda s, m=m, a=a: m in s and a in s).sum())
                                for m in METHODS} for a in AREAS})
grid.to_csv(OUT / "ai_method_by_area.csv")
dev_core = ai_core[ai_core.ai_role == "develops_ai"]
grid_dev = pd.DataFrame({AREAS[a]: {METHODS[m]: int(dev_core.cat_set.map(lambda s, m=m, a=a: m in s and a in s).sum())
                                    for m in METHODS} for a in AREAS})
grid_dev.to_csv(OUT / "ai_method_by_area_develops.csv")
grid

# %% [markdown]
# ## Generative AI

# %%
core["genai"] = (core.ai_label == "Y") & core.cat_set.map(lambda s: "generative_ai" in s)
genai_keys = core.loc[core.genai, "core_project_number"] + "|" + core.loc[core.genai, "subproject_id"]
g = apps[apps.record.isin(set(genai_keys))]
genai = g.groupby("fy").record.nunique().rename("genai_projects").reset_index()
for role in ["develops_ai", "applies_ai", "supports_ai", "studies_ai"]:  # e.g. genai_develops
    genai[f"genai_{role.split('_')[0]}"] = (g[g.ai_role == role].groupby("fy").record.nunique()
                                            .reindex(genai.fy).fillna(0).astype(int).values)
genai["preliminary"] = genai.fy == PRELIMINARY_FY
genai["admin_period"] = genai.fy.map(admin_period)
genai.to_csv(OUT / "genai_by_fy.csv", index=False)
recent = core[core.genai & (core.last_fy >= 2023)]
genai_role = recent.ai_role.value_counts(normalize=True).rename("share")
genai_area = pd.Series({AREAS[a]: recent.cat_set.map(lambda s, a=a: a in s).mean() for a in AREAS},
                       name="share").sort_values(ascending=False)
pd.concat([genai_role, genai_area]).to_frame().to_csv(OUT / "genai_role_area.csv")
print(genai.to_string(index=False))
print(genai_role.round(3).to_dict())
print(genai_area.round(3).to_dict())

# %% [markdown]
# ## Publications per project: data science and AI vs. matched projects
# Extramural core projects starting FY2016–2020 (publication links are by core project number).
# A core project counts as data science (or AI) if any of its records is substantive. Two
# comparisons, each with its own matching:
# - Data science vs. matched non-data-science projects
# - AI vs. matched non-AI projects
# Matching: strata = IC | activity code | first fiscal year | size band (cost tercile within
# activity code). Only strata with both groups are kept; comparison projects are weighted to the
# treated count in each stratum: weight = n_treated / n_comparison. RCR, FWCI, patents, and trials
# come from notebook 12.

# %%
links = pd.concat(pd.read_parquet(f) for f in sorted(source("pub_links").glob("*.parquet")))
links.columns = links.columns.str.lower()
links = links.drop_duplicates(["pmid", "project_number"])
pubs = links.groupby("project_number").pmid.nunique()

proj = (apps[apps.extramural].groupby("core_project_number")
        .agg(ic=("ic", "first"), activity=("activity", "first"), first_fy=("fy", "min"),
             cost=("attributed_cost", "sum"), ai=("ai_label", lambda s: (s == "Y").any()),
             ds=("ds_label", lambda s: (s == "Y").any()))
        .reset_index())
proj = proj[proj.first_fy.between(2016, 2020)]
proj["pubs"] = proj.core_project_number.map(pubs).fillna(0)
proj["activity"] = proj.activity.fillna("")
proj["size_band"] = (proj.groupby("activity").cost.rank(pct=True).fillna(0.5) * 3).clip(upper=2.999).astype(int) + 1
proj["stratum"] = proj.ic + "|" + proj.activity + "|" + proj.first_fy.astype(str) + "|" + proj.size_band.astype(str)

SCOPES = {"Data science": ("ds", "Data science", "Matched non-data-science"),
          "AI": ("ai", "AI-related", "Matched non-AI")}


def match(df: pd.DataFrame, flag: str) -> pd.DataFrame:
    """Matched set for one scope: strata with both groups; comparison weighted to the treated count."""
    n_t = df[df[flag]].groupby("stratum").size()
    n_c = df[~df[flag]].groupby("stratum").size()
    keep = n_t.index.intersection(n_c.index)
    m = df[df.stratum.isin(keep)].copy()
    m["treated"] = m[flag]
    m["weight"] = 1.0
    m.loc[~m.treated, "weight"] = m.loc[~m.treated, "stratum"].map(n_t / n_c)
    return m


def wmean(d, col):
    return (d[col] * d.weight).sum() / d.weight.sum()


def wmedian(d, col):
    d = d.sort_values(col)
    cum = d.weight.cumsum()
    return d.loc[cum >= d.weight.sum() / 2, col].iloc[0]


rows, saved = [], []
for scope, (flag, treated_label, comp_label) in SCOPES.items():
    m = match(proj, flag)
    for label, d in [(treated_label, m[m.treated]), (comp_label, m[~m.treated])]:
        rows.append({"scope": scope, "group": label, "projects": len(d),
                     "pubs_per_project": wmean(d, "pubs"), "median_pubs": wmedian(d, "pubs"),
                     "share_with_pub": wmean(d.assign(p=d.pubs > 0), "p")})
    saved.append(m[["core_project_number", "treated", "stratum", "weight", "pubs"]].assign(scope=scope))
outputs = pd.DataFrame(rows)
outputs.to_csv(OUT / "outputs_matched.csv", index=False)
pd.concat(saved).to_parquet((OUT if ONLY_IC else PROCESSED) / "matched_projects.parquet", index=False)  # one-institute mode must not overwrite the full file
outputs.round(3)
