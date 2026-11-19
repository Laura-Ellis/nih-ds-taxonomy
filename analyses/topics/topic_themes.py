# %% [markdown]
# # B1b. Topic names, themes, and institute views
#
# Reads the saved results of `topics.py` (no refitting) and adds:
# - a readable name and a theme for each of the 112 BERTopic topics (`analyses/topics/topic_names.csv`,
#   named by hand from each topic's top words; edit the file and rerun to change them)
# - shares and trends for about 25 themes, for slide 2 ("what data science works on")
# - the fastest-rising named topics, for slide 3
# - the same view inside each institute, two institutes per chart, so a rise driven by one institute's
#   funding (for example NIA and dementia) shows up as that institute's, not as all of NIH's
#
# **Definitions** (same as `topics.py`)
# - Share (FY) = active data science projects in the topic or theme ÷ all active data science projects that FY
#   (inside an institute: ÷ the institute's active data science projects)
# - Growth = mean share FY2023–FY2025 ÷ mean share FY2016–FY2018; trend test = Kendall's τ, FY2016–FY2025
# - Fast riser = growth ≥ 1.5, τ > 0 with p < 0.05, and at least `MIN_PROJECTS` projects (`MIN_IC_PROJECTS`
#   inside an institute)
# - Institute = administering institute; non-NIH agencies in RePORTER (VA, FDA, AHRQ, CDC) are left out
#
# Inputs: `data/interim/topic_assignments.parquet`, `reports/results/topics_trends.csv`,
# `exporter_core_projects_labeled.parquet`, `analyses/topics/topic_names.csv`.
# Outputs: `reports/results/topics_named.csv`, `topics_themes_by_fy.csv`, `topics_themes_trends.csv`,
# `topics_by_ic.csv`; `reports/figures/topics/04_*.png` to `07_*.png` and `ic/*.png`.

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "topics"
(FIG / "ic").mkdir(parents=True, exist_ok=True)
FY_FIRST, FY_LAST_FULL = 2016, 2025
EARLY, LATE = [2016, 2017, 2018], [2023, 2024, 2025]
MIN_PROJECTS, MIN_IC_PROJECTS, MIN_IC_DS = 100, 30, 500
CAP = 4.0   # growth axis cap on the rising chart; longer bars are labeled
IC_CODE = {"CA": "NCI", "AI": "NIAID", "HL": "NHLBI", "OD": "OD", "AG": "NIA", "GM": "NIGMS", "MH": "NIMH",
           "TR": "NCATS", "NS": "NINDS", "LM": "NLM", "DA": "NIDA", "HG": "NHGRI", "DK": "NIDDK", "HD": "NICHD",
           "ES": "NIEHS", "EB": "NIBIB", "EY": "NEI", "AR": "NIAMS", "DC": "NIDCD", "AA": "NIAAA", "MD": "NIMHD",
           "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH", "TW": "FIC"}
