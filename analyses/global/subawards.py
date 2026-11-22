# %% [markdown]
# # Where NIH funds data science abroad: subawards
#
# Analysis D, part 2. First-tier subawards on NIH grants from USAspending.gov (Custom Award Data → Sub-Awards →
# Sub-Grants, funding agency NIH, one file per fiscal year, FY2016 to FY2026; FY2026 preliminary). Prime recipients
# report subawards of $30,000 or more under the Federal Funding Accountability and Transparency Act (FFATA), so
# smaller subawards are missing.
#
# - Link: `prime_award_fain` = NIH core project number (for example UG1CA242609), joined to the labeled records.
#   Data science = the prime project's `ds_label` = Y.
# - A subaward = one subrecipient on one prime award (FAIN + subaward number + subrecipient). Amount = sum of the
#   reported actions.
# - Reports larger than their prime award are dropped as keying errors (189 reports, about $225B).
# - Foreign = subrecipient country outside the United States.
# - Country names are matched to ISO3 and WHO regions in `regions.py`.
#
# Raw files stay outside the repo (`USASPENDING_DIR`, default `C:/data/usaspending`).
# Outputs in `reports/results/global/`.

# %%
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "analyses" / "global"))
from regions import display, iso3, who_region as region  # noqa: E402  (WHO regions for public outputs)

RAW = Path(os.environ.get("USASPENDING_DIR", "C:/data/usaspending"))
PROCESSED, INTERIM = ROOT / "data" / "processed", ROOT / "data" / "interim"
OUT = ROOT / "reports" / "results" / "global"
OUT.mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST = 2016, 2026
COLS = ["prime_award_fain", "prime_award_amount", "prime_award_funding_sub_agency_name", "prime_awardee_name", "prime_awardee_country_name",
        "subaward_sam_report_id", "subaward_number", "subaward_amount", "subaward_action_date",
        "subaward_action_date_fiscal_year", "subawardee_uei", "subawardee_name", "subawardee_country_name"]


def wilson(k, n, z=1.96):
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = k / n
    d = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return mid - half, mid + half


# %% [markdown]
# ## Read the USAspending files

# %%
cache = INTERIM / "usaspending_subawards.parquet"
zips = sorted(RAW.glob("All_Subawards_*.zip"))
stale = (not cache.exists() or cache.stat().st_mtime < max(z.stat().st_mtime for z in zips)
         or set(COLS) - set(pd.read_parquet(cache).columns))
if stale:
    parts = []
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for name in zf.namelist():
                if "Assistance_Subawards" in name:
                    parts.append(pd.read_csv(zf.open(name), usecols=COLS, dtype=str))
    raw = pd.concat(parts, ignore_index=True).drop_duplicates("subaward_sam_report_id")
    raw.to_parquet(cache, index=False)
raw = pd.read_parquet(cache)
print(f"{len(raw):,} subaward reports from {len(zips)} files")

s = raw[raw.prime_award_funding_sub_agency_name.eq("National Institutes of Health")].copy()
s["fy"] = pd.to_numeric(s.subaward_action_date_fiscal_year, errors="coerce")
s = s[s.fy.between(FY_FIRST, FY_LAST)].copy()
s["amount"] = pd.to_numeric(s.subaward_amount, errors="coerce").fillna(0.0)
# a subaward can't exceed its prime award: these are keying errors (one report lists $166B)
too_big = s.amount > pd.to_numeric(s.prime_award_amount, errors="coerce")
print(f"Dropped {too_big.sum()} reports larger than the prime award (${s.loc[too_big, 'amount'].sum() / 1e9:,.1f}B)")
s = s[~too_big].copy()
s["fain"] = s.prime_award_fain.str.strip().str.upper()
s["iso3"] = s.subawardee_country_name.map(iso3)
s["foreign"] = s.iso3.notna() & s.iso3.ne("USA")
unmatched = s.loc[s.iso3.isna(), "subawardee_country_name"].value_counts(dropna=False)
print("Reports with an unmatched country:", int(unmatched.sum()), dict(unmatched.head(5)))

# %% [markdown]
# ## Link to NIH projects

# %%
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=["core_project_number", "subproject_id", "ds_label", "ai_label", "administering_ic"])
# the prime project's own label: the parent record (no subproject id); a center's subprojects don't count
core["ds"], core["ai"] = core.ds_label.eq("Y"), core.ai_label.eq("Y")
core["parent"] = core.subproject_id.isna() | core.subproject_id.astype(str).str.strip().eq("")
lab = (core.sort_values("parent", ascending=False).drop_duplicates("core_project_number")
       [["core_project_number", "ds", "ai", "administering_ic"]].rename(columns={"administering_ic": "ic"}))
s = s.merge(lab, left_on="fain", right_on="core_project_number", how="left")
s["linked"] = s.core_project_number.notna()
link = s.groupby("foreign").agg(reports=("linked", "size"), linked=("linked", "mean"),
                                amount=("amount", "sum"),
                                amount_linked=("amount", lambda x: x[s.loc[x.index, "linked"]].sum()))
link["amount_linked_share"] = link.amount_linked / link.amount
link.to_csv(OUT / "subaward_link_rate.csv")
print(link.round(3))

# %% [markdown]
# ## One row per subaward

