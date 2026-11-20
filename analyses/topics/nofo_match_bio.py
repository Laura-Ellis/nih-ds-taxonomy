# %% [markdown]
# # B2b. NOFO matching with larger biomedical language models
#
# Follow-up to `nofo_match.py` (slide 6). Same check set: the same 2,000 data science projects funded under
# a targeted NOFO, ranked against the same 2,482 targeted NOFOs, scored by hit@k and MRR.
#
# **Question:** Do biomedical or long-text models find the NOFO a project was funded under better than TF-IDF?
#
# **Models** (all free, run locally; downloaded from Hugging Face on first run)
# - MedCPT (`ncbi/MedCPT-Article-Encoder`): NCBI's retriever trained on PubMed search logs. Abstracts and NOFO
#   chunks are both encoded as articles (512 tokens); a NOFO's score is its best ~200-word chunk.
# - MedCPT reranker (`ncbi/MedCPT-Cross-Encoder`): reads the abstract and the NOFO's best chunk together and
#   rescores MedCPT's top 20. Replaces the web-search cross-encoder from `nofo_match.py`.
# - BGE-M3 (`BAAI/bge-m3`): long-text model (up to 8,192 tokens). NOFOs split into ~1,000-word chunks, read
#   up to 2,048 tokens each, so most of Section I fits in a few chunks.
# - PubMedBERT embeddings (`NeuML/pubmedbert-base-embeddings`): PubMedBERT tuned for sentence similarity;
#   same 200-word chunks as MedCPT. The middle baseline.
# - Hybrid: reciprocal rank fusion of TF-IDF and the best model (score = Σ 1 ÷ (60 + rank)). Tests whether
#   exact terms and meaning together beat either one.
#
# **Definitions:** hit@k = share of projects whose own NOFO is in the top k; MRR (mean reciprocal rank) =
# mean of 1 ÷ the rank of the right NOFO. A project can fit more than one NOFO, so these are lower bounds.
#
# Inputs: same as `nofo_match.py`. Embeddings are cached in `data/interim/` after each model, so a stopped
# run picks up where it left off. Choose models with `NOFO_MODELS=medcpt,bge,pubmedbert` (default: all).
# Outputs: `reports/results/nofo_matching_bio.csv`, `reports/figures/topics/09b_matching_bio.png`.
#
# Runtime on a laptop CPU: roughly 30 minutes each for PubMedBERT and MedCPT, about an hour for the MedCPT
# reranker, and 2 to 4 hours for BGE-M3. Run overnight.

# %%
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
NOFO = ROOT / "data" / "raw" / "nofo"
FIG = ROOT / "reports" / "figures" / "topics"
SEED = 1
N_CHECK = int(os.environ.get("NOFO_CHECK", 2000))   # must match nofo_match.py
MODELS = os.environ.get("NOFO_MODELS", "medcpt,bge,pubmedbert").split(",")
RERANK_K = 20
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
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["nofos"])
txt = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet", columns=key + ["project_title", "abstract_text"])
docs = asg.merge(core, on=key, how="left").merge(txt, on=key, how="left")
assert len(docs) == len(asg), "project keys repeat; check the merge"
docs["text"] = docs.project_title.fillna("") + ". " + docs.abstract_text.fillna("")
docs["nofo_list"] = docs.nofos.fillna("").astype(str).str.upper().str.findall(r"(?:RFA|PAR|PAS|PA|NOT)-[A-Z0-9]+-\d+(?:-\d+)?")
tg_index = {n: i for i, n in enumerate(tg.nofo)}
docs["targets"] = docs.nofo_list.map(lambda ns: [tg_index[n] for n in ns if n in tg_index])
check = docs[docs.targets.str.len() > 0].sample(min(N_CHECK, (docs.targets.str.len() > 0).sum()), random_state=SEED)
truth = check.targets.tolist()
say(f"{len(check):,} projects checked against {len(tg):,} targeted NOFOs")


def chunk(words):
    rows = []
    for i, t in enumerate(tg.text):
        w = t.split()
        for s in range(0, max(len(w), 1), words):
            rows.append((i, " ".join(w[s:s + words])))
    return pd.DataFrame(rows, columns=["nofo_idx", "text"])


