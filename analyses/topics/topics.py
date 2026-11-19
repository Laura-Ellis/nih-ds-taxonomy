# %% [markdown]
# # B1. What data science at NIH works on, and what's rising
#
# Analysis B, part 1 (`analyses/topics/`). Finds topics in data science project abstracts three ways and
# compares them:
# - **LDA** (latent Dirichlet allocation): topics as word-count patterns; each project gets a mix of topics
# - **BERTopic**: sentence embeddings, clustered; each project gets one topic, described by its most distinctive words
# - **Taxonomy groups**: the NIH Data Science Taxonomy's own labels (method, software, infrastructure, and so on)
#
# **Definitions**
# - Data science project = core project (or subproject) with substantive data science (`ds_label` = Y)
# - Active in a FY = the project has a record that fiscal year; FY2026 is preliminary and left out of trends
# - Topic share (FY) = active data science projects whose main topic is the topic ÷ all active data science
#   projects that FY. Main topic = the LDA topic with the highest weight, or the BERTopic cluster
# - Growth = mean share FY2023–FY2025 ÷ mean share FY2016–FY2018
# - Trend test = Kendall's τ between FY and share, FY2016–FY2025 (a rank test; p < 0.05 = a steady rise or fall)
# - Fast riser = growth ≥ 1.5, τ > 0 with p < 0.05, and at least `MIN_PROJECTS` projects
# - Lift = a taxonomy group's share inside a topic ÷ its share across all data science projects (1.0 = no link)
# - Agreement between methods = normalized mutual information (NMI, 0 = unrelated, 1 = the same grouping) and
#   adjusted Rand index (ARI, 0 = chance)
#
# Inputs: `exporter_core_projects_labeled.parquet`, `exporter_flagged_text.parquet`, `taxonomy/categories.yaml`.
# Outputs: `reports/results/topics_*.csv`, `reports/figures/topics/*.png`, embeddings cached in `data/interim/`.
#
# Needs (local, free): `pip install sentence-transformers bertopic scipy`. Without them the notebook still runs,
# using TF-IDF vectors in place of sentence embeddings and k-means in place of BERTopic, and says so.

# %%
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import kendalltau
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation, TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer, TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "topics"
FIG.mkdir(parents=True, exist_ok=True)
SEED = 1
FY_FIRST, FY_LAST_FULL, FY_PRELIM = 2016, 2025, 2026
LDA_K = [20, 30, 40]          # topic counts to try; the best UMass coherence wins
MIN_TOPIC = 60                # smallest BERTopic cluster
MIN_PROJECTS = 100            # smallest topic that can be a fast riser
EMB_MODEL = "all-MiniLM-L6-v2"
SAMPLE = int(os.environ.get("TOPICS_SAMPLE", 0))   # test runs only: use this many projects
pal.use_style()


_stop = None


def stage(name):
    """Start a progress heartbeat for the next step and close the previous one."""
    global _stop
    if _stop:
        _stop()
    _stop = start(name)


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def note(fig, text, y=0.01):
    fig.text(0.02, y, text, fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6, va="bottom")

# %% [markdown]
# ## Data science abstracts

# %%
stage("load abstracts")
key = ["core_project_number", "subproject_id"]
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["fiscal_years", "ds_label", "model_categories", "administering_ic"])
core = core[core.ds_label.eq("Y")]
text = pd.read_parquet(PROCESSED / "exporter_flagged_text.parquet", columns=key + ["project_title", "abstract_text"])
docs = core.merge(text, on=key, how="inner")
BOILER = re.compile(r"(project summary|abstract|narrative|public health relevance|description \(provided by applicant\)|"
                    r"overall|summary)\s*[:/\-–]*\s*", re.I)
docs["text"] = (docs.project_title.fillna("") + ". " + docs.abstract_text.fillna("")).str.replace(BOILER, " ", regex=True)
docs = docs[docs.text.str.len() > 300].reset_index(drop=True)
if SAMPLE:
    docs = docs.sample(min(SAMPLE, len(docs)), random_state=SEED).reset_index(drop=True)
