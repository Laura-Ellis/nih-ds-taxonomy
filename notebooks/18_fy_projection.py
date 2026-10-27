# %% [markdown]
# # 18 Projection for the preliminary fiscal year (FY2026)
#
# FY2026 closed on Sept 30, 2026, but RePORTER keeps adding its records for months. This projects
# the final FY2026 counts and funding from how complete earlier years were at the same point after
# they closed, using each record's `date_added` in the RePORTER API.
#
# **Method**
# - Completeness at lag L = share of a year's final records (or funding) RePORTER had added by L days
#   after the year closed (Sept 30). Computed for FY2024–FY2025, separately for extramural grants,
#   contracts (N and Y activity codes), and intramural records (Z codes), and per institute.
# - Projected final = FY2026 to date / completeness at the same lag
# - Reference: earlier years in the same administration period (settings.yaml admin_periods), so
#   FY2025 for FY2026. The range adds the year before (FY2024). Lag patterns shift between
#   administrations, so longer histories mix different regimes.
# - Back-test: projecting FY2025 from what it had at the same lag, compared with FY2025 today.
# - Cross-check: FY2026 if it repeats FY2025's change from FY2024 (trend method).
#
# **Caveat:** if RePORTER resets `date_added` when it revises a record, earlier years look less
# complete than they were and the projection runs high. Projections are kept separate from actual
# counts (`projected_*` columns) and are internal until FY2026 settles.
#
# Input: raw API pulls (`*.jsonl.gz` in `data/raw/reporter_api/raw/`, or `update.seed_dir`).
# Outputs (reports/internal/), each with to_date, projected, FY2025, and change columns:
# - `fy_projection.csv`: segments (extramural grants, contracts, intramural) with low/high range
# - `fy_projection_by_ic.csv`, `_by_activity.csv` (activity code), `_by_activity_family.csv` (R, U, P, K, T, F, ...),
#   `_by_ic_activity.csv` (institute × activity family), `_by_rcdc.csv`
# - Once FY2026 is labeled (notebooks 08–13): `fy_projection_ds_ai.csv`, `_by_group.csv`, `_by_category.csv`,
#   `_ds_by_ic.csv`, `_ds_by_activity_family.csv`, `_ds_by_rcdc.csv`

# %%
import gzip
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from settings import PRELIMINARY_FY, SETTINGS, admin_period, default_source  # noqa: E402  # pyright: ignore[reportMissingImports]

TARGET = PRELIMINARY_FY or 2026
# Earlier years from the same administration set the projection (FY2025 for FY2026); the year before
# (FY2024, the last Biden year) only widens the range, since lag patterns shift between administrations.
SAME_ADMIN = [fy for fy in range(TARGET - 4, TARGET) if admin_period(fy) == admin_period(TARGET)]
REFERENCE = max(SAME_ADMIN) if SAME_ADMIN else TARGET - 1
HISTORY = sorted(set(SAME_ADMIN) | {REFERENCE - 1})        # FY2024–FY2025
AS_OF = pd.Timestamp(date.today())
LAG = (AS_OF - pd.Timestamp(f"{TARGET}-09-30")).days
OUT = ROOT / "reports" / "internal"
OUT.mkdir(parents=True, exist_ok=True)
RAW_DIRS = [default_source("projects").parent / "raw"] + ([Path(SETTINGS["update"]["seed_dir"])]
                                                         if SETTINGS["update"].get("seed_dir") else [])
NIH = {"CA", "HL", "AI", "GM", "AG", "NS", "MH", "DK", "HD", "DA", "AA", "ES", "EY", "DC", "DE", "AR", "EB", "HG",
       "LM", "MD", "NR", "AT", "TR", "TW", "OD", "RR", "CL", "RM"}


def load(fy: int) -> pd.DataFrame:
    for d in RAW_DIRS:
        f = d / f"projects_FY{fy}.jsonl.gz"
        if f.exists():
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                recs = [json.loads(line) for line in fh]
            df = pd.DataFrame({
                "fy": fy, "date_added": [r.get("date_added") for r in recs],
                "award": [r.get("award_amount") or 0 for r in recs],
                "activity": [r.get("activity_code") or "" for r in recs],
                "ic": [(r.get("agency_ic_admin") or {}).get("code") for r in recs],
                "appl_id": [str(r.get("appl_id")) for r in recs],
                "subproject_id": [str(r.get("subproject_id") or "") for r in recs],
                "rcdc": [r.get("spending_categories_desc") or "" for r in recs]})
            df["date_added"] = pd.to_datetime(df.date_added, errors="coerce").dt.tz_localize(None)
            df["segment"] = np.select([df.activity.str.startswith("Z"), df.activity.str[0].isin(["N", "Y"])],
                                      ["Intramural", "Contract"], "Extramural grant")
            return df[df.ic.isin(NIH)]
    raise FileNotFoundError(f"No raw pull for FY{fy} in {RAW_DIRS}")


