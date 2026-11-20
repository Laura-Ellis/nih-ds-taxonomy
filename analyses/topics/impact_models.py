# %% [markdown]
# # B4. What goes with high-impact outputs
#
# Analysis B, slide 7. Among data science projects, which project traits go with highly cited papers,
# patents, and clinical trials?
#
# **Projects:** the data science projects that started FY2016–FY2020 (`matched_projects.parquet`, scope
# "Data science", treated), so each has had at least five years to produce outputs.
#
# **Outcomes** (one model each)
# - High citation = mean Relative Citation Ratio (RCR) of the project's papers in the top quarter of
#   projects with papers (RCR = citations per year ÷ the field's expected rate; 1.0 = median NIH paper)
# - Patent = the core project number is in ExPORTER's patent table
# - Clinical trial = the core project number is in ExPORTER's clinical studies table
#
# **Traits (features)**
# - Taxonomy: AI (substantive), AI role (develops, applies, supports, studies), and the taxonomy groups
#   (statistics, modeling, AI, software, infrastructure, responsible AI, workforce)
# - Research theme (BERTopic themes from `topic_themes.py`)
# - Structure: institute, activity code family, first FY, years funded, log10 total cost, number of PIs,
#   number of subprojects, training mechanism
#
# **Models:** logistic regression, random forest, and gradient boosting (scikit-learn), compared by 5-fold
# cross-validated ROC AUC (0.5 = chance, 1.0 = perfect) and average precision.
# **Explanation:** SHAP values for gradient boosting (each trait's push on a project's predicted outcome,
# in log-odds); mean |SHAP| ranks traits. Without the `shap` package the notebook uses permutation importance.
# **Causal check:** for the two taxonomy or theme traits with the largest mean |SHAP|, the average effect on
# each outcome estimated by augmented inverse probability weighting (AIPW, "doubly robust": a propensity
# model for having the trait plus an outcome model, both on the structural traits), with a 95% interval from
# `N_BOOT` bootstrap samples. Compared with the raw difference. Associations, not proof: traits not in the
# data (team quality, prior funding) can still confound.
#
# Inputs: `matched_projects.parquet`, `exporter_core_projects_labeled.parquet`, `exporter_applications.parquet`,
# publication links (`sources.pub_links`), `data/interim/icite.parquet`, ExPORTER link tables
# (`sources.link_tables`), `data/interim/topic_assignments.parquet`, `analyses/topics/topic_names.csv`.
# Outputs: `reports/results/impact_*.csv`, `reports/figures/topics/14_*.png` to `16_*.png`.
# Needs `pip install shap` for SHAP (optional).

# %%
import sys
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import source  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "topics"
FIG.mkdir(parents=True, exist_ok=True)
SEED, N_BOOT, TOP_IC = 1, 200, 15
OUTCOMES = {"high_citation": "Highly cited papers", "patent": "Patent", "trial": "Clinical trial"}
SOURCE = "Source: NIH RePORTER API and ExPORTER; iCite; NIH Data Science Taxonomy."
pal.use_style()
_stop = None


def stage(name):
    global _stop
    if _stop:
        _stop()
    _stop = start(name)


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def title(fig, text):
    fig.suptitle(text, x=0.02, ha="left", fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")


def note(fig, text):
    fig.text(0.02, 0.005, text, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")

# %% [markdown]
# ## Projects and traits

# %%
stage("projects and traits")
key = ["core_project_number", "subproject_id"]
proj = pd.read_parquet(PROCESSED / "matched_projects.parquet")
proj = proj[(proj.scope == "Data science") & proj.treated][["core_project_number"]].drop_duplicates()
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["is_subproject", "activity", "administering_ic", "first_fy", "n_fy", "attributed_cost",
                                      "ai_label", "ai_role", "model_categories", "training_mechanism", "n_subprojects"])
core = core[~core.is_subproject.fillna(False).astype(bool)].drop_duplicates("core_project_number")
d = proj.merge(core, on="core_project_number", how="inner")
say(f"{len(proj) - len(d):,} matched projects not found as core projects; left out")

apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=["core_project_number", "pi_ids"])
apps = apps[apps.core_project_number.isin(d.core_project_number)]
team = (apps.assign(pi=apps.pi_ids.fillna("").astype(str).str.split(r"[;,]")).explode("pi")
        .assign(pi=lambda x: x.pi.str.strip()).query("pi != ''").groupby("core_project_number").pi.nunique())