def best_by_nofo(Q, C, owner, batch=200):
    """Best-chunk cosine of each query to every NOFO, and that chunk's index."""
    order = np.argsort(owner, kind="stable")
    starts = np.r_[0, np.flatnonzero(np.diff(owner[order])) + 1]
    out = np.empty((len(Q), len(tg)), dtype=np.float32)
    arg = np.empty((len(Q), len(tg)), dtype=np.int64)
    Cs = C[order]
    for b0 in range(0, len(Q), batch):
        sims = Q[b0:b0 + batch] @ Cs.T
        out[b0:b0 + batch] = np.maximum.reduceat(sims, starts, axis=1)
        for j, (a0, a1) in enumerate(zip(starts, np.r_[starts[1:], len(order)])):
            arg[b0:b0 + batch, j] = order[a0 + sims[:, a0:a1].argmax(axis=1)]
    return out, arg


def ranks(S):
    order = np.argsort(-S, axis=1)
    pos = np.empty_like(order)
    pos[np.arange(len(S))[:, None], order] = np.arange(S.shape[1])[None, :]
    return np.array([min(pos[i, t] for t in ts) + 1 for i, ts in enumerate(truth)])


def cached(name, n, make):
    """Load cached embeddings if they match n rows; otherwise make and save them."""
    f = INTERIM / f"nofo_bio_{name}.npy"
    if f.exists() and np.load(f, mmap_mode="r").shape[0] == n:
        say(f"  {name}: cached")
        return np.load(f)
    E = make()
    np.save(f, E)
    return E

# %% [markdown]
# ## Baseline: TF-IDF (same settings as nofo_match.py)

# %%
stage("TF-IDF")
tf = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.5, sublinear_tf=True).fit(pd.concat([check.text, tg.text]))
S = {"TF-IDF": (tf.transform(check.text) @ tf.transform(tg.text).T).toarray()}

# %% [markdown]
# ## MedCPT article encoder and reranker

# %%
if "medcpt" in MODELS:
    import torch
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(os.cpu_count() or 4)

    def medcpt_encode(texts, batch=32):
        tok = AutoTokenizer.from_pretrained("ncbi/MedCPT-Article-Encoder")
        mod = AutoModel.from_pretrained("ncbi/MedCPT-Article-Encoder").eval()
        out = []
        with torch.no_grad():
            for b in range(0, len(texts), batch):
                enc = tok(texts[b:b + batch], truncation=True, padding=True, max_length=512, return_tensors="pt")
                v = mod(**enc).last_hidden_state[:, 0, :]            # CLS vector, as in the MedCPT examples
                out.append(torch.nn.functional.normalize(v, dim=1).numpy())
                if b % (batch * 50) == 0:
                    say(f"  MedCPT {b:,} of {len(texts):,}")
        return np.vstack(out).astype(np.float32)

    stage("MedCPT encoder")
    ch = chunk(200)
    C = cached("medcpt_chunks", len(ch), lambda: medcpt_encode(ch.text.tolist()))
    Q = cached("medcpt_check", len(check), lambda: medcpt_encode(check.text.tolist()))
    S["MedCPT"], best = best_by_nofo(Q, C, ch.nofo_idx.to_numpy())

    stage("MedCPT reranker")
    f = INTERIM / "nofo_bio_medcpt_rerank.npy"
    top_k = np.argsort(-S["MedCPT"], axis=1)[:, :RERANK_K]
    if f.exists() and np.load(f).shape == top_k.shape:
        sc = np.load(f)
    else:
        tok = AutoTokenizer.from_pretrained("ncbi/MedCPT-Cross-Encoder")
        ce = AutoModelForSequenceClassification.from_pretrained("ncbi/MedCPT-Cross-Encoder").eval()
        sc = np.empty(top_k.shape, dtype=np.float32)
        with torch.no_grad():
            for i in range(len(check)):
                pairs = [[check.text.iloc[i], ch.text.iloc[best[i, j]]] for j in top_k[i]]
                enc = tok(pairs, truncation=True, padding=True, max_length=512, return_tensors="pt")
                sc[i] = ce(**enc).logits.squeeze(dim=1).numpy()
                if i % 200 == 0:
                    say(f"  reranked {i:,} of {len(check):,}")
        np.save(f, sc)
    S_ce = S["MedCPT"] - 100                  # outside the top k keeps MedCPT's order, below every reranked NOFO
    for i in range(len(check)):
        S_ce[i, top_k[i]] = sc[i]
    S["MedCPT + reranker"] = S_ce

