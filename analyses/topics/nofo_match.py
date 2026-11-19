# %% [markdown]
# # B2. What draws data science in: funding opportunities (NOFOs)
#
# Analysis B, slides 5 and 6. Uses the NIH Guide text saved by `src/nofo_pull.py`.
#
# **Questions**
# 1. Do funding opportunities that ask for data science fund more of it?
# 2. Which research topics have no targeted funding opportunity that matches them?
# 3. How well can text matching find the opportunity a project was funded under? (checks the matching itself)
#
# **Definitions**
# - NOFO = notice of funding opportunity. Targeted = RFA or PAR (written for a specific area); parent = PA
#   (broad, investigator-initiated announcements such as the parent R01)
# - NOFO text = Section I, the funding opportunity description
# - Asks for data science = the taxonomy's keyword rules find a data science category in Section I (the same
#   rules used for project abstracts). Asks for AI = an AI category is found
# - Data science share of a NOFO = its data science records ÷ all its records (`ds_by_nofo.csv`)
# - Matching methods, each scoring a project abstract against every targeted NOFO:
#   - TF-IDF: cosine similarity of word weights (words rare across documents count more)
#   - Sentence embeddings: cosine similarity of `all-MiniLM-L6-v2` vectors; a NOFO is split into ~200-word
#     chunks and its score is its best chunk
#   - Cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2` reads the abstract and the NOFO's best chunk
#     together and scores the pair; it rescores the embeddings' top `RERANK_K`
# - Check set = data science projects funded under a targeted NOFO that has text; the right answer is the
#   NOFO the project was funded under. Hit@k = share whose NOFO is in the top k; MRR = mean of 1 ÷ rank.
#   Projects can fit more than one NOFO, so these are lower bounds
# - Topic with no matching NOFO: few of its projects came through targeted NOFOs, and its closest targeted
#   NOFO is not very similar (topic centroid vs. NOFO chunks, cosine)
#
# Inputs: `data/raw/nofo/`, `reports/results/ds_by_nofo.csv`, `exporter_core_projects_labeled.parquet`,
# `exporter_flagged_text.parquet`, `data/interim/topic_assignments.parquet` and the cached embeddings,
# `analyses/topics/topic_names.csv`.
# Outputs: `reports/results/nofo_*.csv`, `reports/figures/topics/08_*.png` to `10_*.png`.
#
# Runs locally and free. The cross-encoder needs `sentence-transformers` (already installed for topics).

# %%
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
NOFO = ROOT / "data" / "raw" / "nofo"
FIG = ROOT / "reports" / "figures" / "topics"
FIG.mkdir(parents=True, exist_ok=True)
SEED = 1
EMB_MODEL = "all-MiniLM-L6-v2"
CE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
N_CHECK = int(os.environ.get("NOFO_CHECK", 2000))   # projects in the matching check
RERANK_K = 20
CHUNK_WORDS = 200
MIN_RECORDS = 20                                     # NOFOs with fewer records are left out of question 1
MIN_TOPIC = 100
SOURCE = "Source: NIH RePORTER API; NIH Guide for Grants and Contracts; NIH Data Science Taxonomy."
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


def kind(n):
    return "Targeted (RFA)" if n.startswith("RFA") else "Targeted (PAR)" if n.startswith("PAR") else \
        "Parent and other PA" if n.startswith("PA") else "Other"

# %% [markdown]
# ## NOFO text, titles, and whether each asks for data science

# %%
stage("NOFO text")
man = pd.read_csv(NOFO / "manifest.csv").drop_duplicates("nofo", keep="last")
nofos = man[man.status == 200][["nofo"]].copy()
nofos["text"] = [(NOFO / "section1" / f"{n}.txt").read_text(encoding="utf-8") if (NOFO / "section1" / f"{n}.txt").exists()
                 else "" for n in nofos.nofo]


