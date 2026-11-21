# %% [markdown]
# # B2c. NOFO matching with learning to rank
#
# Follow-up to `nofo_match.py` and `nofo_match_bio.py` (slides 6 and 7). Same check set: 2,000 data science projects
# funded under a targeted NOFO, ranked against the same 2,482 targeted NOFOs, scored by hit@k and MRR.
#
# **Question:** Text alone puts the right NOFO in the top 10 for under half of projects. Does a model trained to
# combine text scores with what NIH already knows about a project (activity code, institute, funding years) do better?
#
# **Method: learning to rank (LTR)**
# 1. Text scores for every project-NOFO pair: TF-IDF (whole NOFO, best 200-word chunk, and with 1-3 word phrases),
#    BM25 (whole NOFO and best chunk), title-to-title TF-IDF, and PubMedBERT best-chunk cosine (cached by
#    `nofo_match_bio.py`).
# 2. Project details for every pair: does the NOFO allow the project's activity code? Is the project's administering
#    institute the NOFO's issuer or a participant? Was the NOFO open in one of the project's fiscal years (open year to
#    expiration year + 2), and if not, how many years off? Plus NOFO traits: RFA or PAR, number of activity codes,
#    number of institutes. Parsed from the NOFO text and number (e.g. RFA-AI-24-001 = NIAID).
# 3. Candidates: for each project, the 150 NOFOs with the highest average text score (z-scored TF-IDF, BM25 chunk,
#    PubMedBERT), putting NOFOs that pass the activity code and institute filters first.
# 4. Model: LightGBM `LGBMRanker` with the LambdaMART objective (`lambdarank`). LambdaMART is gradient-boosted
#    decision trees trained to put the right item near the top of each list (it optimizes NDCG, a top-weighted
#    ranking score). 300 trees, learning rate 0.05, 31 leaves, 80% row and feature sampling.
# 5. Validation: 5-fold cross-validation by project. Each project is ranked by a model trained on the other 80%. A
#    project whose right NOFO isn't among its 150 candidates counts as a miss (ranked after all candidates).
#
# Also reported for comparison: each text score alone, the tuned 0.6 TF-IDF + 0.4 PubMedBERT blend, each with the
# activity code and institute filters, and learning to rank on text features only.
#
# **Definitions:** hit@k = share of projects whose own NOFO is in the top k; MRR (mean reciprocal rank) = mean of
# 1 ÷ the rank of the right NOFO; z-score = score standardized within each project's row. A project can fit more than
# one NOFO, so these are lower bounds. Fiscal years are a feature, not a filter: as a hard filter they dropped the right
# NOFO for 12% of projects (renewals and reissued NOFOs).
#
# Inputs: same as `nofo_match.py`, plus `data/raw/nofo/text/` and `data/interim/nofo_bio_pubmedbert_*.npy` (run
# `nofo_match_bio.py` first). Outputs: `reports/results/nofo_matching_ltr.csv`,
# `reports/results/nofo_matching_ltr_features.csv`, `reports/figures/topics/09c_matching_ltr.png`.
# Runtime on a laptop CPU: about 5 minutes. Needs `lightgbm` (`pip install lightgbm`).

# %%
import os
import re
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
NOFO = ROOT / "data" / "raw" / "nofo"
FIG = ROOT / "reports" / "figures" / "topics"
SEED = 1
N_CHECK = int(os.environ.get("NOFO_CHECK", 2000))   # must match nofo_match.py
K = 150                                             # candidates per project
FOLDS = 5
SOURCE = "Source: NIH RePORTER API; NIH Guide for Grants and Contracts; NIH Data Science Taxonomy."
pal.use_style()
_stop = None


def stage(name):
    global _stop
    if _stop:
        _stop()
    _stop = start(name)


def kind(n):
    return "Targeted (RFA)" if n.startswith("RFA") else "Targeted (PAR)" if n.startswith("PAR") else \
        "Parent and other PA" if n.startswith("PA") else "Other"

# %% [markdown]
# ## Same NOFOs and check set as nofo_match.py

