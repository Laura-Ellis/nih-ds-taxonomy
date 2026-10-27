# %% [markdown]
# # 16 IC benchmark extract for Tableau: any institute vs. the rest of NIH
#
# One tidy table so a Tableau report can pick an institute (IC) and compare it with the rest of NIH
# on every measure: overall data science and AI, the 7 taxonomy groups and 2 subgroups, the 28 categories, and AI
# roles, for every fiscal year FY2016–FY2026 (FY2026 preliminary). Any one-institute comparison (for example the
# internal I01 report) is this table filtered to that IC; `focus_ic` in config/local.yaml sets the preview below.
#
# Input: notebook 13's `tableau_ds_groups.csv`, `ic_totals_by_fy.csv`, and `ds_projects.parquet`.
# Output: `reports/results/tableau_ic_benchmark.csv`
#
# **Columns**
# - `ic`, `fy`, `level` (Overall, Group, Subgroup, Category, AI role), `item`, `group` (a category's group)
# - `ic_projects`, `ic_total_projects`: records with the item / all records at the IC that year
# - `rest_projects`, `rest_total_projects`: the same for every other NIH IC combined
# - `ic_share` = ic_projects / ic_total_projects; `rest_share` likewise
# - `ratio` = ic_share / rest_share (1.0 = parity)
# - `to_parity` = max(0, rest_share − ic_share) × ic_total_projects: projects the IC would add to
#   match the rest of NIH's rate (a sizing aid, not a target)
# - `rank`, `of`: the IC's rank by share among large ICs (1,000+ records that year); blank otherwise
# - AI role rows use AI projects as the denominator (share of the IC's AI projects in each role)
#
# Overall and group rows count records active in the fiscal year from the application data.
# Category rows count a record as active in every year from its first to its last fiscal year.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from settings import FISCAL_YEARS, PRELIMINARY_FY, SETTINGS, admin_period  # noqa: E402  # pyright: ignore[reportMissingImports]
from taxonomy import load_categories  # noqa: E402  # pyright: ignore[reportMissingImports]

RES, PROCESSED = ROOT / "reports" / "results", ROOT / "data" / "processed"
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}
ROLE_LABELS = {"applies_ai": "Applies AI", "develops_ai": "Develops AI", "supports_ai": "Supports AI",
               "studies_ai": "Studies AI"}
LARGE = 1000

tab = pd.read_csv(RES / "tableau_ds_groups.csv")
tot = pd.read_csv(RES / "ic_totals_by_fy.csv")
proj = pd.read_parquet(PROCESSED / "ds_projects.parquet")
proj["ic"] = proj.ic.map(IC_NAMES).fillna(proj.ic)
cats = load_categories()
cats = cats[cats.dimension.isin(["methods", "software_tools", "data_infrastructure", "data_sharing",
                                 "responsible_ai", "workforce"])].copy()
_sub = cats.group.where(cats.dimension == "methods", cats.dimension).replace(
    {"data_infrastructure": "computing_platforms"})
_parent = {"computing_platforms": "data_infrastructure", "data_sharing": "data_infrastructure"}
cats["group_label"] = _sub.map(lambda g: _parent.get(g, g)).map(dict(zip(tab.ds_group, tab.group_label)))
totals = tot.set_index(["fy", "ic"]).all_projects