data = pd.concat([load(fy) for fy in HISTORY + [TARGET]], ignore_index=True)
print(f"FY{TARGET} is {LAG} days past its close (as of {AS_OF.date()})")

# %% [markdown]
# ## Completeness at the same lag, by year and segment

# %%
def completeness(d: pd.DataFrame, fy: int, lag: int) -> pd.Series:
    cut = pd.Timestamp(f"{fy}-09-30") + pd.Timedelta(days=lag)
    x = d[d.fy == fy]
    early = x.date_added <= cut
    return pd.Series({"records": early.mean(), "funding": x.award[early].sum() / x.award.sum()})


comp = pd.DataFrame([{"fy": fy, "segment": seg, **completeness(data[data.segment == seg], fy, LAG)}
                     for fy in HISTORY for seg in ["Extramural grant", "Contract", "Intramural"]])
comp.round(3)

# %% [markdown]
# ## Project FY2026 by segment (reference year FY2025; range across FY2021–FY2025)

# %%
# Extramural grants: FY2025's completeness (most like FY2026). Contracts: median across years (FY2025
# had an unusual batch of late contracts). Intramural: RePORTER adds intramural reports months after
# the year closes, so with none in yet they are projected at FY2025's level scaled by the extramural change.
RULE = {"Extramural grant": "reference", "Contract": "median", "Intramural": "scaled"}
rows, ext_ratio = [], {}
for seg in ["Extramural grant", "Contract", "Intramural"]:
    now = data[(data.fy == TARGET) & (data.segment == seg)]
    ref = data[(data.fy == REFERENCE) & (data.segment == seg)]
    c = comp[comp.segment == seg].set_index("fy")
    for measure, actual, ref_final in [("records", len(now), len(ref)), ("funding", now.award.sum(), ref.award.sum())]:
        cm = c[measure].replace(0, np.nan)
        if RULE[seg] == "reference":
            p, lo, hi = actual / cm.loc[REFERENCE], actual / cm.max(), actual / cm.min()
            ext_ratio[measure] = p / ref_final
        elif RULE[seg] == "median" and cm.notna().any():
            p, lo, hi = actual / cm.median(), actual / cm.max(), actual / cm.quantile(0.25)
        else:
            p = lo = hi = max(actual, ref_final * ext_ratio.get(measure, 1.0))
        rows.append({"segment": seg, "measure": measure, "method": RULE[seg], "to_date": actual, "projected": p,
                     "low": lo, "high": hi, f"FY{REFERENCE}_final": ref_final})
proj = pd.DataFrame(rows)
tot = proj.groupby("measure")[["to_date", "projected", "low", "high", f"FY{REFERENCE}_final"]].sum().reset_index()
proj = pd.concat([proj, tot.assign(segment="All NIH")], ignore_index=True)
proj["change_vs_reference"] = proj.projected / proj[f"FY{REFERENCE}_final"] - 1

# %% [markdown]
# ## Back-test and trend cross-check

# %%
# Back-test: project FY2025 from what it had LAG days after it closed, using FY2024's completeness
bt = []
for seg in ["Extramural grant", "Contract", "Intramural"]:
    x = data[(data.fy == REFERENCE) & (data.segment == seg)]
    early = x.date_added <= pd.Timestamp(f"{REFERENCE}-09-30") + pd.Timedelta(days=LAG)
    c_prev = comp[(comp.segment == seg) & (comp.fy == REFERENCE - 1)].iloc[0]
    bt.append({"segment": seg, "projected": early.sum() / c_prev.records, "actual": len(x)})
bt = pd.DataFrame(bt)
bt["error"] = bt.projected / bt.actual - 1
print("Back-test (FY2025 records):\n", bt.round(3).to_string(index=False))

# Trend: FY2026 if it repeats FY2025's change from FY2024
n = data.groupby("fy").size()
trend = n[REFERENCE] * n[REFERENCE] / n[REFERENCE - 1]
print(f"Trend cross-check: FY{TARGET} records = {trend:,.0f} if it repeats FY{REFERENCE}'s "
      f"{n[REFERENCE] / n[REFERENCE - 1] - 1:+.1%} change")

