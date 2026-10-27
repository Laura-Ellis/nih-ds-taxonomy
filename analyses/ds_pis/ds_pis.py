# %% [markdown]
# # Who does data science at NIH? Data science principal investigators (PIs)
#
# Side analysis. Builds on notebook 15 (PI profiles): charts and comparisons for the site page and deck.
#
# **Definitions**
# - PI = every investigator listed on a project record (RePORTER profile ID), not only the contact PI
# - Portfolio = a PI's distinct project records (parent projects and subprojects), FY2016 to FY2026
# - Data science share = substantive data science records ÷ all records in the PI's portfolio
# - Data science PI = data science in more than half of the PI's records (true majority), with at least 2 records
# - AI developer PI = develops AI in more than half of the PI's records (role "develops AI")
# - Infrastructure builder PI = builds data infrastructure in more than half of the PI's records: substantive
#   data science records with research software, analysis platforms, data platforms, data engineering, FAIR
#   data, data management and sharing, or human-derived data linkage categories
# - The two builder tiers can overlap; both are subsets of data science PIs
# - Comparison groups = other data science PIs, and all other PIs with at least 2 records
# - Matched comparisons weight the comparison group to the tier's mix of portfolio size and first data
#   science year, since builders tend to be newer and smaller
# - Outputs use all of a PI's projects, so both groups are measured the same way: linked papers, mean
#   Relative Citation Ratio (RCR = citations per year ÷ the field's expected rate; 1.0 = median NIH paper),
#   and links to patents and clinical trials
# - Institute (IC) = the administering IC of most of the PI's records
# - FY2026 is preliminary
#
# **Privacy:** every output is aggregate; cells with fewer than 11 PIs are suppressed.
#
# Inputs: `data/processed/pi_profiles.parquet` (notebook 15), `exporter_applications.parquet`,
# publication links, iCite cache, and ExPORTER patent and clinical study link tables.
# Outputs: `reports/figures/ds_pis/*.png`, `reports/results/ds_pis_*.csv`.

# %%
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import PRELIMINARY_FY, SETTINGS, source  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM = ROOT / "data" / "processed", ROOT / "data" / "interim"
OUT, FIG = ROOT / "reports" / "results", ROOT / "reports" / "figures" / "ds_pis"
FIG.mkdir(parents=True, exist_ok=True)
SUPPRESS = 11
FOCUS_IC = SETTINGS.get("focus_ic")  # highlight one IC if set (Laura's local config); otherwise none
pal.use_style()


def data_dir(name: str) -> Path:
    """Configured source folder; NIH_DATA overrides the base folder when running elsewhere."""
    p = Path(source(name))
    if not p.exists() and os.environ.get("NIH_DATA"):
        p = Path(os.environ["NIH_DATA"]) / ("combined/pub_links" if name == "pub_links" else "")
    return p


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def source_note(ax, text: str = "Source: NIH RePORTER API, FY2016 to FY2026 (FY2026 preliminary).", y: float = -0.16) -> None:
    """Source line under the chart; use a lower y when the chart has an x-axis title."""
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=pal.SIZES["source"], color=pal.SOURCE,
                va="top", linespacing=1.6)

# %% [markdown]
# ## Load PI profiles and every PI's projects

# %%
pi = pd.read_parquet(PROCESSED / "pi_profiles.parquet").set_index("pi")
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["fy", "administering_ic", "core_project_number", "pi_ids"])
pa = apps.assign(pi=apps.pi_ids.fillna("").str.split(";")).explode("pi")
pa["pi"] = pa.pi.str.replace("(contact)", "", regex=False).str.strip()
pa = pa[pa.pi.isin(pi.index)][["pi", "core_project_number"]].drop_duplicates()
INFRA = ["research_software", "analysis_platforms", "data_platforms", "data_engineering", "fair_data",
         "data_management_sharing", "human_data_linkage"]
key = ["core_project_number", "subproject_id"]
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label", "model_categories"])
core["record"] = core.core_project_number + "|" + core.subproject_id.fillna("")
core["infra"] = core.ds_label.eq("Y") & core.model_categories.fillna("").str.split("; ").map(
    lambda cats: any(c in cats for c in INFRA))
rec_apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=key + ["pi_ids"])
rec_apps["record"] = rec_apps.core_project_number + "|" + rec_apps.subproject_id.fillna("")
rp = rec_apps.assign(pi=rec_apps.pi_ids.fillna("").str.split(";")).explode("pi")
rp["pi"] = rp.pi.str.replace("(contact)", "", regex=False).str.strip()
rp = rp[rp.pi.isin(pi.index)][["pi", "record"]].drop_duplicates().merge(core[["record", "infra"]], on="record", how="left")
pi["infra_records"] = rp.groupby("pi").infra.sum()
pi = pi.fillna({"infra_records": 0})

