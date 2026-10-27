# %% [markdown]
# # New data science PIs: where they came from
#
# Companion page to the PI analysis (`entrants.md`, linked from `pi_analysis.md`).
#
# **Definitions**
# - Data science PI = substantive data science in more than half of the PI's records, at least 2 records
#   (`src/pi_tiers.py`)
# - Entry year = fiscal year of the PI's first data science record
# - New data science PI = a data science PI whose entry year is FY2018 or later, so there are at least two years
#   in which earlier work could show up (RePORTER data here start in FY2016)
# - Moved in = the PI had at least one record without data science in an earlier fiscal year
# - Started in data science = the PI's first record in the data is already data science (new to NIH, or new
#   to the FY2016 window)
# - Earlier areas = NIH research, condition, and disease categories (RCDC, NIH's own spending categories) on the
#   PI's earlier records without data science, as a share of those records
# - Comparison = other PIs (at least 2 records, not data science PIs), using all their records
# - Over-representation = category's share of moved-in PIs' earlier records ÷ its share of comparison PIs' records
#   (1.0 = same as other PIs; 2.0 = twice as common)
# - Data science entry = taxonomy groups on the PI's first data science records (entry year)
# - Institute = administering institute; for earlier work, the institute of most earlier records
# - FY2026 is preliminary
#
# **Privacy:** aggregate only; cells with fewer than 11 PIs are suppressed.
# Inputs: `exporter_applications.parquet`, `exporter_core_projects_labeled.parquet`, `pi_profiles.parquet`,
# `taxonomy/categories.yaml`.
# Outputs: `reports/results/ds_entrants_*.csv`, `reports/figures/ds_entrants/*.png`.

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from pi_tiers import explode_pis, load_tiers  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "ds_entrants"
FIG.mkdir(parents=True, exist_ok=True)
FIRST_ENTRY_FY, SUPPRESS, TOP = 2018, 11, 15
IC_CODE = {"CA": "NCI", "AI": "NIAID", "HL": "NHLBI", "OD": "OD", "AG": "NIA", "GM": "NIGMS", "MH": "NIMH",
           "TR": "NCATS", "NS": "NINDS", "LM": "NLM", "DA": "NIDA", "HG": "NHGRI", "DK": "NIDDK", "HD": "NICHD",
           "ES": "NIEHS", "EB": "NIBIB", "EY": "NEI", "AR": "NIAMS", "DC": "NIDCD", "AA": "NIAAA", "MD": "NIMHD",
           "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH", "TW": "FIC", "HS": "AHRQ"}
pal.use_style()


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def note(fig, text: str, y: float = 0.02) -> None:
    fig.text(0.02, y, text, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")

# %% [markdown]
# ## Records per PI with labels, RCDC categories, and institute

# %%
pi = load_tiers(PROCESSED)
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "pi_ids", "nih_spending_cats", "administering_ic", "activity"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["ds_label", "model_categories"])
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy).astype(int)
a["ds"] = a.ds_label.eq("Y")
r = explode_pis(a)
r = r[r.pi.isin(pi.index)]

first_ds = r[r.ds].groupby("pi").fy.min().rename("entry_fy")
first_any = r.groupby("pi").fy.min().rename("first_fy")
dsp = pi.loc[pi.ds_pi].drop(columns=["first_fy", "first_ds_fy"], errors="ignore").join(first_ds).join(first_any)
dsp = dsp[dsp.entry_fy >= FIRST_ENTRY_FY]
prior = r[r.pi.isin(dsp.index)].merge(dsp.entry_fy, left_on="pi", right_index=True)
prior = prior[(prior.fy < prior.entry_fy) & ~prior.ds]
movers = set(prior.pi)
dsp["path"] = np.where(dsp.index.isin(movers), "Moved in", "Started in data science")
paths = (dsp.groupby(["entry_fy", "path"]).size().unstack(fill_value=0))
paths.to_csv(OUT / "ds_entrants_by_year.csv")
n_mov, n_all = len(movers), len(dsp)
gap = (dsp.loc[dsp.path == "Moved in", "entry_fy"] - dsp.loc[dsp.path == "Moved in", "first_fy"]).median()
print(f"New data science PIs FY{FIRST_ENTRY_FY}+: {n_all:,}; moved in {n_mov:,} ({n_mov / n_all:.0%}); "
      f"median years from first record to entry: {gap:.0f}")
