# %% [markdown]
# # How people get to data science research: training awards, time to a research award, and R01 conversion
#
# Part 4 of the PI analysis (`pi_analysis.md`). Follows NIH training awards to later research awards.
#
# **Definitions**
# - Training award = activity code F (fellowship), K (career development, including K99), R00 (independent
#   phase of the K99/R00 Pathway to Independence award), T (institutional training), or R25 (education program)
# - Trainee awards = F, K, and R00: the PI is the trainee. Program awards = T and R25: the PI is the program
#   director, usually senior faculty; RePORTER doesn't list the trainees
# - Data science training award = a training award with substantive data science (in an aim or the stated approach)
# - Start year = fiscal year of the project start date of the person's first award of that training type
#   (NIH fiscal years start October 1). Using the start date, not the first year seen, keeps people whose
#   award began before FY2016 out of the cohorts
# - Cohort = people whose first award of a training type started FY2016 to FY2021
# - Follow-up = through FY2025, the last complete fiscal year (FY2026 is preliminary)
# - Later research award = any non-training, non-intramural award (R, U, P, and similar) in a fiscal year
#   after the start year
# - Later data science (or AI) research = a later research award with substantive data science (or AI)
# - R01 = an R01 award that started after the training award started. R01-equivalent = NIH's list:
#   R01, R37, RF1, R56, DP1, DP2, DP5, RL1, U01, R35 (NIH Extramural Nexus, August 2026)
# - People who already held an R01-equivalent before their training award are left out of the R01 measures
# - A person with more than one training type counts once in each
#
# **Methods**
# - Rates: people with the outcome ÷ cohort
# - Kaplan-Meier (KM) curve = share of the cohort with the outcome by each year since the start year,
#   counting people who haven't reached it yet only for the years we can see (censoring)
# - Cox proportional hazards model = how much faster one group reaches the outcome, holding the other
#   factors fixed. Hazard ratio (HR) 2.0 = twice as likely each year
# - Random survival forest (RSF) = many decision trees on the same question; checks whether a flexible model
#   predicts timing better than Cox. Compared with Harrell's concordance index (C-index: 0.5 = coin flip,
#   1.0 = perfect ordering of who reaches the outcome first)
# - Propensity score matching = pairs each data science K awardee with a similar other K awardee (same mix of
#   K type, institute, and start year), then compares outcomes, so differences in who gets data science
#   K awards don't drive the result
#
# **Privacy:** aggregate only; cells with fewer than 11 people are suppressed.
# Inputs: `exporter_applications.parquet` (notebook 08), `exporter_core_projects_labeled.parquet` (notebook 10).
# Outputs: `reports/results/ds_training_*.csv`, `reports/figures/ds_training/*.png`.
# Packages: scikit-learn and statsmodels (in requirements); scikit-survival only for the RSF cell (skipped
# if not installed: `pip install scikit-survival`).

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from pi_tiers import explode_pis  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "ds_training"
FIG.mkdir(parents=True, exist_ok=True)
FIRST_COHORT_FY, LAST_COHORT_FY, LAST_FOLLOW_FY = 2016, 2021, 2025
SUPPRESS, SEED = 11, 26
TRAINEE, PROGRAM = ["F", "K", "R00"], ["T", "R25"]
LABELS = {"F": "Fellowship (F)", "K": "Career development (K)", "R00": "Pathway to Independence (R00)",
          "T": "Institutional training (T)", "R25": "Education program (R25)"}
R01_EQUIV = ["R01", "R37", "RF1", "R56", "DP1", "DP2", "DP5", "RL1", "U01", "R35"]
# Conte and Omary 2018 (JCI Insight 3:e123875): K awards made 2008 to 2012, R01 within 5 years
BENCH_5Y = {"K99": 0.303, "K01": (0.191, 0.228), "K08": (0.191, 0.228), "K23": (0.191, 0.228)}
pal.use_style()


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def source_note(ax, text: str, y: float = -0.18) -> None:
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=pal.SIZES["source"], color=pal.SOURCE,
                va="top", linespacing=1.6)