two = pi.records >= 2
pi["ds_pi"] = two & (pi.ds_share > 0.5)                                  # true majority
pi["ai_developer"] = two & (pi.develops_records / pi.records > 0.5)
pi["infra_builder"] = two & (pi.infra_records / pi.records > 0.5)
pi["tier"] = np.select([pi.ai_developer & pi.infra_builder, pi.ai_developer, pi.infra_builder, pi.ds_pi],
                       ["AI developer and infrastructure builder", "AI developer", "Infrastructure builder",
                        "Other data science PI"], np.where(two, "Other PIs", None))
pi["group"] = np.where(pi.ds_pi, "Data science PIs", np.where(two, "Other PIs", None))
tiers = pd.Series({"Data science PIs": pi.ds_pi.sum(), "AI developer PIs": pi.ai_developer.sum(),
                   "Infrastructure builder PIs": pi.infra_builder.sum(),
                   "Both builder tiers": (pi.ai_developer & pi.infra_builder).sum(), "All PIs": len(pi)})
tiers.rename("pis").to_csv(OUT / "ds_pis_tiers.csv")
print(tiers.to_string())

# %% [markdown]
# ## Outputs from all of each PI's projects

# %%
links = pd.concat(pd.read_parquet(f) for f in sorted(data_dir("pub_links").glob("*.parquet")))
links.columns = links.columns.str.lower()
links["pmid"] = pd.to_numeric(links.pmid, errors="coerce")
links = links.dropna(subset=["pmid"])[["pmid", "project_number"]].drop_duplicates()
pp = pa.merge(links, left_on="core_project_number", right_on="project_number")[["pi", "pmid"]].drop_duplicates()
pi["papers"] = pp.groupby("pi").size()
rcr = pd.read_parquet(INTERIM / "icite.parquet").drop_duplicates("pmid").set_index("pmid").rcr
pp["rcr"] = pp.pmid.map(rcr)
pi["mean_rcr"] = pp.groupby("pi").rcr.mean()

base = data_dir("link_tables") if data_dir("link_tables").exists() else Path(os.environ.get("NIH_DATA", "."))
for label, fname, col in [("patent", "Patents.csv", "project_id"), ("trial", "ClinicalStudies.csv", "core_project_number")]:
    t = pd.read_csv(base / fname, encoding="latin-1", low_memory=False)
    t.columns = t.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
    linked = set(t[col].astype(str).str.strip())
    pi[f"{label}_linked"] = pa.assign(h=pa.core_project_number.isin(linked)).groupby("pi").h.any()
pi = pi.fillna({"papers": 0, "patent_linked": False, "trial_linked": False})

# Compare within portfolio size, since data science PIs and others differ in how many projects they hold
pi["size_band"] = pd.cut(pi.records, [1, 2, 3, 5, 10, np.inf], labels=["2", "3", "4–5", "6–10", "11+"])
g = pi.dropna(subset=["group"])
compare = g.groupby("group").agg(pis=("records", "size"), median_records=("records", "median"),
                                 median_papers=("papers", "median"), median_mean_rcr=("mean_rcr", "median"),
                                 patent_linked=("patent_linked", "mean"), trial_linked=("trial_linked", "mean"),
                                 multi_ic=("n_ics", lambda s: (s > 1).mean()))
compare["median_years_active"] = (g.last_fy - g.first_fy + 1).groupby(g.group).median()
by_size = g.groupby(["size_band", "group"], observed=True).agg(
    pis=("records", "size"), median_papers=("papers", "median"), median_mean_rcr=("mean_rcr", "median"),
    patent_linked=("patent_linked", "mean"), trial_linked=("trial_linked", "mean")).reset_index()
by_size.loc[by_size.pis < SUPPRESS, ["median_papers", "median_mean_rcr", "patent_linked", "trial_linked"]] = np.nan
compare.to_csv(OUT / "ds_pis_vs_other.csv")
by_size.to_csv(OUT / "ds_pis_vs_other_by_portfolio_size.csv", index=False)
compare.round(3)

# %%
by_size.round(3)

# %% [markdown]
# ## Chart 1. Share of active PIs who are data science PIs, by fiscal year

