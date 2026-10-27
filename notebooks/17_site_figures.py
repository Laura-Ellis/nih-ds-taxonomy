# %% [markdown]
# # 17 Figures for the portfolio site
#
# Input: `reports/results/*.csv` from notebook 11. Output: PNGs in `reports/figures/`, copied to the
# site's `images/` folder. Each measure has one fixed color (`src/palette.py`); everything else neutral.
# Highlights come from the data (the largest or highest value), never a fixed institute.
#
# **Definitions**
# - Share of projects = substantive AI (or data science) records / all records active that fiscal year
# - Share of funding = extramural attributed cost of substantive AI records / all extramural attributed cost
# - IC = NIH Institute or Center (administering)
# - The preliminary fiscal year (FY2026) is drawn lighter or dashed: NIH is still adding its records

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import FISCAL_YEARS, PRELIMINARY_FY  # noqa: E402  # pyright: ignore[reportMissingImports]

RES, FIG = ROOT / "reports" / "results", ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
TEXT, SUB = pal.HEADING, pal.MUTED
pal.use_style()
plt.rcParams["figure.dpi"] = 150
FIRST, LAST = min(FISCAL_YEARS), max(FISCAL_YEARS)
YEARS = f"FY{FIRST} to FY{LAST}" + (f" (FY{PRELIMINARY_FY} preliminary)" if PRELIMINARY_FY else "")


def title(ax, text, sub):
    ax.set_title(text, loc="left", pad=30)
    ax.text(0, 1.03, sub, transform=ax.transAxes, fontsize=pal.SIZES["label"], color=SUB, va="bottom")


def source(fig, text=f"Source: NIH RePORTER API, {YEARS}; NIH Data Science Taxonomy labels."):
    fig.text(0.01, 0.01, text, fontsize=pal.SIZES["source"], color=pal.SOURCE)


# %% AI and data science share over time (preliminary year dashed)
t = pd.read_csv(RES / "trend_by_fy.csv")
full = t[~t.preliminary]
fig, ax = plt.subplots(figsize=(9, 5))
for col, name, c, lw, dy in [("ai_share", "AI, share of projects", pal.AI_PROJECTS, 2.5, -0.006),
                             ("ai_cost_share", "AI, share of funding", pal.AI_FUNDING, 2.5, 0.006),
                             ("ds_share", "Data science, share of projects", pal.DATA_SCIENCE, 2, 0)]:
    ax.plot(full.fy, full[col], color=c, lw=lw, solid_capstyle="round")
    if t.preliminary.any():
        tail = t.iloc[-2:]
        ax.plot(tail.fy, tail[col], color=c, lw=lw, ls=(0, (2, 2)))
    ax.text(t.fy.iloc[-1] + 0.2, t[col].iloc[-1] + dy, f"{name} {t[col].iloc[-1]:.1%}", color=c, va="center",
            fontsize=pal.SIZES["axis"])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xticks(t.fy, [f"FY{str(y)[2:]}" + ("*" if p else "") for y, p in zip(t.fy, t.preliminary)])
ax.set_ylim(0, t.ds_share.max() * 1.15)
ax.set_xlim(t.fy.min() - 0.3, t.fy.max() + 3.6)
ax.grid(axis="y", color=pal.GRID, lw=0.8)
title(ax, f"AI projects grew from {full.ai_share.iloc[0]:.1%} to {full.ai_share.iloc[-1]:.1%} of NIH projects "
          f"(FY{full.fy.iloc[0]} to FY{full.fy.iloc[-1]})",
      "Substantive AI and data science, share of project records (all) and of extramural funding")
