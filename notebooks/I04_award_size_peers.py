# %% [markdown]
# # I04 Award size: data science vs. other projects, NIAID and NIH peers
#
# Builds the data for the "Award Size" dashboard (skill: nih-peer-award-size), NIH data only.
#
# Inputs (same as I03):
# - `data/processed/exporter_applications.parquet`: every NIH record by fiscal year with its funding
#   (RePORTER API pull plus ExPORTER files in `C:\data\nih`)
# - `reports/results/tableau_ds_groups.csv`: which records count as data science and AI (notebooks 08 → 13)
# - `data/processed/ds_projects.parquet`: titles and organizations for the largest-awards table
#
# **Definitions**
# - Record = core project + subproject, one row per fiscal year (FY); cost = attributed extramural cost
#   (intramural Z codes and $0 records left out), the same rule as I03
# - Mean = funding ÷ projects; median = the typical project; P10/P25/P75/P90 = percentiles
# - Data science (DS) premium = DS median ÷ not-DS median − 1
# - Top 1% share = funding held by the largest 1% of projects ÷ all funding in the group
# - Peers = `peer_ics` in config/local.yaml (default NIDDK, NHLBI, NIGMS, NCI); Other ICs = every IC except NIAID
# - FY2026 is preliminary (partial year)

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
PROCESSED, RES = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT = ROOT / "reports" / "internal" / "peer_dashboards"
OUT.mkdir(parents=True, exist_ok=True)
FOCUS, Y_SIZE, PRELIM = "NIAID", 2025, 2026
try:
    from settings import SETTINGS  # pyright: ignore[reportMissingImports]
    PEERS = list(SETTINGS.get("peer_ics") or ["NIDDK", "NHLBI", "NIGMS", "NCI"])
except Exception:
    PEERS = ["NIDDK", "NHLBI", "NIGMS", "NCI"]
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD"}


def family(code: str) -> str:
    """Activity family (same groups as I03)."""
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
# ## Records: every extramural NIH record per year, flagged for data science and AI

# %%
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["fy", "administering_ic", "activity", "core_project_number", "subproject_id",
                                "attributed_cost"])
apps = apps[apps.administering_ic.isin(IC_NAMES)]
apps["record"] = apps.core_project_number + "|" + apps.subproject_id.fillna("")
apps["ic"] = apps.administering_ic.map(IC_NAMES)
apps["activity"] = apps.activity.fillna("").astype(str)
apps["cost"] = apps.attributed_cost.where(~apps.activity.str.startswith("Z"), 0).fillna(0)
rec = (apps.groupby(["fy", "record"])
       .agg(ic=("ic", "first"), activity=("activity", "first"), cost=("cost", "sum")).reset_index())

tab = pd.read_csv(RES / "tableau_ds_groups.csv", usecols=["record", "fy", "ai_label", "level", "parent_group"])
flags = tab.drop_duplicates(["fy", "record"]).assign(ds=True, ai=lambda d: d.ai_label.eq("Y"))[["fy", "record", "ds", "ai"]]
rec = rec.merge(flags, on=["fy", "record"], how="left")
rec["ds"], rec["ai"] = rec.ds.eq(True), rec.ai.eq(True)
rec["family"] = rec.activity.map(family)
fp = rec[~rec.activity.str.startswith("Z") & (rec.cost > 0)].copy()
print(f"{len(fp):,} funded extramural records, FY{fp.fy.min()}–FY{fp.fy.max()}")
fp.groupby("fy").agg(records=("record", "size"), ds=("ds", "mean"), ai=("ai", "mean")).round(3)

# %% [markdown]
# ## Award size by IC group, status, and activity

# %%
WHO = {FOCUS: lambda d: d.ic == FOCUS, "Peers": lambda d: d.ic.isin(PEERS),
       "Other ICs": lambda d: d.ic != FOCUS, "All NIH": lambda d: d.ic.notna()}
GROUP_WHO = list(WHO)
WHO.update({ic: (lambda d, ic=ic: d.ic == ic) for ic in sorted(fp.ic.unique()) if ic != FOCUS})
STATUS = {"All projects": lambda d: d, "Data science": lambda d: d[d.ds], "AI": lambda d: d[d.ai],
          "Not data science": lambda d: d[~d.ds]}