print(paths)

# %% [markdown]
# ## Earlier research areas (RCDC) vs. other PIs

# %%
def rec_cats(rows: pd.DataFrame) -> tuple[pd.Series, int]:
    """Distinct records with each RCDC category, and the number of records with any category."""
    x = rows.assign(record=rows.core_project_number + "|" + rows.subproject_id.fillna(""))
    x = x[["record", "nih_spending_cats"]].dropna().drop_duplicates("record")
    n = len(x)
    x = x.assign(cat=x.nih_spending_cats.str.split(";")).explode("cat")
    x["cat"] = x.cat.str.strip()
    return x[x.cat != ""].drop_duplicates(["record", "cat"]).cat.value_counts(), n


mov_rec, n_mov_rec = rec_cats(prior)
others = pi.index[pi.group.eq("Other PIs")]
oth_rec, n_oth_rec = rec_cats(r[r.pi.isin(others)])
mov_pis = (prior[["pi", "nih_spending_cats"]].dropna().assign(cat=lambda d: d.nih_spending_cats.str.split(";"))
           .explode("cat").assign(cat=lambda d: d.cat.str.strip()).drop_duplicates(["pi", "cat"]).cat.value_counts())
mov_cats = (prior[["pi", "nih_spending_cats"]].dropna().assign(cat=lambda d: d.nih_spending_cats.str.split(";"))
            .explode("cat").assign(cat=lambda d: d.cat.str.strip()))[["pi", "cat"]].drop_duplicates()
mov_cats = mov_cats[mov_cats.cat != ""]
areas = pd.DataFrame({"moved_in_pis": mov_pis, "moved_in_records": mov_rec, "other_records": oth_rec}).fillna(0)
areas["moved_in_share"] = areas.moved_in_records / n_mov_rec
areas["other_share"] = areas.other_records / n_oth_rec
areas["over_representation"] = areas.moved_in_share / areas.other_share
areas = areas[areas.moved_in_pis >= SUPPRESS].sort_values("moved_in_share", ascending=False)
areas.to_csv(OUT / "ds_entrants_prior_areas.csv")
print(f"Earlier records with RCDC categories: {n_mov_rec:,} (moved-in PIs); {n_oth_rec:,} (other PIs)")
areas.head(20).round(3)

# %% [markdown]
# ## Chart 1. New data science PIs by entry year: moved in vs. started in data science

# %%
fig, ax = plt.subplots(figsize=(9, 4.4))
fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.24)
xs = paths.index.to_numpy()
for col, color, lw in [("Moved in", pal.PROJECTS, 2.6), ("Started in data science", pal.NEUTRAL, 2.6)]:
    ys = paths[col].to_numpy()
    ax.plot(xs, ys, color=color, lw=lw, marker="o", markersize=4)
    ax.annotate(col, (xs[1], ys[1]), xytext=(0, 10), textcoords="offset points",
                va="bottom", ha="left", color=pal.PROJECTS if col == "Moved in" else pal.MUTED, fontsize=pal.SIZES["axis"],
                fontweight="bold" if col == "Moved in" else "normal")
ax.axvspan(2022.5, xs[-1] + 0.5, color=pal.GRID, alpha=0.5, lw=0)
ax.annotate("Undercounted: recent entrants\nhave had little time to reach\nthe 2 records a data science\nPI needs"
            " (FY2026 preliminary)", (2022.7, ax.get_ylim()[1]), ha="left", va="top", fontsize=pal.SIZES["axis"],
            color=pal.MUTED)