# %%
yr = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=["fy", "pi_ids"])
yr = yr.assign(pi=yr.pi_ids.fillna("").str.split(";")).explode("pi")
yr["pi"] = yr.pi.str.replace("(contact)", "", regex=False).str.strip()
yr = yr[yr.pi.isin(pi.index)][["fy", "pi"]].drop_duplicates()
yr["fy"] = pd.to_numeric(yr.fy).astype(int)
yr["ds_pi"] = yr.pi.map(pi.ds_pi)
by_fy = yr.groupby("fy").agg(all_pis=("pi", "size"), active_ds_pis=("ds_pi", "sum")).reset_index()
by_fy["ds_pi_share"] = by_fy.active_ds_pis / by_fy.all_pis
by_fy["preliminary"] = by_fy.fy == PRELIMINARY_FY
by_fy.to_csv(OUT / "ds_pis_by_fy.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 4.2))
full = by_fy[~by_fy.preliminary]
ax.plot(full.fy, 100 * full.ds_pi_share, color=pal.PROJECTS, lw=2.5)
prelim = by_fy[by_fy.fy >= full.fy.max()]
ax.plot(prelim.fy, 100 * prelim.ds_pi_share, color=pal.PROJECTS, lw=2.5, ls="--")
for _, r in by_fy[by_fy.fy.isin([by_fy.fy.min(), full.fy.max()])].iterrows():
    ax.annotate(f"{100 * r.ds_pi_share:.1f}%", (r.fy, 100 * r.ds_pi_share), textcoords="offset points",
                xytext=(0, 8), ha="center", color=pal.PROJECTS, fontweight="bold")
ax.set_ylim(0, 100 * by_fy.ds_pi_share.max() * 1.3)
ax.set_xticks(by_fy.fy, [f"FY{str(y)[2:]}" for y in by_fy.fy])
ax.set_ylabel("Data science PIs, % of active PIs")
first, last = by_fy.iloc[0], full.iloc[-1]
ax.set_title(f"Data science PIs grew from {100 * first.ds_pi_share:.1f}% to {100 * last.ds_pi_share:.1f}% "
             f"of active NIH PIs,\nthen leveled off after FY2022", pad=12)
source_note(ax, "Active = on at least one project that year. FY2026 is preliminary (dashed).\nSource: NIH RePORTER API.", y=-0.14)
save(fig, "01_share_by_fy")

# %% [markdown]
# ## Chart 2. Share of PIs who are data science PIs, by main institute

# %%
by_ic = pi.groupby("main_ic").agg(pis=("ds_pi", "size"), ds_pis=("ds_pi", "sum")).reset_index()
by_ic["ds_pi_share"] = by_ic.ds_pis / by_ic.pis
by_ic = by_ic[by_ic.ds_pis >= SUPPRESS].sort_values("ds_pi_share")
nih = pi.ds_pi.sum() / len(pi)
fig, ax = plt.subplots(figsize=(8, 7))
colors = [pal.PROJECTS if (FOCUS_IC is None or ic == FOCUS_IC) else pal.NEUTRAL for ic in by_ic.main_ic]
ax.barh(by_ic.main_ic, 100 * by_ic.ds_pi_share, color=colors)
ax.axvline(100 * nih, color=pal.MUTED, lw=1, ls=":", zorder=0)
ax.annotate(f"All NIH {100 * nih:.1f}%", (100 * nih, len(by_ic) - 0.2), xytext=(0, 6), textcoords="offset points",
            ha="center", color=pal.MUTED, fontsize=pal.SIZES["axis"])
for y, v in enumerate(by_ic.ds_pi_share):
    ax.annotate(f"{100 * v:.0f}%", (100 * v, y), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=pal.SIZES["axis"], color=pal.MUTED,
                bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))
ax.set_ylim(-0.6, len(by_ic) + 0.4)
ax.set_xlabel("Data science PIs, % of the institute's PIs")
top = by_ic.iloc[-2:][::-1]
ax.set_title(f"{top.main_ic.iloc[0]} and {top.main_ic.iloc[1]} have the highest share of data science PIs", pad=12)
source_note(ax, "Institute = the administering institute of most of the PI's projects.\n"
            "Source: NIH RePORTER API, FY2016 to FY2026.", y=-0.1)
save(fig, "02_share_by_ic")

# %% [markdown]
# ## Chart 3. How data science PIs work with AI