docs["fys"] = docs.fiscal_years.astype(str).str.findall(r"\d{4}").map(lambda ys: sorted({int(y) for y in ys}))
say(f"{len(docs):,} data science projects with text")

# %% [markdown]
# ## Taxonomy groups per project

# %%
tax = yaml.safe_load((ROOT / "taxonomy" / "categories.yaml").read_text(encoding="utf-8"))
GLABEL = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
          "artificial_intelligence": "Artificial intelligence", "software_tools": "Software and tools",
          "data_infrastructure": "Data infrastructure", "data_sharing": "Data infrastructure",
          "responsible_ai": "Responsible AI", "workforce": "Workforce"}
cat_group = {}
for d in tax["dimensions"]:
    for c in d.get("categories", []):
        g = c.get("group") or d["id"]
        if g in GLABEL:
            cat_group[c["id"]] = GLABEL[g]
GROUPS = sorted(set(GLABEL.values()))
cats = docs.model_categories.fillna("").str.split("; ")
for g in GROUPS:
    docs[g] = cats.map(lambda cs: any(cat_group.get(c) == g for c in cs))
docs["main_group"] = docs[GROUPS].idxmax(axis=1).where(docs[GROUPS].any(axis=1), "None")
overall_group = docs[GROUPS].mean()
overall_group

# %% [markdown]
# ## LDA
#
# Word counts (single words and two-word phrases), common English words and grant boilerplate removed. UMass
# coherence = mean over each topic's top-10 word pairs of log((documents with both + 1) ÷ documents with the
# first); closer to 0 is more coherent.

# %%
stage("LDA")
STOP = list(ENGLISH_STOP_WORDS | {
    "aim", "aims", "specific", "propose", "proposed", "project", "projects", "study", "studies", "research",
    "data", "using", "use", "used", "new", "novel", "develop", "development", "approach", "approaches", "based",
    "application", "applications", "provide", "program", "center", "core", "investigator", "investigators",
    "goal", "goals", "long", "term", "overall", "proposal", "significance", "innovation", "health", "public",
    "relevance", "summary", "abstract", "narrative", "phase", "year", "years", "high", "including", "important",
    "understanding", "potential", "methods", "method", "results", "analysis", "analyses", "work", "support",
    "nih", "funded", "renewal", "competing", "continuation", "award", "grant"})