d["n_pis"] = d.core_project_number.map(team).fillna(1)

tax = yaml.safe_load((ROOT / "taxonomy" / "categories.yaml").read_text(encoding="utf-8"))
GLABEL = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
          "artificial_intelligence": "AI methods", "software_tools": "Software and tools",
          "data_infrastructure": "Data infrastructure", "data_sharing": "Data infrastructure",
          "responsible_ai": "Responsible AI", "workforce": "Workforce"}
cat_group = {c["id"]: GLABEL[c.get("group") or dim["id"]] for dim in tax["dimensions"] for c in dim.get("categories", [])
             if (c.get("group") or dim["id"]) in GLABEL}
cats = d.model_categories.fillna("").str.split("; ")
TAX = sorted(set(GLABEL.values()))
for g in TAX:
    d[f"tax: {g}"] = cats.map(lambda cs, g=g: any(cat_group.get(c) == g for c in cs)).astype(int)
d["tax: AI substantive"] = d.ai_label.eq("Y").astype(int)
for r in ["develops_ai", "applies_ai", "supports_ai", "studies_ai"]:
    d[f"tax: AI role {r.split('_')[0]}"] = d.ai_role.eq(r).astype(int)

asg = pd.read_parquet(INTERIM / "topic_assignments.parquet")
names = pd.read_csv(ROOT / "analyses" / "topics" / "topic_names.csv")
theme = (asg.merge(names, left_on="bt_topic", right_on="topic").groupby("core_project_number").theme
         .agg(lambda s: s.mode().iloc[0]))
d["theme"] = d.core_project_number.map(theme).fillna("None")
for t in sorted(d.theme.unique()):
    if t != "None":
        d[f"theme: {t}"] = d.theme.eq(t).astype(int)

top_ic = d.administering_ic.value_counts().head(TOP_IC).index
d["ic"] = d.administering_ic.where(d.administering_ic.isin(top_ic), "Other")
act = d.activity.fillna("").astype(str)
d["family"] = np.select([act.str[:1].isin(["F", "K", "T"]) | act.isin(["R00", "R25"]), act.isin(["R01", "R37", "R35"]),
                         act.str[:1].eq("R"), act.str[:1].isin(["U"]), act.str[:1].isin(["P"]), act.str[:1].isin(["N"])],
                        ["Training", "R01-type", "Other R", "Cooperative (U)", "Centers (P)", "Contracts (N)"], "Other")
d["log_cost"] = np.log10(d.attributed_cost.clip(lower=1000).fillna(1000))
d["first_fy"] = pd.to_numeric(d.first_fy).fillna(pd.to_numeric(d.first_fy).median())
d["years_funded"] = pd.to_numeric(d.n_fy).fillna(1)
d["n_subprojects"] = pd.to_numeric(d.n_subprojects).fillna(0)
d["training"] = d.training_mechanism.fillna(False).astype(int)
STRUCT_NUM = ["first_fy", "years_funded", "log_cost", "n_pis", "n_subprojects", "training"]
STRUCT = pd.get_dummies(d[["ic", "family"]], prefix=["ic", "type"], dtype=int)
say(f"{len(d):,} data science projects that started FY2016–FY2020")

# %% [markdown]
# ## Outcomes

# %%
stage("outcomes")
links = pd.concat(pd.read_parquet(f) for f in sorted(source("pub_links").glob("*.parquet")))
links.columns = links.columns.str.lower()
links = links[links.project_number.isin(d.core_project_number)].drop_duplicates(["pmid", "project_number"])
links["pmid"] = pd.to_numeric(links.pmid, errors="coerce")
icite = pd.read_parquet(INTERIM / "icite.parquet").drop_duplicates("pmid")
pp = links.merge(icite, on="pmid", how="left").groupby("project_number").agg(papers=("pmid", "nunique"), rcr=("rcr", "mean"))
d["papers"] = d.core_project_number.map(pp.papers).fillna(0)
d["rcr"] = d.core_project_number.map(pp.rcr)
cut = d.loc[d.papers > 0, "rcr"].quantile(0.75)
d["high_citation"] = (d.rcr >= cut).astype(int)


