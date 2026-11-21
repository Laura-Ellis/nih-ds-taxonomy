# %% [markdown]
# # B2d. Link every data science project to a targeted funding call
#
# Uses the learning-to-rank model from `nofo_match_ltr.py` (slide 7) to link projects to targeted funding calls
# (NOFOs: RFAs and PARs).
#
# Every grant record lists the call it was funded under. For the 45,803 data science projects:
# - **Targeted call listed** (about 53%): the record already names an RFA or PAR. Nothing to link; these are the
#   training data.
# - **No funding call by design** (about 5%): intramural (Z codes), VA (I codes), contracts (N, Y), and other
#   transactions (OT). These never go through a funding call, so they aren't linked.
# - **Grant, no call listed** (well under 1%): the model names the call the grant was most likely funded under. This
#   is the task the model was tested on (actual call in the top 10 for about 95% of projects).
# - **Broad call only** (about 41%, mostly the parent R01): the model names the targeted call the project fits best.
#   This answers a different question, "which targeted call would fit this project?", so the 95% doesn't apply.
#   A weak best fit points to areas no targeted call covers.
#
# **Model:** LightGBM LambdaMART (`lambdarank`), same settings and features as `nofo_match_ltr.py` except PubMedBERT,
# which is cached only for the 2,000 check projects (it carried 5% of the model's gain). Trained on 6,000 projects
# with a targeted call listed, not in the check set. Checked on the same 2,000 check projects as slides 6 and 7.
#
# **Fit strength (broad-call projects):** a best fit is "strong" if its model score is at least the median score of
# correct first picks in the check set, otherwise "weak".
#
# Inputs: same as `nofo_match_ltr.py`. Outputs: `reports/results/nofo_links.csv` (top 3 calls per linked project),
# `nofo_links_by_call.csv`, `nofo_links_by_institute.csv`, `nofo_links_by_area.csv`, `nofo_links_check.csv`,
# `reports/figures/topics/09d_call_links.png`.
# Runtime on a laptop CPU: about 20 to 30 minutes. Work is saved in `data/interim/nofo_link/` after each batch, so a
# stopped run picks up where it left off (delete the folder to start over). `NOFO_LINK_BUDGET=<seconds>` stops a run
# cleanly after that long. Needs `lightgbm`.

# %%
import os
import pickle
import sys
import time
from pathlib import Path

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from nofo_rank import NOFO_RE, TextScorer, details, features, load_targeted  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
WORK = INTERIM / "nofo_link"
FIG = ROOT / "reports" / "figures" / "topics"
SEED, K, BATCH, N_CHECK, N_TRAIN = 1, 150, 1000, 2000, 6000
BUDGET = float(os.environ.get("NOFO_LINK_BUDGET", "inf"))
T0 = time.time()
SOURCE = "Source: NIH RePORTER API and ExPORTER; NIH Guide for Grants and Contracts; NIH Data Science Taxonomy."
WORK.mkdir(parents=True, exist_ok=True)
pal.use_style()
_stop = None


def stage(name):
    global _stop
    if _stop:
        _stop()
    _stop = start(name)


def out_of_time():
    if time.time() - T0 > BUDGET:
        say("time budget reached; run again to continue")
        if _stop:
            _stop()
        sys.exit(0)

# %% [markdown]
# ## Projects, their listed calls, and the targeted calls

# %%
stage("projects and calls")
tg = load_targeted(ROOT / "data" / "raw" / "nofo")
key = ["core_project_number", "subproject_id"]
asg = pd.read_parquet(INTERIM / "topic_assignments.parquet")
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["nofos", "activity", "administering_ic", "fiscal_years"])
txt = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet", columns=key + ["project_title", "abstract_text"])
docs = asg.merge(core, on=key, how="left").merge(txt, on=key, how="left")
assert len(docs) == len(asg), "project keys repeat; check the merge"
docs["text"] = docs.project_title.fillna("") + ". " + docs.abstract_text.fillna("")
docs["title"] = docs.project_title.fillna("")
listed = docs.nofos.fillna("").astype(str).str.upper().str.findall(NOFO_RE)
tg_index = {n: i for i, n in enumerate(tg.nofo)}
docs["targets"] = listed.map(lambda ns: [tg_index[n] for n in ns if n in tg_index])
any_targeted = listed.map(lambda ns: any(n.startswith(("RFA", "PAR")) for n in ns))
docs["group"] = np.select([docs.targets.str.len() > 0, any_targeted, listed.str.len() > 0],
                          ["Targeted call listed", "Targeted call listed (text not saved)", "Broad call only"],
                          "No call listed")
no_call_by_design = docs.activity.fillna("").str.match(r"^(Z|I|N|Y|OT)")   # intramural, VA, contracts, other transactions
docs.loc[(docs.group == "No call listed") & no_call_by_design, "group"] = "No funding call by design"
docs.loc[docs.group == "No call listed", "group"] = "Grant, no call listed"
say(docs.group.value_counts().to_string())