cv = CountVectorizer(stop_words=STOP, ngram_range=(1, 2), min_df=25 if not SAMPLE else 5, max_df=0.4,
                     max_features=20000, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b")
X = cv.fit_transform(docs.text)
vocab = np.array(cv.get_feature_names_out())
Xb = (X > 0).astype(np.int32).tocsc()
df_ = np.asarray(Xb.sum(axis=0)).ravel()


def umass(top_idx):
    s, n = 0.0, 0
    for i in range(1, len(top_idx)):
        for j in range(i):
            a, b = top_idx[i], top_idx[j]
            both = Xb[:, a].multiply(Xb[:, b]).sum()
            s += np.log((both + 1) / df_[b])
            n += 1
    return s / n


fits = {}
for k in LDA_K:
    m = LatentDirichletAllocation(n_components=k, learning_method="online", batch_size=2048, max_iter=15,
                                  random_state=SEED, n_jobs=-1).fit(X)
    tops = [np.argsort(-c)[:10] for c in m.components_]
    fits[k] = (m, np.mean([umass(t) for t in tops]))
    say(f"LDA k={k}: UMass coherence {fits[k][1]:.3f}")
K = max(fits, key=lambda k: fits[k][1])
lda = fits[K][0]
theta = lda.transform(X)
docs["lda_topic"] = theta.argmax(axis=1)
lda_terms = pd.DataFrame({"topic": range(K), "terms": [", ".join(vocab[np.argsort(-c)[:10]]) for c in lda.components_],
                          "projects": np.bincount(docs.lda_topic, minlength=K)})
pd.DataFrame({"k": list(fits), "umass": [v[1] for v in fits.values()]}).to_csv(OUT / "topics_lda_coherence.csv", index=False)
say(f"LDA: k = {K} chosen")
lda_terms

# %% [markdown]
# ## Sentence embeddings and BERTopic
#
# Each abstract becomes a 384-number vector (`all-MiniLM-L6-v2`, first 256 word pieces), cached so reruns
# skip this step. BERTopic reduces the vectors with UMAP, clusters them with HDBSCAN, then reassigns projects
# left out of every cluster to their nearest topic.

# %%
stage("embeddings")
emb_path = INTERIM / f"topic_embeddings_{EMB_MODEL}{'_sample' if SAMPLE else ''}.npy"
EMB_METHOD = "sentence embeddings"
try:
    from sentence_transformers import SentenceTransformer
    if emb_path.exists() and np.load(emb_path, mmap_mode="r").shape[0] == len(docs):
        emb = np.load(emb_path)
    else:
        st = SentenceTransformer(EMB_MODEL)
        st.max_seq_length = 256
        emb = st.encode(docs.text.tolist(), batch_size=64, show_progress_bar=True, normalize_embeddings=True)
        np.save(emb_path, emb)
except Exception as e:  # not installed, or the model can't be downloaded
    EMB_METHOD = "TF-IDF + SVD (sentence embeddings unavailable)"
    say(f"sentence embeddings unavailable ({type(e).__name__}); using TF-IDF + SVD instead")
    tf = TfidfVectorizer(stop_words=STOP, min_df=5, max_df=0.4, sublinear_tf=True).fit_transform(docs.text)
    emb = normalize(TruncatedSVD(256, random_state=SEED).fit_transform(tf))
say(f"vectors: {EMB_METHOD}, {emb.shape}")

# %%
stage("BERTopic")
topic_vec = CountVectorizer(stop_words=STOP, ngram_range=(1, 2), min_df=10 if not SAMPLE else 3,
                            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b")
try:
    from bertopic import BERTopic
    from umap import UMAP
    bt = BERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=SEED),
                  vectorizer_model=topic_vec, min_topic_size=MIN_TOPIC, calculate_probabilities=False)
    t, _ = bt.fit_transform(docs.text.tolist(), embeddings=emb)
    t = bt.reduce_outliers(docs.text.tolist(), t, strategy="embeddings", embeddings=emb)
    bt.update_topics(docs.text.tolist(), topics=t, vectorizer_model=topic_vec)
    docs["bt_topic"] = t
    BT_METHOD = "BERTopic"
    bt_words = {k: ", ".join(w for w, _ in v[:10]) for k, v in bt.get_topics().items() if k != -1}
except ImportError:
    BT_METHOD = "k-means on vectors + class TF-IDF (bertopic not installed)"
    km = KMeans(n_clusters=K, n_init=4, random_state=SEED).fit(emb)
    docs["bt_topic"] = km.labels_
    C = topic_vec.fit_transform(docs.groupby("bt_topic").text.apply(" ".join))
    tfc = normalize(C.multiply(np.log(1 + C.sum(axis=1).mean() / (np.asarray(C.sum(axis=0)).ravel() + 1))), norm="l1")
    words = np.array(topic_vec.get_feature_names_out())
    bt_words = {k: ", ".join(words[np.argsort(-tfc[i].toarray().ravel())[:10]]) for i, k in enumerate(sorted(docs.bt_topic.unique()))}
docs["bt_topic"] = docs.bt_topic.astype(int)
bt_terms = (docs.groupby("bt_topic").size().rename("projects").reset_index().rename(columns={"bt_topic": "topic"})
            .assign(terms=lambda d: d.topic.map(bt_words)))
say(f"{BT_METHOD}: {docs.bt_topic.nunique()} topics")
bt_terms.sort_values("projects", ascending=False).head(15)

# %% [markdown]
# ## How the three methods agree
#
# For each topic: its most over-represented taxonomy group (highest lift) and that group's share inside the topic.