# %%
d = pi[pi.ds_pi]
counts = d.ai_type.value_counts().reindex(["Develops AI", "Applies or supports AI", "No AI projects"])
mix = counts / len(d)
n_all = len(pi)
fig, ax = plt.subplots(figsize=(8, 2.1))
left = 0
for label, v, n, c in zip(mix.index, mix.values, counts.values,
                          [pal.ROLE_COLORS["develops_ai"], pal.ROLE_COLORS["applies_ai"], pal.NEUTRAL]):
    ax.barh(0, v, left=left, color=c)
    ax.text(left + v / 2, 0, f"{label}\n{100 * v:.0f}% ({n:,})\n{100 * n / n_all:.1f}% of all PIs", ha="center",
            va="center", color="white" if c != pal.NEUTRAL else pal.INK, fontsize=pal.SIZES["axis"])
    left += v
ax.set_xlim(0, 1)
ax.axis("off")
any_ai = mix["Develops AI"] + mix["Applies or supports AI"]
ax.set_title(f"{100 * any_ai:.0f}% of the {len(d):,} data science PIs ({100 * len(d) / n_all:.1f}% of all "
             f"{n_all:,} NIH PIs) have an AI project", pad=12)
source_note(ax, "Develops AI = develops AI on at least one project.\nSource: NIH RePORTER API, FY2016 to FY2026.", y=-0.05)
save(fig, "03_ai_mix")

# %% [markdown]
# ## Chart 4. Outputs: data science PIs vs. other PIs with the same number of projects

# %%
s = by_size.pivot(index="size_band", columns="group", values="median_papers")
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(s))
ax.bar(x - 0.2, s["Data science PIs"], 0.4, color=pal.PROJECTS, label="Data science PIs")
ax.bar(x + 0.2, s["Other PIs"], 0.4, color=pal.NEUTRAL, label="Other PIs")
for i, (a, b) in enumerate(zip(s["Data science PIs"], s["Other PIs"])):
    ax.annotate(f"{a:.0f}", (i - 0.2, a), xytext=(0, 3), textcoords="offset points", ha="center", color=pal.PROJECTS)
    ax.annotate(f"{b:.0f}", (i + 0.2, b), xytext=(0, 3), textcoords="offset points", ha="center", color=pal.MUTED)
ax.set_xticks(x, s.index)
ax.set_xlabel("Project records in the PI's portfolio, FY2016 to FY2026")
ax.set_ylabel("Median linked papers per PI")
ax.legend(loc="upper left")
ratio = (s["Data science PIs"] / s["Other PIs"]).median()
verdict = ("about as much as" if 0.9 <= ratio <= 1.1 else f"{abs(ratio - 1):.0%} {'more' if ratio > 1 else 'less'} than")
ax.set_title(f"At the same portfolio size, data science PIs publish {verdict} other PIs", pad=12)
source_note(ax, "Papers linked to any of the PI's projects (ExPORTER publication links).\nSource: NIH RePORTER API.", y=-0.22)
save(fig, "04_papers_by_size")

# %% [markdown]
# ## Chart 5. Definition check: how the count changes with the cutoffs

# %%
sens = pd.DataFrame([{"share": s_, "min_projects": m, "pis": int(((pi.ds_share > s_ if s_ == 0.5 else pi.ds_share >= s_)
                                                                 & (pi.records >= m)).sum())}
                     for s_ in (0.25, 0.5, 2 / 3, 1.0) for m in (1, 2, 3)])
sens.to_csv(OUT / "ds_pis_cutoff_sensitivity.csv", index=False)
sens = sens.pivot(index="share", columns="min_projects", values="pis")
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.imshow(sens.values, cmap="Greys", aspect="auto", vmin=0, vmax=sens.values.max() * 1.6)
for (i, j), v in np.ndenumerate(sens.values):
    chosen = sens.index[i] == 0.5 and sens.columns[j] == 2  # more than half, 2+ records
    ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontweight="bold" if chosen else "normal",
            color=pal.HEADING if chosen else pal.INK)
    if chosen:
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=pal.HEADING, lw=2))
ax.set_xticks(range(len(sens.columns)), [f"{c} or more" for c in sens.columns])
ax.set_yticks(range(len(sens.index)), ["25% or more", "More than 50%", "67% or more", "100%"])
ax.xaxis.set_ticks_position("top")
ax.xaxis.set_label_position("top")
ax.set_xlabel("Minimum project records, FY2016 to FY2026")
ax.set_ylabel("Share of the PI's records\nwith substantive data science")
chosen_n = int(sens.loc[0.5, 2])
fig.suptitle(f"Requiring data science in more than half of a PI's projects identifies {chosen_n:,} data science PIs",
             x=0.02, ha="left", fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING, y=1.2)