ax.set_xticks(xs, [f"FY{x}" if x in (xs[0], xs[-1]) else str(x)[2:] for x in xs])
ax.set_ylabel("New data science PIs")
ax.set_ylim(0, None)
share_early = paths.loc[:2022, "Moved in"].sum() / paths.loc[:2022].to_numpy().sum()
fig.suptitle(f"About 1 in 5 new data science PIs moved in from other research ({share_early:.0%}, FY{FIRST_ENTRY_FY} to "
             "FY2022);\nthe rest started in data science",  x=0.02, y=0.95, ha="left",
             fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
note(fig, f"New data science PI = data science PI whose first data science record is FY{FIRST_ENTRY_FY} or later. Moved in "
     "= had an earlier record without\ndata science. Started in data science = first record in the data is data "
     "science. Source: NIH RePORTER API, FY2016 to FY2026.")
save(fig, "01_entrants_by_year")

# %% [markdown]
# ## Chart 2. Earlier research areas of PIs who moved in, vs. other PIs

# %%
top = areas.head(TOP).iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 7))
fig.subplots_adjust(left=0.3, right=0.8, top=0.84, bottom=0.2)
yy = np.arange(len(top))
ax.barh(yy + 0.19, 100 * top.moved_in_share, 0.36, color=pal.PROJECTS, label="Moved-in PIs, earlier records")
ax.barh(yy - 0.19, 100 * top.other_share, 0.36, color=pal.NEUTRAL, label="Other PIs, all records")
for yi, (_, rw) in zip(yy, top.iterrows()):
    ax.annotate(f"{100 * rw.moved_in_share:.0f}%", (100 * rw.moved_in_share, yi + 0.19), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=pal.SIZES["axis"], color=pal.PROJECTS,
                fontweight="bold")
    ax.annotate(f"{100 * rw.other_share:.0f}%", (100 * rw.other_share, yi - 0.19), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=pal.SIZES["axis"], color=pal.MUTED)
    ax.annotate(f"{rw.over_representation:.1f}×", (1.0, yi), xycoords=("axes fraction", "data"), xytext=(14, 0),
                textcoords="offset points", va="center", fontsize=pal.SIZES["label"],
                fontweight="bold" if rw.over_representation >= 1.5 else "normal",
                color=pal.HEADING if rw.over_representation >= 1.5 else pal.MUTED)
ax.annotate("Times as\ncommon", (1.0, len(top) - 0.45), xycoords=("axes fraction", "data"), xytext=(14, 0),
            textcoords="offset points", va="bottom", fontsize=pal.SIZES["axis"], color=pal.MUTED)
ax.set_yticks(yy, top.index)
ax.set_xlabel("Records in the category, %")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)
hi = areas.head(TOP).over_representation.idxmax()
lo = areas.head(TOP).over_representation.idxmin()
fig.suptitle(f"PIs who moved into data science came mostly from {areas.index[0].lower()};\n"
             f"{hi.lower()} is {areas.loc[hi, 'over_representation']:.1f} times as common in their earlier work as for "
             f"other PIs, {lo.lower()} {areas.loc[lo, 'over_representation']:.1f} times",
             x=0.02, y=0.97, ha="left", fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
note(fig, f"{TOP} most common RCDC categories (NIH research, condition, and disease categories) on moved-in PIs' earlier "
     "records without data science.\nOther PIs = PIs with at least 2 records who are not data science PIs. Times as "
     "common = moved-in share ÷ other PIs' share. A record\ncan have several categories. Source: NIH RePORTER API, "
     "FY2016 to FY2026 (FY2026 preliminary).")
save(fig, "02_prior_areas")

# %% [markdown]
# ## Earlier institute and award type

# %%
prior_ic = prior.groupby("pi").administering_ic.agg(lambda s: s.mode().iat[0])
entry_rows = r[r.pi.isin(movers)].merge(dsp.entry_fy, left_on="pi", right_index=True)
entry_rows = entry_rows[entry_rows.ds & (entry_rows.fy == entry_rows.entry_fy)]
entry_ic = entry_rows.groupby("pi").administering_ic.agg(lambda s: s.mode().iat[0])
same_ic = (prior_ic.reindex(entry_ic.index) == entry_ic).mean()
act = prior.activity.fillna("").astype(str)
prior["kind"] = np.select([act.str[:1].isin(["F", "K", "T"]) | act.isin(["R00", "R25"]), act.str.startswith("R"),
                           act.str[:1].isin(["P", "U"])], ["Training (F, K, T, R00, R25)", "Research (R)",
                                                          "Centers and cooperative (P, U)"], "Other")
kinds = prior[["pi", "kind"]].drop_duplicates().kind.value_counts() / n_mov
kinds.rename("share_of_moved_in_pis").to_csv(OUT / "ds_entrants_prior_award_types.csv")
ic_flow = pd.DataFrame({"prior_ic": prior_ic.reindex(entry_ic.index), "entry_ic": entry_ic})
ic_tab = ic_flow.prior_ic.value_counts().rename("moved_in_pis").to_frame()
ic_tab["same_ic_at_entry"] = ic_flow.assign(same=ic_flow.prior_ic == ic_flow.entry_ic).groupby("prior_ic").same.mean()
ic_tab = ic_tab[ic_tab.moved_in_pis >= SUPPRESS]
ic_tab.index = ic_tab.index.map(lambda c: IC_CODE.get(c, c))
ic_tab.to_csv(OUT / "ds_entrants_prior_ic.csv")
print(f"Entered data science at the same institute as their earlier work: {same_ic:.0%}")
print(kinds.round(3).to_string())

# %% [markdown]
# ## Chart 3. Where they went: data science groups at entry, by earlier research area

# %%
tax = yaml.safe_load((ROOT / "taxonomy" / "categories.yaml").read_text(encoding="utf-8"))
GLABEL = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
          "artificial_intelligence": "Artificial intelligence", "software_tools": "Software and tools",
          "data_infrastructure": "Data infrastructure", "data_sharing": "Data infrastructure",
          "responsible_ai": "Responsible AI", "workforce": "Workforce"}