# %%
stage("check set")
man = pd.read_csv(NOFO / "manifest.csv").drop_duplicates("nofo", keep="last")
nofos = man[man.status == 200][["nofo"]].copy()
nofos["text"] = [(NOFO / "section1" / f"{n}.txt").read_text(encoding="utf-8") if (NOFO / "section1" / f"{n}.txt").exists()
                 else "" for n in nofos.nofo]
nofos = nofos[nofos.text.str.len() > 200].reset_index(drop=True)
nofos["kind"] = nofos.nofo.map(kind)
tg = nofos[nofos.kind.str.startswith("Targeted")].reset_index(drop=True)

key = ["core_project_number", "subproject_id"]
asg = pd.read_parquet(INTERIM / "topic_assignments.parquet")
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["nofos", "activity", "administering_ic", "fiscal_years"])
txt = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet", columns=key + ["project_title", "abstract_text"])
docs = asg.merge(core, on=key, how="left").merge(txt, on=key, how="left")
assert len(docs) == len(asg), "project keys repeat; check the merge"
docs["text"] = docs.project_title.fillna("") + ". " + docs.abstract_text.fillna("")
docs["nofo_list"] = docs.nofos.fillna("").astype(str).str.upper().str.findall(r"(?:RFA|PAR|PAS|PA|NOT)-[A-Z0-9]+-\d+(?:-\d+)?")
tg_index = {n: i for i, n in enumerate(tg.nofo)}
docs["targets"] = docs.nofo_list.map(lambda ns: [tg_index[n] for n in ns if n in tg_index])
check = docs[docs.targets.str.len() > 0].sample(min(N_CHECK, (docs.targets.str.len() > 0).sum()), random_state=SEED)
n, m = len(check), len(tg)
T = np.zeros((n, m), bool)                       # T[i, j]: NOFO j is a right answer for project i
for i, ts in enumerate(check.targets):
    T[i, ts] = True
say(f"{n:,} projects checked against {m:,} targeted NOFOs")

ch = pd.DataFrame([(i, " ".join(w[s:s + 200])) for i, t in enumerate(tg.text) for w in [t.split()]
                   for s in range(0, max(len(w), 1), 200)], columns=["nofo_idx", "text"])
starts = np.r_[0, np.flatnonzero(np.diff(ch.nofo_idx.to_numpy())) + 1]


def chunk_max(Q, C, batch=200):
    """Best-chunk score of each project against every NOFO (chunks are in NOFO order)."""
    out = np.empty((Q.shape[0], m), np.float32)
    for b in range(0, Q.shape[0], batch):
        sims = Q[b:b + batch] @ C.T
        out[b:b + batch] = np.maximum.reduceat(sims.toarray() if sparse.issparse(sims) else sims, starts, axis=1)
    return out

# %% [markdown]
# ## Text scores

# %%
stage("text scores")
S = {}
both = pd.concat([check.text, tg.text])
tf = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.5, sublinear_tf=True).fit(both)
Qt = tf.transform(check.text)
S["TF-IDF"] = (Qt @ tf.transform(tg.text).T).toarray().astype(np.float32)
S["TF-IDF, best chunk"] = chunk_max(Qt, tf.transform(ch.text))
tf3 = TfidfVectorizer(stop_words="english", ngram_range=(1, 3), min_df=2, max_df=0.5, sublinear_tf=True).fit(both)
S["TF-IDF, 1-3 word phrases"] = (tf3.transform(check.text) @ tf3.transform(tg.text).T).toarray().astype(np.float32)


def bm25(docs, queries, k1=1.2, b=0.75):
    """BM25 weights for documents (words and two-word phrases); queries are 0/1 term vectors."""
    cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, max_df=0.5).fit(pd.concat([docs, queries]))
    D = cv.transform(docs).astype(np.float32).tocoo()
    dl = np.asarray(D.tocsr().sum(1)).ravel()
    df = np.bincount(D.col, minlength=D.shape[1])
    idf = np.log(1 + (D.shape[0] - df + 0.5) / (df + 0.5)).astype(np.float32)
    w = D.data * (k1 + 1) / (D.data + k1 * (1 - b + b * dl[D.row] / dl.mean())) * idf[D.col]
    Q = cv.transform(queries).astype(np.float32)
    Q.data[:] = 1
    return Q.tocsr(), sparse.csr_matrix((w, (D.row, D.col)), shape=D.shape)


