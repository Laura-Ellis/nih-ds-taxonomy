# %% [markdown]
# # I05 Time from award start to publications, clinical trials, and patents
#
# Builds the data for the "Time to Output" dashboard (skill: dimensions-time-to-output, NIH-data version).
# NIH sources only; NIH has no policy-document links, so policy documents are left out.
#
# Inputs:
# - `data/processed/exporter_applications.parquet`: every NIH record by fiscal year
# - `reports/results/tableau_ds_groups.csv`: data science and AI records (notebooks 08 → 13)
# - ExPORTER publication links and publications (`C:\data\nih\combined\pub_links`, `...\publications`)
# - ExPORTER `Patents.csv` and `ClinicalStudies.csv` (`C:\data\nih`)
#
# **Definitions**
# - Cohort = extramural core projects whose project period starts in FY2016–FY2026 (new projects only,
#   so the start date is the real start). FY = year of start date + 1 if the month is October or later
# - IC and activity code = from the project's first record; data science (DS) or AI = any record of the
#   project is flagged in the taxonomy
# - Years to output = (output date − project start date) ÷ 365.25
# - Time to first output = per project, the earliest output; mean and median across projects with one
# - Mean across all outputs = every project–output link
# - Yield = projects with at least one output ÷ all projects in the cohort
# - Follow-up = (data date − project start) ÷ 365.25; data date = date the ExPORTER files were downloaded
# - Short follow-up = cohort median follow-up is less than the time by which 90% of first outputs of that
#   type arrived in the FY2016–FY2018 cohorts (all NIH)
# - KM median = Kaplan–Meier median time to first output (projects with no output counted as censored at
#   follow-up), which corrects for recent cohorts that haven't had time to produce outputs
# - Outputs dated before the project start are left out of timing (counted as "pre-start")
#
# **Output dates (ExPORTER has no dates for trials or patents)**
# - Publications: PUB_DATE (month and year; day 15; July when only the year is given)
# - Clinical trials: trial start date estimated from the NCT number (assigned in order of registration),
#   calibrated on 26 trials looked up on ClinicalTrials.gov; about ±1 year for any one trial
# - Patents: issue date estimated from the patent number, using the first utility patent number issued each
#   year (USPTO); within a few months. Reissue and design patents (RE, D) left out

# %%
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
PROCESSED, RES = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT = ROOT / "reports" / "internal" / "peer_dashboards"
OUT.mkdir(parents=True, exist_ok=True)
try:
    from settings import SETTINGS, source  # pyright: ignore[reportMissingImports]
    PEERS = list(SETTINGS.get("peer_ics") or ["NIDDK", "NHLBI", "NIGMS", "NCI"])
    PUB_LINKS, LINK_TABLES = source("pub_links"), source("link_tables")
except Exception:
    PEERS = ["NIDDK", "NHLBI", "NIGMS", "NCI"]
    PUB_LINKS, LINK_TABLES = Path(r"C:\data\nih\combined\pub_links"), Path(r"C:\data\nih")
if os.environ.get("NIH_DATA"):  # run outside Windows (e.g. a Linux VM) with the data folder mounted elsewhere
    LINK_TABLES = Path(os.environ["NIH_DATA"])
    PUB_LINKS = LINK_TABLES / "combined" / "pub_links"
PUBS = PUB_LINKS.parent / "publications"
FOCUS, PRELIM = "NIAID", 2026
DATA_DATE = pd.Timestamp("2026-10-24")
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD"}


def family(code: str) -> str:
    c = str(code or "")
    if c in {"R01", "R37", "R56", "RF1", "R35", "DP1", "DP2", "DP5"}:
        return "R01-type research"
    if c.startswith("R"):
        return "Other R (R21, R03, SBIR...)"
    if c[:1] in {"T", "F", "K", "D"}:
        return "Training and career"
    if c.startswith("U"):
        return "Cooperative agreements (U)"
    if c.startswith("P"):
        return "Centers and program projects (P)"
    if c.startswith("N") or c.startswith("75"):
        return "Contracts"
    return "Other"


# %% [markdown]
# ## Cohort: new extramural projects starting FY2016–FY2026

# %%
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["fy", "administering_ic", "activity", "core_project_number", "subproject_id",
                                "project_start"])