proj["as_of"], proj["lag_days"], proj["fy"] = AS_OF.date(), LAG, TARGET
proj.to_csv(OUT / "fy_projection.csv", index=False)
proj.round(3)

# %% [markdown]
# ## Projections by institute, RCDC category, and taxonomy group and category
# Each FY2026 record gets a weight = 1 / completeness of its segment and institute in FY2025 at the
# same lag (records and funding separately). A slice's projection is the sum of its records' weights.
# Segment-institute cells with fewer than MIN_CELL FY2025 records use the segment-wide completeness,
# so small institutes don't swing on a handful of late records. Intramural records get the scaled
# factor above (none are in yet), so their slices are projected from FY2025 directly.
# - projected_records = sum of record weights; projected_funding = sum of award × funding weight
# - change = projected / FY2025 final − 1, same slice

# %%
MIN_CELL = 200
IC_SHORT = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}
FAMILY = {"R": "Research (R)", "U": "Cooperative agreements (U)", "P": "Program projects and centers (P)",
          "K": "Career development (K)", "T": "Training (T)", "F": "Fellowships (F)", "S": "Research-related (S)",
          "D": "Training, D", "N": "Contracts (N)", "Y": "Contracts (Y)", "Z": "Intramural (Z)", "O": "Other transactions (OT)"}
ref = data[data.fy == REFERENCE].copy()
cut = pd.Timestamp(f"{REFERENCE}-09-30") + pd.Timedelta(days=LAG)
ref["early"] = ref.date_added <= cut
seg_c = proj[proj.segment != "All NIH"].set_index(["segment", "measure"])
cell = ref.groupby(["segment", "ic"]).agg(n=("early", "size"), rec=("early", "mean"),
                                         fund=("award", lambda a: a[ref.loc[a.index, "early"]].sum() / max(a.sum(), 1)))


def weights(seg: str, ic: str, measure: str) -> float:
    lvl = seg_c.loc[(seg, measure)]
    seg_w = lvl.projected / lvl.to_date if lvl.to_date else np.nan
    # Institute-level completeness only for extramural grants (the reference-year rule); contracts use the
    # segment's median rule
    if seg == "Extramural grant" and (seg, ic) in cell.index and cell.loc[(seg, ic), "n"] >= MIN_CELL:
        c = cell.loc[(seg, ic), "rec" if measure == "records" else "fund"]
        return 1 / c if c > 0 else seg_w
    return seg_w


now = data[data.fy == TARGET].copy()
wmap = {(r.segment, r.ic): (weights(r.segment, r.ic, "records"), weights(r.segment, r.ic, "funding"))
        for r in now[["segment", "ic"]].drop_duplicates().itertuples()}
now["w_rec"] = [wmap[k][0] for k in zip(now.segment, now.ic)]
now["w_fund"] = [wmap[k][1] for k in zip(now.segment, now.ic)]
# Rescale so each segment's slices add up to the segment projection above
for seg, g in now.groupby("segment"):
    now.loc[g.index, "w_rec"] *= seg_c.loc[(seg, "records")].projected / g.w_rec.sum()
    now.loc[g.index, "w_fund"] *= seg_c.loc[(seg, "funding")].projected / (g.award * g.w_fund).sum()
# Intramural: none in yet, so FY2025's intramural records stand in, scaled by the extramural change
intr = ref[ref.segment == "Intramural"].assign(w_rec=ext_ratio["records"], w_fund=ext_ratio["funding"])
proj_rows = pd.concat([now, intr], ignore_index=True)
proj_rows["is_actual"] = proj_rows.fy == TARGET
for d in (proj_rows, ref):
    d["ic_name"] = d.ic.map(IC_SHORT).fillna(d.ic)
    d["activity_family"] = d.activity.str[0].map(FAMILY).fillna("Other")


def slice_table(col: str, explode_sep: str | None = None) -> pd.DataFrame:
    a, r = proj_rows.copy(), ref.copy()
    if explode_sep:
        for d in (a, r):
            d[col] = d[col].fillna("").str.split(explode_sep)
        a, r = a.explode(col), r.explode(col)
        a[col], r[col] = a[col].str.strip(), r[col].str.strip()
        a, r = a[a[col] != ""], r[r[col] != ""]
    t = pd.DataFrame({
        "to_date_records": a[a.is_actual].groupby(col).size(),
        "to_date_funding": a[a.is_actual].groupby(col).award.sum(),
        "projected_records": a.groupby(col).w_rec.sum(),
        "projected_funding": (a.award * a.w_fund).groupby(a[col]).sum(),
        f"FY{REFERENCE}_records": r.groupby(col).size(),
        f"FY{REFERENCE}_funding": r.groupby(col).award.sum(),
    }).fillna(0)
    t["records_change"] = t.projected_records / t[f"FY{REFERENCE}_records"].replace(0, np.nan) - 1
    t["funding_change"] = t.projected_funding / t[f"FY{REFERENCE}_funding"].replace(0, np.nan) - 1
    return t.sort_values("projected_records", ascending=False).reset_index().rename(columns={col: "item"})


