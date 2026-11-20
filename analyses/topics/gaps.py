# %% [markdown]
# # B3. Where data science is thin relative to need
#
# Analysis B, slide 4. Compares NIH data science funding by disease area with U.S. disease burden.
#
# **Definitions**
# - Area = a GBD cause (level 2 for the slide, level 3 for the analysis), matched to one or more RCDC
#   categories in `analyses/topics/rcdc_gbd_crosswalk.csv`. A record counts once in an area even if it has
#   several of the area's RCDC categories
# - Funding = attributed cost of NIH records, FY2016–FY2025 (FY2026 preliminary, left out); data science
#   funding = records of data science projects (`ds_label` = Y)
# - Burden = U.S. DALYs (disability-adjusted life years: years of life lost plus years lived with disability),
#   all ages, both sexes, averaged over the years in the GBD export that fall in FY2016–FY2025
# - Burden share = area DALYs ÷ all-cause DALYs (the sum of all level 3 causes; level 2 = sum of its level 3 causes)
# - Data science funding share = area data science funding ÷ all NIH data science funding
# - Gap ratio = data science funding share ÷ burden share (1.0 = in proportion to burden; < 1 = thin)
# - Data science intensity = area data science funding ÷ all NIH funding in the area
# - Expected funding: least squares fit of log10(funding) on log10(DALYs) across level 3 areas, separately
#   for data science and for all NIH funding. Residual = log10(actual ÷ expected); −0.3 ≈ half of expected.
#   Data science lag = data science residual − all-NIH residual (< 0: data science is thinner than NIH's own
#   investment in the area would suggest)
# - Uncertain crosswalk matches (`confidence` medium or low) are flagged in every table
#
# RCDC categories overlap, so area shares don't sum to 100%. Burden is one measure of need; scientific
# opportunity, cost, and other funders matter too.
#
# Inputs: `data/raw/gbd/*.csv` (GBD Results tool export), `exporter_applications.parquet`,
# `exporter_core_projects_labeled.parquet`, `analyses/topics/rcdc_gbd_crosswalk.csv`.
# Outputs: `reports/results/gaps_*.csv`, `reports/figures/topics/11_*.png` to `13_*.png`.

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
GBD = ROOT / "data" / "raw" / "gbd"
FIG = ROOT / "reports" / "figures" / "topics"
FIG.mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST_FULL = 2016, 2025
EARLY, LATE = range(2016, 2019), range(2023, 2026)
SOURCE = "Source: NIH RePORTER API (RCDC categories); IHME Global Burden of Disease; NIH Data Science Taxonomy."
pal.use_style()


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def title(fig, text):
    fig.suptitle(text, x=0.02, ha="left", fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")


def note(fig, text):
    fig.text(0.02, 0.005, text, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")

# %% [markdown]
# ## Burden (GBD export)

# %%
files = sorted(GBD.glob("*.csv"))
assert files, f"Put the GBD Results tool CSV in {GBD}"
g = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
need = {"measure_name", "location_name", "sex_name", "age_name", "cause_name", "metric_name", "year", "val"}
assert need <= set(g.columns), f"GBD export is missing {need - set(g.columns)}; export with ID and name columns"
g = g[g.measure_name.str.startswith("DALYs") & g.metric_name.eq("Number") & g.sex_name.eq("Both")
      & g.age_name.eq("All ages") & g.year.between(FY_FIRST, FY_LAST_FULL)]
years = sorted(g.year.unique())
print("GBD years used:", years[0], "to", years[-1], "| locations:", sorted(g.location_name.unique()))
dalys = g.groupby(["location_name", "cause_name"]).val.mean().rename("dalys").reset_index()
# The Results tool export holds level 3 causes; level 2 = sum of its level 3 causes (GBD cause hierarchy)
here = Path(__file__).resolve().parent if "__file__" in globals() else ROOT / "analyses" / "topics"
h = pd.read_csv(here / "gbd_level3_to_level2.csv")
unmapped = sorted(set(dalys.cause_name) - set(h.level3_cause) - set(h.level2_cause))
assert not unmapped, f"GBD causes missing from gbd_level3_to_level2.csv: {unmapped}"
l3 = dalys[dalys.cause_name.isin(h.level3_cause)]
l2 = (l3.merge(h, left_on="cause_name", right_on="level3_cause").groupby(["location_name", "level2_cause"]).dalys.sum()
      .rename_axis(["location_name", "cause_name"]).reset_index())
dalys = pd.concat([l3, l2[~l2.cause_name.isin(l3.cause_name)]], ignore_index=True)
total = l3.groupby("location_name").dalys.sum()

cw = pd.read_csv(here / "rcdc_gbd_crosswalk.csv")
cw["rcdc"] = cw.rcdc_categories.str.split(";").map(lambda xs: [x.strip() for x in xs])
missing_causes = sorted(set(cw.gbd_cause) - set(dalys.cause_name))
if missing_causes:
    print("Crosswalk causes not in the GBD export (check names):", missing_causes)
US = "United States of America"
print(f"All-cause DALYs (sum of all level 3 causes), {US}: {total.get(US, np.nan):,.0f}")

# %% [markdown]
# ## NIH funding by area

# %%
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=key + ["fy", "nih_spending_cats", "attributed_cost"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label"])
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy)
a = a[a.fy.between(FY_FIRST, FY_LAST_FULL)].copy()
a["ds"] = a.ds_label.eq("Y")
a["cost"] = a.attributed_cost.fillna(0)
a["cats"] = a.nih_spending_cats.fillna("").str.split(";").map(lambda xs: {x.strip() for x in xs if x.strip()})
all_cats = set().union(*a.cats)
missing_rcdc = sorted({c for cs in cw.rcdc for c in cs} - all_cats)
if missing_rcdc:
    print("Crosswalk RCDC categories not in the data (check names):", missing_rcdc)
ds_total = a.loc[a.ds, "cost"].sum()
ds_total_by = a[a.ds].groupby(a.fy.isin(LATE)).cost.sum()

rows = []
for r in cw.itertuples():
    m = a.cats.map(lambda cs, want=set(r.rcdc): bool(cs & want))
    sub = a[m]
    early, late = sub[sub.fy.isin(EARLY)], sub[sub.fy.isin(LATE)]
    rows.append({"gbd_level": r.gbd_level, "gbd_cause": r.gbd_cause, "confidence": r.confidence,
                 "all_cost": sub.cost.sum(), "ds_cost": sub.loc[sub.ds, "cost"].sum(),
                 "ds_share_early": early.loc[early.ds, "cost"].sum() / a[a.fy.isin(EARLY) & a.ds].cost.sum(),
                 "ds_share_late": late.loc[late.ds, "cost"].sum() / a[a.fy.isin(LATE) & a.ds].cost.sum()})
f = pd.DataFrame(rows)

# %% [markdown]
# ## Shares, gap ratio, intensity, expected funding

# %%
def build(loc):
    d = f.merge(dalys[dalys.location_name == loc][["cause_name", "dalys"]], left_on="gbd_cause", right_on="cause_name", how="left")
    d["burden_share"] = d.dalys / total.get(loc, np.nan)
    d["ds_funding_share"] = d.ds_cost / ds_total
    d["nih_funding_share"] = d.all_cost / a.cost.sum()
    d["gap_ratio"] = d.ds_funding_share / d.burden_share
    d["nih_gap_ratio"] = d.nih_funding_share / d.burden_share
    d["ds_intensity"] = d.ds_cost / d.all_cost
    d["gap_ratio_change"] = (d.ds_share_late / d.ds_share_early.replace(0, np.nan))
    d["uncertain_match"] = d.confidence.ne("high")
    for lvl in (2, 3):
        s = d[(d.gbd_level == lvl) & (d.dalys > 0) & (d.ds_cost > 0) & (d.all_cost > 0)]
        if len(s) < 5:
            continue
        x = np.log10(s.dalys)
        for col, res in [("ds_cost", "ds_residual"), ("all_cost", "nih_residual")]:
            b1, b0 = np.polyfit(x, np.log10(s[col]), 1)
            d.loc[s.index, res] = np.log10(s[col]) - (b0 + b1 * x)
            d.loc[s.index, f"{res}_slope"] = b1
    d["ds_lag"] = d.ds_residual - d.nih_residual
    return d.drop(columns="cause_name").assign(location=loc)


us = build(US)
us.to_csv(OUT / "gaps_us.csv", index=False)
if "Global" in set(dalys.location_name):
    build("Global").to_csv(OUT / "gaps_global.csv", index=False)
cols = ["gbd_cause", "burden_share", "ds_funding_share", "gap_ratio", "ds_intensity", "ds_lag", "uncertain_match"]
print("Level 3, thinnest relative to burden:")
print(us[us.gbd_level == 3].sort_values("gap_ratio")[cols].head(12).round(3).to_string(index=False))
print("\nLevel 3, data science thinner than NIH's own investment (ds_lag):")
print(us[us.gbd_level == 3].sort_values("ds_lag")[cols].head(12).round(3).to_string(index=False))

# %% [markdown]
# ## Charts

# %%
def scatter(d, lvl, name, label_n=None):
    """Numbered dots with a key to the right, so long cause names never overlap."""
    s = d[(d.gbd_level == lvl) & d.burden_share.gt(0) & d.ds_funding_share.gt(0)]
    lab = s if label_n is None else pd.concat([s.nsmallest(label_n, "gap_ratio"), s.nlargest(4, "gap_ratio")])
    lab = lab.sort_values("gap_ratio").reset_index(drop=True)
    fig = plt.figure(figsize=(13, 7.8))
    ax = fig.add_axes([0.08, 0.2, 0.52, 0.66])
    col = lambda u: pal.NEUTRAL if u else pal.PROJECTS  # noqa: E731
    rest = s[~s.gbd_cause.isin(lab.gbd_cause)]
    ax.scatter(rest.burden_share * 100, rest.ds_funding_share * 100, s=40, color=[col(u) for u in rest.uncertain_match],
               edgecolor=pal.MUTED, lw=0.5, zorder=3)
    placed = []
    for i, r in lab.iterrows():
        x0, y0 = r.burden_share * 100, r.ds_funding_share * 100
        x, y = x0, y0
        for _ in range(6):   # nudge a numbered dot off any it would cover; a thin line shows where it really sits
            near = [(px, py) for px, py in placed if abs(np.log10(x / px)) < 0.07 and abs(np.log10(y / py)) < 0.07]
            if not near:
                break
            y *= 10 ** -0.09 if y <= near[0][1] else 10 ** 0.09
        placed.append((x, y))
        if (x, y) != (x0, y0):
            ax.plot([x0, x], [y0, y], color=pal.MUTED, lw=0.7, zorder=3)
            ax.scatter([x0], [y0], s=12, color=pal.MUTED, zorder=3)
        ax.scatter([x], [y], s=210, color=col(r.uncertain_match), edgecolor=pal.MUTED, lw=0.5, zorder=4)
        ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=8,
                fontweight="bold", color="white" if not r.uncertain_match else pal.INK, zorder=5)
    lim = [min(s.burden_share.min(), s.ds_funding_share.min()) * 100 * 0.6, max(s.burden_share.max(), s.ds_funding_share.max()) * 100 * 1.6]
    ax.plot(lim, lim, color=pal.MUTED, lw=1, ls=":")
    ax.text(lim[0] * 3, lim[0] * 1.9, "funding share = burden share", color=pal.MUTED, fontsize=pal.SIZES["axis"],
            rotation=45, rotation_mode="anchor", transform_rotates_text=True)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    fmt = plt.FuncFormatter(lambda v, _: f"{v:g}%")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(fmt)
        axis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlabel("Share of U.S. disease burden (% of DALYs, log scale)")
    ax.set_ylabel("Share of NIH data science funding (%, log scale)")
    # key: number, name, gap ratio
    kx, ky, step = 0.63, 0.86, min(0.66 / max(len(lab), 1), 0.045)
    fig.text(kx, ky + 0.02, "Gap ratio = funding share ÷ burden share", fontsize=pal.SIZES["axis"], color=pal.MUTED, fontweight="bold")
    for i, r in lab.iterrows():
        y = ky - (i + 0.6) * step
        fig.text(kx, y, f"{i + 1:>2}", fontsize=pal.SIZES["axis"], fontweight="bold", color=pal.INK, ha="right")
        fig.text(kx + 0.012, y, f"{r.gbd_cause}  ({r.gap_ratio:.2f})", fontsize=pal.SIZES["axis"], color=pal.INK)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], ls="", marker="o", ms=9, color=pal.PROJECTS, mec=pal.MUTED, label="Confident RCDC match"),
                       Line2D([], [], ls="", marker="o", ms=9, color=pal.NEUTRAL, mec=pal.MUTED, label="Uncertain RCDC match")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=pal.SIZES["axis"])
    title(fig, "Data science funding vs. disease burden" + (" (GBD level 2)" if lvl == 2 else " (GBD level 3)"))
    shown = "" if label_n is None else f" Numbered: the {label_n} lowest and 4 highest gap ratios."
    note(fig, f"FY{FY_FIRST}–FY{FY_LAST_FULL} funding; U.S. DALYs averaged over {years[0]}–{years[-1]}. Below the line = less data science funding\n"
              f"than burden share. Areas overlap, so shares don't sum to 100%.{shown}\n" + SOURCE)
    save(fig, name)