def read_link_table(pattern):
    files = [f for f in source("link_tables").rglob("*") if pattern in f.name.lower() and f.suffix.lower() in (".csv", ".zip")]
    if not files:
        say(f"no ExPORTER file matching '{pattern}'; that outcome is skipped")
        return None
    f = sorted(files)[-1]
    if f.suffix.lower() == ".zip":
        with zipfile.ZipFile(f) as z:
            df = pd.read_csv(z.open(next(n for n in z.namelist() if n.lower().endswith(".csv"))), encoding="latin-1", low_memory=False)
    else:
        df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
    col = next(c for c in df.columns if "project" in c and ("core" in c or c in ("project_id", "project_number")))
    return set(df[col].astype(str).str.strip())


for out, pat in [("patent", "patent"), ("trial", "clinical")]:
    s = read_link_table(pat)
    if s is None:
        OUTCOMES.pop(out)
    else:
        d[out] = d.core_project_number.isin(s).astype(int)
base = pd.Series({o: d[o].mean() for o in OUTCOMES}).rename("share_of_projects")
say(f"RCR cutoff for the top quarter: {cut:.2f}; outcome rates: " + ", ".join(f"{o} {v:.1%}" for o, v in base.items()))

# %% [markdown]
# ## Model comparison

# %%
stage("models")
FEATS = [c for c in d.columns if c.startswith(("tax: ", "theme: "))]
X = pd.concat([d[FEATS + STRUCT_NUM], STRUCT], axis=1).astype(float)
X.columns = [str(c) for c in X.columns]
assert not X.isna().any().any(), f"missing values in {X.columns[X.isna().any()].tolist()}"
models = {"Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5)),
          "Random forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=10, n_jobs=-1, random_state=SEED),
          "Gradient boosting": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=SEED)}
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
rows = []
for o in OUTCOMES:
    y = d[o].to_numpy()
    for m, est in models.items():
        p = cross_val_predict(est, X, y, cv=cv, method="predict_proba")[:, 1]
        rows.append({"outcome": OUTCOMES[o], "model": m, "auc": roc_auc_score(y, p), "average_precision": average_precision_score(y, p),
                     "base_rate": y.mean(), "projects": len(y)})
comp = pd.DataFrame(rows)
comp.to_csv(OUT / "impact_model_comparison.csv", index=False)
print(comp.round(3).to_string(index=False))

# %% [markdown]
# ## What drives the predictions (SHAP)

# %%
stage("SHAP")
imp, shap_vals = [], {}
try:
    import shap
    HAVE_SHAP = True
except ImportError:
    HAVE_SHAP = False
    say("shap not installed; using permutation importance (pip install shap for SHAP)")
for o in OUTCOMES:
    y = d[o].to_numpy()
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=SEED).fit(X, y)
    if HAVE_SHAP:
        sv = shap.TreeExplainer(gb).shap_values(X)
        sv = sv[1] if isinstance(sv, list) else sv
        shap_vals[o] = sv
        mean_abs = np.abs(sv).mean(axis=0)
        signed = np.array([np.corrcoef(X.iloc[:, j], sv[:, j])[0, 1] if X.iloc[:, j].std() > 0 and sv[:, j].std() > 0 else np.nan
                           for j in range(X.shape[1])])
    else:
        pi_ = permutation_importance(gb, X, y, scoring="roc_auc", n_repeats=5, random_state=SEED, n_jobs=-1)
        mean_abs, signed = pi_.importances_mean, np.full(X.shape[1], np.nan)
    imp.append(pd.DataFrame({"outcome": OUTCOMES[o], "feature": X.columns, "importance": mean_abs, "direction": signed}))
