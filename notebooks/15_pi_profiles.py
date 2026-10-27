# %% [markdown]
# # 15 Who does data science: principal investigator (PI) profiles
#
# Finds the NIH investigators whose portfolios are mostly data science and describes them in
# aggregate: how many there are, how that changes each fiscal year, which institutes fund them, what
# kind of AI work they do, and what their projects produce.
#
# **Definitions**
# - PI = every investigator listed on a project record (`pi_ids`, RePORTER profile IDs), not only the
#   contact PI. A multi-PI project counts for each of its PIs.
# - Portfolio = the PI's distinct project records (parents and subprojects), FY2016–FY2026
# - Data science share = PI's substantive data science records / PI's records
# - Data science PI = data science share > MIN_DS_SHARE (more than half) and at least MIN_PROJECTS records, so a
#   single project doesn't make a PI 100% data science. The sensitivity table shows other cutoffs.
# - AI developer = a data science PI with at least one substantive AI project whose role is develops AI
# - Outputs come from the PI's data science projects: linked papers (publication links by core
#   project number), mean Relative Citation Ratio (RCR, iCite: citations per year / field-expected
#   rate; 1.0 = median NIH paper), and links to patents and clinical trials
# - FY2026 is preliminary (settings.yaml); per-year tables flag it
#
# **Privacy:** outputs in `reports/results/` are aggregate only, and any count under 11 PIs is
# suppressed. The PI-level table stays in `data/processed/` (git-ignored) for internal use.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from settings import PRELIMINARY_FY, source  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
MIN_DS_SHARE = 0.5   # data science share of a PI's portfolio to count as a data science PI
MIN_PROJECTS = 2     # and at least this many project records
SUPPRESS = 11        # hide aggregate cells with fewer PIs than this
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}

key = ["core_project_number", "subproject_id"]
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["fy", "administering_ic", "core_project_number", "subproject_id", "pi_ids"])
apps = apps[apps.administering_ic.isin(IC_NAMES)]
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["ds_label", "ai_label", "ai_role"])
apps["record"] = apps.core_project_number + "|" + apps.subproject_id.fillna("")
core["record"] = core.core_project_number + "|" + core.subproject_id.fillna("")

# One row per PI × record × fiscal year. pi_ids looks like "1903457 (contact);1234567;"
pa = apps.assign(pi=apps.pi_ids.fillna("").str.split(";")).explode("pi")
pa["pi"] = pa.pi.str.replace("(contact)", "", regex=False).str.strip()
pa = pa[pa.pi.str.fullmatch(r"\d+")]
pa["ic"] = pa.administering_ic.map(IC_NAMES)
pa = pa.merge(core[["record", "ds_label", "ai_label", "ai_role"]], on="record", how="left")
pa["ds"] = pa.ds_label.eq("Y")
pa["ai"] = pa.ai_label.eq("Y")
pa["develops"] = pa.ai & pa.ai_role.eq("develops_ai")
print(f"{pa.pi.nunique():,} PIs on {pa.record.nunique():,} records")

# %% [markdown]
# ## PI portfolios

# %%
rec = pa.drop_duplicates(["pi", "record"])
pi = rec.groupby("pi").agg(records=("record", "nunique"), ds_records=("ds", "sum"), ai_records=("ai", "sum"),
                           develops_records=("develops", "sum"))
pi["ds_share"] = pi.ds_records / pi.records
yrs = pa.groupby("pi").fy.agg(first_fy="min", last_fy="max")
ds_yrs = pa[pa.ds].groupby("pi").fy.agg(first_ds_fy="min", last_ds_fy="max")
main_ic = pa.groupby(["pi", "ic"]).record.nunique().reset_index().sort_values("record", ascending=False) \
    .drop_duplicates("pi").set_index("pi").ic.rename("main_ic")
pi = pi.join(yrs).join(ds_yrs).join(main_ic)
pi["n_ics"] = pa.groupby("pi").ic.nunique()
pi["ds_pi"] = (pi.ds_share > MIN_DS_SHARE) & (pi.records >= MIN_PROJECTS)  # more than half
pi["ai_type"] = np.select([pi.develops_records > 0, pi.ai_records > 0], ["Develops AI", "Applies or supports AI"],
                          "No AI projects")
print(f"Data science PIs: {pi.ds_pi.sum():,} of {len(pi):,} ({pi.ds_pi.mean():.1%}) at share >= {MIN_DS_SHARE:.0%} "
      f"and {MIN_PROJECTS}+ records")

# %% [markdown]
# ## Outputs of data science projects, per PI

# %%
links = pd.concat(pd.read_parquet(f) for f in sorted(source("pub_links").glob("*.parquet")))
links.columns = links.columns.str.lower()
links["pmid"] = pd.to_numeric(links.pmid, errors="coerce")
links = links.dropna(subset=["pmid"]).drop_duplicates(["pmid", "project_number"])
ds_cores = pa[pa.ds][["pi", "core_project_number"]].drop_duplicates()
pp = ds_cores.merge(links, left_on="core_project_number", right_on="project_number")
pi["ds_papers"] = pp.groupby("pi").pmid.nunique()
icite_file = INTERIM / "icite.parquet"
if icite_file.exists():
    ic_rcr = pd.read_parquet(icite_file).drop_duplicates("pmid").set_index("pmid").rcr
    pp["rcr"] = pp.pmid.map(ic_rcr)
    pi["ds_mean_rcr"] = pp.drop_duplicates(["pi", "pmid"]).groupby("pi").rcr.mean()