cat_group = {}
for d in tax["dimensions"]:
    for c in d.get("categories", []):
        g = c.get("group") or d["id"]
        if g in GLABEL:
            cat_group[c["id"]] = GLABEL[g]
eg = entry_rows[["pi", "model_categories"]].dropna()
eg = eg.assign(cat=eg.model_categories.str.split("; ")).explode("cat")
eg["group"] = eg.cat.map(cat_group)
eg = eg.dropna(subset=["group"])[["pi", "group"]].drop_duplicates()
top_areas = areas.head(8).index
flow = mov_cats[mov_cats.cat.isin(top_areas)].merge(eg, on="pi")
mat = flow.groupby(["cat", "group"]).pi.nunique().unstack(fill_value=0)
base_n = mov_cats[mov_cats.cat.isin(top_areas)].groupby("cat").pi.nunique()
mat = mat.div(base_n, axis=0).reindex(index=top_areas)
order = eg.group.value_counts().index
mat = mat.reindex(columns=order).fillna(0)
all_row = eg.group.value_counts().reindex(order) / eg.pi.nunique()
mat.to_csv(OUT / "ds_entrants_area_to_group.csv")

fig, ax = plt.subplots(figsize=(10.5, 5.8))
fig.subplots_adjust(left=0.24, right=0.97, top=0.72, bottom=0.17)
show = pd.concat([pd.DataFrame([all_row.values], index=["All moved-in PIs"], columns=order), mat])
cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#FFFFFF", pal.PROJECTS])
ax.imshow(show.to_numpy(), cmap=cmap, vmin=0, vmax=1, aspect="auto")
for i in range(show.shape[0]):
    for j in range(show.shape[1]):
        v = show.iat[i, j]
        ax.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=pal.SIZES["axis"],
                color="white" if v >= 0.55 else pal.INK, fontweight="bold" if i == 0 else "normal")
ax.axhline(0.5, color=pal.MUTED, lw=1)
import textwrap  # noqa: E402
ax.set_xticks(range(len(order)), [textwrap.fill(o, 14, break_long_words=False) for o in order])
ax.xaxis.tick_top()
ax.set_yticks(range(show.shape[0]), show.index)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
top_g = all_row.index[0]
fig.suptitle(f"Whatever their earlier area, most PIs entered data science through {top_g.lower()};\n"
             f"{all_row.index[1].lower()} came next", x=0.02, y=0.97, ha="left",
             fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
note(fig, "Cell = % of moved-in PIs from that earlier RCDC area whose first data science records include the group "
     "(a record can have several groups,\nso rows add to more than 100%). Rows = the 8 most common earlier areas. "
     "Source: NIH RePORTER API, FY2016 to FY2026; NIH Data Science Taxonomy.")
save(fig, "03_area_to_group")
print("Charts saved to", FIG)