imp = pd.concat(imp)
IC_CODE = {"CA": "NCI", "AI": "NIAID", "HL": "NHLBI", "OD": "OD", "AG": "NIA", "GM": "NIGMS", "MH": "NIMH", "TR": "NCATS",
           "NS": "NINDS", "LM": "NLM", "DA": "NIDA", "HG": "NHGRI", "DK": "NIDDK", "HD": "NICHD", "ES": "NIEHS", "EB": "NIBIB",
           "EY": "NEI", "AR": "NIAMS", "DC": "NIDCD", "AA": "NIAAA", "MD": "NIMHD", "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH"}
NICE = {"log_cost": "Total cost (log)", "first_fy": "First fiscal year", "years_funded": "Years funded",
        "n_pis": "Number of PIs", "n_subprojects": "Number of subprojects", "training": "Training mechanism"}


def nice(f):
    if f in NICE:
        return NICE[f]
    if f.startswith("ic_"):
        return "Institute: " + IC_CODE.get(f[3:], f[3:])
    if f.startswith("type_"):
        return "Type: " + f[5:]
    return f.split(": ", 1)[1] if f.startswith(("tax: ", "theme: ")) else f


imp["label"] = imp.feature.map(nice)
imp["kind"] = np.where(imp.feature.str.startswith("tax: "), "Taxonomy",
                       np.where(imp.feature.str.startswith("theme: "), "Theme", "Structure"))
imp.to_csv(OUT / "impact_feature_importance.csv", index=False)
for o in OUTCOMES.values():
    print(f"\n{o}: top traits")
    print(imp[imp.outcome == o].nlargest(10, "importance")[["label", "kind", "importance", "direction"]].round(3).to_string(index=False))

# %%
fig, axes = plt.subplots(1, len(OUTCOMES), figsize=(5.3 * len(OUTCOMES), 6.2))
axes = np.atleast_1d(axes)
fig.subplots_adjust(left=0.13, wspace=1.05, top=0.78, bottom=0.2)
for ax, o in zip(axes, OUTCOMES.values()):
    t = imp[imp.outcome == o].nlargest(10, "importance")[::-1]
    col = [pal.PROJECTS if k != "Structure" else pal.NEUTRAL for k in t.kind]
    ax.barh(t.label, t.importance, color=col)
    for i, (v, dr) in enumerate(zip(t.importance, t.direction)):
        if not np.isnan(dr):
            ax.annotate("↑" if dr > 0 else "↓", (v, i), xytext=(4, 0), textcoords="offset points", va="center",
                        fontsize=pal.SIZES["axis"], color=pal.INK)
    ax.set_title(o, loc="left", fontsize=pal.SIZES["label"], color=pal.HEADING)
    ax.set_xlabel("Mean |SHAP| (log-odds)" if HAVE_SHAP else "Permutation importance (AUC drop)")
title(fig, "What goes with highly cited papers, patents, and trials")
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
fig.legend(handles=[Patch(color=pal.PROJECTS, label="Taxonomy or research theme"),
                    Patch(color=pal.NEUTRAL, label="Project structure (institute, type, size, cost)"),
                    Line2D([], [], ls="", marker="$↑$", ms=10, color=pal.INK, label="Higher value raises the chance"),
                    Line2D([], [], ls="", marker="$↓$", ms=10, color=pal.INK, label="Higher value lowers the chance")],
           loc="upper left", bbox_to_anchor=(0.02, 0.935), ncol=4, frameon=False, fontsize=pal.SIZES["axis"], handlelength=1.2)
note(fig, "Gradient boosting on data science projects that started FY2016–FY2020. Bar length = mean absolute SHAP value: how much\n"
          "the trait moves the predicted log-odds of the outcome, on average.\n" + SOURCE)
save(fig, "14_impact_drivers")

fig, ax = plt.subplots(figsize=(8, 4.2))
fig.subplots_adjust(left=0.1, top=0.8, bottom=0.28)
w = 0.8 / len(models)
for i, (m, c) in enumerate(zip(models, [pal.NEUTRAL, pal.PROJECTS, pal.FUNDING])):
    v = [comp[(comp.model == m) & (comp.outcome == o)].auc.iloc[0] for o in OUTCOMES.values()]
    xs = np.arange(len(OUTCOMES)) + (i - 1) * w
    ax.bar(xs, v, w, color=c, label=m)
    for x, h in zip(xs, v):
        ax.annotate(f"{h:.2f}", (x, h), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)