fig.text(0.02, 1.14, f"How to read: each cell is the number of PIs who meet both rules, the row's data science share and the\n"
         f"column's minimum records. Boxed = the definition used here. Looser or stricter rules give "
         f"{int(sens.values.min()):,} to {int(sens.values.max()):,} PIs.", ha="left", va="top",
         fontsize=pal.SIZES["axis"], color=pal.MUTED)
for side in ("left", "bottom", "top", "right"):
    ax.spines[side].set_visible(False)
source_note(ax, "Substantive = data science in an aim or the stated approach.\nSource: NIH RePORTER API, FY2016 to FY2026.", y=-0.06)
save(fig, "05_cutoff_sensitivity")

# %% [markdown]
# ## Builders: AI developers and infrastructure builders vs. other data science PIs (matched)
# Each comparison PI is weighted so the comparison group has the tier's mix of portfolio size and first
# data science year (FY2016 to FY2018, FY2019 to FY2021, FY2022 to FY2026).
# - Weighted median = the median of the comparison values, each counted by its weight

# %%
pi["start_band"] = pd.cut(pi.first_ds_fy, [2015, 2018, 2021, 2026], labels=["FY16–18", "FY19–21", "FY22–26"])
pi["stratum"] = pi.size_band.astype(str) + " | " + pi.start_band.astype(str)


def wmedian(v: pd.Series, w: pd.Series) -> float:
    v, w = v.astype(float), w.astype(float)
    ok = v.notna() & (w > 0)
    v, w = v[ok], w[ok]
    if v.empty:
        return np.nan
    o = np.argsort(v.values)
    c = np.cumsum(w.values[o])
    return float(v.values[o][np.searchsorted(c, c[-1] / 2)])


MEASURES = {"papers": "median", "mean_rcr": "median", "patent_linked": "mean", "trial_linked": "mean"}
rows = []
for tier_col, tier_name in [("ai_developer", "AI developer PIs"), ("infra_builder", "Infrastructure builder PIs")]:
    t = pi[pi[tier_col]]
    comp = pi[pi.ds_pi & ~pi[tier_col]]
    tw = t.stratum.value_counts()
    cw = comp.stratum.value_counts()
    w = comp.stratum.map(tw / cw).fillna(0)
    row = {"tier": tier_name, "pis": len(t), "comparison_pis": int((w > 0).sum())}
    for m, how in MEASURES.items():
        row[f"{m}_tier"] = t[m].median() if how == "median" else t[m].mean()
        row[f"{m}_matched_comparison"] = (wmedian(comp[m], w) if how == "median"
                                          else float(np.average(comp[m].astype(float), weights=w)) if w.sum() else np.nan)
    rows.append(row)
builders = pd.DataFrame(rows)
builders.to_csv(OUT / "ds_pis_builders_matched.csv", index=False)
builders.round(3).T

# %%
# Builders by main institute (counts under 11 suppressed)
b_ic = pi[pi.ds_pi].groupby("main_ic").agg(ds_pis=("ds_pi", "sum"), ai_developers=("ai_developer", "sum"),
                                            infra_builders=("infra_builder", "sum"))
for c in b_ic:
    b_ic[c] = b_ic[c].where(b_ic[c] >= SUPPRESS)
b_ic.sort_values("ds_pis", ascending=False).to_csv(OUT / "ds_pis_builders_by_ic.csv")
b_ic.sort_values("ds_pis", ascending=False).head(15)

# %% [markdown]
# ## Software and data papers: outputs that journal counts miss
# Papers in journals that mainly publish software tools or data resources. iCite returns each paper's
# journal; results are cached in `data/interim/icite_journals.parquet`. Without network access this
# step is skipped.
# - Software or data paper share = the PI's linked papers in these journals / all the PI's linked papers

# %%
TOOL_JOURNALS = {"Bioinformatics", "BMC Bioinformatics", "Bioinform Adv", "NAR Genom Bioinform", "J Open Source Softw",
                 "Sci Data", "Database (Oxford)", "Gigascience", "Brief Bioinform"}