# %%
def group_profile(col, method):
    g = docs.groupby(col)[GROUPS].mean()
    lift = g / overall_group
    top = lift.idxmax(axis=1)
    return pd.DataFrame({"method": method, "topic": g.index, "projects": docs.groupby(col).size().values,
                         "top_group": top.values, "top_group_share": [g.loc[i, top[i]] for i in g.index],
                         "top_group_lift": lift.max(axis=1).values})


agree = pd.concat([group_profile("lda_topic", f"LDA (k = {K})"), group_profile("bt_topic", BT_METHOD)])
agree["terms"] = [ (lda_terms.set_index("topic").terms if m.startswith("LDA") else bt_terms.set_index("topic").terms).get(t, "")
                   for m, t in zip(agree.method, agree.topic)]
method_agree = pd.DataFrame([
    {"pair": "LDA vs. BERTopic", "nmi": normalized_mutual_info_score(docs.lda_topic, docs.bt_topic),
     "ari": adjusted_rand_score(docs.lda_topic, docs.bt_topic)},
    {"pair": "LDA vs. taxonomy main group", "nmi": normalized_mutual_info_score(docs.lda_topic, docs.main_group),
     "ari": adjusted_rand_score(docs.lda_topic, docs.main_group)},
    {"pair": "BERTopic vs. taxonomy main group", "nmi": normalized_mutual_info_score(docs.bt_topic, docs.main_group),
     "ari": adjusted_rand_score(docs.bt_topic, docs.main_group)}])
agree.to_csv(OUT / "topics_agreement.csv", index=False)
method_agree.assign(vectors=EMB_METHOD, clusters=BT_METHOD).to_csv(OUT / "topics_method_agreement.csv", index=False)
method_agree.round(3)

# %% [markdown]
# ## Topic shares by fiscal year and fast risers

# %%
stage("trends")
yrs = docs[["lda_topic", "bt_topic", "fys"]].explode("fys").dropna().rename(columns={"fys": "fy"})
yrs["fy"] = yrs.fy.astype(int)
yrs = yrs[yrs.fy.between(FY_FIRST, FY_PRELIM)]
active = yrs.groupby("fy").size()
rows = []
for col, method in [("lda_topic", "LDA"), ("bt_topic", "BERTopic")]:
    s = yrs.groupby(["fy", col]).size().div(active, level="fy").rename("share").reset_index().rename(columns={col: "topic"})
    rows.append(s.assign(method=method))
by_fy = pd.concat(rows).pivot_table(index=["method", "topic"], columns="fy", values="share", fill_value=0)
by_fy.to_csv(OUT / "topics_by_fy.csv")

full = [y for y in range(FY_FIRST, FY_LAST_FULL + 1) if y in by_fy.columns]
early, late = [y for y in full if y <= FY_FIRST + 2], [y for y in full if y >= FY_LAST_FULL - 2]
size = pd.concat([lda_terms.assign(method="LDA"), bt_terms.assign(method="BERTopic")]).set_index(["method", "topic"])
trend = pd.DataFrame(index=by_fy.index)
trend["projects"] = size.projects.reindex(trend.index)
trend["terms"] = size.terms.reindex(trend.index)
trend["share_early"] = by_fy[early].mean(axis=1)
trend["share_late"] = by_fy[late].mean(axis=1)
trend["growth"] = trend.share_late / trend.share_early.replace(0, np.nan)
tau = [kendalltau(full, by_fy.loc[i, full]) for i in by_fy.index]
trend["tau"], trend["p"] = [t.statistic for t in tau], [t.pvalue for t in tau]
trend["fast_riser"] = (trend.growth >= 1.5) & (trend.tau > 0) & (trend.p < 0.05) & (trend.projects >= MIN_PROJECTS)
trend = trend.reset_index().sort_values(["method", "growth"], ascending=[True, False])
trend.to_csv(OUT / "topics_trends.csv", index=False)
say(f"fast risers: {trend.groupby('method').fast_riser.sum().to_dict()}")
trend[trend.fast_riser].head(15)

# %% [markdown]
# ## Charts

# %%
def short(terms, n=3):
    return ", ".join(str(terms).split(", ")[:n])