def nofo_title(n):
    f = NOFO / "text" / f"{n}.txt"
    if not f.exists():
        return ""
    m = re.search(r"Funding Opportunity Title\s+(.+?)\s+(?:Activity Code|Announcement Type)", f.read_text(encoding="utf-8"), re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


nofos["title"] = nofos.nofo.map(nofo_title)
nofos = nofos[nofos.text.str.len() > 200].reset_index(drop=True)
nofos["kind"] = nofos.nofo.map(kind)
lab = tx.label_projects(nofos.assign(project_title=nofos.title, abstract_text=nofos.text))
nofos["asks_ds"], nofos["asks_ai"] = lab.data_science_related.values, lab.ai_related.values
say(f"{len(nofos):,} NOFOs with Section I text; {nofos.asks_ds.mean():.0%} ask for data science, {nofos.asks_ai.mean():.0%} for AI")

# %% [markdown]
# ## 1. Do NOFOs that ask for data science fund more of it?

# %%
stage("question 1")
dsn = pd.read_csv(OUT / "ds_by_nofo.csv")
q1 = nofos.merge(dsn[["nofo", "records", "ds_records", "ds_share", "ai_share"]], on="nofo")
q1 = q1[q1.records >= MIN_RECORDS]
by_kind = (q1.groupby(["kind", "asks_ds"]).agg(nofos=("nofo", "size"), records=("records", "sum"), ds_records=("ds_records", "sum"),
                                              median_ds_share=("ds_share", "median"))
           .assign(pooled_ds_share=lambda d: d.ds_records / d.records).reset_index())
by_kind.to_csv(OUT / "nofo_ds_share_by_ask.csv", index=False)
top = (q1.sort_values("ds_records", ascending=False).head(25)
       [["nofo", "title", "kind", "records", "ds_records", "ds_share", "asks_ds", "asks_ai"]])
top.to_csv(OUT / "nofo_top_by_ds_records.csv", index=False)
print(by_kind.round(3).to_string(index=False))
print(top.head(10).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(9, 4.8))
fig.subplots_adjust(left=0.27, top=0.82, bottom=0.26)
kinds = ["Targeted (RFA)", "Targeted (PAR)", "Parent and other PA"]
yy = np.arange(len(kinds))
for off, ask, col, lab_ in [(0.2, True, pal.PROJECTS, "Asks for data science"), (-0.2, False, pal.NEUTRAL, "Does not")]:
    v = [by_kind[(by_kind.kind == k) & (by_kind.asks_ds == ask)].median_ds_share.sum() * 100 for k in kinds]
    ax.barh(yy + off, v, 0.38, color=col, label=lab_)
    for y_, x in zip(yy + off, v):
        ax.annotate(f"{x:.0f}%", (x, y_), xytext=(4, 0), textcoords="offset points", va="center", fontsize=pal.SIZES["axis"])
ax.set_yticks(yy, kinds)
ax.invert_yaxis()
ax.set_xlabel("Median share of a NOFO's funded records that are data science (%)")
ax.legend(frameon=False, loc="lower right")
title(fig, "Funding opportunities that ask for data science fund more of it")
note(fig, f"NOFOs with at least {MIN_RECORDS} funded records. Asks for data science = taxonomy keyword rules find a data science\n"
          "category in the NOFO's Section I.\n" + SOURCE)
save(fig, "08_nofo_ds_share")

# %% [markdown]
# ## Vectors for abstracts and targeted NOFO chunks

# %%
stage("vectors")
key = ["core_project_number", "subproject_id"]
asg = pd.read_parquet(INTERIM / "topic_assignments.parquet")
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["nofos"])
txt = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet", columns=key + ["project_title", "abstract_text"])
docs = asg.merge(core, on=key, how="left").merge(txt, on=key, how="left")
assert len(docs) == len(asg), "project keys repeat; check the merge"
docs["text"] = docs.project_title.fillna("") + ". " + docs.abstract_text.fillna("")
docs["nofo_list"] = docs.nofos.fillna("").astype(str).str.upper().str.findall(r"(?:RFA|PAR|PAS|PA|NOT)-[A-Z0-9]+-\d+(?:-\d+)?")

tg = nofos[nofos.kind.str.startswith("Targeted")].reset_index(drop=True)
chunks = []
for i, t in enumerate(tg.text):
    w = t.split()
    for s in range(0, max(len(w), 1), CHUNK_WORDS):
        chunks.append((i, " ".join(w[s:s + CHUNK_WORDS])))
ch = pd.DataFrame(chunks, columns=["nofo_idx", "text"])
say(f"{len(tg):,} targeted NOFOs, {len(ch):,} chunks")

emb_path = INTERIM / f"topic_embeddings_{EMB_MODEL}.npy"
nofo_emb_path = INTERIM / f"nofo_chunk_embeddings_{EMB_MODEL}.npy"
try:
    from sentence_transformers import SentenceTransformer
    A = np.load(emb_path)
    assert A.shape[0] == len(docs), "cached abstract embeddings don't match topic_assignments; rerun topics.py"
    if nofo_emb_path.exists() and np.load(nofo_emb_path, mmap_mode="r").shape[0] == len(ch):
        C = np.load(nofo_emb_path)
    else:
        st = SentenceTransformer(EMB_MODEL)
        st.max_seq_length = 256
        C = st.encode(ch.text.tolist(), batch_size=64, show_progress_bar=True, normalize_embeddings=True)
        np.save(nofo_emb_path, C)
    VEC = "sentence embeddings"