jfile = INTERIM / "icite_journals.parquet"
jcache = pd.read_parquet(jfile) if jfile.exists() else pd.DataFrame(columns=["pmid", "journal"])
want = pp[pp.pi.isin(pi.index[pi.ds_pi])].pmid.drop_duplicates()
todo = sorted(set(want.astype(int)) - set(jcache.pmid.astype(int)))
try:
    import requests
    got = []
    for i in range(0, len(todo), 200):
        r = requests.get("https://icite.od.nih.gov/api/pubs",
                         params={"pmids": ",".join(map(str, todo[i:i + 200])), "fl": "pmid,journal"}, timeout=60)
        r.raise_for_status()
        got += r.json().get("data", [])
        if i % 10000 == 0:
            print(f"  iCite journals: {min(i + 200, len(todo)):,} of {len(todo):,}", flush=True)
    if got:
        jcache = pd.concat([jcache, pd.DataFrame(got)[["pmid", "journal"]]], ignore_index=True)
        jcache.to_parquet(jfile, index=False)
except Exception as e:  # no network: use whatever is cached
    print(f"iCite journal lookup skipped ({type(e).__name__}); using {len(jcache):,} cached journals")
if len(jcache):
    jmap = jcache.drop_duplicates("pmid").set_index(jcache.drop_duplicates("pmid").pmid.astype(int)).journal
    pj = pp.assign(journal=pp.pmid.astype(int).map(jmap))
    pj["tool_paper"] = pj.journal.isin(TOOL_JOURNALS)
    share = pj.dropna(subset=["journal"]).groupby("pi").tool_paper.mean()
    pi["other_ds"] = pi.ds_pi & ~pi.ai_developer & ~pi.infra_builder
    groups = [("AI developer PIs", "ai_developer"), ("Infrastructure builder PIs", "infra_builder"),
              ("Other data science PIs", "other_ds")]  # journals are looked up only for data science PIs' papers
    rows_t = []
    for t, c in groups:
        idx = pi.index[pi[c]]
        sh = share.reindex(idx).dropna()
        rows_t.append({"group": t, "pis_with_papers": len(sh), "mean_share_tool_papers": sh.mean(),
                       "share_of_pis_with_any_tool_paper": (sh > 0).mean()})
    tool = pd.DataFrame(rows_t)
    tool.to_csv(OUT / "ds_pis_tool_papers.csv")
    print(tool.round(3).to_string(index=False))

# %% [markdown]
# ## Chart 6. Builders publish fewer papers than matched data science PIs

# %%
fig, ax = plt.subplots(figsize=(8, 3.2))
y = np.arange(len(builders))
tier_colors = {"AI developer PIs": pal.ROLE_COLORS["develops_ai"], "Infrastructure builder PIs": pal.PROJECTS}
for i, r in builders.iterrows():
    c = tier_colors[r.tier]
    ax.barh(i + 0.2, r.papers_tier, 0.4, color=c)
    ax.barh(i - 0.2, r.papers_matched_comparison, 0.4, color=pal.NEUTRAL)
    ax.annotate(f"{r.papers_tier:.0f}", (r.papers_tier, i + 0.2), xytext=(3, 0), textcoords="offset points",
                va="center", color=c, fontweight="bold")
    ax.annotate(f"{r.papers_matched_comparison:.0f} matched data science PIs", (r.papers_matched_comparison, i - 0.2),
                xytext=(3, 0), textcoords="offset points", va="center", color=pal.MUTED, fontsize=pal.SIZES["axis"])
ax.set_yticks(y, [f"{t}\n({n:,})" for t, n in zip(builders.tier, builders.pis)])
ax.set_xlabel("Median linked papers per PI")
ax.set_xlim(0, builders[["papers_tier", "papers_matched_comparison"]].max().max() * 1.5)
diff = (builders.set_index("tier").papers_tier / builders.set_index("tier").papers_matched_comparison - 1)
ai_d, inf_d = diff["AI developer PIs"], diff["Infrastructure builder PIs"]
ax.set_title(f"AI developers have {abs(ai_d):.0%} {'fewer' if ai_d < 0 else 'more'} papers than similar data science "
             f"PIs;\ninfrastructure builders have {abs(inf_d):.0%} {'fewer' if inf_d < 0 else 'more'}", pad=12)
source_note(ax, "AI developer PIs: develop new or improved AI methods in more than half of their project records.\n\n"
            "Infrastructure builder PIs: build research software, analysis or data platforms, data engineering,\n"
            "FAIR data and standards, data management and sharing, or human-derived data linkage\n"
            "in more than half of their records.\n\n"
            "Both groups are data science PIs; 255 PIs are in both.\n\n"
            "Matched data science PIs are weighted to the same portfolio size and first data science year.\n"
            "Source: NIH RePORTER API, ExPORTER publication links.", y=-0.3)
save(fig, "06_builders_papers")
print("Charts saved to", FIG)
