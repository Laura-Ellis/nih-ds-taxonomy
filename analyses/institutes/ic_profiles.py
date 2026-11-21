# %% [markdown]
# # F. Institute profiles
#
# One profile per NIH institute or center (IC) with at least 500 data science projects, FY2016 to FY2025.
# Every IC gets the same tables, the same four-panel chart, and the same page, so any IC can be compared
# with another or with the rest of NIH. No IC is singled out.
#
# **Questions**
# 1. How did data science grow at the IC, compared with the rest of NIH?
# 2. What brought it there: funding opportunity types, activity codes, training awards, new data science PIs?
# 3. What does the IC's data science work on, and what is rising?
# 4. Where could it do more: research areas (RCDC) where its data science share trails the rest of NIH, and
#    taxonomy categories it funds less often than the rest of NIH?
#
# **Definitions**
# - IC = administering IC. Rest of NIH = every other NIH IC.
# - Project = core project or subproject (one record). Active in a FY = has an application that FY.
# - Data science project = taxonomy label "Y" (substantive data science). AI project = AI label "Y".
# - Data science share (FY) = active data science projects ÷ all active projects. Funding share uses
#   attributed cost.
# - Growth = data science share FY2023–FY2025 ÷ FY2016–FY2018.
# - Route = how a data science application came in: targeted (RFA, PAR), parent or other PA, or none listed.
#   Activity group: R01-type (R01, R37, RF1), other R, cooperative (U), centers (P), training (K, F, T), other.
# - New data science PI = a PI whose first data science record is that FY. Established = had NIH records
#   before their first data science record. Works across ICs = records at more than one IC.
# - Area gap (methods and computing categories such as Data Science and NITRD left out) = IC data science FUNDING share
#   (data science attributed cost ÷ all attributed cost) within an RCDC category − rest-of-NIH data science share in the same
#   category, for categories with at least 100 IC applications. Negative = the IC does less data science in
#   that area than the rest of NIH does.
# - Category ratio = share of the IC's data science projects with a taxonomy category ÷ the same share for
#   the rest of NIH. Below 1 = the IC funds that kind of data science less often.
# - Counts under 11 are suppressed.
#
# Inputs: `exporter_applications.parquet`, `exporter_core_projects_labeled.parquet`, `pi_profiles.parquet`,
# `reports/results/topics_by_ic.csv` (from `analyses/topics/topic_themes.py`),
# `reports/results/ds_pis_builders_by_ic.csv` (from `analyses/ds_pis/ds_pis.py`).
# Outputs: `reports/results/institutes/` (one folder per IC plus `ic_summary.csv` and cross-IC tables),
# `reports/figures/institutes/<ic>.png`, and a page per IC in `analyses/institutes/<ic>.md`.
#
# Run all ICs:      python -u analyses/institutes/ic_profiles.py
# Run one or a few: python -u analyses/institutes/ic_profiles.py --ic NCI NIA
# Redo finished ICs: add --force (otherwise ICs with a finished page are skipped, so a stopped run resumes).

# %%
import argparse
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT_ALL = ROOT / "data" / "processed", ROOT / "reports" / "results"
OUT = OUT_ALL / "institutes"
FIG = ROOT / "reports" / "figures" / "institutes"
PAGES = ROOT / "analyses" / "institutes"
for d in (OUT, FIG, PAGES):
    d.mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST = 2016, 2025
EARLY, LATE = [2016, 2017, 2018], [2023, 2024, 2025]
MIN_DS = 500          # IC needs this many data science projects for a profile
MIN_AREA = 300        # IC applications needed in an RCDC category for an area gap (funding shares are noisy in small areas)
SUPPRESS = 11
SOURCE = "Source: NIH RePORTER API and ExPORTER, FY2016 to FY2025; NIH Data Science Taxonomy."
IC = {"CA": "NCI", "GM": "NIGMS", "AG": "NIA", "AI": "NIAID", "HL": "NHLBI", "MH": "NIMH", "NS": "NINDS",
      "HD": "NICHD", "DK": "NIDDK", "DA": "NIDA", "EB": "NIBIB", "HG": "NHGRI", "ES": "NIEHS", "EY": "NEI",
      "AR": "NIAMS", "OD": "OD", "DC": "NIDCD", "LM": "NLM", "AA": "NIAAA", "TR": "NCATS", "MD": "NIMHD",
      "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH", "RR": "NCRR"}
