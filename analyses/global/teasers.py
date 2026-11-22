# %% [markdown]
# # Public one-page teasers for the institute global reports
#
# One page per institute (`analyses/global/<ic>.md`) and one figure (`reports/figures/global/<ic>.png`), plus an index
# (`analyses/global/README.md`). The full reports stay internal; the pages show the question, one chart without exact
# values, a few findings with one number, and how to ask for the report. Public pages use WHO regions.
# Inputs: `reports/internal/global_ic/<ic>/headline.json` (from `ic_global.py`) and the record tables in `data/interim/`.

# %%
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analyses" / "global"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from regions import iso3, who_region  # noqa: E402

R = ROOT / "reports" / "internal" / "global_ic"
INTERIM = ROOT / "data" / "interim"
FIG = ROOT / "reports" / "figures" / "global"
PAGES = ROOT / "analyses" / "global"
FIG.mkdir(parents=True, exist_ok=True)
ICS = ["NCI", "NHLBI", "NIA", "NIAID", "NICHD", "NIDA", "NIDDK", "NIGMS", "NIMH", "NINDS"]
CODE = {"NCI": "CA", "NHLBI": "HL", "NIA": "AG", "NIAID": "AI", "NICHD": "HD", "NIDA": "DA", "NIDDK": "DK",
        "NIGMS": "GM", "NIMH": "MH", "NINDS": "NS"}
WHO = ["African Region", "Region of the Americas", "European Region", "Western Pacific Region", "South-East Asia Region",
       "Eastern Mediterranean Region"]
LI = "https://www.linkedin.com/in/laura-ellis-profile/"
pal.use_style()
HI, GREY = "#B06F60", "#B9B2A6"

direct = pd.read_parquet(INTERIM / "global_direct_records.parquet")
direct["who"] = direct.country.map(lambda c: who_region(iso3(c)))
sub = pd.read_parquet(INTERIM / "global_subawards.parquet")
sub = sub[sub.foreign & sub.linked].copy()
sub["ds"] = sub.ds.fillna(False).astype(bool)
sub["ds_amount"] = sub.amount.where(sub.ds, 0.0)
sub["who"] = sub.iso3.map(who_region)