source(fig, f"*Preliminary (dashed). Source: NIH RePORTER API, FY{FIRST} to FY{LAST}; NIH Data Science Taxonomy labels.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "ai_share_trend.png")

# %% AI funding by institute (top 8): highlight the largest funder and the highest share
ic = pd.read_csv(RES / "ai_by_institute.csv").head(8)
top_cost, top_share = ic.ic.iloc[0], ic.loc[ic.ai_share.idxmax(), "ic"]
ic = ic.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(ic.ic, ic.ai_cost / 1e9, color=[pal.AI_FUNDING if i == top_cost else pal.NEUTRAL for i in ic.ic], height=0.65)
xmax = ic.ai_cost.max() / 1e9
for y, (c, s, name) in enumerate(zip(ic.ai_cost, ic.ai_share, ic.ic)):
    ax.text(c / 1e9 + xmax * 0.01, y, f"${c / 1e9:.1f}B", va="center", fontsize=pal.SIZES["axis"], color=TEXT)
    ax.text(xmax * 1.3, y, f"{s:.1%}", va="center", ha="right", fontsize=pal.SIZES["axis"],
            color=pal.AI_FUNDING if name == top_share else SUB, fontweight="bold" if name == top_share else "normal")
ax.set_ylim(-0.6, len(ic) + 0.5)
ax.text(xmax * 1.3, len(ic) - 0.45, "AI share of the IC's\nextramural funding", ha="right", va="bottom",
        fontsize=pal.SIZES["source"], color=SUB, linespacing=1.4)
ax.set_xlim(0, xmax * 1.32)
ax.set_xticks([])
ax.spines[["bottom", "left"]].set_visible(False)
ax.tick_params(left=False)
title(ax, f"{top_cost} spends the most on AI; {top_share} puts the largest share into it",
      f"Extramural funding for substantive AI projects, FY{FIRST} to FY{LAST}*, top 8 ICs")
source(fig, f"*FY{PRELIMINARY_FY} preliminary. Source: NIH RePORTER API; NIH Data Science Taxonomy labels.")
fig.tight_layout(rect=(0, 0.04, 1, 0.97))
fig.savefig(FIG / "ai_by_institute.png")

# %% Generative AI projects by fiscal year (preliminary year lighter)
g = pd.read_csv(RES / "genai_by_fy.csv")
gf = g[~g.preliminary]
mult = gf.genai_projects.iloc[-1] / gf.loc[gf.fy == 2023, "genai_projects"].iloc[0]
fig, ax = plt.subplots(figsize=(9, 4.5))
colors = [pal.AI_PROJECTS if y >= 2023 else pal.NEUTRAL for y in g.fy]
bars = ax.bar(g.fy, g.genai_projects, color=colors, width=0.65)
for b, p in zip(bars, g.preliminary):
    if p:
        b.set_alpha(0.4)
        b.set_hatch("//")
        b.set_edgecolor(pal.AI_PROJECTS)
for x, v, p in zip(g.fy, g.genai_projects, g.preliminary):
    ax.text(x, v + g.genai_projects.max() * 0.015, f"{v:,}" + ("*" if p else ""), ha="center",
            fontsize=pal.SIZES["axis"], color=TEXT)
ax.set_xticks(g.fy, [f"FY{str(y)[2:]}" for y in g.fy])
ax.set_yticks([])
ax.spines[["left"]].set_visible(False)
title(ax, f"Generative AI projects grew {mult:.1f}× from FY2023 to FY{gf.fy.iloc[-1]}",
      "Substantive AI projects that use generative AI or large language models")
source(fig, f"*Preliminary (hatched). Source: NIH RePORTER API, FY{FIRST} to FY{LAST}; NIH Data Science Taxonomy labels.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "genai_by_fy.png")

# %% Method x research area heatmap
m = pd.read_csv(RES / "ai_method_by_area.csv", index_col=0)
fig, ax = plt.subplots(figsize=(10, 4.8))
z = np.sqrt(m.values / m.values.max())
ax.imshow(z, cmap=plt.matplotlib.colors.LinearSegmentedColormap.from_list("s", [pal.PANEL, pal.AI_PROJECTS]), aspect="auto")
for i in range(m.shape[0]):
    for j in range(m.shape[1]):
        ax.text(j, i, f"{m.values[i, j]:,}", ha="center", va="center", fontsize=pal.SIZES["axis"],
                color="white" if z[i, j] > 0.6 else TEXT)
import textwrap  # noqa: E402
ax.set_xticks(range(m.shape[1]), [textwrap.fill(c.replace(" and ", " & ").replace("Mental & behavioral health", "Mental & behavioral"),
                                                10, break_long_words=False) for c in m.columns], fontsize=pal.SIZES["axis"])
ax.set_yticks(range(m.shape[0]), m.index)
ax.tick_params(length=0)
ax.spines[:].set_visible(False)
cv_top = m.loc["Computer vision"].idxmax() if "Computer vision" in m.index else ""
nlp_top = m.loc["NLP"].idxmax() if "NLP" in m.index else ""
def lc(x):
    return x[:1].lower() + x[1:]


title(ax, f"Vision clusters in {lc(cv_top)}; language processing in {lc(nlp_top)}",
      f"Substantive AI projects by method and research area, FY{FIRST} to FY{LAST}*")
source(fig, f"*FY{PRELIMINARY_FY} preliminary. A project can count in several cells. Source: NIH RePORTER API; "
       "NIH Data Science Taxonomy labels.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "ai_method_area.png")
print("Figures saved to", FIG)