NAME = {"NCI": "National Cancer Institute", "NIGMS": "National Institute of General Medical Sciences",
        "NIA": "National Institute on Aging", "NIAID": "National Institute of Allergy and Infectious Diseases",
        "NHLBI": "National Heart, Lung, and Blood Institute", "NIMH": "National Institute of Mental Health",
        "NINDS": "National Institute of Neurological Disorders and Stroke",
        "NICHD": "Eunice Kennedy Shriver National Institute of Child Health and Human Development",
        "NIDDK": "National Institute of Diabetes and Digestive and Kidney Diseases",
        "NIDA": "National Institute on Drug Abuse", "NIBIB": "National Institute of Biomedical Imaging and Bioengineering",
        "NHGRI": "National Human Genome Research Institute", "NIEHS": "National Institute of Environmental Health Sciences",
        "NEI": "National Eye Institute", "NIAMS": "National Institute of Arthritis and Musculoskeletal and Skin Diseases",
        "OD": "NIH Office of the Director", "NIDCD": "National Institute on Deafness and Other Communication Disorders",
        "NLM": "National Library of Medicine", "NIAAA": "National Institute on Alcohol Abuse and Alcoholism",
        "NCATS": "National Center for Advancing Translational Sciences",
        "NIMHD": "National Institute on Minority Health and Health Disparities",
        "NIDCR": "National Institute of Dental and Craniofacial Research", "NINR": "National Institute of Nursing Research",
        "NCCIH": "National Center for Complementary and Integrative Health"}
# RCDC categories that describe methods or computing, not a disease or research area; data science is part of
# their definition, so comparing data science shares inside them says little about where an IC could do more
METHOD_AREAS = {"Data Science", "Networking and Information Technology R&D (NITRD)", "Networking and Information Technology R&D",
                "Machine Learning and Artificial Intelligence", "Bioengineering", "Biotechnology"}
ROUTES = ["Targeted (RFA, PAR)", "Parent or other PA", "None listed"]
ACTS = ["R01-type", "Other R", "Cooperative (U)", "Centers (P)", "Training (K, F, T)", "Other"]
pal.use_style()
_stop = None


def stage(name):
    global _stop
    if _stop:
        _stop()
    _stop = start(name)


def route(n):
    n = str(n or "").upper()
    return "Targeted (RFA, PAR)" if n.startswith(("RFA", "PAR")) else "Parent or other PA" if n.startswith("PA") else "None listed"


def act_group(a):
    a = str(a or "")
    return ("R01-type" if a in ("R01", "R37", "RF1") else "Other R" if a.startswith("R") else "Cooperative (U)" if a.startswith("U")
            else "Centers (P)" if a.startswith("P") else "Training (K, F, T)" if a[:1] in ("K", "F", "T") else "Other")


def sup(n):
    """Suppress small counts."""
    return np.nan if n < SUPPRESS else n


# %% [markdown]
# ## Load once (the slow part)

# %%
ap = argparse.ArgumentParser()
ap.add_argument("--ic", nargs="*", help="IC acronyms to run (default: all with enough data science projects)")
ap.add_argument("--force", action="store_true", help="redo ICs that already have a page")
args = ap.parse_args([] if "ipykernel" in sys.modules else None)

stage("loading applications")
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "administering_ic", "activity", "nofo", "nih_spending_cats", "attributed_cost", "pi_ids"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["ds_label", "ai_label", "ai_role", "categories", "administering_ic"])
# same count as the topic charts: data science records per administering IC, all years
ds_by_ic = core[core.ds_label.eq("Y")].administering_ic.map(IC).value_counts()
core = core.drop(columns="administering_ic")
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy, errors="coerce")
a = a[a.fy.between(FY_FIRST, FY_LAST)].copy()
a["ic"] = a.administering_ic.map(IC)
a = a[a.ic.notna()].copy()                                   # NIH ICs only
a["record"] = a.core_project_number + "|" + a.subproject_id.fillna("").astype(str)
a["ds"], a["ai"] = a.ds_label.eq("Y"), a.ai_label.eq("Y")
a["cost"] = a.attributed_cost.fillna(0)
a["route"] = a.nofo.fillna("").astype(str).map(route)
a["act"] = a.activity.fillna("").astype(str).map(act_group)
say(f"{len(a):,} NIH applications FY{FY_FIRST}–FY{FY_LAST}; {a[a.ds].record.nunique():,} data science projects")