def start_fy(dates: pd.Series) -> pd.Series:
    d = pd.to_datetime(dates, errors="coerce")
    return (d.dt.year + (d.dt.month >= 10)).astype("Int64")

# %% [markdown]
# ## Load awards, one row per PI × award × fiscal year

# %%
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "activity", "pi_ids", "project_start", "administering_ic"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label", "ai_label"])
a = a.merge(core, on=key, how="left")
a["fy"] = pd.to_numeric(a.fy).astype(int)
a = a[a.fy <= LAST_FOLLOW_FY]
a = explode_pis(a)
act = a.activity.fillna("").astype(str)
a["activity"] = act
a["kind"] = np.select([act.str.startswith("F"), act.str.startswith("K"), act.eq("R00"), act.str.startswith("T"),
                       act.eq("R25")], ["F", "K", "R00", "T", "R25"], "")
a["research"] = a.kind.eq("") & act.ne("") & ~act.str.startswith("Z")
a["ds"], a["ai"] = a.ds_label.eq("Y"), a.ai_label.eq("Y")
a["start_fy"] = start_fy(a.project_start)

# %% [markdown]
# ## Cohorts: each person's first award of each training type

# %%
tr = a[a.kind != ""].sort_values(["start_fy", "fy"])
first = (tr.groupby(["pi", "kind"])
         .agg(start=("start_fy", "min"), first_seen=("fy", "min"), ds_training=("ds", "any"),
              k_type=("activity", "first"), ic=("administering_ic", "first")).reset_index())
first["start"] = first.start.fillna(first.first_seen).astype(int)
first = first[first.start.between(FIRST_COHORT_FY, LAST_COHORT_FY)]
first["follow_years"] = LAST_FOLLOW_FY - first.start

# %% [markdown]
# ## Outcomes: later research, later data science research, R01, R01-equivalent

# %%
res = a[a.research][["pi", "fy", "ds", "ai", "activity", "start_fy"]]
m = first[["pi", "kind", "start"]].merge(res, on="pi", how="inner")
later = m[m.fy > m.start]
out = later.groupby(["pi", "kind"]).agg(research_fy=("fy", "min"))
out["ds_fy"] = later[later.ds].groupby(["pi", "kind"]).fy.min()
out["ai_fy"] = later[later.ai].groupby(["pi", "kind"]).fy.min()
r01 = m[m.activity.eq("R01") & (m.start_fy > m.start)]
out = out.join(r01.groupby(["pi", "kind"]).start_fy.min().rename("r01_fy"), how="outer")
eq = m[m.activity.isin(R01_EQUIV)]
out = out.join(eq[eq.start_fy > eq.start].groupby(["pi", "kind"]).start_fy.min().rename("r01eq_fy"), how="outer")
prior = eq[eq.start_fy.fillna(eq.fy) <= eq.start].groupby(["pi", "kind"]).size().rename("prior_r01eq")
coh = first.merge(out.reset_index(), on=["pi", "kind"], how="left").merge(prior.reset_index(), on=["pi", "kind"],
                                                                          how="left")
coh["prior_r01eq"] = coh.prior_r01eq.fillna(0).gt(0)
for o in ["research", "ds", "ai", "r01", "r01eq"]:
    fy = pd.to_numeric(coh[f"{o}_fy"], errors="coerce")
    fy = fy.where(fy <= LAST_FOLLOW_FY)
    coh[f"{o}_event"] = fy.notna()
    coh[f"{o}_years"] = (fy - coh.start).fillna(coh.follow_years)
coh["later_research"], coh["later_ds"], coh["later_ai"] = coh.research_event, coh.ds_event, coh.ai_event
print(coh.groupby(["kind", "ds_training"]).size().unstack())

# %% [markdown]
# ## Rates by training type (any time through FY2025)

# %%
rates = (coh.groupby(["kind", "ds_training"])
         .agg(people=("pi", "size"), later_research=("later_research", "mean"), later_ds=("later_ds", "mean"),
              later_ai=("later_ai", "mean"), median_years_to_research=("research_years", "median"))
         .reset_index())