apps = apps[apps.administering_ic.isin(IC_NAMES) & (apps.subproject_id.fillna("") == "")]
apps["activity"] = apps.activity.fillna("").astype(str)
apps = apps[~apps.activity.str.startswith("Z")]
apps["start"] = pd.to_datetime(apps.project_start, errors="coerce")
proj = (apps.sort_values("fy").groupby("core_project_number")
        .agg(ic=("administering_ic", "first"), activity=("activity", "first"), start=("start", "min")).reset_index())
proj["ic"] = proj.ic.map(IC_NAMES)
proj["start_fy"] = proj.start.dt.year + (proj.start.dt.month >= 10)
proj = proj[proj.start_fy.between(2016, PRELIM)].copy()
proj["family"] = proj.activity.map(family)
proj["follow_up"] = (DATA_DATE - proj.start).dt.days / 365.25

tab = pd.read_csv(RES / "tableau_ds_groups.csv", usecols=["record", "ai_label"])
tab["core"] = tab.record.str.split("|").str[0]
proj["ds"] = proj.core_project_number.isin(tab.core)
proj["ai"] = proj.core_project_number.isin(tab[tab.ai_label.eq("Y")].core)
print(f"{len(proj):,} new projects; DS share {proj.ds.mean():.1%}")
proj.groupby("start_fy").agg(projects=("ds", "size"), ds=("ds", "mean")).round(3)

# %% [markdown]
# ## Outputs with dates

# %%
cores = set(proj.core_project_number)

# Publications
links = pd.concat(pd.read_parquet(f) for f in sorted(PUB_LINKS.glob("*.parquet")))
links.columns = links.columns.str.lower()
links = links[links.project_number.isin(cores)].drop_duplicates(["pmid", "project_number"])
pubs = pd.concat(pd.read_parquet(f, columns=["PMID", "PUB_DATE", "PUB_YEAR"]) for f in sorted(PUBS.glob("*.parquet")))
links["pmid"] = links.pmid.astype(str).str.strip()
pubs["PMID"] = pubs.PMID.astype(str).str.strip()
pubs = pubs.drop_duplicates("PMID")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], 1)}
yr = pd.to_numeric(pubs.PUB_YEAR, errors="coerce")
mo = pubs.PUB_DATE.astype(str).str.split().str[1].str[:3].str.lower().map(MONTHS).fillna(7)
pubs["date"] = pd.to_datetime(dict(year=yr, month=mo, day=15), errors="coerce")
pub = links.merge(pubs[["PMID", "date"]], left_on="pmid", right_on="PMID")[["project_number", "date"]]

# Clinical trials: start date estimated from NCT number (calibration: NCT number, start date looked up)
NCT_ANCHORS = [(1500317, "2011-05-15"), (1750073, "2012-12-07"), (1999946, "2014-06-27"), (2249962, "2015-05-15"),
               (2499913, "2015-07-15"), (2750059, "2015-01-15"), (3000166, "2017-01-31"), (3250247, "2018-07-02"),
               (3500172, "2018-06-22"), (3750227, "2018-11-19"), (3999892, "2019-06-24"), (4250051, "2020-12-21"),
               (4500119, "2020-08-12"), (4749849, "2021-02-01"), (4999982, "2021-11-30"), (5250037, "2022-03-30"),
               (5500235, "2023-06-27"), (5750459, "2023-11-29"), (6000007, "2023-08-25"), (6249984, "2024-12-20"),
               (6499883, "2024-07-11"), (6750107, "2025-01-22"), (7000019, "2025-06-15"), (7250061, "2026-03-05"),
               (7500363, "2026-03-25"), (7749885, "2026-03-06")]