except Exception as e:
    say(f"sentence embeddings unavailable ({type(e).__name__}); using TF-IDF + SVD vectors instead")
    tfv = TfidfVectorizer(stop_words="english", min_df=5, max_df=0.5, sublinear_tf=True).fit(pd.concat([docs.text, ch.text]))
    svd = TruncatedSVD(256, random_state=SEED).fit(tfv.transform(docs.text))
    A, C = normalize(svd.transform(tfv.transform(docs.text))), normalize(svd.transform(tfv.transform(ch.text)))
    VEC = "TF-IDF + SVD (sentence embeddings unavailable)"
chunk_owner = ch.nofo_idx.to_numpy()


def best_by_nofo(Q, batch=200):
    """For each query vector, its best-chunk similarity to every targeted NOFO, and that chunk's index."""
    order = np.argsort(chunk_owner, kind="stable")
    starts = np.r_[0, np.flatnonzero(np.diff(chunk_owner[order])) + 1]
    out = np.empty((len(Q), len(tg)), dtype=np.float32)
    arg = np.empty((len(Q), len(tg)), dtype=np.int64)
    Cs = C[order]
    for b0 in range(0, len(Q), batch):
        sims = Q[b0:b0 + batch] @ Cs.T
        out[b0:b0 + batch] = np.maximum.reduceat(sims, starts, axis=1)
        for j, (a0, a1) in enumerate(zip(starts, np.r_[starts[1:], len(order)])):
            arg[b0:b0 + batch, j] = order[a0 + sims[:, a0:a1].argmax(axis=1)]
    return out, arg


# %% [markdown]
# ## 3. Matching check: can text find the NOFO a project was funded under?

# %%
stage("matching check")
tg_index = {n: i for i, n in enumerate(tg.nofo)}
docs["targets"] = docs.nofo_list.map(lambda ns: [tg_index[n] for n in ns if n in tg_index])
check = docs[docs.targets.str.len() > 0].sample(min(N_CHECK, (docs.targets.str.len() > 0).sum()), random_state=SEED)
qi = check.index.to_numpy()
say(f"{(docs.targets.str.len() > 0).sum():,} data science projects funded under a targeted NOFO with text; checking {len(check):,}")

tf = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.5, sublinear_tf=True).fit(pd.concat([check.text, tg.text]))
S_tfidf = (tf.transform(check.text) @ tf.transform(tg.text).T).toarray()
S_emb, best_chunk = best_by_nofo(A[qi])


def ranks(S, truth):
    order = np.argsort(-S, axis=1)
    pos = np.empty_like(order)
    pos[np.arange(len(S))[:, None], order] = np.arange(S.shape[1])[None, :]
    return np.array([min(pos[i, t] for t in ts) + 1 for i, ts in enumerate(truth)])


truth = check.targets.tolist()
R = {"TF-IDF": ranks(S_tfidf, truth), f"Sentence embeddings": ranks(S_emb, truth)}
CE = "not run"
try:
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(CE_MODEL, max_length=512)
    top_k = np.argsort(-S_emb, axis=1)[:, :RERANK_K]
    pairs = [(check.text.iloc[i], ch.text.iloc[best_chunk[i, j]]) for i in range(len(check)) for j in top_k[i]]
    sc = np.asarray(ce.predict(pairs, batch_size=64, show_progress_bar=True)).reshape(len(check), RERANK_K)
    S_ce = S_emb.copy() - 100            # outside the top k keeps the embedding order, below every reranked NOFO
    for i in range(len(check)):
        S_ce[i, top_k[i]] = sc[i]
    R["Cross-encoder (reranks top 20)"] = ranks(S_ce, truth)
    CE = CE_MODEL
except Exception as e:
    say(f"cross-encoder unavailable ({type(e).__name__}); skipped")

check_tbl = pd.DataFrame([{"method": m, "projects": len(r), "hit_at_1": (r <= 1).mean(), "hit_at_5": (r <= 5).mean(),
                           "hit_at_10": (r <= 10).mean(), "mrr": (1 / r).mean(), "candidates": len(tg)} for m, r in R.items()])