has = docs[docs.targets.str.len() > 0]
check = has.sample(min(N_CHECK, len(has)), random_state=SEED)          # same check set as nofo_match.py
train = has.drop(check.index).sample(min(N_TRAIN, len(has) - len(check)), random_state=SEED)
link = docs[docs.group.isin(["Grant, no call listed", "Broad call only"])]
say(f"train {len(train):,}, check {len(check):,}, to link {len(link):,} against {len(tg):,} targeted calls")

f = WORK / "scorer.pkl"
if f.exists():
    scorer = pickle.loads(f.read_bytes())
else:
    stage("fit word weights")
    fit = pd.concat([train, check])
    scorer = TextScorer(tg, fit.text, fit.title)
    f.write_bytes(pickle.dumps(scorer))


def batch_features(df):
    S = scorer.scores(df.text, df.title)
    return features(S, details(df, tg), K)

# %% [markdown]
# ## Train on 6,000 projects with a targeted call listed

# %%
stage("training features")
for b in range(0, len(train), BATCH):
    f = WORK / f"train_{b // BATCH:03d}.npz"
    if not f.exists():
        part = train.iloc[b:b + BATCH]
        X, names, cand, _ = batch_features(part)
        y = np.zeros(cand.shape, np.int8)
        for i, ts in enumerate(part.targets):
            y[i] = np.isin(cand[i], ts)
        np.savez_compressed(f, X=X, y=y)
        say(f"  train batch {b // BATCH + 1} of {-(-len(train) // BATCH)}")
        out_of_time()
parts = [np.load(WORK / f"train_{b // BATCH:03d}.npz") for b in range(0, len(train), BATCH)]
X = np.concatenate([p["X"] for p in parts])
y = np.concatenate([p["y"] for p in parts])
keep = y.any(1)                                  # projects whose actual call is among the candidates
say(f"actual call among the {K} candidates for {keep.mean():.1%} of training projects")

f = WORK / "model.txt"
if f.exists():
    booster = lgb.Booster(model_file=str(f))
else:
    stage("train model")
    mdl = lgb.LGBMRanker(objective="lambdarank", n_estimators=300, learning_rate=0.05, num_leaves=31,
                         min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                         random_state=SEED, verbose=-1)
    mdl.fit(X[keep].reshape(-1, X.shape[2]), y[keep].ravel(), group=[K] * keep.sum())
    booster = mdl.booster_
    booster.save_model(str(f))
names = booster.feature_name()
del X, y, parts


def rank_batch(df):
    """Model scores for each project's candidates; projects x K scores, candidate indexes, and the prior."""
    X, _, cand, prior = batch_features(df)
    s = booster.predict(X.reshape(-1, X.shape[2])).reshape(len(df), K).astype(np.float32)
    order = np.argsort(-s, axis=1)
    rr = np.arange(len(df))[:, None]
    return s[rr, order], cand[rr, order], prior

# %% [markdown]
# ## Check on the 2,000 check projects (same as slides 6 and 7)

# %%
stage("check")
f = WORK / "check.parquet"
if not f.exists():
    rows = []
    for b in range(0, len(check), BATCH):
        part = check.iloc[b:b + BATCH]
        s, c, prior = rank_batch(part)
        for i, ts in enumerate(part.targets):
            hit = np.flatnonzero(np.isin(c[i], ts))
            if hit.size:
                r = hit[0] + 1
            else:                                # not among candidates: rank after them, in prior order
                p = prior[i]
                r = K + 1 + (p > max(p[t] for t in ts)).sum() - (p[c[i]] > max(p[t] for t in ts)).sum()
            rows.append({"rank": int(r), "top_score": float(s[i, 0])})
    pd.DataFrame(rows).to_parquet(f)
chk = pd.read_parquet(f)
r = chk["rank"].to_numpy()
check_tbl = pd.DataFrame([{"model": "Learning to rank + project details, no PubMedBERT", "projects": len(r),
                           "hit_at_1": (r <= 1).mean(), "hit_at_5": (r <= 5).mean(), "hit_at_10": (r <= 10).mean(),
                           "mrr": (1 / r).mean()}])
check_tbl.to_csv(OUT / "nofo_links_check.csv", index=False)
STRONG = float(chk.loc[chk["rank"] == 1, "top_score"].median())
say(f"check: first {(r <= 1).mean():.1%}, top 10 {(r <= 10).mean():.1%}, MRR {(1 / r).mean():.3f}; "
    f"strong-fit score >= {STRONG:.2f}")

# %% [markdown]
# ## Link projects with no call listed or a broad call only