bt_tr = trend[trend.method == "BERTopic"].set_index("topic")
top12 = bt_tr.sort_values("projects", ascending=False).head(12).index
fig, axes = plt.subplots(3, 4, figsize=(13, 8.5), sharex=True)
fig.subplots_adjust(top=0.86, bottom=0.12, hspace=0.55, wspace=0.3)
for ax, t in zip(axes.flat, top12):
    v = by_fy.loc[("BERTopic", t), full] * 100
    ax.plot(full, v, color=pal.PROJECTS, lw=2)
    ax.set_title(short(bt_tr.terms[t]), fontsize=pal.SIZES["axis"], loc="left")
    ax.set_ylim(0, max(v) * 1.3)
    ax.tick_params(labelsize=9)
for ax in axes.flat[len(top12):]:
    ax.set_visible(False)
fig.suptitle("Shares of the largest topics among active data science projects", x=0.02, ha="left",
             fontsize=pal.SIZES["chart_title"], color=pal.HEADING, fontweight="bold")
fig.supylabel("% of active data science projects", fontsize=pal.SIZES["axis"])
note(fig, f"Topics from {BT_METHOD} on {EMB_METHOD}; labels are each topic's top three words. "
          f"FY{FY_FIRST} to FY{FY_LAST_FULL}.\nSource: NIH RePORTER API; NIH Data Science Taxonomy.")
save(fig, "01_top_topics_by_fy")

rise = bt_tr[bt_tr.projects >= MIN_PROJECTS].sort_values("growth", ascending=False).head(12)[::-1]
fig, ax = plt.subplots(figsize=(9, 6))
fig.subplots_adjust(left=0.38, top=0.88, bottom=0.14)
ax.barh([short(x) for x in rise.terms], rise.growth, color=[pal.PROJECTS if f else pal.NEUTRAL for f in rise.fast_riser])
for y, (g, p) in enumerate(zip(rise.growth, rise.p)):
    ax.annotate(f"{g:.1f}×", (g, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=pal.SIZES["axis"])
ax.axvline(1, color=pal.MUTED, lw=1, ls=":")
ax.set_xlabel(f"Growth in share (FY{late[0]}–{late[-1]} ÷ FY{early[0]}–{early[-1]})")
fig.suptitle("Fastest-growing data science topics", x=0.02, ha="left", fontsize=pal.SIZES["chart_title"],
             color=pal.HEADING, fontweight="bold")
note(fig, f"Dark = steady rise (Kendall's τ, p < 0.05) and at least {MIN_PROJECTS} projects.\n"
          "Source: NIH RePORTER API; NIH Data Science Taxonomy.")
save(fig, "02_fastest_rising")

big = bt_tr.sort_values("projects", ascending=False).head(15).index
lift = (docs[docs.bt_topic.isin(big)].groupby("bt_topic")[GROUPS].mean() / overall_group).reindex(big)
fig, ax = plt.subplots(figsize=(10, 7))
fig.subplots_adjust(left=0.34, top=0.8, bottom=0.12)
im = ax.imshow(np.log2(lift.clip(lower=0.125).values), cmap="BrBG", vmin=-2, vmax=2, aspect="auto")
ax.set_xticks(range(len(GROUPS)), GROUPS, rotation=35, ha="right")
ax.set_yticks(range(len(big)), [short(bt_tr.terms[t]) for t in big])
for i in range(len(big)):
    for j in range(len(GROUPS)):
        ax.text(j, i, f"{lift.values[i, j]:.1f}", ha="center", va="center", fontsize=8, color=pal.INK)
fig.suptitle("Where topics and taxonomy groups line up (lift)", x=0.02, ha="left", fontsize=pal.SIZES["chart_title"],
             color=pal.HEADING, fontweight="bold")
note(fig, "Lift = group's share in the topic ÷ its share in all data science projects (1.0 = no link).\n"
          "Source: NIH RePORTER API; NIH Data Science Taxonomy.")
save(fig, "03_topic_group_lift")

# %%
docs[key + ["lda_topic", "bt_topic", "main_group"]].to_parquet(INTERIM / "topic_assignments.parquet", index=False)
_stop()
say("done")