Q, W = bm25(tg.text, check.text)
S["BM25"] = (Q @ W.T).toarray().astype(np.float32)
Q, W = bm25(ch.text, check.text)
S["BM25, best chunk"] = chunk_max(Q, W)

full = [(NOFO / "text" / f"{x}.txt").read_text(encoding="utf-8", errors="ignore") if (NOFO / "text" / f"{x}.txt").exists()
        else "" for x in tg.nofo]


def between(t, a, z, cap=600):
    i = t.find(a)
    if i < 0:
        return ""
    j = t.find(z, i + len(a))
    return t[i + len(a): j if j > 0 else i + cap]


titles = [re.sub(r"\s+", " ", between(t, "Funding Opportunity Title", "Activity Code")).strip() for t in full]
ptitle = check.project_title.fillna("").tolist()
tt = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(titles + ptitle)
S["Title match"] = (tt.transform(ptitle) @ tt.transform(titles).T).toarray().astype(np.float32)

for f in ["pubmedbert_chunks", "pubmedbert_check"]:
    assert (INTERIM / f"nofo_bio_{f}.npy").exists(), "run nofo_match_bio.py first (PubMedBERT embeddings)"
C, Qe = np.load(INTERIM / "nofo_bio_pubmedbert_chunks.npy"), np.load(INTERIM / "nofo_bio_pubmedbert_check.npy")
assert len(C) == len(ch) and len(Qe) == n, "cached PubMedBERT embeddings don't match; rerun nofo_match_bio.py"
S["PubMedBERT"] = chunk_max(Qe, C)
Z = {k: (s - s.mean(1, keepdims=True)) / (s.std(1, keepdims=True) + 1e-9) for k, s in S.items()}

# %% [markdown]
# ## Project details: activity code, institute, fiscal years

# %%
stage("project details")
IC = {"NCI": "CA", "NIAID": "AI", "NIGMS": "GM", "NHLBI": "HL", "NIA": "AG", "NINDS": "NS", "NIDDK": "DK", "NIMH": "MH",
      "NICHD": "HD", "NIDA": "DA", "NIAAA": "AA", "NIEHS": "ES", "NHGRI": "HG", "NEI": "EY", "NIBIB": "EB", "NLM": "LM",
      "NIAMS": "AR", "NIDCR": "DE", "NIDCD": "DC", "NINR": "NR", "NIMHD": "MD", "NCCIH": "AT", "NCCAM": "AT",
      "NCATS": "TR", "FIC": "TW", "OD": "OD", "NCRR": "RR", "ORIP": "OD"}
meta = []
for x, t in zip(tg.nofo, full):
    acts = set(re.findall(r"\b([A-Z]{1,2}\d[0-9A-Z])\b", between(t, "Activity Code", "Announcement Type")[:400]))
    parts = between(t, "Components", "Funding Opportunity Title")
    ics = {IC[a] for a in re.findall(r"\(([A-Z]{2,6})\)", parts) if a in IC}
    mm = re.match(r"(?:RFA|PAR|PAS|PA)-([A-Z]{2})-\d{2}-", x)
    if mm:
        ics.add(mm.group(1))                     # issuing institute from the NOFO number
    if "Common Fund" in parts or "Roadmap" in parts:
        ics |= {"OD", "RM"}
    yr = re.search(r"-(\d{2})-", x)
    ny = 2000 + int(yr.group(1)) if yr else None
    o = re.findall(r"\b(?:19|20)\d\d\b", between(t, "Open Date", "\n\n\n")[:120])
    e = re.findall(r"\b(?:19|20)\d\d\b", between(t, "Expiration Date", "\n\n\n")[:120])
    meta.append({"acts": acts, "ics": ics, "open": int(o[0]) if o else ny, "exp": int(e[0]) if e else (ny + 3 if ny else None)})