ics = [i for i in ds_by_ic.index if ds_by_ic[i] >= MIN_DS]
if args.ic:
    unknown = set(args.ic) - set(ics)
    if unknown:
        say(f"skipping {sorted(unknown)}: not an NIH IC with at least {MIN_DS} data science projects")
    ics = [i for i in ics if i in args.ic]
say(f"{len(ics)} ICs to profile: {', '.join(ics)}")

stage("RCDC categories")
a["cats"] = a.nih_spending_cats.fillna("").str.split(";")
cat_long = a[["ic", "record", "ds", "cats"]].explode("cats")
cat_long["cats"] = cat_long.cats.str.strip()
cat_long = cat_long[cat_long.cats.ne("")].drop_duplicates(["ic", "record", "cats"])
# per IC and category: projects and data science projects (once per project)
area = cat_long.groupby(["ic", "cats"]).agg(projects=("record", "nunique"),
                                            ds_projects=("ds", "sum")).reset_index()
# funding: attributed cost of every application in the category (an application counts in each of its categories)
cost_long = a[["ic", "ds", "cost", "cats"]].explode("cats")
cost_long["cats"] = cost_long.cats.str.strip()
cost_long = cost_long[cost_long.cats.ne("")]
cost_long["ds_cost"] = cost_long.cost.where(cost_long.ds, 0)
area = area.merge(cost_long.groupby(["ic", "cats"])[["cost", "ds_cost"]].sum().reset_index(), on=["ic", "cats"], how="left")
area_all = area.groupby("cats")[["projects", "ds_projects", "cost", "ds_cost"]].sum()

stage("taxonomy categories")
dsp = a[a.ds].drop_duplicates("record")[["record", "ic", "categories"]]
tax_long = dsp.assign(cat=dsp.categories.fillna("").str.split(";")).explode("cat")
tax_long["cat"] = tax_long.cat.str.strip()
tax_long = tax_long[tax_long.cat.ne("")]
tax_n = tax_long.groupby(["ic", "cat"]).record.nunique().rename("n").reset_index()
ds_n_ic = dsp.groupby("ic").record.nunique()

stage("PIs")
pi = pd.read_parquet(PROCESSED / "pi_profiles.parquet")
pi_ds = pi[pi.ds_pi.fillna(False).astype(bool)].copy()
pi_ds["established"] = pi_ds.first_fy < pi_ds.first_ds_fy
pi_ds["across_ics"] = pi_ds.n_ics > 1
builders = pd.read_csv(OUT_ALL / "ds_pis_builders_by_ic.csv").set_index("main_ic") \
    if (OUT_ALL / "ds_pis_builders_by_ic.csv").exists() else pd.DataFrame()
topics = pd.read_csv(OUT_ALL / "topics_by_ic.csv") if (OUT_ALL / "topics_by_ic.csv").exists() else pd.DataFrame()

# %% [markdown]
# ## One IC at a time

# %%
def share_by_fy(frame):
    g = frame.groupby("fy")
    t = pd.DataFrame({"projects": g.record.nunique(),
                      "ds_projects": frame[frame.ds].groupby("fy").record.nunique(),
                      "ai_projects": frame[frame.ai].groupby("fy").record.nunique(),
                      "cost": g.cost.sum(), "ds_cost": frame[frame.ds].groupby("fy").cost.sum()}).fillna(0)
    t["ds_share"], t["ai_share"], t["ds_cost_share"] = t.ds_projects / t.projects, t.ai_projects / t.projects, t.ds_cost / t.cost
    return t


def mix(frame, col, levels):
    f = frame[frame.ds].drop_duplicates(["record", "fy"])
    return f[col].value_counts(normalize=True).reindex(levels).fillna(0)