def a_slice(fy_rows: pd.DataFrame, ref_rows: pd.DataFrame, col: str, sep: str | None = None) -> pd.DataFrame:
    global proj_rows, ref
    keep = proj_rows, ref
    proj_rows, ref = fy_rows, ref_rows
    try:
        return slice_table(col, sep)
    finally:
        proj_rows, ref = keep


by_ic = slice_table("ic_name")
by_ic.to_csv(OUT / "fy_projection_by_ic.csv", index=False)
slice_table("activity").to_csv(OUT / "fy_projection_by_activity.csv", index=False)
slice_table("activity_family").to_csv(OUT / "fy_projection_by_activity_family.csv", index=False)
slice_table("rcdc", ";").to_csv(OUT / "fy_projection_by_rcdc.csv", index=False)
# Institute × activity family, for Tableau filtering
ic_act = (proj_rows.assign(k=proj_rows.ic_name + "|" + proj_rows.activity_family),
          ref.assign(k=ref.ic_name + "|" + ref.activity_family))
t = a_slice(*ic_act, "k")
t[["ic", "activity_family"]] = t.item.str.split("|", expand=True)
t.drop(columns="item").to_csv(OUT / "fy_projection_by_ic_activity.csv", index=False)
print(by_ic.head(10).round(3).to_string(index=False))
print(slice_table("activity_family").round(3).to_string(index=False))

# %% [markdown]
# ### Data science, AI, taxonomy groups, and categories
# Needs FY2026 labels: run notebooks 08–13 first. Records join to labels through their application ID.

# %%
PROCESSED = ROOT / "data" / "processed"
apps_file, dsp_file = PROCESSED / "exporter_applications.parquet", PROCESSED / "ds_projects.parquet"
ap = pd.read_parquet(apps_file, columns=["application_id", "core_project_number", "subproject_id", "fy"]) \
    if apps_file.exists() and dsp_file.exists() else None
if ap is not None and pd.to_numeric(ap.fy).max() >= TARGET:
    rec = lambda d: d.core_project_number + "|" + d.subproject_id.fillna("").astype(str)  # noqa: E731
    dsp = pd.read_parquet(dsp_file, columns=["core_project_number", "subproject_id", "groups", "categories", "ai_label"])
    lab = ap.assign(record=rec(ap), application_id=ap.application_id.astype(str))[["application_id", "record"]] \
        .merge(dsp.assign(record=rec(dsp))[["record", "groups", "categories", "ai_label"]], on="record")
    lab = lab.drop_duplicates("application_id")
    fy_l = proj_rows.merge(lab, left_on="appl_id", right_on="application_id", how="inner")
    ref_l = ref.merge(lab, left_on="appl_id", right_on="application_id", how="inner")
    scope = pd.concat([a_slice(fy_l.assign(s="Data science"), ref_l.assign(s="Data science"), "s"),
                       a_slice(fy_l[fy_l.ai_label == "Y"].assign(s="AI"), ref_l[ref_l.ai_label == "Y"].assign(s="AI"), "s")])
    scope.to_csv(OUT / "fy_projection_ds_ai.csv", index=False)
    a_slice(fy_l, ref_l, "groups", "; ").to_csv(OUT / "fy_projection_by_group.csv", index=False)
    a_slice(fy_l, ref_l, "categories", "; ").to_csv(OUT / "fy_projection_by_category.csv", index=False)
    a_slice(fy_l, ref_l, "ic_name").to_csv(OUT / "fy_projection_ds_by_ic.csv", index=False)
    a_slice(fy_l, ref_l, "activity_family").to_csv(OUT / "fy_projection_ds_by_activity_family.csv", index=False)
    a_slice(fy_l, ref_l, "rcdc", ";").to_csv(OUT / "fy_projection_ds_by_rcdc.csv", index=False)
    print(scope.round(3).to_string(index=False))
else:
    print(f"Labels don't include FY{TARGET} yet: run notebooks 08–13, then this again for data science projections")