for label, pattern in [("patent", "patent"), ("trial", "clinical")]:
    files = [f for f in source("link_tables").rglob("*") if pattern in f.name.lower() and f.suffix.lower() == ".csv"]
    if files:
        t = pd.read_csv(sorted(files)[-1], encoding="latin-1", low_memory=False)
        t.columns = t.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
        col = next(c for c in t.columns if "project" in c and ("core" in c or c in ("project_id", "project_number")))
        linked = set(t[col].astype(str).str.strip())
        pi[f"ds_{label}_linked"] = ds_cores.assign(h=ds_cores.core_project_number.isin(linked)).groupby("pi").h.any()
pi = pi.fillna({"ds_papers": 0})
pi.reset_index().to_parquet(PROCESSED / "pi_profiles.parquet", index=False)  # internal, git-ignored

# %% [markdown]
# ## Aggregate tables for the site (counts under 11 suppressed)

# %%
def suppress(df: pd.DataFrame, count_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in count_cols:
        df[c] = df[c].where(df[c] >= SUPPRESS)
    return df


# Sensitivity: how many data science PIs at other cutoffs
sens = pd.DataFrame([{"min_ds_share": s, "min_projects": m,
                      "ds_pis": int(((pi.ds_share >= s) & (pi.records >= m)).sum())}
                     for s in (0.25, 0.5, 0.75, 1.0) for m in (1, 2, 3)])
sens["share_of_pis"] = sens.ds_pis / len(pi)
sens.to_csv(OUT / "pi_cutoff_sensitivity.csv", index=False)

# Per fiscal year: active data science PIs and new ones (first data science project that year)
dsp = set(pi.index[pi.ds_pi])
act = pa[pa.pi.isin(dsp)].groupby("fy").pi.nunique().rename("active_ds_pis")
all_pis = pa.groupby("fy").pi.nunique().rename("all_pis")
new = pi[pi.ds_pi].groupby("first_ds_fy").size().rename("new_ds_pis")
by_fy = pd.concat([act, all_pis, new], axis=1).fillna(0).astype(int).rename_axis("fy").reset_index()
by_fy["ds_pi_share"] = by_fy.active_ds_pis / by_fy.all_pis
by_fy["preliminary"] = by_fy.fy == PRELIMINARY_FY
by_fy.loc[by_fy.fy == by_fy.fy.min(), "new_ds_pis"] = np.nan  # first year: "new" includes everyone already active
by_fy.to_csv(OUT / "pi_by_fy.csv", index=False)

# By main institute
by_ic = (pi.groupby("main_ic").agg(pis=("ds_pi", "size"), ds_pis=("ds_pi", "sum")).reset_index())
by_ic["ds_pi_share"] = by_ic.ds_pis / by_ic.pis
suppress(by_ic, ["pis", "ds_pis"]).sort_values("ds_pis", ascending=False).to_csv(OUT / "pi_by_ic.csv", index=False)

# Data science PIs vs. other PIs with 2+ records: portfolio and outputs
pi["group"] = np.where(pi.ds_pi, "Data science PIs", np.where(pi.records >= MIN_PROJECTS, "Other PIs (2+ records)", None))
cmp_cols = {"pis": ("records", "size"), "median_records": ("records", "median"),
            "median_ds_share": ("ds_share", "median"), "share_multi_ic": ("n_ics", lambda s: (s > 1).mean())}
summary = pi.dropna(subset=["group"]).groupby("group").agg(**cmp_cols)
d = pi[pi.ds_pi]
profile = pd.DataFrame({
    "measure": ["Data science PIs", "Share of all PIs", "Develop AI", "Apply or support AI", "No AI projects",
                "Funded by 2+ institutes", "Median data science projects", "Median papers from data science projects",
                "Mean RCR of those papers (median across PIs)", "Linked to a patent", "Linked to a clinical trial"],
    "value": [len(d), len(d) / len(pi), (d.ai_type == "Develops AI").mean(), (d.ai_type == "Applies or supports AI").mean(),
              (d.ai_type == "No AI projects").mean(), (d.n_ics > 1).mean(), d.ds_records.median(), d.ds_papers.median(),
              d.ds_mean_rcr.median() if "ds_mean_rcr" in d else np.nan,
              d.ds_patent_linked.mean() if "ds_patent_linked" in d else np.nan,
              d.ds_trial_linked.mean() if "ds_trial_linked" in d else np.nan],
})
profile.to_csv(OUT / "pi_profile_summary.csv", index=False)
summary.to_csv(OUT / "pi_group_comparison.csv")
print(profile.round(3).to_string(index=False))
by_fy.round(3)