def profile(ic):
    out = OUT / ic.lower()
    out.mkdir(exist_ok=True)
    mine, rest = a[a.ic == ic], a[a.ic != ic]

    # 1. growth
    tr = share_by_fy(mine).add_prefix("ic_").join(share_by_fy(rest).add_prefix("rest_"))
    tr.to_csv(out / "trend.csv")
    g_ic = tr.loc[LATE, "ic_ds_share"].mean() / tr.loc[EARLY, "ic_ds_share"].mean()
    g_rest = tr.loc[LATE, "rest_ds_share"].mean() / tr.loc[EARLY, "rest_ds_share"].mean()

    # 2. routes, activity groups, PIs
    routes = pd.DataFrame({"ic": mix(mine, "route", ROUTES), "rest_of_nih": mix(rest, "route", ROUTES)})
    acts = pd.DataFrame({"ic": mix(mine, "act", ACTS), "rest_of_nih": mix(rest, "act", ACTS)})
    routes.to_csv(out / "routes.csv")
    acts.to_csv(out / "activity_groups.csv")
    p = pi_ds[pi_ds.main_ic == ic]
    per = pd.cut(p.first_ds_fy, [0, 2018, 2021, 2025], labels=["FY2016–18 or earlier", "FY2019–21", "FY2022–25"])
    new = per.value_counts().reindex(["FY2016–18 or earlier", "FY2019–21", "FY2022–25"], fill_value=0).map(sup)
    new.rename("new_ds_pis").to_csv(out / "new_ds_pis.csv")
    b = builders.loc[ic] if ic in builders.index else pd.Series(dtype=float)

    # 3. topics
    tp = topics[topics.ic == ic].copy() if len(topics) else pd.DataFrame()
    rising = tp[(tp.projects >= 30) & (tp.growth > 1)].sort_values("growth", ascending=False).head(6) if len(tp) else tp
    themes = tp.groupby("theme").share_late.sum().sort_values(ascending=False).head(6) if len(tp) else pd.Series(dtype=float)
    rising.to_csv(out / "rising_topics.csv", index=False)

    # 4. where to improve
    ar = area[(area.ic == ic) & (area.projects >= MIN_AREA) & ~area.cats.isin(METHOD_AREAS)].set_index("cats")
    rest_area = area_all.loc[ar.index] - ar[["projects", "ds_projects", "cost", "ds_cost"]]
    # gaps use funding shares (data science dollars ÷ all dollars in the area); project shares kept for reference
    ar = ar.assign(ic_ds_share=ar.ds_cost / ar.cost, rest_ds_share=rest_area.ds_cost / rest_area.cost,
                   ic_ds_project_share=ar.ds_projects / ar.projects, rest_ds_project_share=rest_area.ds_projects / rest_area.projects)
    ar["gap_points"] = (ar.ic_ds_share - ar.rest_ds_share) * 100
    ar = ar.sort_values("gap_points")
    ar.assign(ds_projects=ar.ds_projects.map(sup)).to_csv(out / "area_gaps.csv")
    tx_ic = tax_n[tax_n.ic == ic].set_index("cat").n
    tx_rest = tax_n[tax_n.ic != ic].groupby("cat").n.sum()
    cats = (pd.DataFrame({"ic_share": tx_ic / ds_n_ic[ic], "rest_share": tx_rest / (ds_n_ic.sum() - ds_n_ic[ic])})
            .fillna(0).query("rest_share >= 0.01"))
    cats["ratio"] = cats.ic_share / cats.rest_share
    cats = cats.sort_values("ratio")
    cats.to_csv(out / "taxonomy_categories.csv")

    row = {"ic": ic, "name": NAME.get(ic, ic), "ds_projects": int(ds_by_ic[ic]),
           "ds_share_late": tr.loc[LATE, "ic_ds_share"].mean(), "rest_ds_share_late": tr.loc[LATE, "rest_ds_share"].mean(),
           "rest_ds_cost_share_late": tr.loc[LATE, "rest_ds_cost_share"].mean(),
           "ds_cost_share_late": tr.loc[LATE, "ic_ds_cost_share"].mean(), "ai_share_late": tr.loc[LATE, "ic_ai_share"].mean(),
           "growth": g_ic, "rest_growth": g_rest,
           **{f"route: {k}": v for k, v in routes.ic.items()}, **{f"activity: {k}": v for k, v in acts.ic.items()},
           "ds_pis": sup(len(p)), "established_share": p.established.mean() if len(p) else np.nan,
           "across_ics_share": p.across_ics.mean() if len(p) else np.nan,
           "ai_developers": sup(b.get("ai_developers", np.nan)) if len(b) else np.nan,
           "infra_builders": sup(b.get("infra_builders", np.nan)) if len(b) else np.nan,
           "top_theme": themes.index[0] if len(themes) else "", "top_riser": rising.name.iloc[0] if len(rising) else "",
           "top_riser_growth": rising.growth.iloc[0] if len(rising) else np.nan,
           "weakest_area": ar.index[0] if len(ar) else "", "weakest_area_gap": ar.gap_points.iloc[0] if len(ar) else np.nan,
           "rarest_category": cats.index[0] if len(cats) else "", "rarest_category_ratio": cats.ratio.iloc[0] if len(cats) else np.nan}
    chart(ic, tr, routes, rising, ar)
    page(ic, row, routes, acts, rising, themes, ar, cats, new)
    return row, themes.rename(ic)