# %%
def benchmark(counts: pd.DataFrame, denom: pd.Series, level: str) -> pd.DataFrame:
    """counts: fy, ic, item, projects. denom: projects by (fy, ic). Returns IC vs. rest-of-NIH rows."""
    c = counts.set_index(["fy", "ic", "item"]).projects
    items = counts[["item"]].drop_duplicates()
    grid = (denom.reset_index()[["fy", "ic"]].merge(items, how="cross"))
    grid["ic_projects"] = grid.set_index(["fy", "ic", "item"]).index.map(c).fillna(0).astype(int)
    grid["ic_total_projects"] = grid.set_index(["fy", "ic"]).index.map(denom).astype(float)
    fy_item = grid.groupby(["fy", "item"])[["ic_projects", "ic_total_projects"]].transform("sum")
    grid["rest_projects"] = fy_item.ic_projects - grid.ic_projects
    grid["rest_total_projects"] = fy_item.ic_total_projects - grid.ic_total_projects
    grid["ic_share"] = grid.ic_projects / grid.ic_total_projects.replace(0, np.nan)
    grid["rest_share"] = grid.rest_projects / grid.rest_total_projects.replace(0, np.nan)
    grid["ratio"] = grid.ic_share / grid.rest_share.replace(0, np.nan)
    grid["to_parity"] = ((grid.rest_share - grid.ic_share).clip(lower=0) * grid.ic_total_projects).round()
    large = grid.ic_total_projects >= LARGE
    grid["rank"] = grid[large].groupby(["fy", "item"]).ic_share.rank(ascending=False, method="min")
    grid["of"] = grid[large].groupby(["fy", "item"]).ic.transform("size")
    grid["level"] = level
    return grid


# Overall: data science and AI
d = tab.drop_duplicates(["record", "fy"])
overall = pd.concat([
    d.groupby(["fy", "ic"]).record.nunique().rename("projects").reset_index().assign(item="Data science"),
    d[d.ai_label == "Y"].groupby(["fy", "ic"]).record.nunique().rename("projects").reset_index().assign(item="AI"),
])
parts = [benchmark(overall, totals, "Overall")]

# Groups
# Groups (7) and the two Data infrastructure subgroups, as separate levels
lvl = tab["level"] if "level" in tab.columns else pd.Series("Group", index=tab.index)
for level in ["Group", "Subgroup"]:
    g = tab[lvl == level].groupby(["fy", "ic", "group_label"]).record.nunique().rename("projects").reset_index()
    if len(g):
        parts.append(benchmark(g.rename(columns={"group_label": "item"}), totals, level))

# Categories (records active from first to last fiscal year)
e = proj.assign(item=proj.categories.fillna("").str.split("; ")).explode("item")
e = e[e["item"] != ""]
rows = []
for fy in FISCAL_YEARS:
    a = e[(e.first_fy <= fy) & (e.last_fy >= fy)]
    rows.append(a.groupby(["ic", "item"]).size().rename("projects").reset_index().assign(fy=fy))
cat_counts = pd.concat(rows)
cat_counts["item"] = cat_counts["item"].map(dict(zip(cats.category_id, cats.label))).fillna(cat_counts["item"])
parts.append(benchmark(cat_counts, totals, "Category"))

# AI roles: denominator = AI projects at the IC
ai = d[d.ai_label == "Y"]
ai_tot = ai.groupby(["fy", "ic"]).record.nunique()
r = ai.groupby(["fy", "ic", "ai_role"]).record.nunique().rename("projects").reset_index()
r["item"] = r.ai_role.map(ROLE_LABELS)
parts.append(benchmark(r[["fy", "ic", "item", "projects"]], ai_tot, "AI role"))

bench = pd.concat(parts, ignore_index=True)
bench["group"] = bench["item"].map(dict(zip(cats.label, cats.group_label))).where(bench.level == "Category")
bench = bench[["ic", "fy", "level", "item", "group", "ic_projects", "ic_total_projects", "rest_projects",
               "rest_total_projects", "ic_share", "rest_share", "ratio", "to_parity", "rank", "of"]]
bench["preliminary"] = bench.fy == PRELIMINARY_FY  # FY2026 records are still settling: compare with care
bench["admin_period"] = bench.fy.map(admin_period)
bench.to_csv(RES / "tableau_ic_benchmark.csv", index=False)
print(f"{len(bench):,} rows; {bench.ic.nunique()} ICs; levels {bench.level.value_counts().to_dict()}")
FOCUS_IC = SETTINGS.get("focus_ic")  # preview one IC; the saved table covers every IC
last_full = max(FISCAL_YEARS) - (1 if PRELIMINARY_FY == max(FISCAL_YEARS) else 0)
if FOCUS_IC:
    print(bench[(bench.ic == FOCUS_IC) & (bench.fy == last_full) & (bench.level != "Category")].round(3).to_string())
else:
    print("Set focus_ic in config/local.yaml to preview one institute here")