rates["later_ds_among_research"] = (coh[coh.later_research].groupby(["kind", "ds_training"]).later_ds.mean()
                                    .reindex(pd.MultiIndex.from_frame(rates[["kind", "ds_training"]])).values)
rates["group"] = np.where(rates.kind.isin(TRAINEE), "Trainee award", "Program award")
rates.loc[rates.people < SUPPRESS, ["later_research", "later_ds", "later_ai", "later_ds_among_research"]] = np.nan
rates["kind"] = pd.Categorical(rates.kind, TRAINEE + PROGRAM, ordered=True)
rates = rates.sort_values(["kind", "ds_training"], ascending=[True, False])
rates.to_csv(OUT / "ds_training_pipeline.csv", index=False)
rates.round(3)

# %% [markdown]
# ## Chart 1. Trainees: later data science research, by training type

# %%
def paired_chart(kinds: list[str], measure: str, title: str, xlabel: str, name: str, note: str) -> None:
    r = rates.set_index(["kind", "ds_training"])[measure]
    fig, ax = plt.subplots(figsize=(8, 0.9 + 0.9 * len(kinds)))
    for i, k in enumerate(kinds[::-1]):
        ds, other = r.get((k, True), np.nan), r.get((k, False), np.nan)
        ax.barh(i + 0.2, 100 * ds, 0.38, color=pal.PROJECTS)
        ax.barh(i - 0.2, 100 * other, 0.38, color=pal.NEUTRAL)
        ax.annotate(f"{100 * ds:.0f}%  data science training", (100 * ds, i + 0.2), xytext=(4, 0),
                    textcoords="offset points", va="center", color=pal.PROJECTS, fontweight="bold",
                    fontsize=pal.SIZES["axis"])
        ax.annotate(f"{100 * other:.0f}%  other training", (100 * other, i - 0.2), xytext=(4, 0),
                    textcoords="offset points", va="center", color=pal.MUTED, fontsize=pal.SIZES["axis"])
    ax.set_yticks(range(len(kinds)), [LABELS[k] for k in kinds[::-1]])
    ax.set_xlim(0, 100)
    ax.set_xlabel(xlabel)
    ax.set_title(title, pad=12)
    source_note(ax, note, y=-0.34 if len(kinds) < 3 else -0.28)
    save(fig, name)


t = rates.set_index(["kind", "ds_training"])
k_ds, k_other = t.loc[("K", True), "later_ds"], t.loc[("K", False), "later_ds"]
paired_chart(TRAINEE, "later_ds",
             f"Career award holders with data science training are {k_ds / k_other:.1f} times as likely\n"
             "to go on to data science research",
             "People with a later data science research award, % of cohort", "01_trainees_later_ds",
             "First award started FY2016 to FY2021, followed through FY2025.\nSource: NIH RePORTER API.")

# %% [markdown]
# ## Chart 2. Data science training doesn't slow the path to a research award

# %%
paired_chart(TRAINEE, "later_research",
             "Trainees with data science training reach a research award at the same rate",
             "People with any later research award, % of cohort", "02_trainees_later_research",
             "Fellows (F) have had little time to reach independence; most will later.\nSource: NIH RePORTER API.")

# %% [markdown]
# ## Chart 3. Program directors: data science programs and the director's own research

# %%
paired_chart(PROGRAM, "later_ds",
             "Directors of data science training programs also lead data science research",
             "Directors with a later data science research award, % of cohort", "03_programs_later_ds",
             "T and R25 PIs are program directors, not trainees.\nSource: NIH RePORTER API.")

# %% [markdown]
# ## Kaplan-Meier curves for K awardees
# Cumulative share = 1 − KM survival. Survival at year t = product over years up to t of
# (1 − people reaching the outcome that year ÷ people still at risk that year).

# %%
def km(years: pd.Series, event: pd.Series, horizon: int = 9) -> pd.DataFrame:
    rows, s = [], 1.0
    for t_ in range(1, horizon + 1):
        at_risk = (years >= t_).sum()
        d = ((years == t_) & event).sum()
        if at_risk < SUPPRESS:
            break
        s *= 1 - d / at_risk
        rows.append({"year": t_, "at_risk": int(at_risk), "events": int(d), "cumulative": 1 - s})
    return pd.DataFrame(rows)


