# %% [markdown]
# # Administering vs. funding institutes: who manages an award and who pays for it
#
# Every NIH award has one **administering IC** (institute or center), which manages it, and one or more
# **funding ICs**, which pay for it. Usually they are the same. This notebook shows how often they differ,
# which IC pairs co-fund most, and whether data science and AI projects are co-funded more than other projects.
#
# **Scope:** NIH extramural awards (activity codes not starting with Z), attributed cost (centers counted once).
# Summary tables cover the last 5 complete fiscal years; the Tableau file has every year.
#
# **Definitions**
# - Award-year = one application funded in one fiscal year
# - Funded cost = attributed cost × the funding IC's share of the award (its amount / all funding ICs' amounts)
# - Self-funded share (admin IC) = funded cost paid by the administering IC itself / all cost of the awards it administers
# - Co-funded award share = award-years with at least one funding IC other than the administering IC / all award-years
# - Paid through other ICs (funding IC) = its funded cost on awards other ICs administer / all its funded cost
# - Scopes: All · Data science (substantive data science, label Y) · Not data science · AI (substantive AI, label Y)
#
# Inputs: notebook 08's `exporter_applications.parquet`, notebook 10's `exporter_core_projects_labeled.parquet`.
# Outputs (`reports/results/`): `funding_self_share_by_ic.csv`, `funding_by_funding_ic.csv`, `funding_pairs.csv`,
# `funding_ds_vs_non_ds.csv`, `tableau_funding_pairs.csv`.

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from funding import IC_NAMES, by_funding_ic  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, step  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import FISCAL_YEARS, PRELIMINARY_FY, admin_period  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT.mkdir(parents=True, exist_ok=True)
LATEST_FULL_FY = FISCAL_YEARS[-1] - 1 if PRELIMINARY_FY == FISCAL_YEARS[-1] else FISCAL_YEARS[-1]
SUMMARY_YEARS = list(range(LATEST_FULL_FY - 4, LATEST_FULL_FY + 1))
TOP_PAIRS = 15

# %% [markdown]
# ## Load awards and split each one by funding IC

# %%
with step("Load awards and labels"):
    apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                           columns=["application_id", "fy", "administering_ic", "funding_ics", "activity",
                                    "core_project_number", "subproject_id", "attributed_cost"])
    apps["fy"] = pd.to_numeric(apps.fy).astype(int)
    apps = apps[apps.administering_ic.isin(IC_NAMES) & apps.fy.isin(FISCAL_YEARS)
                & ~apps.activity.fillna("").str.startswith("Z")]
    core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                           columns=["core_project_number", "subproject_id", "ds_label", "ai_label"])
    apps = apps.merge(core, on=["core_project_number", "subproject_id"], how="left")
    say(f"{len(apps):,} extramural award-years, FY{FISCAL_YEARS[0]}–FY{FISCAL_YEARS[-1]}")

with step("Split awards by funding IC"):
    f = by_funding_ic(apps)
    say(f"{f.funding_ic.ne(f.admin_ic).mean():.1%} of funding rows are a non-administering IC; "
        f"{(1 - f[f.same_ic].funded_cost.sum() / f.funded_cost.sum()):.1%} of dollars")

# Scopes: one copy of each row per scope it belongs to
SCOPES = {"All": lambda d: d.index == d.index,
          "Data science": lambda d: d.ds_label == "Y",
          "Not data science": lambda d: d.ds_label != "Y",
          "AI": lambda d: d.ai_label == "Y"}
f = pd.concat([f[rule(f)].assign(scope=name) for name, rule in SCOPES.items()], ignore_index=True)
f["award"] = f.application_id.astype(str)
summary = f[f.fy.isin(SUMMARY_YEARS)]
PERIOD = f"FY{SUMMARY_YEARS[0]}–FY{SUMMARY_YEARS[-1]}"

# %% [markdown]
# ## 1. How much of each IC's portfolio does it pay for itself?

# %%
def self_share(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["scope", "admin_ic"])
    awards = d.groupby(["scope", "admin_ic", "award"]).same_ic.all().groupby(["scope", "admin_ic"])
    other = d[~d.same_ic].groupby(["scope", "admin_ic", "funding_ic"]).funded_cost.sum()
    top = other.sort_values(ascending=False).reset_index().drop_duplicates(["scope", "admin_ic"]) \
        .set_index(["scope", "admin_ic"])
    t = pd.DataFrame({"award_years": g.award.nunique(),
                      "cost": g.funded_cost.sum(),
                      "self_funded_cost": d[d.same_ic].groupby(["scope", "admin_ic"]).funded_cost.sum(),
                      "cofunded_award_share": 1 - awards.mean(),
                      "top_other_funder": top.funding_ic,
                      "top_other_funder_cost": top.funded_cost}).fillna({"self_funded_cost": 0})
    t["self_funded_share"] = t.self_funded_cost / t.cost
    t["top_other_funder_share"] = t.top_other_funder_cost / t.cost
    return t.reset_index()