def isotonic(y: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators: the closest non-decreasing fit to y."""
    blocks = [[v, 1] for v in y]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            v = (blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / (blocks[i][1] + blocks[i + 1][1])
            blocks[i] = [v, blocks[i][1] + blocks[i + 1][1]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return np.concatenate([[v] * n for v, n in blocks])


ax = np.array([a for a, _ in NCT_ANCHORS], float)
ay = isotonic(pd.to_datetime([d for _, d in NCT_ANCHORS]).map(pd.Timestamp.toordinal).values.astype(float))
ct = pd.read_csv(LINK_TABLES / "ClinicalStudies.csv")
ct.columns = ["project_number", "nct", "study", "status"]
ct = ct[ct.project_number.isin(cores)].drop_duplicates(["project_number", "nct"])
n = pd.to_numeric(ct.nct.str[3:], errors="coerce")
ct["date"] = [pd.Timestamp.fromordinal(int(o)) for o in np.interp(n.fillna(0), ax, ay)]
ct.loc[n < ax.min(), "date"] = pd.Timestamp("2010-01-01")  # registered before the calibration range: pre-start
ct = ct.assign(output="Clinical trials")[["project_number", "date", "output"]]

# Patents: issue date from the first utility patent number issued each year (2024+ estimated from weekly rate)
FIRST = {2010: 7640598, 2011: 7861317, 2012: 8087094, 2013: 8341762, 2014: 8621662, 2015: 8925111,
         2016: 9226437, 2017: 9532494, 2018: 9854839, 2019: 10165721, 2020: 10524402, 2021: 10881038,
         2022: 11212878, 2023: 11540906, 2024: 11857000, 2025: 12185000, 2026: 12510000, 2027: 12835000}
pt = pd.read_csv(LINK_TABLES / "Patents.csv", dtype=str)
pt = pt[pt.PROJECT_ID.isin(cores)].drop_duplicates(["PROJECT_ID", "PATENT_ID"])
pn = pd.to_numeric(pt.PATENT_ID, errors="coerce")
pt = pt[pn.notna() & (pn >= FIRST[2010])]
yrs = np.interp(pn[pn.notna() & (pn >= FIRST[2010])], list(FIRST.values()), list(FIRST.keys()))
pt["date"] = pd.to_datetime([f"{int(y)}-01-01" for y in yrs]) + pd.to_timedelta((yrs % 1) * 365.25, unit="D")
pt = pt.rename(columns={"PROJECT_ID": "project_number"}).assign(output="Patents")[["project_number", "date", "output"]]

out = pd.concat([pub[["project_number", "date"]].assign(output="Publications"), ct, pt], ignore_index=True)
out = out.dropna(subset=["date"]).merge(proj[["core_project_number", "start"]], left_on="project_number",
                                        right_on="core_project_number")
out["years"] = (out.date - out.start).dt.days / 365.25
out["pre_start"] = out.years < 0
out = out[out.date <= DATA_DATE + pd.Timedelta(days=366)]
print(out.groupby("output").agg(links=("years", "size"), pre_start=("pre_start", "mean"),
                                median_years=("years", "median")).round(2))

# %% [markdown]
# ## Per project: time to first output and counts

# %%
ok = out[~out.pre_start]
OUTPUTS = ["Publications", "Clinical trials", "Patents"]
first = ok.groupby(["project_number", "output"]).years.min().unstack()
counts = ok.groupby(["project_number", "output"]).size().unstack()
pre = out[out.pre_start].groupby(["project_number", "output"]).size().unstack()
P = proj.set_index("core_project_number")
for o in OUTPUTS:
    P[f"first_{o}"] = first.get(o)
    P[f"n_{o}"] = counts.get(o, pd.Series(dtype=float)).reindex(P.index).fillna(0)
    P[f"pre_{o}"] = pre.get(o, pd.Series(dtype=float)).reindex(P.index).fillna(0) if pre is not None else 0
P = P.reset_index()
pairs = ok.merge(P[["core_project_number", "ic", "activity", "family", "start_fy", "ds", "ai"]],
                 on="core_project_number")


def km_median(t: np.ndarray, event: np.ndarray) -> float:
    """Kaplan–Meier median: first time the share still without an output falls to 0.5 or below."""
    if len(t) == 0:
        return np.nan
    order = np.argsort(t)
    t, event = t[order], event[order]
    at_risk = len(t) - np.arange(len(t))
    s = np.cumprod(1 - event / at_risk)
    hit = np.nonzero(s <= 0.5)[0]
    return float(t[hit[0]]) if len(hit) else np.nan


# %% [markdown]
# ## Aggregate by IC group, start year, status, and activity

# %%
WHO = {FOCUS: lambda d: d.ic == FOCUS, "Peers": lambda d: d.ic.isin(PEERS),
       "Other ICs": lambda d: d.ic != FOCUS, "All NIH": lambda d: d.ic.notna()}
GROUP_WHO = list(WHO)
WHO.update({ic: (lambda d, ic=ic: d.ic == ic) for ic in sorted(P.ic.dropna().unique()) if ic != FOCUS})
STATUS = {"All projects": lambda d: d, "Data science": lambda d: d[d.ds], "AI": lambda d: d[d.ai],
          "Not data science": lambda d: d[~d.ds]}
TOP_CODES = P.activity.value_counts().head(15).index.tolist()
CUTS = [("All activities", lambda d: pd.Series("All activities", index=d.index))]
CUTS_FAM = [("family", lambda d: "Family: " + d.family)]
CUTS_CODE = [("code", lambda d: d.activity.where(d.activity.isin(TOP_CODES)))]

rows = []
for who, sel in WHO.items():
    p0, q0 = P[sel(P)], pairs[sel(pairs)]
    cuts = CUTS + CUTS_FAM + (CUTS_CODE if who in GROUP_WHO else [])
    for status, f in STATUS.items():
        p1, q1 = f(p0), f(q0)
        for _, cut in cuts:
            gp = p1.assign(activity_group=cut(p1)).dropna(subset=["activity_group"])
            gq = q1.assign(activity_group=cut(q1)).dropna(subset=["activity_group"])
            for (fy, act), d in gp.groupby(["start_fy", "activity_group"]):
                pq = gq[(gq.start_fy == fy) & (gq.activity_group == act)]
                for o in OUTPUTS:
                    t = d[f"first_{o}"]
                    a = pq[pq.output == o].years
                    has = t.notna()
                    km = km_median(np.where(has, t, d.follow_up).astype(float), has.values.astype(float)) \
                        if act == "All activities" or act.startswith("Family") else np.nan
                    rows.append({"who": who, "status": status, "activity_group": act, "start_fy": fy, "output": o,
                                 "projects": len(d), "with_output": int(has.sum()), "yield": has.mean(),
                                 "outputs_per_project": d[f"n_{o}"].sum() / len(d),
                                 "first_mean": t.mean(), "first_median": t.median(),
                                 "first_p25": t.quantile(0.25), "first_p75": t.quantile(0.75),
                                 "all_links": len(a), "all_mean": a.mean(), "all_median": a.median(),
                                 "km_median": km, "follow_up_median": d.follow_up.median(),
                                 "pre_start_links": d[f"pre_{o}"].sum()})
tto = pd.DataFrame(rows)
# Short follow-up: the cohort's median follow-up is shorter than the time by which 90% of first outputs
# arrive in the FY2016–FY2018 cohorts (all NIH), so its timing still leaves out slower outputs
ref = pd.Series({o: P.loc[P.start_fy <= 2018, f"first_{o}"].quantile(0.9) for o in OUTPUTS})
tto["short_follow_up"] = tto.follow_up_median < tto.output.map(ref)
tto["preliminary"] = tto.start_fy == PRELIM
num = [c for c in tto.columns if tto[c].dtype == float]
tto[num] = tto[num].round(3)
tto.to_csv(OUT / "time_to_output.csv", index=False)
pd.DataFrame({"output": ref.index, "p90_first_years": ref.round(2).values}).to_csv(
    OUT / "time_to_output_followup_ref.csv", index=False)
print(f"time_to_output.csv: {len(tto):,} rows; 90th percentile time to first output (FY2016–FY2018 cohorts):")
print(ref.round(2))

# %% [markdown]
# ## Calibration and coverage tables (for the Definitions panel)

# %%
cov = (P.groupby("start_fy").agg(projects=("core_project_number", "size"), **{
    f"share_with_{o.split()[0].lower()}": (f"first_{o}", lambda s: s.notna().mean()) for o in OUTPUTS})
    .reset_index())
cov.round(4).to_csv(OUT / "time_to_output_coverage.csv", index=False)
pd.DataFrame(NCT_ANCHORS, columns=["nct_number", "start_date"]).assign(
    fitted=[pd.Timestamp.fromordinal(int(o)).date() for o in ay]).to_csv(OUT / "nct_calibration.csv", index=False)
cov
