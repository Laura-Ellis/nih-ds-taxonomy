# %% [markdown]
# # Public one-page teasers for the institute gap reports
#
# One page per institute (`analyses/ic_gaps/<ic>.md`) and one figure (`reports/figures/ic_gaps/<ic>.png`), plus an index
# (`analyses/ic_gaps/README.md`). The full reports stay private; the pages show the question, one chart without exact
# values, a few findings with one number, and how to ask for the report.
# Inputs: `reports/internal/ic_gaps/<ic>/teaser.json` (from `deck/ic_gaps/build_ic_gap_slides.py`) and `lens2_mission_areas.csv`.

# %%
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]

R = ROOT / "reports" / "internal" / "ic_gaps"
FIG = ROOT / "reports" / "figures" / "ic_gaps"
PAGES = ROOT / "analyses" / "ic_gaps"
FIG.mkdir(parents=True, exist_ok=True)
ICS = ["NCI", "NHLBI", "NIA", "NIAID", "NICHD", "NIDA", "NIDDK", "NIGMS", "NIMH", "NINDS"]
LI = "https://www.linkedin.com/in/laura-ellis-profile/"
NUM = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "all five"}
pal.use_style()
HI, NEUTRAL, P = "#B06F60", pal.NEUTRAL, pal.PROJECTS


def heatmap(ic, l2):
    """The institute's 10 largest research areas: is data science below its own average, and below the rest of NIH? No values."""
    d = l2.sort_values("cost", ascending=False).head(10).iloc[::-1]
    m = pd.DataFrame({"Below the institute's own average": (d.gap_points < -2).astype(int) + (d.gap_points < -5).astype(int),
                      "Below the rest of NIH": (d.vs_rest_points < -2).astype(int) + (d.vs_rest_points < -5).astype(int)})
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    fig.subplots_adjust(left=0.42, right=0.97, top=0.80, bottom=0.12)
    ax.imshow(m.to_numpy(), cmap=ListedColormap([pal.BG, "#E4BFB5", HI]), vmin=0, vmax=2, aspect="auto")
    ax.set_xticks([0, 1], ["Below its own\naverage", "Below the rest\nof NIH"])
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(d)), [a if len(a) <= 34 else a[:33] + "…" for a in d.area])
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([0.5], minor=True)
    ax.set_yticks([i + 0.5 for i in range(len(d) - 1)], minor=True)
    ax.grid(which="minor", color="white", linewidth=3)
    fig.suptitle(f"Where is data science thin in {ic}'s largest research areas?", x=0.02, ha="left",
                 fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
    fig.text(0.02, 0.02, "Darker = further below (more than 2 or 5 points of data science funding share). Exact values in the full report.\n"
             "Source: NIH RePORTER and ExPORTER, FY2016–FY2025; NIH Data Science Taxonomy.", fontsize=9, color=pal.SOURCE)
    fig.savefig(FIG / f"{ic.lower()}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def page(ic, t, l2):
    g = l2[l2.gap]
    big = l2.sort_values("cost", ascending=False).head(5)
    n_big = int(big.gap.sum())
    hooks = []
    if len(g):
        hooks.append(f"**Data science trails both {ic}'s own average and the rest of NIH in {len(g)} of its research areas"
                     + (f", including {NUM[n_big]} of its five largest.**" if n_big else ".**") + " Which ones, and by how much, is in the report.")
    if t["n_burden_gaps"]:
        hooks.append(f"**Some of the highest-burden diseases {ic} funds get less data science there than elsewhere at NIH.** "
                     "The report names them and sets each against U.S. disability-adjusted life years.")
    else:
        hooks.append(f"**{ic}'s highest-burden diseases get as much data science as elsewhere at NIH.** The report shows where it runs ahead and behind.")
    hooks.append("**New NOFOs that ask for data science come before more data science projects, but not only because of the NOFO.** "
                 "The report shows how much, and what else was going on.")
    lines = [f"# Where is data science thin at {ic}?", "",
             f"**Laura Ellis** · [LinkedIn]({LI}) · FY2016 to FY2025 · [All 10 institutes](README.md) · [Institute profile](../institutes/{ic.lower()}.md)", "",
             f"Data science projects got {t['ds_funding_share']:.0%} of the {t['name']}'s funding from FY2016 to FY2025. I looked for the places where data science is "
             f"thin: compared with the rest of NIH, with {ic}'s own research areas, and with the burden of the diseases it funds.", "",
             f"![Where data science is thin in {ic}'s largest research areas](../../reports/figures/ic_gaps/{ic.lower()}.png)", "",
             "## What I found", ""] + [f"- {h}" for h in hooks] + ["",
             "## Three ways to see a gap", "",
             "1. **Against the rest of NIH.** Does the institute use some data science methods much less often?",
             "2. **Against its own mission.** In which research areas is data science thinner than the institute's own average?",
             "3. **Against disease burden.** Which high-burden diseases get less data science here than at the rest of NIH?", "",
             "## The full report", "",
             f"The full {ic} report (13 slides) adds the methods gap, the disease-burden chart, how data science projects came in (targeted vs. broad NOFOs), "
             "whether new NOFOs draw projects in (an event study), and which levers go with more highly cited papers, patents, and clinical trials. "
             f"It's internal; [message me on LinkedIn]({LI}) if you'd like to see it.", "",
             "## How the methods work, in plain terms", "",
             "- **Gaps:** no model. The share of funding that goes to data science in an area or disease, compared with a benchmark.",
             "- **Disease burden:** each disease is matched to NIH's own categories, then compared with how much healthy life it costs Americans each year (GBD 2023).",
             "- **Data science labels:** keyword rules, then two large language models, decide whether data science is central to a project "
             "([NIH Data Science Taxonomy](../../METHODOLOGY.md)).", ""]
    (PAGES / f"{ic.lower()}.md").write_text("\n".join(lines), encoding="utf-8")


rows = []
for ic in ICS:
    tj = R / ic.lower() / "teaser.json"
    if not tj.exists():
        print("no teaser.json for", ic, "- run deck/ic_gaps/build_ic_gap_slides.py first")
        continue
    t = json.loads(tj.read_text(encoding="utf-8"))
    l2 = pd.read_csv(R / ic.lower() / "lens2_mission_areas.csv")
    heatmap(ic, l2)
    page(ic, t, l2)
    rows.append(f"| [{ic}]({ic.lower()}.md) | {t['name']} | {t['ds_funding_share']:.0%} |")
    print("wrote", ic)

(PAGES / "README.md").write_text("\n".join([
    "# Where is data science thin at NIH's 10 largest institutes?", "",
    f"**Laura Ellis** · [LinkedIn]({LI}) · FY2016 to FY2025", "",
    "For the 10 institutes with the most data science projects, I looked for the places where data science is thin: against the rest of NIH, "
    "against each institute's own research areas, and against disease burden. Each page shows one chart and the headline findings. "
    "The full reports are internal.", "",
    "| Institute | Name | Data science share of funding |", "|---|---|---:|", *rows, "",
    "Code: `ic_gaps.py` (gaps), `nofo_asks.py` and `nofo_panel.py` (NOFOs and projects), `ic_outputs.py` (outputs and levers), `teasers.py` (these pages).", ""]),
    encoding="utf-8")