K = coh[coh.kind.eq("K")].copy()
K_r01 = K[~K.prior_r01eq]
curves = []
for outcome, frame in [("ds", K), ("r01", K_r01), ("r01eq", K_r01)]:
    for g, d in frame.groupby("ds_training"):
        c = km(d[f"{outcome}_years"], d[f"{outcome}_event"])
        c["outcome"], c["ds_training"] = outcome, g
        curves.append(c)
curves = pd.concat(curves)
curves.to_csv(OUT / "ds_training_km.csv", index=False)

# %% [markdown]
# ## Chart 4. Time to data science research after a K award

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
fig.subplots_adjust(left=0.07, right=0.97, top=0.8, bottom=0.3, wspace=0.12)
for ax, (outcome, ttl) in zip(axes, [("ds", "Later data science research award"), ("r01", "First R01")]):
    ends = {}
    for g, color in [(True, pal.PROJECTS), (False, pal.NEUTRAL)]:
        c = curves[(curves.outcome == outcome) & (curves.ds_training == g)]
        ax.step(c.year, 100 * c.cumulative, where="post", color=color, lw=2.6)
        ends[g] = (c.year.iloc[-1], 100 * c.cumulative.iloc[-1])
    close = abs(ends[True][1] - ends[False][1]) < 6
    for g, color, lab, dy in [(True, pal.PROJECTS, "Data science K", 8 if close else 0),
                              (False, pal.MUTED, "Other K", -8 if close else 0)]:
        x, yv = ends[g]
        ax.annotate(f"{lab} {yv:.0f}%", (x, yv), xytext=(6, dy), textcoords="offset points", va="center",
                    color=color, fontsize=pal.SIZES["axis"], fontweight="bold" if g else "normal")
    ax.set_title(ttl, fontsize=pal.SIZES["label"], pad=8)
    ax.set_xlabel("Years since the K award started")
    ax.set_xlim(0, 12.5)
    ax.set_xticks(range(0, 10))