scatter(us, 2, "11_gap_scatter_level2")
scatter(us, 3, "12_gap_scatter_level3", label_n=10)

s3 = us[(us.gbd_level == 3) & us.ds_lag.notna()].sort_values("ds_lag")
show = pd.concat([s3.head(10), s3.tail(10)])
fig, ax = plt.subplots(figsize=(10, 8))
fig.subplots_adjust(left=0.38, top=0.9, bottom=0.14)
ax.barh(show.gbd_cause[::-1], show.ds_lag[::-1], color=[pal.PROJECTS if v < 0 else pal.NEUTRAL for v in show.ds_lag[::-1]])
for i, (v, x) in enumerate(zip(show.ds_lag[::-1], show.ds_intensity[::-1])):
    ax.annotate(f"{x:.0%} data science", (max(v, 0), i), xytext=(4, 0), textcoords="offset points",
                ha="left", va="center", fontsize=8.5, color=pal.MUTED)
ax.axvline(0, color=pal.MUTED, lw=1)
ax.set_xlabel("Data science lag (log10 of data science vs. all-NIH funding relative to burden)")
title(fig, "Where data science lags NIH's own investment in an area")
note(fig, "Lag = data science residual − all-NIH residual from funding-vs-burden fits across GBD level 3 areas. −0.3 ≈ half.\n"
          "Labels = data science share of the area's NIH funding.\n" + SOURCE)
save(fig, "13_ds_lag_level3")
print("done")