meta = pd.DataFrame(meta)
say(f"NOFOs with activity codes {(meta.acts.str.len() > 0).mean():.0%}, institutes {(meta.ics.str.len() > 0).mean():.0%}")

act_ok, ic_ok, fy_ok = (np.ones((n, m), np.int8) for _ in range(3))
fy_gap = np.zeros((n, m), np.float32)
o, e = meta.open.fillna(0).to_numpy(), meta.exp.fillna(9999).to_numpy()
for i, (a, c, f) in enumerate(zip(check.activity, check.administering_ic, check.fiscal_years)):
    if isinstance(a, str) and a:                 # a NOFO with no parsed codes passes
        act_ok[i] = [not s or a in s for s in meta.acts]
    if isinstance(c, str) and c:
        ic_ok[i] = [not s or c in s for s in meta.ics]
    fy = np.array(sorted({int(y) for y in re.findall(r"\d{4}", str(f))}))[:, None]
    if fy.size:
        inside = ((fy >= o) & (fy <= e + 2)).any(0)
        fy_ok[i] = inside
        fy_gap[i] = np.where(inside, 0, np.minimum(np.abs(fy - o), np.abs(fy - e - 2)).min(0))
filt = (act_ok & ic_ok).astype(bool)
for name, F in [("activity code", act_ok), ("institute", ic_ok), ("fiscal year", fy_ok), ("activity code + institute", filt)]:
    say(f"  {name}: right NOFO kept {(F.astype(bool) & T).any(1).mean():.1%}, candidates kept {F.mean():.1%}")

# %% [markdown]
# ## Learning to rank (LightGBM LambdaMART), 5-fold cross-validation by project

# %%
stage("learning to rank")
rr = np.arange(n)[:, None]
TEXT = list(S)
RAW = ["TF-IDF", "BM25, best chunk", "PubMedBERT", "Title match"]


def rank(s):
    """Rank of the best right NOFO in each project's row."""
    best = np.where(T, s, -np.inf).max(1)
    return 1 + (s > best[:, None]).sum(1)


def ltr(details):
    prior = (Z["TF-IDF"] + Z["BM25, best chunk"] + Z["PubMedBERT"]) / 3
    if details:
        prior = np.where(filt, prior, prior - 100)
    cand = np.argsort(-prior, axis=1)[:, :K]
    feats = {f"{k} (z)": Z[k] for k in TEXT} | {f"{k} (raw)": S[k] for k in RAW}
    if details:
        feats |= {"Activity code allowed": act_ok, "Institute issues or joins": ic_ok, "Open in a funding year": fy_ok,
                  "Years from open window": fy_gap,
                  "RFA (vs. PAR)": np.broadcast_to(tg.nofo.str.startswith("RFA").to_numpy(), (n, m)),
                  "Number of activity codes": np.broadcast_to(meta.acts.str.len().to_numpy(), (n, m)),
                  "Number of institutes": np.broadcast_to(meta.ics.str.len().to_numpy(), (n, m))}
    X = np.stack([f[rr, cand] for f in feats.values()], -1).astype(np.float32)
    y = T[rr, cand].astype(int)
    fold = np.random.default_rng(SEED).permutation(n) % FOLDS
    pred, gain = np.empty((n, K), np.float32), np.zeros(len(feats))
    for f in range(FOLDS):
        tr = (fold != f) & (y.sum(1) > 0)        # train on projects whose right NOFO is among the candidates
        mdl = lgb.LGBMRanker(objective="lambdarank", n_estimators=300, learning_rate=0.05, num_leaves=31,
                             min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                             random_state=SEED, verbose=-1)
        mdl.fit(X[tr].reshape(-1, X.shape[2]), y[tr].ravel(), group=[K] * tr.sum())
        pred[fold == f] = mdl.predict(X[fold == f].reshape(-1, X.shape[2])).reshape(-1, K)
        gain += mdl.booster_.feature_importance("gain")
    s = prior - 1000                             # outside the candidates: prior order, below every candidate
    s[rr, cand] = pred
    say(f"  right NOFO among the {K} candidates: {y.any(1).mean():.1%}")
    return s, pd.Series(gain / gain.sum(), list(feats))