TOP_CODES = fp[fp.fy == Y_SIZE].activity.value_counts().head(20).index.tolist()


def summarize(d: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Award-size statistics for each group of keys (fy plus an activity column)."""
    g = d.groupby(keys).cost
    q = g.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
    q.columns = ["p10", "p25", "median", "p75", "p90"]
    s = pd.DataFrame({"projects": g.size(), "funding": g.sum()}).join(q)
    s["mean"] = s.funding / s.projects

    def top1(x):
        x = np.sort(x.values)[::-1]
        return x[:max(1, int(round(len(x) * 0.01)))].sum() / x.sum()
    s["top1_share"] = g.apply(top1)
    return s.reset_index()


rows = []
for who, sel in WHO.items():
    d0 = fp[sel(fp)]
    for status, f in STATUS.items():
        d = f(d0)
        if d.empty:
            continue
        parts = [summarize(d.assign(activity_group="All activities"), ["fy", "activity_group"]),
                 summarize(d.assign(activity_group="Family: " + d.family), ["fy", "activity_group"])]
        if who in GROUP_WHO:
            parts.append(summarize(d[d.activity.isin(TOP_CODES)].assign(activity_group=lambda x: x.activity),
                                   ["fy", "activity_group"]))
        for p in parts:
            rows.append(p.assign(who=who, status=status))
size = pd.concat(rows, ignore_index=True)
size["preliminary"] = size.fy == PRELIM
size = size[size.projects >= 1]
num = ["funding", "p10", "p25", "median", "p75", "p90", "mean"]
size[num] = size[num].round(0)
size["top1_share"] = size.top1_share.round(4)
size = size[["who", "status", "activity_group", "fy", "preliminary", "projects", "funding", "mean", "median",
             "p10", "p25", "p75", "p90", "top1_share"]]
size.to_csv(OUT / "award_size.csv", index=False)
print(f"award_size.csv: {len(size):,} rows")
size[(size.fy == Y_SIZE) & (size.activity_group == "All activities") & size.who.isin(GROUP_WHO)]

# %% [markdown]
# ## Award size by data science group (DS projects only, all activities)

# %%
grp = (tab[tab.level == "Group"].drop_duplicates(["fy", "record", "parent_group"])[["fy", "record", "parent_group"]]
       .merge(fp[["fy", "record", "ic", "cost"]], on=["fy", "record"]))
rows = []
for who, sel in WHO.items():
    d = grp[sel(grp)]
    if not d.empty:
        rows.append(summarize(d, ["fy", "parent_group"]).assign(who=who))
cat = pd.concat(rows, ignore_index=True).rename(columns={"parent_group": "ds_group"})
cat[num] = cat[num].round(0)
cat["preliminary"] = cat.fy == PRELIM
cat[["who", "ds_group", "fy", "preliminary", "projects", "funding", "mean", "median", "p25", "p75"]].to_csv(
    OUT / "award_size_ds_groups.csv", index=False)

# %% [markdown]
# ## Largest data science awards, FY2025

# %%
titles = pd.read_parquet(PROCESSED / "ds_projects.parquet",
                         columns=["core_project_number", "subproject_id", "project_title", "org_name"])
titles["record"] = titles.core_project_number + "|" + titles.subproject_id.fillna("")
top = fp[(fp.fy == Y_SIZE) & fp.ds].merge(titles[["record", "project_title", "org_name"]].drop_duplicates("record"),
                                          on="record", how="left")
rows = []
for who in GROUP_WHO:
    t = top[WHO[who](top)].sort_values("cost", ascending=False).head(25)
    rows.append(t.assign(who=who, rank=range(1, len(t) + 1)))
top = pd.concat(rows)
top["project"] = top.record.str.rstrip("|").str.replace("|", " sub ", regex=False)
top[["who", "rank", "ic", "project", "activity", "project_title", "org_name", "cost", "ai"]].to_csv(
    OUT / "award_size_top.csv", index=False)
top.groupby("who").head(3)[["who", "ic", "project", "cost"]]