def figure(ic):
    """Data science funding abroad by WHO region and route. Bars only: no values."""
    code = CODE[ic]
    a = direct[direct.ic.eq(code)].groupby("who").ds_cost.sum().reindex(WHO).fillna(0)
    b = sub[sub.ic.eq(code)].groupby("who").ds_amount.sum().reindex(WHO).fillna(0)
    order = (a + b).sort_values().index
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    fig.subplots_adjust(left=0.36, right=0.97, top=0.78, bottom=0.14)
    ax.barh(order, a[order], color=GREY, height=0.62, label="Direct awards")
    ax.barh(order, b[order], left=a[order], color=HI, height=0.62, label="Subawards from U.S. partners")
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    fig.suptitle(f"Where does {ic}'s data science funding abroad go, and how?", x=0.02, ha="left",
                 fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
    fig.text(0.02, 0.86, "Data science funding by WHO region, FY2016–FY2026. Exact values in the full report.", fontsize=10, color=pal.MUTED)
    fig.text(0.02, 0.02, "Source: NIH RePORTER API and USAspending.gov sub-grants; NIH Data Science Taxonomy.", fontsize=9, color=pal.SOURCE)
    fig.savefig(FIG / f"{ic.lower()}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return (a + b).idxmax()


def page(ic, h, top_who):
    ab, home = h["share_abroad"], h["share_home"]
    sub_only = h["routes"].get("Subaward only", 0)
    hooks = [f"**U.S. partners carry {h['sub_share']:.0%} of {ic}'s data science funding abroad.** "
             "The report shows which partners, in which countries."]
    hooks.append(f"**{ic} supports data science in {h['n_ds_countries']} countries outside the United States"
                 + (", some of them only through U.S. partners.**" if sub_only else ".**")
                 + f" The largest share goes to the WHO {top_who}; the report maps every country.")
    if ab["n"] >= 30 and ab["lo"] > home["share"]:
        hooks.append(f"**{ic}'s direct foreign awards are more often data science than its projects at home.** "
                     "The report shows by how much, and how that has changed since FY2016.")
    elif ab["n"] >= 30 and ab["hi"] < home["share"]:
        hooks.append(f"**Data science has room to grow in {ic}'s direct foreign awards, compared with its projects at home.** "
                     "The report shows where, and how that has changed since FY2016.")
    else:
        hooks.append(f"**{ic}'s direct foreign awards are about as often data science as its projects at home.** "
                     "The report shows how that has changed since FY2016.")
    lines = [f"# Where does {ic} fund data science abroad?", "",
             f"**Laura Ellis** · [LinkedIn]({LI}) · FY2016 to FY2026 · [All 10 institutes](README.md) · "
             f"[Institute profile](../institutes/{ic.lower()}.md)", "",
             f"The {h['name']} supports data science research outside the United States in two ways: direct awards to "
             f"foreign organizations, and subawards that its U.S. grantees pass to foreign partners. I traced both.", "",
             f"![Where {ic}'s data science funding abroad goes](../../reports/figures/global/{ic.lower()}.png)", "",
             "## What I found", ""] + [f"- {x}" for x in hooks] + ["",
             "## Two ways NIH funding reaches partners abroad", "",
             "1. **Direct awards.** NIH grants to organizations outside the United States (NIH RePORTER).",
             "2. **Subawards.** Money a U.S. grantee passes to a foreign partner, reported to USAspending.gov and linked back to the NIH project.", "",
             "## The full report", "",
             f"The full {ic} report (8 slides) maps every country, splits each region into direct awards and subawards, names the U.S. partners "
             "and foreign institutions that carry the most data science work, compares data science abroad with the institute at home over time, "
             f"and explains the methods. It's internal; [message me on LinkedIn]({LI}) if you'd like to see it.", "",
             "## How the methods work, in plain terms", "",
             "- **Subawards:** USAspending.gov sub-grants, linked to NIH projects by award number. Only subawards of $30,000 or more must be reported, so totals are a floor.",
             "- **Regions:** World Health Organization (WHO) regions.",
             "- **Data science labels:** keyword rules, then two large language models, decide whether data science is central to a project "
             "([NIH Data Science Taxonomy](../../METHODOLOGY.md)). A subaward counts when its NIH project is data science.", ""]
    (PAGES / f"{ic.lower()}.md").write_text("\n".join(lines), encoding="utf-8")


rows = []
for ic in ICS:
    hj = R / ic.lower() / "headline.json"
    if not hj.exists():
        print("no headline.json for", ic, "- run analyses/global/ic_global.py first")
        continue
    h = json.loads(hj.read_text(encoding="utf-8"))
    top = figure(ic)
    page(ic, h, top)
    rows.append(f"| [{ic}]({ic.lower()}.md) | {h['name']} | {h['sub_share']:.0%} |")
    print("wrote", ic)

(PAGES / "README.md").write_text("\n".join([
    "# Where do NIH's institutes fund data science abroad?", "",
    f"**Laura Ellis** · [LinkedIn]({LI}) · FY2016 to FY2026", "",
    "For the 10 institutes in the [opportunity analysis](../ic_gaps/README.md), I traced data science funding outside the United States, "
    "both direct awards to foreign organizations and subawards from U.S. grantees to foreign partners. Each page shows one chart "
    "and the headline findings. The full reports are internal.", "",
    "| Institute | Name | Data science funding abroad through U.S. partners |", "|---|---|---:|", *rows, "",
    "Code: `direct_awards.py` and `subawards.py` (NIH-wide tables), `regions.py` (country lookup), `ic_global.py` (institute tables), "
    "`teasers.py` (these pages).", ""]), encoding="utf-8")