SOURCE = "Source: NIH RePORTER API; NIH Data Science Taxonomy. Topics from BERTopic on sentence embeddings."
pal.use_style()


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def title(fig, text):
    fig.suptitle(text, x=0.02, ha="left", fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")


def note(fig, text):
    fig.text(0.02, 0.005, text, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")

# %% [markdown]
# ## Projects, topics, names, fiscal years

# %%
key = ["core_project_number", "subproject_id"]
asg = pd.read_parquet(INTERIM / "topic_assignments.parquet")
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["fiscal_years", "administering_ic"])
names = pd.read_csv(Path(__file__).resolve().parent / "topic_names.csv" if "__file__" in globals()
                    else ROOT / "analyses" / "topics" / "topic_names.csv")
d = asg.merge(core, on=key, how="left").merge(names, left_on="bt_topic", right_on="topic", how="left")
missing = d.name.isna().sum()
assert missing == 0, f"{missing} projects have a topic not in topic_names.csv"
d["ic"] = d.administering_ic.map(IC_CODE)
d["fys"] = d.fiscal_years.astype(str).str.findall(r"\d{4}").map(lambda ys: sorted({int(y) for y in ys}))
y = d[["ic", "name", "theme", "fys"]].explode("fys").dropna(subset=["fys"]).rename(columns={"fys": "fy"})
y["fy"] = y.fy.astype(int)
y = y[y.fy.between(FY_FIRST, FY_LAST_FULL)]
FULL = list(range(FY_FIRST, FY_LAST_FULL + 1))
print(f"{len(d):,} projects; {d.theme.nunique()} themes; {d.name.nunique()} topics")


def trends(frame, col, base, min_n, n_projects):
    """Share by FY within `base` groups, growth, and Kendall's tau for each value of `col`."""
    active = frame.groupby(base + ["fy"]).size()
    s = frame.groupby(base + [col, "fy"]).size().div(active).rename("share").reset_index()
    wide = s.pivot_table(index=base + [col], columns="fy", values="share", fill_value=0).reindex(columns=FULL, fill_value=0)
    out = pd.DataFrame(index=wide.index)
    out["projects"] = n_projects.reindex(out.index).fillna(0).astype(int)
    out["share_early"], out["share_late"] = wide[EARLY].mean(axis=1), wide[LATE].mean(axis=1)
    out["growth"] = out.share_late / out.share_early.replace(0, np.nan)
    t = [kendalltau(FULL, wide.loc[i]) for i in wide.index]
    out["tau"], out["p"] = [r.statistic for r in t], [r.pvalue for r in t]
    out["fast_riser"] = (out.growth >= 1.5) & (out.tau > 0) & (out.p < 0.05) & (out.projects >= min_n)
    return wide, out.reset_index()

# %% [markdown]
# ## Themes (slide 2) and named topics (slide 3)

# %%
y["all"], d["all"] = "NIH", "NIH"
theme_wide, theme_tr = trends(y, "theme", ["all"], MIN_PROJECTS, d.groupby(["all", "theme"]).size())
topic_wide, topic_tr = trends(y, "name", ["all"], MIN_PROJECTS, d.groupby(["all", "name"]).size())
theme_tr = theme_tr.drop(columns="all").sort_values("projects", ascending=False)
topic_tr = topic_tr.drop(columns="all").merge(names[["name", "theme"]], on="name").sort_values("growth", ascending=False)
theme_wide.droplevel(0).to_csv(OUT / "topics_themes_by_fy.csv")
theme_tr.to_csv(OUT / "topics_themes_trends.csv", index=False)
topic_tr.to_csv(OUT / "topics_named.csv", index=False)
theme_tr.round(3)

# %%
latest = theme_wide.droplevel(0)[FY_LAST_FULL].sort_values()
fig, ax = plt.subplots(figsize=(9, 9))
fig.subplots_adjust(left=0.42, top=0.92, bottom=0.1)
ax.barh(latest.index, latest * 100, color=pal.PROJECTS)
for i, v in enumerate(latest * 100):
    ax.annotate(f"{v:.1f}%", (v, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=pal.SIZES["axis"])
ax.set_xlabel(f"% of active data science projects, FY{FY_LAST_FULL}")
title(fig, "What data science at NIH works on")
note(fig, "Themes group 112 topics found in project abstracts; each project has one topic.\n" + SOURCE)
save(fig, "04_themes_share")

top = theme_tr.head(16).theme
fig, axes = plt.subplots(4, 4, figsize=(13, 10.5), sharex=True)
fig.subplots_adjust(top=0.9, bottom=0.11, hspace=0.6, wspace=0.3)
for ax, t in zip(axes.flat, top):
    v = theme_wide.droplevel(0).loc[t, FULL] * 100
    ax.plot(FULL, v, color=pal.PROJECTS, lw=2)
    ax.set_title(t, fontsize=pal.SIZES["axis"], loc="left")
    ax.set_ylim(0, v.max() * 1.3)
    ax.tick_params(labelsize=9)
title(fig, "Theme shares over time, 16 largest themes")
fig.supylabel("% of active data science projects", fontsize=pal.SIZES["axis"])
note(fig, f"FY{FY_FIRST} to FY{FY_LAST_FULL}.\n" + SOURCE)
save(fig, "05_themes_by_fy")


def rising_chart(tr, ax, cap=CAP, n=12, min_n=MIN_PROJECTS):
    r = tr[(tr.projects >= min_n) & tr.growth.notna()].sort_values("growth", ascending=False).head(n)[::-1]
    shown = r.growth.clip(upper=cap)
    ax.barh(r.name, shown, color=[pal.PROJECTS if f else pal.NEUTRAL for f in r.fast_riser])
    for i, (g, s, p) in enumerate(zip(r.growth, shown, r.projects)):
        lab = f"{g:.1f}×" + (f" ({p:,} projects)" if g > cap else "")
        ax.annotate(lab, (s, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=pal.SIZES["axis"])
    ax.axvline(1, color=pal.MUTED, lw=1, ls=":")
    ax.set_xlim(0, cap * 1.25)
    return r


fig, ax = plt.subplots(figsize=(10, 6.8))
fig.subplots_adjust(left=0.36, top=0.9, bottom=0.2)
rising_chart(topic_tr, ax)
ax.set_xlabel(f"Growth in share of data science projects (FY{LATE[0]}–{LATE[-1]} ÷ FY{EARLY[0]}–{EARLY[-1]})")
title(fig, "Fastest-growing data science topics")
note(fig, f"Dark = steady rise (Kendall's τ, p < 0.05) with at least {MIN_PROJECTS} projects; light = growth without a steady\n"
          f"trend. Bars stop at {CAP:.0f}×; longer ones are labeled. 1 = same share as FY{EARLY[0]}–{EARLY[-1]}.\n" + SOURCE)
save(fig, "06_fastest_rising_named")

# %% [markdown]
# ## Inside each institute
#
# Same measures within each institute with at least `MIN_IC_DS` data science projects. Two institutes per chart.

# %%
yi = y.dropna(subset=["ic"])
big = d.dropna(subset=["ic"]).ic.value_counts()
ics = big[big >= MIN_IC_DS].index.tolist()
yi = yi[yi.ic.isin(ics)]
ic_wide, ic_tr = trends(yi, "name", ["ic"], MIN_IC_PROJECTS, d.groupby(["ic", "name"]).size())
ic_tr = ic_tr.merge(names[["name", "theme"]], on="name")
ic_tr.to_csv(OUT / "topics_by_ic.csv", index=False)

for k in range(0, len(ics), 2):
    pair = ics[k:k + 2]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    fig.subplots_adjust(left=0.2, right=0.97, wspace=0.75, top=0.86, bottom=0.2)
    for ax, ic in zip(axes, pair):
        rising_chart(ic_tr[ic_tr.ic == ic], ax, n=10, min_n=MIN_IC_PROJECTS)
        ax.set_title(f"{ic} ({big[ic]:,} data science projects)", loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)
        ax.set_xlabel("Growth in share of the institute's data science projects")
    if len(pair) == 1:
        axes[1].set_visible(False)
    title(fig, "Fastest-growing data science topics inside each institute")
    note(fig, f"Share of the institute's own active data science projects, FY{LATE[0]}–{LATE[-1]} ÷ FY{EARLY[0]}–{EARLY[-1]}. "
              f"Topics with at least {MIN_IC_PROJECTS} projects at the institute.\nDark = steady rise (Kendall's τ, p < 0.05). "
              f"Bars stop at {CAP:.0f}×.\n" + SOURCE)
    save(fig, f"ic/{k // 2 + 1:02d}_{'_'.join(pair)}")

# where each NIH-wide fast riser grew: share of its late-period projects by institute
risers = topic_tr[topic_tr.fast_riser].name
late_ic = (y[y.name.isin(risers) & y.fy.isin(LATE)].groupby(["name", "ic"]).size()
           .groupby(level=0, group_keys=False).apply(lambda s: s / s.sum()).rename("share_of_topic").reset_index())
lead = late_ic.sort_values("share_of_topic", ascending=False).drop_duplicates("name")
lead.to_csv(OUT / "topics_risers_lead_ic.csv", index=False)
print("NIH-wide fast risers and the institute with most of their FY2023–2025 projects:")
print(lead.round(2).to_string(index=False))