# %%
s["sub_key"] = s.fain + "|" + s.subaward_number.fillna("") + "|" + s.subawardee_uei.fillna(s.subawardee_name)
sub = (s.sort_values("fy").groupby("sub_key")
       .agg(fain=("fain", "first"), prime=("prime_awardee_name", "last"), subrecipient=("subawardee_name", "last"),
            iso3=("iso3", "last"), foreign=("foreign", "max"), linked=("linked", "max"), ds=("ds", "max"),
            ai=("ai", "max"), ic=("ic", "first"), first_fy=("fy", "min"), n_reports=("fy", "size"),
            amount=("amount", "sum"))
       .reset_index())
sub["region"] = sub.iso3.map(region)
sub["ds"] = sub.ds.fillna(False).astype(bool)
sub["ds_amount"] = sub.amount.where(sub.ds, 0.0)

# amendments: how often a subaward's later reports repeat the same amount (a sign of cumulative reporting)
rep = s[s.sub_key.isin(sub.loc[sub.n_reports > 1, "sub_key"])]
same = rep.groupby("sub_key").amount.nunique().eq(1).mean()
print(f"Subawards with more than one report: {(sub.n_reports > 1).mean():.1%}; of those, all reports the same amount: {same:.1%}")

sub.to_parquet(INTERIM / "global_subawards.parquet", index=False)
f = sub[sub.foreign & sub.linked]
lo, hi = wilson(f.ds.sum(), len(f))
head = pd.DataFrame({
    "group": ["Foreign subawards", "All NIH subawards"],
    "subawards": [len(f), int(sub.linked.sum())], "ds": [f.ds.sum(), sub[sub.linked].ds.sum()],
    "countries": [f.iso3.nunique(), np.nan], "primes": [f.fain.nunique(), sub[sub.linked].fain.nunique()],
    "amount": [f.amount.sum(), sub[sub.linked].amount.sum()],
    "ds_amount": [f.ds_amount.sum(), sub[sub.linked].ds_amount.sum()]})
head["ds_share"] = head.ds / head.subawards
head["ds_lo"], head["ds_hi"] = wilson(head.ds, head.subawards)
head["ds_amount_share"] = head.ds_amount / head.amount
head.to_csv(OUT / "subaward_headline.csv", index=False)
print(head.round(3).to_string(index=False))

# %% [markdown]
# ## Countries, regions, U.S. partners

# %%
def by(df, col):
    g = df.groupby(col).agg(subawards=("sub_key", "size"), ds=("ds", "sum"), primes=("fain", "nunique"),
                            amount=("amount", "sum"), ds_amount=("ds_amount", "sum")).reset_index()
    g["ds_share"] = g.ds / g.subawards
    g["ds_lo"], g["ds_hi"] = wilson(g.ds, g.subawards)
    return g.sort_values("amount", ascending=False)


sub_countries = by(f, "iso3").assign(name=lambda d: d.iso3.map(display), region=lambda d: d.iso3.map(region))
sub_countries.to_csv(OUT / "subaward_countries.csv", index=False)
by(f, "region").to_csv(OUT / "subaward_regions.csv", index=False)
partners = (f.groupby("prime").agg(subawards=("sub_key", "size"), countries=("iso3", "nunique"),
                                   amount=("amount", "sum"), ds_amount=("ds_amount", "sum"))
            .reset_index().sort_values("amount", ascending=False))
partners.to_csv(OUT / "subaward_us_partners.csv", index=False)
print(sub_countries.head(12)[["name", "subawards", "ds", "ds_share", "amount", "ds_amount"]].round(3).to_string(index=False))
print(partners.head(8).to_string(index=False))

# %% [markdown]
# ## Direct awards vs. subawards
#
# Data science funding per country: direct = attributed cost of data science projects with a recipient in the
# country (`direct_awards.py`); subaward = reported subaward amounts on data science primes. Route: direct only,
# subaward only, or both.

# %%
direct = pd.read_csv(OUT / "countries.csv")
direct["iso3"] = direct.country.map(iso3)
both = (direct[["iso3", "records", "ds", "cost", "ds_cost"]]
        .rename(columns={"records": "direct_records", "ds": "direct_ds", "cost": "direct_cost", "ds_cost": "direct_ds_cost"})
        .merge(sub_countries[["iso3", "subawards", "ds", "amount", "ds_amount"]]
               .rename(columns={"ds": "sub_ds", "amount": "sub_amount", "ds_amount": "sub_ds_amount"}),
               on="iso3", how="outer").fillna(0))
both["name"], both["region"] = both.iso3.map(display), both.iso3.map(region)
both["route_ds"] = np.select([(both.direct_ds > 0) & (both.sub_ds > 0), both.direct_ds > 0, both.sub_ds > 0],
                             ["Both", "Direct only", "Subaward only"], "No data science")
both["sub_share_ds"] = both.sub_ds_amount / (both.sub_ds_amount + both.direct_ds_cost).replace(0, np.nan)
both = both.sort_values("direct_ds_cost", ascending=False)
both.to_csv(OUT / "direct_vs_subaward.csv", index=False)
print(both.route_ds.value_counts().to_string())

reg = both.groupby("region")[["direct_ds_cost", "sub_ds_amount", "direct_ds", "sub_ds"]].sum()
reg["sub_share_ds"] = reg.sub_ds_amount / (reg.sub_ds_amount + reg.direct_ds_cost)
reg["countries_sub_only"] = both[both.route_ds.eq("Subaward only")].groupby("region").size()
reg = reg.fillna(0).sort_values("direct_ds_cost", ascending=False)
reg.to_csv(OUT / "direct_vs_subaward_regions.csv")
print(reg.round(3).to_string())