axes[0].set_ylabel("Share of K awardees, %")
fig.suptitle("Data science K awardees reach data science research sooner and reach an R01 at the same pace",
             x=0.07, y=0.95, ha="left", fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
fig.text(0.07, 0.03, "Kaplan-Meier cumulative share: people not there yet count only for the years we can see.\n"
         "K awards started FY2016 to FY2021, followed through FY2025. The R01 panel leaves out people who already\n"
         "held an R01-equivalent. Source: NIH RePORTER API.", fontsize=pal.SIZES["source"], color=pal.SOURCE,
         linespacing=1.6)
save(fig, "04_k_time_to_outcome")

# %% [markdown]
# ## R01 conversion within 5 and 7 years, by K type, with the published benchmark
# 5-year window uses K awards that started FY2016 to FY2020; 7-year window, FY2016 to FY2018.

# %%
K_r01 = K_r01.assign(k_group=np.where(K_r01.k_type.isin(["K99", "K01", "K08", "K23", "K25"]), K_r01.k_type,
                                      "Other K"))
win = []
for w, last in [(5, LAST_FOLLOW_FY - 5), (7, LAST_FOLLOW_FY - 7)]:
    d = K_r01[K_r01.start <= last]
    for cols in (["k_group", "ds_training"], ["ds_training"]):
        g = (d.assign(r01=d.r01_event & (d.r01_years <= w), r01eq=d.r01eq_event & (d.r01eq_years <= w))
             .groupby(cols).agg(people=("pi", "size"), r01=("r01", "mean"), r01eq=("r01eq", "mean")).reset_index())
        if "k_group" not in g:
            g["k_group"] = "All K"
        g["window_years"], g["cohort"] = w, f"FY{FIRST_COHORT_FY}–FY{last}"
        win.append(g)
win = pd.concat(win)
win.loc[win.people < SUPPRESS, ["r01", "r01eq"]] = np.nan
win["benchmark_r01_5y"] = win.k_group.map(
    lambda k: None if k not in BENCH_5Y else (f"{BENCH_5Y[k]:.3f}" if isinstance(BENCH_5Y[k], float)
                                              else "{:.3f} to {:.3f}".format(*BENCH_5Y[k]))).where(win.window_years.eq(5))
win.to_csv(OUT / "ds_training_r01_windows.csv", index=False)
win.round(3)

# %% [markdown]
# ## Chart 5. R01 within 5 years: this cohort vs. the published benchmark

# %%
w5 = win[(win.window_years == 5) & win.k_group.isin(["K99", "K01", "K08", "K23"])].pivot(
    index="k_group", columns="ds_training", values="r01").reindex(["K99", "K01", "K08", "K23"])
fig, ax = plt.subplots(figsize=(8.5, 5.4))
for i, k in enumerate(w5.index[::-1]):
    ds, other = w5.loc[k].get(True, np.nan), w5.loc[k].get(False, np.nan)
    ax.barh(i + 0.15, 100 * ds, 0.28, color=pal.PROJECTS)
    ax.barh(i - 0.15, 100 * other, 0.28, color=pal.NEUTRAL)
    for v, dy, c, lab in [(ds, 0.15, pal.PROJECTS, "data science K"), (other, -0.15, pal.MUTED, "other K")]:
        if pd.notna(v):
            ax.annotate(f"{100 * v:.0f}%  {lab}", (100 * v, i + dy), xytext=(4, 0), textcoords="offset points",
                        va="center", color=c, fontsize=pal.SIZES["axis"], fontweight="bold" if dy > 0 else "normal")
    b = BENCH_5Y[k]
    lo, hi = (b, b) if isinstance(b, float) else b
    ax.plot([100 * lo, 100 * hi + (0 if hi > lo else 0.4)], [i + 0.44, i + 0.44], color=pal.HEADING, lw=5,
            solid_capstyle="butt")
    ax.annotate("benchmark " + (f"{100 * lo:.0f}%" if hi == lo else f"{100 * lo:.0f}% to {100 * hi:.0f}%"),
                (100 * hi, i + 0.44), xytext=(6, 0), textcoords="offset points", va="center",
                color=pal.HEADING, fontsize=pal.SIZES["axis"])
ax.set_yticks(range(len(w5)), w5.index[::-1])
ax.set_xlim(0, 70)
ax.set_xlabel("K awardees with an R01 within 5 years of the K start, %")
ax.set_ylim(-0.6, len(w5) - 0.3)
ax.set_title("Recent K01, K08, and K23 awardees reach an R01 within 5 years more often than\n"
             "the 2008 to 2012 benchmark; K99 awardees less often", pad=14, loc="left")
source_note(ax, "K awards started FY2016 to FY2020, followed through FY2025; leaves out people who already held an\n"
            "R01-equivalent. Benchmark (dark line): K awards made 2008 to 2012, Conte and Omary 2018, JCI Insight;\n"
            "the paper gives one 19% to 23% range for K01, K08, and K23. "
            "Source: NIH RePORTER API.", y=-0.2)
save(fig, "05_k_r01_5yr_benchmark")

# %% [markdown]
# ## Cox model and random survival forest, K awardees
# Features: data science training, K type, administering institute (top 10, rest grouped), start year.

# %%
def features(d: pd.DataFrame) -> pd.DataFrame:
    top_ic = d.ic.value_counts().index[:10]
    k_top = d.k_type.value_counts().index[:8]
    x = pd.DataFrame({"ds_training": d.ds_training.astype(float), "start_year": d.start - FIRST_COHORT_FY},
                     index=d.index)
    x = x.join(pd.get_dummies(d.k_type.where(d.k_type.isin(k_top), "K other"), prefix="k", dtype=float)
               .drop(columns="k_K23", errors="ignore"))
    x = x.join(pd.get_dummies(d.ic.where(d.ic.isin(top_ic), "other"), prefix="ic", dtype=float)
               .drop(columns="ic_other", errors="ignore"))
    return x


rng = np.random.default_rng(SEED)
cox_rows, model_rows = [], []
for outcome, frame in [("ds", K), ("r01", K_r01), ("r01eq", K_r01)]:
    d = frame[frame[f"{outcome}_years"] > 0]
    X, T, E = features(d), d[f"{outcome}_years"].to_numpy(float), d[f"{outcome}_event"].to_numpy(bool)
    fit = sm.PHReg(T, X, status=E.astype(int), ties="efron").fit()
    ci = np.exp(fit.conf_int())
    cox_rows.append({"outcome": outcome, "people": len(d), "events": int(E.sum()),
                     "hr_ds_training": float(np.exp(fit.params[X.columns.get_loc("ds_training")])),
                     "hr_low": float(ci[X.columns.get_loc("ds_training"), 0]),
                     "hr_high": float(ci[X.columns.get_loc("ds_training"), 1]),
                     "p_value": float(fit.pvalues[X.columns.get_loc("ds_training")])})
    # held-out comparison: Cox vs RSF on the same 25% test split
    test = rng.random(len(d)) < 0.25
    cox_tr = sm.PHReg(T[~test], X[~test], status=E[~test].astype(int), ties="efron").fit()
    risk_cox = X[test].to_numpy() @ cox_tr.params
    try:
        from sksurv.ensemble import RandomSurvivalForest
        from sksurv.metrics import concordance_index_censored
        y = np.array(list(zip(E, T)), dtype=[("e", bool), ("t", float)])
        rsf = RandomSurvivalForest(n_estimators=300, min_samples_leaf=25, max_features="sqrt", n_jobs=-1,
                                   random_state=SEED).fit(X[~test], y[~test])
        c_cox = concordance_index_censored(E[test], T[test], risk_cox)[0]
        c_rsf = concordance_index_censored(E[test], T[test], rsf.predict(X[test]))[0]
    except ImportError:
        c_cox, c_rsf = np.nan, np.nan
        print("scikit-survival not installed: RSF skipped")
    model_rows.append({"outcome": outcome, "test_people": int(test.sum()), "c_index_cox": c_cox, "c_index_rsf": c_rsf})
cox = pd.DataFrame(cox_rows)
cox.to_csv(OUT / "ds_training_cox.csv", index=False)
models = pd.DataFrame(model_rows)
models.to_csv(OUT / "ds_training_models.csv", index=False)
print(cox.round(3).to_string(), "\n", models.round(3).to_string())

# %% [markdown]
# ## Propensity score matching: data science K awardees vs. similar other K awardees
# Propensity score = predicted chance of a data science K from K type, institute, and start year (logistic
# regression). Each data science K awardee is paired with the other K awardee with the closest score
# (with replacement, within 0.2 standard deviations of the logit). 95% intervals from 1,000 bootstrap samples.

# %%
X = features(K).drop(columns="ds_training")
ps = LogisticRegression(max_iter=2000).fit(X, K.ds_training).predict_proba(X)[:, 1]
logit = np.log(ps / (1 - ps))
treated, control = np.where(K.ds_training)[0], np.where(~K.ds_training)[0]
nn = NearestNeighbors(n_neighbors=1).fit(logit[control].reshape(-1, 1))
dist, idx = nn.kneighbors(logit[treated].reshape(-1, 1))
keep = dist[:, 0] <= 0.2 * logit.std()
t_idx, c_idx = treated[keep], control[idx[keep, 0]]
match_rows = []
for outcome, label, base in [("ds", "Later data science research", K), ("research", "Any later research award", K)]:
    yt, yc = K[f"{outcome}_event"].to_numpy()[t_idx], K[f"{outcome}_event"].to_numpy()[c_idx]
    boots = [yt[s].mean() - yc[s].mean() for s in (rng.integers(0, len(yt), len(yt)) for _ in range(1000))]
    match_rows.append({"outcome": label, "pairs": int(keep.sum()), "unmatched_ds_k": int((~keep).sum()),
                       "ds_k_rate": yt.mean(), "matched_other_k_rate": yc.mean(), "difference": yt.mean() - yc.mean(),
                       "diff_low": np.percentile(boots, 2.5), "diff_high": np.percentile(boots, 97.5)})
matched = pd.DataFrame(match_rows)
matched.to_csv(OUT / "ds_training_matched.csv", index=False)
matched.round(3)

# %%
print("Charts saved to", FIG)