# %% [markdown]
# ## Chart and page

# %%
def chart(ic, tr, routes, rising, ar):
    fig, axs = plt.subplots(2, 2, figsize=(13, 9))
    fig.subplots_adjust(left=0.2, right=0.97, top=0.88, bottom=0.12, wspace=0.75, hspace=0.55)
    ax = axs[0, 0]
    ax.plot(tr.index, tr.ic_ds_share * 100, color=pal.PROJECTS, lw=2.2, label=f"{ic}, projects")
    ax.plot(tr.index, tr.ic_ds_cost_share * 100, color=pal.PROJECTS, lw=2.2, ls="--", label=f"{ic}, funding")
    ax.plot(tr.index, tr.rest_ds_share * 100, color=pal.NEUTRAL, lw=2.2, label="Rest of NIH, projects")
    ax.plot(tr.index, tr.rest_ds_cost_share * 100, color=pal.NEUTRAL, lw=2.2, ls="--", label="Rest of NIH, funding")
    ax.set_ylim(0, min(100, max(tr.ic_ds_share.max(), tr.rest_ds_share.max(), tr.ic_ds_cost_share.max(), tr.rest_ds_cost_share.max()) * 118))
    ax.set_ylabel("% of active projects")
    ax.set_title("Data science share of projects and funding", loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)
    ax.legend(frameon=False, loc="lower right", fontsize=pal.SIZES["axis"] - 1, ncol=2)

    ax = axs[0, 1]
    y = np.arange(len(ROUTES))
    ax.barh(y - 0.2, routes.ic * 100, 0.38, color=pal.PROJECTS, label=ic)
    ax.barh(y + 0.2, routes.rest_of_nih * 100, 0.38, color=pal.NEUTRAL, label="Rest of NIH")
    for yy, v in zip(y - 0.2, routes.ic * 100):
        ax.annotate(f"{v:.0f}%", (v, yy), xytext=(3, 0), textcoords="offset points", va="center", fontsize=pal.SIZES["axis"])
    ax.set_yticks(y, ROUTES)
    ax.invert_yaxis()
    ax.set_xlabel("% of data science applications")
    ax.set_title("How data science came in", loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)
    ax.legend(frameon=False, loc="lower right", fontsize=pal.SIZES["axis"])

    ax = axs[1, 0]
    if len(rising):
        r = rising[::-1]
        ax.barh(r.name, r.growth.clip(upper=4), color=pal.PROJECTS)
        for i, v in enumerate(r.growth):
            ax.annotate(f"{v:.1f}×", (min(v, 4), i), xytext=(3, 0), textcoords="offset points", va="center",
                        fontsize=pal.SIZES["axis"])
        ax.axvline(1, color=pal.MUTED, lw=0.8, ls=":")
    ax.set_xlabel(f"Growth in share, FY{LATE[0]}–{LATE[-1]} ÷ FY{EARLY[0]}–{EARLY[-1]}")
    ax.set_title("Fastest-rising topics (at least 30 projects)", loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)

    ax = axs[1, 1]
    w = ar[ar.gap_points < 0].head(6)[::-1]
    if len(w):
        ax.barh(w.index, w.gap_points, color=pal.NEUTRAL)
        for i, (v, s) in enumerate(zip(w.gap_points, w.ic_ds_share)):
            ax.annotate(f"{s:.0%} here", (0, i), xytext=(4, 0), textcoords="offset points", va="center",
                        fontsize=pal.SIZES["axis"], color=pal.MUTED)
        ax.axvline(0, color=pal.MUTED, lw=0.8)
    ax.set_xlabel("Data science funding share vs. rest of NIH (points)")
    ax.set_title("Areas where data science trails the rest of NIH", loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)

    fig.suptitle(f"Data science at {ic}", x=0.02, ha="left", fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
    fig.text(0.02, 0.005, f"Administering IC. Areas = RCDC categories with at least {MIN_AREA} {ic} applications; "
             "'% here' = data science share of the IC's funding in that area.\n" + SOURCE,
             fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")
    fig.savefig(FIG / f"{ic.lower()}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def pct(v, d=0):
    return "suppressed" if pd.isna(v) else f"{v * 100:.{d}f}%"


LINKS = ROOT / "reports" / "results" / "nofo_links_by_institute.csv"
LINK_COLS = [("Targeted NOFO (RFA, PAR)", "Targeted call listed"), ("Researcher-initiated, strong fit", "Broad call: strong fit"),
             ("Researcher-initiated, weak fit", "Broad call: weak fit"), ("Not through a NOFO (intramural, VA, contract)",
                                                              "No funding call (intramural, VA, contract)")]


def call_links(ic):
    """Call-link lines for the IC page, from analyses/topics/nofo_link_ltr.py (skipped if not run yet)."""
    if not LINKS.exists():
        return []
    from nofo_rank import IC as IC_CODE  # pyright: ignore[reportMissingImports]
    code = IC_CODE.get(ic, ic)
    t = pd.read_csv(LINKS).set_index("administering_ic")
    if code not in t.index:
        return []
    cols = [c for _, c in LINK_COLS]
    mine, alln = t.loc[code, cols], t[cols].sum()
    mine, alln = mine / mine.sum(), alln / alln.sum()
    lk = pd.read_csv(ROOT / "reports" / "results" / "nofo_links.csv", usecols=["administering_ic", "fit", "call_1", "call_1_title"])
    top = lk[(lk.administering_ic == code) & (lk.fit == "Strong fit")].groupby(["call_1", "call_1_title"]).size()
    top = top[top >= 11].sort_values(ascending=False).head(3)
    out = ["### Linking projects to NOFOs", "",
           "Every grant record names the NOFO (notice of funding opportunity) it answered. For researcher-initiated projects, which name only a broad NOFO such as the parent R01, a ranking model "
           "found the targeted NOFO each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-nofo)). "
           "Weak fit = no targeted NOFO comes close, so that data science came in without a NOFO that asked for it. "
           "Shares of data science projects.", "",
           f"| NOFO on the grant record | {ic} | All NIH |", "|---|---:|---:|",
           *[f"| {lab} | {pct(mine[c])} | {pct(alln[c])} |" for lab, c in LINK_COLS], ""]
    if len(top):
        out += ["Targeted NOFOs its researcher-initiated projects fit best (strong fits, 11 or more projects): " +
                "; ".join(f"{c} ({str(tt)[:80]}, {n})" for (c, tt), n in top.items()) + ".", ""]
    return out


def page(ic, r, routes, acts, rising, themes, ar, cats, new):
    trail = ar[ar.gap_points < 0].head(5)
    lead = ar.sort_values("gap_points", ascending=False).head(3)
    rare = cats.head(5)
    n_pis = "suppressed" if pd.isna(r["ds_pis"]) else f"{int(r['ds_pis']):,}"
    lines = [
        f"# Data science at the {NAME.get(ic, ic)} ({ic})", "",
        "**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · "
        f"FY{FY_FIRST} to FY{FY_LAST}, administering IC · [All institutes](README.md) · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)", "",
        f"{ic} funded {r['ds_projects']:,} data science projects from FY{FY_FIRST} to FY{FY_LAST}. "
        f"In FY{LATE[0]} to FY{LATE[-1]}, {pct(r['ds_share_late'])} of its projects used data science, "
        f"compared with {pct(r['rest_ds_share_late'])} for the rest of NIH. By funding, data science was "
        f"{pct(r['ds_cost_share_late'])} of its dollars, compared with {pct(r['rest_ds_cost_share_late'])} for the rest of NIH. "
        "Funding shares run higher because data science projects tend to be larger awards.", "",
        f"Its share grew {r['growth']:.1f} times since FY{EARLY[0]} to FY{EARLY[-1]}; the rest of NIH grew {r['rest_growth']:.1f} times.", "",
        "Terms are defined in the [glossary](#glossary) at the end.", "",
        f"![Data science at {ic}](../../reports/figures/institutes/{ic.lower()}.png)", "",
        "## How data science came in", "", "Most projects answer a NOFO (notice of funding opportunity). Targeted NOFOs (RFAs and PARs) ask for work in an area; broad NOFOs (PAs), such as the parent R01, let the researcher pick the topic.", "",
        "| Route | " + ic + " | Rest of NIH |", "|---|---:|---:|",
        *[f"| {k} | {pct(routes.ic[k])} | {pct(routes.rest_of_nih[k])} |" for k in ROUTES], "",
        "| Activity group | " + ic + " | Rest of NIH |", "|---|---:|---:|",
        *[f"| {k} | {pct(acts.ic[k])} | {pct(acts.rest_of_nih[k])} |" for k in ACTS], "",
        *call_links(ic),
        f"{ic} is the main institute for {n_pis} data science PIs. "
        f"{pct(r['established_share'])} had NIH projects before their first data science project. "
        f"{pct(r['across_ics_share'])} have projects at more than one institute.", "",
        "Data science PIs by when they started data science: " +
        ", ".join(f"{k} {'under 11' if pd.isna(n) else int(n)}" for k, n in new.items()) +
        ". FY2016 is the first year in the data, so earlier starts count there.", "",
        "## What it works on", "",
        "Largest themes, FY2023 to FY2025 (share of the IC's data science projects): " +
        "; ".join(f"{t} ({v:.0%})" for t, v in themes.items()) + ".", "",
        "Fastest-rising topics: " + "; ".join(f"{t.name} ({t.growth:.1f}×)" for t in rising.itertuples()) + ".", "",
        "## Where it could do more", "",
        f"These research areas are where {ic} puts a smaller share of its funding into data science than the rest of NIH does in the same area. "
        f"Areas come from NIH's RCDC categories; each has at least {MIN_AREA} {ic} applications.", "",
        "| Area | " + ic + " data science share of funding | Rest of NIH | Difference (points) |", "|---|---:|---:|---:|",
        *[f"| {k} | {pct(v.ic_ds_share)} | {pct(v.rest_ds_share)} | {v.gap_points:.1f} |" for k, v in trail.iterrows()], "",
        "Where it leads: " + "; ".join(f"{k} (+{v.gap_points:.1f})" for k, v in lead.iterrows()) + ".", "",
        f"Kinds of data science {ic} funds least often compared with the rest of NIH "
        "(1 = as often, 0.5 = half as often): " + "; ".join(f"{k.replace('_', ' ')} ({v.ratio:.2f})" for k, v in rare.iterrows()) + ".", "",
        "## Method and limits", "",
        "Projects are counted once per fiscal year they are active; the administering IC gets the whole project. "
        "Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the "
        "IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are "
        f"suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/{ic.lower()}/`.", "",
        "**Source:** NIH RePORTER API and ExPORTER, FY2016 to FY2025; NIH Data Science Taxonomy.", "",
        "## Glossary", "",
        "| Term | Meaning |", "|---|---|",
        "| Activity group | The kind of award: R01-type research grants, other R grants, cooperative agreements (U), centers (P), training (K, F, T) |",
        "| Administering institute | The NIH institute or center that manages a project |",
        "| Data science project | An NIH project whose aims or approach rely on data science, per the NIH Data Science Taxonomy |",
        "| Data science PI | A PI with 2 or more project records, more than half with substantive data science |",
        "| Growth | Data science share in FY2023–25 ÷ share in FY2016–18 |",
        "| NOFO | Notice of funding opportunity: NIH's public request for grant proposals. RFA and PAR = targeted (NIH asks for a topic); PA = broad, such as the parent R01 (the researcher picks) |",
        "| PI | Principal investigator: a person who leads an NIH-funded project |",
        "| RCDC | NIH's research, condition, and disease categories, used to tag every project |",
        "| Rest of NIH | Every other NIH institute and center |", "",
        "## How the methods work, in plain terms", "",
        "- **Counts and shares, no model.** Each project counts once in every year it's active, under the institute that manages it. "
        "Data science share = data science projects ÷ all projects; growth = share now ÷ share in FY2016–18.",
        "- **Data science labels.** Projects are tagged by the NIH Data Science Taxonomy: keyword rules first, then two large "
        "language models (AI systems that read text) that decide whether data science is central to the project.",
        "- **Themes and rising topics.** A topic-grouping method (BERTopic) sorts project summaries into groups that share "
        "meaning, like sorting mail by subject when nothing is labeled.",
        "- **Area gaps.** For each research area, the institute's data science share of funding minus the rest of NIH's share in the same area. "
        "Negative means the institute does less data science there.",
        "- **NOFO links.** A ranking model (LightGBM LambdaMART) looks at 150 candidate NOFOs for each project and sorts them so the "
        "best fit comes first. It's built from 300 small decision trees, each a short chain of yes-or-no questions (\"Does the NOFO allow "
        "this grant type?\"), and it finds a project's actual NOFO in the top 10 for 95% of projects whose NOFO we know.", ""]
    (PAGES / f"{ic.lower()}.md").write_text("\n".join(lines), encoding="utf-8")


# %% [markdown]
# ## Run

# %%
rows, theme_cols = [], []
summary_path = OUT / "ic_summary.csv"
old = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
for k, ic in enumerate(ics, 1):
    if not args.force and (PAGES / f"{ic.lower()}.md").exists() and len(old) and ic in set(old.ic):
        say(f"[{k}/{len(ics)}] {ic}: done earlier, skipped (use --force to redo)")
        continue
    stage(f"[{k}/{len(ics)}] {ic}")
    row, th = profile(ic)
    rows.append(row)
    theme_cols.append(th)
    # save after each IC so a stopped run keeps what it finished
    cur = pd.DataFrame(rows)
    allrows = pd.concat([old[~old.ic.isin(cur.ic)] if len(old) else old, cur], ignore_index=True)
    allrows.sort_values("ds_projects", ascending=False).to_csv(summary_path, index=False)

if theme_cols:
    hm_path = OUT / "ic_themes.csv"
    hm_old = pd.read_csv(hm_path, index_col=0) if hm_path.exists() else pd.DataFrame()
    hm = pd.concat(theme_cols, axis=1)
    hm = pd.concat([hm_old.drop(columns=[c for c in hm.columns if c in hm_old.columns], errors="ignore"), hm], axis=1)
    hm.to_csv(hm_path)

# index page for the IC pages
if not summary_path.exists():
    say("no ICs profiled; nothing to index")
    sys.exit()
summ = pd.read_csv(summary_path).sort_values("ds_projects", ascending=False)
idx = ["# Data science at each NIH institute", "",
       "**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · "
       f"FY{FY_FIRST} to FY{FY_LAST} · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)", "",
       "For each NIH institute or center, how did data science grow, what brought it there, and where could it do more? "
       f"Profiles cover institutes and centers with at least {MIN_DS} data science projects. Every profile uses the same layout. "
       "The findings across institutes, and how the methods work, are in [Across institutes](institutes_analysis.md).", "",
       "| Institute or center | Data science projects | Data science share, FY2023–25 | Growth since FY2016–18 |",
       "|---|---:|---:|---:|",
       *[f"| [{r.ic}]({r.ic.lower()}.md): {r.name} | {r.ds_projects:,} | {r.ds_share_late:.1%} | {r.growth:.1f}× |"
         for r in summ.itertuples()], "",
       f"Rest of NIH comparisons exclude the institute itself. {SOURCE}", ""]
(PAGES / "README.md").write_text("\n".join(idx), encoding="utf-8")
if _stop:
    _stop()
say(f"done: {len(rows)} ICs profiled this run; pages in analyses/institutes/, tables in reports/results/institutes/")