ax.set_xticks(range(len(OUTCOMES)), list(OUTCOMES.values()))
ax.set_ylim(0.5, 1)
ax.set_ylabel("ROC AUC (5-fold cross-validated)")
ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.15))
title(fig, "Model comparison")
note(fig, "AUC = chance a random project with the outcome scores above a random one without it (0.5 = chance).\n" + SOURCE)
save(fig, "15_impact_models")

# %% [markdown]
# ## Causal check on the two strongest taxonomy or theme traits

# %%
stage("causal check")
cand = (imp[imp.kind != "Structure"].groupby("feature").importance.mean().sort_values(ascending=False))
cand = [f for f in cand.index if 0.05 < d[f].mean() < 0.95][:2]
W = pd.concat([d[STRUCT_NUM], STRUCT], axis=1).astype(float).to_numpy()


def aipw(t, y, W, idx=None):
    if idx is not None:
        t, y, W = t[idx], y[idx], W[idx]
    sc = StandardScaler().fit(W)
    Ws = sc.transform(W)
    e = LogisticRegression(max_iter=3000).fit(Ws, t).predict_proba(Ws)[:, 1].clip(0.02, 0.98)
    om = LogisticRegression(max_iter=3000).fit(np.c_[Ws, t], y)
    m1 = om.predict_proba(np.c_[Ws, np.ones_like(t)])[:, 1]
    m0 = om.predict_proba(np.c_[Ws, np.zeros_like(t)])[:, 1]
    return np.mean(m1 - m0 + t * (y - m1) / e - (1 - t) * (y - m0) / (1 - e))


rng = np.random.default_rng(SEED)
causal = []
for f in cand:
    t = d[f].to_numpy()
    for o in OUTCOMES:
        y = d[o].to_numpy()
        est = aipw(t, y, W)
        boot = [aipw(t, y, W, rng.integers(0, len(t), len(t))) for _ in range(N_BOOT)]
        causal.append({"trait": f.split(": ", 1)[1], "outcome": OUTCOMES[o], "with_trait": y[t == 1].mean(),
                       "without_trait": y[t == 0].mean(), "raw_difference": y[t == 1].mean() - y[t == 0].mean(),
                       "aipw_effect": est, "low": np.percentile(boot, 2.5), "high": np.percentile(boot, 97.5)})
causal = pd.DataFrame(causal)
causal.to_csv(OUT / "impact_causal_check.csv", index=False)
print(causal.round(3).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(9, 0.6 * len(causal) + 2))
fig.subplots_adjust(left=0.42, top=0.85, bottom=0.25)
lab = [f"{r.trait} → {r.outcome}" for r in causal.itertuples()]
yy = np.arange(len(causal))[::-1]
ax.errorbar(causal.aipw_effect * 100, yy, xerr=[(causal.aipw_effect - causal.low) * 100, (causal.high - causal.aipw_effect) * 100],
            fmt="o", color=pal.PROJECTS, ecolor=pal.MUTED, capsize=3, label="Adjusted (AIPW)")
ax.scatter(causal.raw_difference * 100, yy, marker="|", s=200, color=pal.HIGHLIGHT if hasattr(pal, "HIGHLIGHT") else "#B06F60",
           label="Raw difference")
ax.axvline(0, color=pal.MUTED, lw=1)
ax.set_yticks(yy, lab)
ax.set_xlabel("Difference in share of projects with the outcome (percentage points)")
ax.legend(frameon=False, loc="lower right")
title(fig, "Causal check: does the trait still matter after adjusting for project structure?")
note(fig, f"Adjusted for institute, project type, first FY, years funded, cost, PIs, subprojects, training. 95% interval from "
          f"{N_BOOT} bootstrap samples.\n" + SOURCE)
save(fig, "16_impact_causal")
_stop()
say("done")