check_tbl.assign(vectors=VEC).to_csv(OUT / "nofo_matching_check.csv", index=False)
print(check_tbl.round(3).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(9, 4.6))
fig.subplots_adjust(left=0.1, top=0.8, bottom=0.27)
ks, w = ["hit_at_1", "hit_at_5", "hit_at_10"], 0.8 / len(check_tbl)
cols = [pal.NEUTRAL, pal.PROJECTS, pal.FUNDING][: len(check_tbl)]
for i, (r, c) in enumerate(zip(check_tbl.itertuples(), cols)):
    v = [getattr(r, k) * 100 for k in ks]
    xs = np.arange(3) + (i - (len(check_tbl) - 1) / 2) * w
    ax.bar(xs, v, w, color=c, label=r.method)
    for x, h in zip(xs, v):
        ax.annotate(f"{h:.0f}%", (x, h), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=pal.SIZES["axis"])
ax.set_xticks(range(3), ["Top 1", "Top 5", "Top 10"])
ax.set_ylabel("Projects whose own NOFO is ranked (%)")
ax.set_ylim(0, 105)
ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.12))
title(fig, "How often text matching finds the NOFO a project was funded under")
note(fig, f"{len(check):,} data science projects funded under targeted NOFOs (RFA, PAR), matched against all {len(tg):,} targeted NOFOs.\n"
          "A project can fit several NOFOs, so these are lower bounds.\n" + SOURCE)
save(fig, "09_matching_check")

# %% [markdown]
# ## 2. Topics with no matching targeted NOFO

# %%
stage("topics without a NOFO")
names = pd.read_csv(ROOT / "analyses" / "topics" / "topic_names.csv")
docs["any_targeted"] = docs.nofo_list.map(lambda ns: any(kind(n).startswith("Targeted") for n in ns))
docs["has_nofo"] = docs.nofo_list.str.len() > 0
cent_topics = sorted(docs.bt_topic.unique())
cent = normalize(np.vstack([A[docs.bt_topic.to_numpy() == t].mean(axis=0) for t in cent_topics]))
S_top, _ = best_by_nofo(cent)
gap = pd.DataFrame({"topic": cent_topics, "projects": docs.groupby("bt_topic").size().reindex(cent_topics).values,
                    "targeted_share": docs[docs.has_nofo].groupby("bt_topic").any_targeted.mean().reindex(cent_topics).values,
                    "best_similarity": S_top.max(axis=1),
                    "best_nofo": [tg.nofo[j] for j in S_top.argmax(axis=1)],
                    "best_nofo_title": [tg.title[j] for j in S_top.argmax(axis=1)]}).merge(names, on="topic")
gap = gap[gap.projects >= MIN_TOPIC]
gap["sim_rank"] = gap.best_similarity.rank(pct=True)
gap["targeted_rank"] = gap.targeted_share.rank(pct=True)
gap["gap_score"] = 1 - (gap.sim_rank + gap.targeted_rank) / 2
gap = gap.sort_values("gap_score", ascending=False)
gap.to_csv(OUT / "nofo_topic_gaps.csv", index=False)
print(gap.head(12)[["name", "projects", "targeted_share", "best_similarity", "best_nofo"]].round(3).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(10, 7))
fig.subplots_adjust(left=0.1, top=0.88, bottom=0.17)
ax.scatter(gap.best_similarity, gap.targeted_share * 100, s=np.sqrt(gap.projects) * 4, color=pal.NEUTRAL, edgecolor=pal.MUTED, lw=0.5)
lo = gap.head(8)
ax.scatter(lo.best_similarity, lo.targeted_share * 100, s=np.sqrt(lo.projects) * 4, color=pal.PROJECTS)
for r in lo.itertuples():
    ax.annotate(r.name, (r.best_similarity, r.targeted_share * 100), xytext=(6, 4), textcoords="offset points",
                fontsize=pal.SIZES["axis"], color=pal.INK)
ax.set_xlabel("Similarity to the closest targeted NOFO (cosine)")
ax.set_ylabel("Projects funded through targeted NOFOs (%)")
title(fig, "Topics that no targeted funding opportunity matches")
note(fig, f"One dot per topic with at least {MIN_TOPIC} projects; size = projects. Dark = the 8 lowest on both measures (rank average).\n"
          f"Targeted = RFA or PAR. Similarity of the topic's average abstract vector to its closest NOFO chunk ({VEC}).\n" + SOURCE)
save(fig, "10_topics_without_nofo")
_stop()
say(f"done (vectors: {VEC}; cross-encoder: {CE})")