# %%
stage("link projects")
nb = -(-len(link) // BATCH)
for b in range(0, len(link), BATCH):
    f = WORK / f"link2_{b // BATCH:03d}.parquet"
    if f.exists():
        continue
    part = link.iloc[b:b + BATCH]
    s, c, _ = rank_batch(part)
    out = part[key + ["group", "administering_ic", "activity", "main_group"]].reset_index(drop=True)
    for j in range(3):
        out[f"call_{j + 1}"] = tg.nofo.to_numpy()[c[:, j]]
        out[f"score_{j + 1}"] = s[:, j]
    out.to_parquet(f)
    say(f"  link batch {b // BATCH + 1} of {nb}")
    out_of_time()
links = pd.concat([pd.read_parquet(WORK / f"link2_{b // BATCH:03d}.parquet") for b in range(0, len(link), BATCH)],
                  ignore_index=True)
links["fit"] = np.where(links.group == "Grant, no call listed", "Likely funding call",
                        np.where(links.score_1 >= STRONG, "Strong fit", "Weak fit"))
meta = tg.set_index("nofo")[["title", "issuer"]]
links["call_1_title"] = links.call_1.map(meta.title)
links["call_1_issuer"] = links.call_1.map(meta.issuer)
links.to_csv(OUT / "nofo_links.csv", index=False)

# %% [markdown]
# ## Summaries by call, institute, and data science area

# %%
stage("summaries")
actual = has.explode("targets")
actual["call"] = tg.nofo.to_numpy()[actual.targets.astype(int)]
by_call = (actual.groupby("call").size().rename("funded_listed").to_frame()
           .join(links[links.group == "Grant, no call listed"].groupby("call_1").size().rename("likely_unlisted"), how="outer")
           .join(links[links.fit == "Strong fit"].groupby("call_1").size().rename("broad_call_strong_fit"), how="outer")
           .fillna(0).astype(int).join(meta).sort_values("broad_call_strong_fit", ascending=False))
by_call.index.name = "call"
by_call.to_csv(OUT / "nofo_links_by_call.csv")


def shares(col):
    t = docs.assign(fit="").copy()
    t.loc[t.group.str.startswith("Targeted"), "fit"] = "Targeted call listed"
    t.loc[t.group == "No funding call by design", "fit"] = "No funding call (intramural, VA, contract)"
    lk = links.set_index(key).fit
    t = t.set_index(key)
    t.loc[lk.index, "fit"] = np.where(lk == "Likely funding call", "Grant, no call listed", "Broad call: " + lk.str.lower())
    t = t.reset_index()
    out = pd.crosstab(t[col], t.fit)
    out["projects"] = out.sum(1)
    for c in [c for c in out.columns if c != "projects"]:
        out[f"{c} (%)"] = (100 * out[c] / out.projects).round(1)
    return out.sort_values("projects", ascending=False)


by_ic = shares("administering_ic")
by_ic.to_csv(OUT / "nofo_links_by_institute.csv")
by_area = shares("main_group")
by_area.to_csv(OUT / "nofo_links_by_area.csv")
print(by_area.filter(like="(%)").to_string())

# %%
order = ["Targeted call listed", "Broad call: strong fit", "Broad call: weak fit", "Grant, no call listed",
         "No funding call (intramural, VA, contract)"]
colors = [pal.PROJECTS, "#B06F60", "#E1B781", pal.HEADING, pal.NEUTRAL]
show = by_area[by_area.projects >= 300]
pct = show[[f"{c} (%)" for c in order if f"{c} (%)" in show]].fillna(0)
fig, ax = plt.subplots(figsize=(10, 0.6 * len(pct) + 2.4))
fig.subplots_adjust(left=0.26, top=0.8, bottom=0.24)
left = np.zeros(len(pct))
for c, col in zip(order, colors):
    v = pct.get(f"{c} (%)", pd.Series(0, index=pct.index)).to_numpy()
    ax.barh(np.arange(len(pct)), v, left=left, color=col, label=c)
    left += v
ax.set_yticks(np.arange(len(pct)), pct.index)
ax.invert_yaxis()
ax.set_xlim(0, 100)
ax.set_xlabel("Share of data science projects (%)")
ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=pal.SIZES["axis"])
fig.suptitle("How data science projects connect to targeted funding calls", x=0.02, ha="left",
             fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
fig.text(0.02, 0.005, "Broad call = only a broad announcement (such as the parent R01) on the grant record. Strong or weak = how well the best-fitting\n"
         "targeted call fits (learning-to-rank score vs. the median for correct first picks). Data science areas with 300+ projects.\n" + SOURCE,
         fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")
fig.savefig(FIG / "09d_call_links.png", dpi=200, bbox_inches="tight")
plt.close(fig)
_stop()
say(f"done; linked {len(links):,} projects ({(links.fit == 'Strong fit').sum():,} strong fits among broad-call projects)")