R = {}
blend = 0.6 * Z["TF-IDF"] + 0.4 * Z["PubMedBERT"]
for k in TEXT:
    R[(k, "Text only")] = rank(S[k])
R[("Blend: 0.6 TF-IDF + 0.4 PubMedBERT", "Text only")] = rank(blend)
s, _ = ltr(False)
R[("Learning to rank", "Text only")] = rank(s)
for k in ["TF-IDF", "PubMedBERT", "Title match"]:
    R[(k, "Activity code + institute filter")] = rank(np.where(filt, Z[k], Z[k] - 100))
R[("Blend: 0.6 TF-IDF + 0.4 PubMedBERT", "Activity code + institute filter")] = rank(np.where(filt, blend, blend - 100))
s, gain = ltr(True)
R[("Learning to rank", "Text + project details")] = rank(s)

tbl = pd.DataFrame([{"method": k, "inputs": g, "projects": len(r), "hit_at_1": (r <= 1).mean(), "hit_at_5": (r <= 5).mean(),
                     "hit_at_10": (r <= 10).mean(), "mrr": (1 / r).mean(), "candidates": m} for (k, g), r in R.items()])
tbl.to_csv(OUT / "nofo_matching_ltr.csv", index=False)
gain.sort_values(ascending=False).rename("share_of_gain").to_csv(OUT / "nofo_matching_ltr_features.csv")
print(tbl.round(3).to_string(index=False))
print(gain.sort_values(ascending=False).round(3).to_string())

# %%
show = [("TF-IDF", "Text only"), ("Blend: 0.6 TF-IDF + 0.4 PubMedBERT", "Text only"), ("Learning to rank", "Text only"),
        ("TF-IDF", "Activity code + institute filter"), ("Title match", "Activity code + institute filter"),
        ("Learning to rank", "Text + project details")]
sub = tbl.set_index(["method", "inputs"]).loc[show].reset_index()
fig, ax = plt.subplots(figsize=(10, 5.4))
fig.subplots_adjust(left=0.42, top=0.84, bottom=0.24)
y = np.arange(len(sub))
ax.barh(y, sub.hit_at_10 * 100, color=[pal.PROJECTS if i == len(sub) - 1 else pal.NEUTRAL for i in y])
for yy, v, mrr in zip(y, sub.hit_at_10 * 100, sub.mrr):
    ax.annotate(f"{v:.0f}%  (MRR {mrr:.2f})", (v, yy), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=pal.SIZES["axis"])
ax.set_yticks(y, [f"{a}\n{b}" for a, b in zip(sub.method, sub.inputs)])
ax.invert_yaxis()
ax.set_xlabel("Projects whose own NOFO is in the top 10 (%)")
ax.set_xlim(0, 110)
fig.suptitle("Adding what NIH knows about a project finds the right funding call far more often", x=0.02, ha="left",
             fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
fig.text(0.02, 0.005, f"{n:,} data science projects funded under targeted NOFOs, ranked against all {m:,} targeted NOFOs. "
         f"{FOLDS}-fold cross-validation by project.\nLearning to rank = LightGBM LambdaMART on text scores and project details "
         "(activity code, institute, fiscal years). MRR = mean of 1 ÷ rank of the right NOFO.\n" + SOURCE,
         fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")
fig.savefig(FIG / "09c_matching_ltr.png", dpi=200, bbox_inches="tight")
plt.close(fig)
_stop()
best = tbl.sort_values("mrr").iloc[-1]
say(f"done; best: {best.method} ({best.inputs}), top 10 {best.hit_at_10:.0%}, MRR {best.mrr:.2f}")