self_ic = self_share(summary).assign(period=PERIOD)
self_ic.to_csv(OUT / "funding_self_share_by_ic.csv", index=False)
(self_ic[self_ic.scope == "All"].sort_values("cost", ascending=False)
 [["admin_ic", "award_years", "cost", "self_funded_share", "cofunded_award_share", "top_other_funder",
   "top_other_funder_share"]].round(3))

# %% [markdown]
# ## 2. Which ICs pay for awards other ICs manage?

# %%
g = summary.groupby(["scope", "funding_ic"])
fund_ic = pd.DataFrame({"funded_cost": g.funded_cost.sum(),
                        "through_other_ics": summary[~summary.same_ic].groupby(["scope", "funding_ic"]).funded_cost.sum()
                        }).fillna(0)
fund_ic["paid_through_other_ics_share"] = fund_ic.through_other_ics / fund_ic.funded_cost
fund_ic = fund_ic.reset_index().assign(period=PERIOD)
fund_ic.to_csv(OUT / "funding_by_funding_ic.csv", index=False)
(fund_ic[fund_ic.scope == "All"].sort_values("funded_cost", ascending=False).head(28).round(3))

# %% [markdown]
# ## 3. Common pairs: administering IC → another funding IC

# %%
other = summary[~summary.same_ic]
pairs = other.groupby(["scope", "admin_ic", "funding_ic"]).agg(cost=("funded_cost", "sum"),
                                                               award_years=("award", "nunique")).reset_index()
admin_cost = summary.groupby(["scope", "admin_ic"]).funded_cost.sum()
funder_cost = summary.groupby(["scope", "funding_ic"]).funded_cost.sum()
pairs["share_of_admin_ic_cost"] = pairs.cost / pairs.set_index(["scope", "admin_ic"]).index.map(admin_cost)
pairs["share_of_funding_ic_cost"] = pairs.cost / pairs.set_index(["scope", "funding_ic"]).index.map(funder_cost)
pairs["rank"] = pairs.groupby("scope").cost.rank(ascending=False, method="first").astype(int)
pairs = pairs.sort_values(["scope", "rank"]).assign(period=PERIOD)
pairs.to_csv(OUT / "funding_pairs.csv", index=False)
pairs[(pairs.scope == "All") & (pairs["rank"] <= TOP_PAIRS)].round(3)

# %% [markdown]
# ## 4. Data science vs. not data science
# Difference = data science − not data science, in percentage points (pp). ICs with fewer than 50 data
# science award-years in the period are marked `small`.

# %%
w = self_ic[self_ic.scope.isin(["Data science", "Not data science"])].pivot(
    index="admin_ic", columns="scope", values=["self_funded_share", "cofunded_award_share", "award_years"])
w.columns = [f"{m}_{'ds' if s == 'Data science' else 'non_ds'}" for m, s in w.columns]
w["self_funded_diff_pp"] = 100 * (w.self_funded_share_ds - w.self_funded_share_non_ds)
w["cofunded_diff_pp"] = 100 * (w.cofunded_award_share_ds - w.cofunded_award_share_non_ds)
w["small"] = w.award_years_ds.fillna(0) < 50
overall = self_share(summary.assign(admin_ic="All NIH"))
overall = overall[overall.scope.isin(["Data science", "Not data science"])].set_index("scope")
say(f"All NIH, {PERIOD}: co-funded award share {overall.loc['Data science', 'cofunded_award_share']:.1%} "
    f"(data science) vs {overall.loc['Not data science', 'cofunded_award_share']:.1%} (not); self-funded "
    f"dollars {overall.loc['Data science', 'self_funded_share']:.1%} vs "
    f"{overall.loc['Not data science', 'self_funded_share']:.1%}")
w = w.reset_index().assign(period=PERIOD).sort_values("cofunded_diff_pp", ascending=False)
w.to_csv(OUT / "funding_ds_vs_non_ds.csv", index=False)
w.round(3)

# %% [markdown]
# ## 5. Tableau: every year, filterable by scope, administering IC, and funding IC

# %%
tab = (f.groupby(["fy", "scope", "admin_ic", "funding_ic", "same_ic"])
       .agg(funded_cost=("funded_cost", "sum"), award_years=("award", "nunique")).reset_index())
tab["preliminary"] = tab.fy == PRELIMINARY_FY
tab["admin_period"] = tab.fy.map(admin_period)
tab.to_csv(OUT / "tableau_funding_pairs.csv", index=False)
say(f"Tableau extract: {len(tab):,} rows")