# %% [markdown]
# ## PubMedBERT embeddings and BGE-M3 (sentence-transformers)

# %%
from sentence_transformers import SentenceTransformer  # noqa: E402

for tag, model_id, words, max_len, label in [
        ("pubmedbert", "NeuML/pubmedbert-base-embeddings", 200, 512, "PubMedBERT embeddings"),
        ("bge", "BAAI/bge-m3", 1000, 2048, "BGE-M3 (long text)")]:
    if tag not in MODELS:
        continue
    stage(label)
    st = SentenceTransformer(model_id)
    st.max_seq_length = max_len
    ch = chunk(words)
    batch = 4 if tag == "bge" else 32
    C = cached(f"{tag}_chunks", len(ch), lambda: st.encode(ch.text.tolist(), batch_size=batch, show_progress_bar=True,
                                                             normalize_embeddings=True))
    Q = cached(f"{tag}_check", len(check), lambda: st.encode(check.text.tolist(), batch_size=batch, show_progress_bar=True,
                                                               normalize_embeddings=True))
    S[label], _ = best_by_nofo(Q, C, ch.nofo_idx.to_numpy())
    del st

# %% [markdown]
# ## Results, plus a TF-IDF hybrid with the best model

# %%
stage("results")
R = {m: ranks(s) for m, s in S.items()}
best_model = max((m for m in R if m != "TF-IDF"), key=lambda m: (1 / R[m]).mean(), default=None)
if best_model:
    def rank_all(s):
        return np.argsort(np.argsort(-s, axis=1), axis=1) + 1
    R[f"Hybrid: TF-IDF + {best_model}"] = ranks(1 / (60 + rank_all(S["TF-IDF"])) + 1 / (60 + rank_all(S[best_model])))
tbl = pd.DataFrame([{"method": m, "projects": len(r), "hit_at_1": (r <= 1).mean(), "hit_at_5": (r <= 5).mean(),
                     "hit_at_10": (r <= 10).mean(), "mrr": (1 / r).mean(), "candidates": len(tg)} for m, r in R.items()])
prev = OUT / "nofo_matching_check.csv"
if prev.exists():
    old = pd.read_csv(prev)
    tbl = pd.concat([old[old.method != "TF-IDF"].drop(columns=["vectors"], errors="ignore").assign(run="nofo_match.py"),
                     tbl.assign(run="nofo_match_bio.py")], ignore_index=True)
tbl = tbl.sort_values("mrr", ascending=False)
tbl.to_csv(OUT / "nofo_matching_bio.csv", index=False)
print(tbl.round(3).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(10, 0.55 * len(tbl) + 2.2))
fig.subplots_adjust(left=0.36, top=0.86, bottom=0.2)
y = np.arange(len(tbl))
ax.barh(y, tbl.hit_at_10 * 100, color=[pal.PROJECTS if m == "TF-IDF" else pal.NEUTRAL for m in tbl.method])
for yy, v, mrr in zip(y, tbl.hit_at_10 * 100, tbl.mrr):
    ax.annotate(f"{v:.0f}%  (MRR {mrr:.2f})", (v, yy), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=pal.SIZES["axis"])
ax.set_yticks(y, tbl.method)
ax.invert_yaxis()
ax.set_xlabel("Projects whose own NOFO is in the top 10 (%)")
ax.set_xlim(0, 100)
fig.suptitle("Do biomedical models find the right funding opportunity better than word matching?", x=0.02, ha="left",
             fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
fig.text(0.02, 0.005, f"{len(check):,} data science projects funded under targeted NOFOs (RFA, PAR), ranked against all {len(tg):,} "
         "targeted NOFOs.\nMRR = mean of 1 ÷ rank of the right NOFO. Hybrid = reciprocal rank fusion (1 ÷ (60 + rank), summed).\n"
         + SOURCE, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")
fig.savefig(FIG / "09b_matching_bio.png", dpi=200, bbox_inches="tight")
plt.close(fig)
_stop()
say(f"done; best model: {best_model}")
