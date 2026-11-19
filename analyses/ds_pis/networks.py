# %% [markdown]
# # Who data science PIs work with: the NIH co-PI network
#
# Part 5 of the PI analysis (`pi_analysis.md`).
#
# **Definitions**
# - Co-PI tie = two PIs listed on the same parent award (multiple-PI awards), FY2016 to FY2026. Subprojects of
#   centers are left out, so a center doesn't tie every subproject leader to every other one
# - Awards listing more than 10 PIs are left out (a few consortium awards would otherwise dominate)
# - PI groups (from `src/pi_tiers.py`): AI developer PIs, infrastructure builder PIs, other data science PIs,
#   other PIs (at least 2 records). A PI in both builder tiers counts as an AI developer
# - Cross-field tie = a tie between a data science PI and a PI who is not one
# - Institute views: institutes with more than $1B in data science funding (attributed cost), FY2016 to FY2026
# - Community = a group of PIs who work with each other much more than with everyone else (Louvain method,
#   which groups PIs to maximize ties inside groups relative to chance)
# - Communities reached = number of different communities among a PI's co-PIs; a simple measure of bridging
# - Betweenness = share of shortest paths between other PIs that pass through this PI (estimated from 500
#   sampled PIs); higher = more of a bridge
# - FY2026 is preliminary
#
# **Link prediction:** will two PIs who have never shared an award do so later? Ties from awards first seen
# FY2016 to FY2021 form the training network; new ties first seen FY2022 to FY2026 are the answers. Compared:
# 1. Adamic-Adar score (baseline): shared co-PIs, counting rarely connected shared co-PIs more
# 2. Logistic regression on network and PI features
# 3. Gradient boosting on the same features
# 4. Graph embedding: each PI's position in the network compressed to 32 numbers (truncated singular value
#    decomposition of the adjacency matrix), then logistic regression on the pair
# Scored on held-out pairs: area under the ROC curve (AUC; 0.5 = chance, 1.0 = perfect) and average precision.
# Non-ties are random pairs of PIs, which makes the task easier than real use; compare models with each other,
# not with an absolute bar.
#
# **Privacy:** aggregate only; no PI names or IDs leave this script; groups under 11 PIs are suppressed.
# Inputs: `exporter_applications.parquet`, `pi_profiles.parquet`, `exporter_core_projects_labeled.parquet`.
# Outputs: `reports/results/ds_network_*.csv`, `reports/figures/ds_network/*.png`.
# Packages: networkx, scikit-learn, scipy.

# %%
import itertools
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import palette as pal  # noqa: E402  # pyright: ignore[reportMissingImports]
from pi_tiers import GROUPS, explode_pis, load_tiers  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, step  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import SETTINGS  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, OUT = ROOT / "data" / "processed", ROOT / "reports" / "results"
FIG = ROOT / "reports" / "figures" / "ds_network"
FIG.mkdir(parents=True, exist_ok=True)
SUPPRESS, SEED, MAX_PIS, SPLIT_FY = 11, 26, 10, 2021
GROUP_COLORS = {"AI developer PIs": pal.ROLE_COLORS["develops_ai"], "Infrastructure builder PIs": pal.PROJECTS,
                "Other data science PIs": pal.DATA_SCIENCE, "Other PIs": pal.NEUTRAL}
FOCUS = None  # public page: no institute is highlighted (focus_ic in config/local.yaml is for internal previews only)
pal.use_style()


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def source_note(ax, text: str, y: float = -0.16) -> None:
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=pal.SIZES["source"], color=pal.SOURCE,
                va="top", linespacing=1.6)

# %% [markdown]
# ## PI groups and co-PI ties

# %%
with step("PI groups"):
    pi = load_tiers(PROCESSED)
apps = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                       columns=["core_project_number", "is_subproject", "pi_ids", "fy"])
apps = apps[~apps.is_subproject]
apps["fy"] = pd.to_numeric(apps.fy).astype(int)
ap = explode_pis(apps)[["core_project_number", "fy", "pi"]]
awards = ap.groupby("core_project_number").agg(first_fy=("fy", "min"), pis=("pi", lambda s: sorted(set(s))))
awards = awards[awards.pis.str.len().between(2, MAX_PIS)]
pairs = [(p1, p2, fy) for ps, fy in zip(awards.pis, awards.first_fy) for p1, p2 in itertools.combinations(ps, 2)]
ties = (pd.DataFrame(pairs, columns=["a", "b", "first_fy"]).groupby(["a", "b"])
        .agg(first_fy=("first_fy", "min"), awards=("first_fy", "size")).reset_index())
say(f"{len(awards):,} multiple-PI parent awards; {len(ties):,} co-PI ties")

G = nx.Graph()
G.add_weighted_edges_from(ties[["a", "b", "awards"]].itertuples(index=False))
grp = pi.group.reindex(list(G.nodes)).fillna("One-record PIs")
nx.set_node_attributes(G, grp.to_dict(), "group")
ds = pi.ds_pi.reindex(list(G.nodes)).fillna(False)

# %% [markdown]
# ## 1. How often each group has co-PIs, and who they partner with

# %%
deg = pd.Series(dict(G.degree()))
base = pi[pi.group.notna()].copy()
base["has_copi"] = base.index.isin(deg.index)
base["co_pis"] = deg.reindex(base.index).fillna(0)
e = ties[["a", "b"]].assign(a_ds=ds.reindex(ties.a).values, b_ds=ds.reindex(ties.b).values)
both = pd.concat([e.rename(columns={"a": "pi", "a_ds": "ds", "b_ds": "other_ds"})[["pi", "other_ds"]],
                  e.rename(columns={"b": "pi", "b_ds": "ds", "a_ds": "other_ds"})[["pi", "other_ds"]]])
partner_ds = both.groupby("pi").other_ds.mean()
base["partner_ds_share"] = partner_ds.reindex(base.index)
collab = (base.groupby("group")
          .agg(pis=("records", "size"), share_with_copi=("has_copi", "mean"),
               median_co_pis_if_any=("co_pis", lambda s: s[s > 0].median()),
               partner_ds_share=("partner_ds_share", "mean"))
          .reindex(GROUPS))
expected = ds.mean()  # share of data science PIs among all PIs in the network
collab["expected_partner_ds_share"] = expected
collab.to_csv(OUT / "ds_network_collaboration.csv")
print(collab.round(3).to_string())

# %% [markdown]
# ## 2. Communities and bridging

# %%
with step("communities (Louvain)"):
    comm = nx.community.louvain_communities(G, weight="weight", seed=SEED, resolution=1.0)
cid = {n: i for i, c in enumerate(comm) for n in c}
nx.set_node_attributes(G, cid, "community")
BTW_CACHE = ROOT / "data" / "interim" / "ds_network_betweenness.parquet"  # reused while the network is unchanged
if BTW_CACHE.exists() and pd.read_parquet(BTW_CACHE).shape[0] == len(G):
    btw = pd.read_parquet(BTW_CACHE).betweenness
else:
    with step("betweenness (500 sampled PIs, about 3 minutes)"):
        btw = pd.Series(nx.betweenness_centrality(G, k=min(500, len(G)), seed=SEED, weight=None))
    BTW_CACHE.parent.mkdir(parents=True, exist_ok=True)
    btw.rename("betweenness").to_frame().to_parquet(BTW_CACHE)
reach = pd.Series({n: len({cid[m] for m in G.neighbors(n)}) for n in G.nodes})
node = pd.DataFrame({"group": grp, "community": pd.Series(cid), "co_pis": deg, "communities_reached": reach,
                     "betweenness": btw})
bridge = (node[node.group.isin(GROUPS)].groupby("group")
          .agg(pis_with_copi=("co_pis", "size"), median_co_pis=("co_pis", "median"),
               mean_communities_reached=("communities_reached", "mean"),
               share_reaching_3plus=("communities_reached", lambda s: (s >= 3).mean()),
               mean_betweenness_x1e5=("betweenness", lambda s: 1e5 * s.mean()))
          .reindex(GROUPS))
bridge.to_csv(OUT / "ds_network_bridging.csv")
print(bridge.round(3).to_string())

# Bridging with the number of co-PIs held fixed: communities reached by co-PI count band
node["co_pi_band"] = pd.cut(node.co_pis, [0, 1, 2, 4, 8, np.inf], labels=["1", "2", "3–4", "5–8", "9+"])
band = (node[node.group.isin(GROUPS)].groupby(["co_pi_band", "group"], observed=True)
        .agg(pis=("co_pis", "size"), mean_communities_reached=("communities_reached", "mean")).reset_index())
band.loc[band.pis < SUPPRESS, "mean_communities_reached"] = np.nan
band.to_csv(OUT / "ds_network_bridging_by_degree.csv", index=False)

# %% [markdown]
# ## 3. Institutes: who each institute's data science PIs work with
# Institutes with more than $1B in data science funding, FY2016 to FY2026 (attributed cost, administering IC).
# A PI's institute = the administering IC of most of their records. Each co-PI tie of a data science PI counts
# once for that PI's institute (a tie between two data science PIs counts for both).

# %%
CODE = {"CA": "NCI", "AI": "NIAID", "HL": "NHLBI", "OD": "OD", "AG": "NIA", "GM": "NIGMS", "MH": "NIMH",
        "TR": "NCATS", "NS": "NINDS", "LM": "NLM", "DA": "NIDA", "HG": "NHGRI", "DK": "NIDDK", "HD": "NICHD",
        "ES": "NIEHS", "EB": "NIBIB", "EY": "NEI", "AR": "NIAMS", "DC": "NIDCD", "AA": "NIAAA", "MD": "NIMHD",
        "DE": "NIDCR", "NR": "NINR", "AT": "NCCIH", "TW": "FIC"}
lab = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                      columns=["administering_ic", "attributed_cost", "ds_label"])
ds_fund = lab[lab.ds_label.eq("Y")].groupby("administering_ic").attributed_cost.sum()
ds_fund = ds_fund.groupby(ds_fund.index.map(lambda c: CODE.get(c, c))).sum()
BIG = ds_fund[ds_fund > 1e9].sort_values(ascending=False).index.tolist()
ic_of = pi.main_ic.to_dict()
dsd0 = ds.to_dict()
ends = pd.concat([ties[["a", "b"]].rename(columns={"a": "pi", "b": "partner"}),
                  ties[["b", "a"]].rename(columns={"b": "pi", "a": "partner"})], ignore_index=True)
ends = ends[ends.pi.map(dsd0).fillna(False).astype(bool)]
ends["ic"], ends["partner_ic"] = ends.pi.map(ic_of), ends.partner.map(ic_of)
ends["partner_ds"] = ends.partner.map(dsd0).fillna(False).astype(bool)
ends = ends[ends.ic.notna() & ends.partner_ic.notna()]
ends["cross_ic"] = ends.ic != ends.partner_ic
ic_tbl = (ends.groupby("ic").agg(ties=("pi", "size"), ds_pis_with_ties=("pi", "nunique"),
                                 cross_ic=("cross_ic", "mean"), cross_field=("partner_ds", lambda s: 1 - s.mean()),
                                 ties_to_ds=("partner_ds", "sum"))
          .reindex(BIG))
ic_tbl["ds_funding_b"] = (ds_fund.reindex(BIG) / 1e9).round(2)
ic_tbl["cross_ic_ds"] = ends[ends.partner_ds].groupby("ic").cross_ic.mean().reindex(BIG)
nih = pd.Series({"cross_ic": ends.cross_ic.mean(), "cross_field": 1 - ends.partner_ds.mean(),
                 "cross_ic_ds": ends[ends.partner_ds].cross_ic.mean()})
ic_tbl.loc[ic_tbl.ds_pis_with_ties < SUPPRESS, ["cross_ic", "cross_field", "cross_ic_ds"]] = np.nan
ic_tbl.to_csv(OUT / "ds_network_by_ic.csv")
mat = pd.crosstab(ends.ic, ends.partner_ic.where(ends.partner_ic.isin(BIG), "Other"), normalize="index")
mat = mat.reindex(index=BIG, columns=BIG + ["Other"]).fillna(0)
mat.to_csv(OUT / "ds_network_ic_partners.csv")
print(ic_tbl.round(3).to_string())

# %% [markdown]
# ## Chart 1. Simplified network: institutes linked by their data science PIs' co-PI ties
# Circle = institute (size = data science PIs with a co-PI). Line = co-PI ties between a data science PI at one
# institute and a PI at the other, both directions added; only the 20 strongest links are drawn.

# %%
cnt = pd.crosstab(ends.ic, ends.partner_ic).reindex(index=BIG, columns=BIG).fillna(0)
sym = cnt + cnt.T
links = [(a_, b_, sym.at[a_, b_]) for i_, a_ in enumerate(BIG) for b_ in BIG[i_ + 1:] if sym.at[a_, b_] > 0]
links = sorted(links, key=lambda t: -t[2])
pd.DataFrame(links, columns=["ic_a", "ic_b", "ties"]).to_csv(OUT / "ds_network_ic_links.csv", index=False)
TOP_LINKS = 20
N = nx.Graph()
N.add_nodes_from(BIG)
N.add_weighted_edges_from(links[:TOP_LINKS])
ang = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi, len(BIG), endpoint=False)
posN = {ic: (np.cos(t), np.sin(t)) for ic, t in zip(BIG, ang)}
fig, ax = plt.subplots(figsize=(9, 9))
wmax = links[0][2]
for a_, b_, w_ in links[:TOP_LINKS]:
    (x1, y1), (x2, y2) = posN[a_], posN[b_]
    ax.plot([x1, x2], [y1, y2], color=pal.PROJECTS, lw=0.8 + 7 * w_ / wmax, alpha=0.25 + 0.6 * w_ / wmax,
            solid_capstyle="round", zorder=1)
npis = ic_tbl.ds_pis_with_ties.reindex(BIG).fillna(0)
for ic in BIG:
    x, y = posN[ic]
    linked = any(ic in (a_, b_) for a_, b_, _ in links[:TOP_LINKS])
    ax.scatter(x, y, s=120 + 1600 * npis[ic] / npis.max(), color=pal.PROJECTS if linked else pal.NEUTRAL,
               edgecolors="white", linewidths=1.5, zorder=2)
    ax.annotate(ic, (x, y), xytext=(1.24 * x, 1.24 * y), textcoords="data", ha="center", va="center",
                fontsize=pal.SIZES["label"], fontweight="bold" if linked else "normal",
                color=pal.HEADING if linked else pal.MUTED)
ax.set_xlim(-1.35, 1.35)
ax.set_ylim(-1.35, 1.35)
ax.set_aspect("equal")
ax.set_axis_off()
a1, b1, w1 = links[0]
hub = max(N.degree, key=lambda t: t[1])
ax.set_title(f"{a1} and {b1} share the most data science co-PI ties ({int(w1):,});\n"
             f"{hub[0]} links to the most institutes ({hub[1]} of the {TOP_LINKS} strongest links)", loc="left", pad=12)
ax.annotate(f"Circle = institute; size = its data science PIs with a co-PI. Line = co-PI ties between a data science PI"
            f" at one institute\nand a PI at the other; thicker = more ties. Only the {TOP_LINKS} strongest links are"
            " shown; gray circles have none of them.\nInstitutes with more than $1B in data science funding, multiple-PI"
            " parent awards, FY2016 to FY2026 (FY2026 preliminary).\nSource: NIH RePORTER API.", xy=(0, -0.02),
            xycoords="axes fraction", va="top", fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6)
save(fig, "01_ic_network")

# %% [markdown]
# ## Chart 2. How often each institute's data science PIs work across institutes and fields

# %%
order = ic_tbl.sort_values("cross_ic").index
fig, axes = plt.subplots(1, 2, figsize=(11, 6.2), sharey=True)
fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.17, wspace=0.25)
yy = np.arange(len(order))
for ax, col, ttl in [(axes[0], "cross_ic", "All co-PI ties: % with a PI at another institute"),
                     (axes[1], "cross_ic_ds", "Ties to other data science PIs: % at another institute")]:
    v = 100 * ic_tbl.loc[order, col]
    colors = [pal.PROJECTS if (FOCUS is None or i == FOCUS) else pal.NEUTRAL for i in order]
    ax.barh(yy, v, color=colors, height=0.65)
    for yi, x in zip(yy, v):
        ax.annotate(f"{x:.0f}%", (x, yi), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=pal.SIZES["axis"])
    ax.axvline(100 * nih[col], color=pal.MUTED, lw=1, ls=":")
    ax.annotate(f"All NIH {100 * nih[col]:.0f}%", (100 * nih[col], len(order) - 0.4), xytext=(4, 0),
                textcoords="offset points", fontsize=pal.SIZES["axis"], color=pal.MUTED)
    ax.set_title(ttl, fontsize=pal.SIZES["label"], pad=14)
    ax.set_xlim(0, 100)
axes[0].set_yticks(yy, order)
fig.suptitle(f"{100 * nih.cross_ic:.0f}% of data science PIs' co-PI ties cross institute lines; "
             + ("ties with other data science PIs cross them about as often" if abs(nih.cross_ic_ds - nih.cross_ic) < 0.03
              else f"ties with other data science PIs cross them {'more' if nih.cross_ic_ds > nih.cross_ic else 'less'} often")
             + f" ({100 * nih.cross_ic_ds:.0f}%)",
             x=0.02, y=0.96, ha="left", fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
fig.text(0.02, 0.02, "Institutes with more than $1B in data science funding, FY2016 to FY2026 (FY2026 preliminary). "
         "Tie = two PIs on the same multiple-PI parent award.\nA PI's institute = administering institute of most of "
         "their records. Source: NIH RePORTER API.", fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6)
save(fig, "02_ic_cross_ties")

# %% [markdown]
# ## Chart 3. Which institutes they partner with (row = data science PI's institute)

# %%
own = np.median([mat.at[i, i] for i in mat.index])
top_out = (mat.drop(columns="Other").where(~np.eye(len(mat), len(mat) + 0, dtype=bool)).mean().idxmax())
fig, ax = plt.subplots(figsize=(11, 8))
cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#FFFFFF", pal.PROJECTS])
im = ax.imshow(mat.to_numpy(), cmap=cmap, vmin=0, vmax=0.6, aspect="auto")
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat.iat[i, j]
        if v >= 0.05:
            ax.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=9,
                    color="white" if v >= 0.35 else pal.INK)
ax.set_xticks(range(mat.shape[1]), mat.columns, rotation=90)
ax.set_yticks(range(mat.shape[0]), mat.index)
ax.xaxis.tick_top()
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_xlabel("Co-PI's institute")
ax.xaxis.set_label_position("top")
ax.set_ylabel("Data science PI's institute")
ax.set_title(f"About {100 * own:.0f}% of an institute's data science co-PI ties stay inside it (median); "
             f"{top_out} is the most\ncommon outside partner", 
             pad=60, loc="left")
fig.text(0.125, 0.04, "Each row sums to 100%: share of that institute's data science PI co-PI ties going to each "
         "institute (numbers shown at 5% or more).\nOther = all institutes under $1B in data science funding. "
         "Multiple-PI parent awards, FY2016 to FY2026. Source: NIH RePORTER API.",
         fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6)
save(fig, "03_ic_partners")

# %% [markdown]
# ## Chart 4. Who data science PIs partner with, and how far they reach

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
fig.subplots_adjust(left=0.2, right=0.97, top=0.78, bottom=0.3, wspace=0.35)
y = np.arange(len(GROUPS))[::-1]
for ax, col, ttl, fmt in [
        (axes[0], collab.partner_ds_share, "Co-PIs who are data science PIs, %", lambda v: f"{100 * v:.0f}%"),
        (axes[1], bridge.share_reaching_3plus, "PIs whose co-PIs span 3+ communities, %", lambda v: f"{100 * v:.0f}%")]:
    ax.barh(y, 100 * col.values, color=[GROUP_COLORS[g] for g in GROUPS], height=0.6)
    for yi, v in zip(y, col.values):
        ax.annotate(fmt(v), (100 * v, yi), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=pal.SIZES["axis"])
    ax.set_title(ttl, fontsize=pal.SIZES["label"], pad=8)
    ax.set_xlim(0, 100 * col.max() * 1.3)
    ax.xaxis.set_major_locator(plt.MaxNLocator(5, integer=True))
axes[0].axvline(100 * expected, color=pal.MUTED, lw=1, ls=":")
axes[0].set_ylim(-0.6, len(GROUPS) - 0.1)
axes[0].annotate(f"{100 * expected:.0f}% if partners were random", (100 * expected, len(GROUPS) - 0.45),
                 xytext=(4, 0), textcoords="offset points", fontsize=pal.SIZES["axis"], color=pal.MUTED)
axes[0].set_yticks(y, [f"{g}\n({int(n):,})" for g, n in zip(GROUPS, collab.pis)])
fig.suptitle(f"Data science PIs pick data science co-PIs {collab.partner_ds_share.iloc[2] / expected:.0f} to "
             f"{collab.partner_ds_share.iloc[0] / expected:.0f} times as often as chance; infrastructure builders reach the most communities",
             x=0.02, y=0.95, ha="left", fontsize=pal.SIZES["chart_title"], fontweight="bold", color=pal.HEADING)
fig.text(0.02, 0.02, "PIs with at least one co-PI on a multiple-PI parent award, FY2016 to FY2026 (FY2026 preliminary)."
         " Community = Louvain\ncommunity of the full co-PI network. Source: NIH RePORTER API.",
         fontsize=pal.SIZES["source"], color=pal.SOURCE, linespacing=1.6)
save(fig, "04_partners_and_reach")

# %% [markdown]
# ## 4. Link prediction: which pairs of PIs will share an award next?

# %%
train_t = ties[ties.first_fy <= SPLIT_FY]
G0 = nx.Graph()
G0.add_edges_from(train_t[["a", "b"]].itertuples(index=False))
new = ties[(ties.first_fy > SPLIT_FY) & ties.a.isin(G0) & ties.b.isin(G0)]
new = new[[not G0.has_edge(a_, b_) for a_, b_ in zip(new.a, new.b)]]
nodes0 = np.array(list(G0.nodes))
rng = np.random.default_rng(SEED)
pos_pairs = list(zip(new.a, new.b))
neg = set()
all_ties = set(zip(ties.a, ties.b)) | set(zip(ties.b, ties.a))
while len(neg) < len(pos_pairs):
    a_, b_ = rng.choice(nodes0, 2, replace=False)
    if (a_, b_) not in all_ties and a_ != b_:
        neg.add((a_, b_))
pairs_df = pd.DataFrame(pos_pairs + list(neg), columns=["a", "b"])
pairs_df["y"] = np.r_[np.ones(len(pos_pairs)), np.zeros(len(neg))]
say(f"link prediction: {len(G0):,} PIs in the FY2016–FY2021 network; {len(pos_pairs):,} new ties FY2022–FY2026")

with step("pair features"):
    cid0 = {n: i for i, c in enumerate(nx.community.louvain_communities(G0, seed=SEED)) for n in c}
    pl = list(pairs_df[["a", "b"]].itertuples(index=False, name=None))
    pairs_df["common"] = [len(list(nx.common_neighbors(G0, a_, b_))) for a_, b_ in pl]
    pairs_df["adamic_adar"] = [s for *_, s in nx.adamic_adar_index(G0, pl)]
    pairs_df["jaccard"] = [s for *_, s in nx.jaccard_coefficient(G0, pl)]
    pairs_df["pref_attach"] = np.log1p([s for *_, s in nx.preferential_attachment(G0, pl)])
    pairs_df["same_community"] = [cid0[a_] == cid0[b_] for a_, b_ in pl]
    ic_ = pi.main_ic.to_dict()
    pairs_df["same_ic"] = [ic_.get(a_) is not None and ic_.get(a_) == ic_.get(b_) for a_, b_ in pl]
    dsd = ds.to_dict()
    pairs_df["both_ds"] = [bool(dsd.get(a_)) and bool(dsd.get(b_)) for a_, b_ in pl]
    pairs_df["one_ds"] = [bool(dsd.get(a_)) != bool(dsd.get(b_)) for a_, b_ in pl]

with step("graph embedding (truncated SVD)"):
    idx = {n: i for i, n in enumerate(nodes0)}
    A = nx.to_scipy_sparse_array(G0, nodelist=list(nodes0), format="csr")
    dinv = sparse.diags(1 / np.sqrt(np.maximum(A.sum(axis=1), 1)))
    Z = TruncatedSVD(32, random_state=SEED).fit_transform(dinv @ A @ dinv)
    Z = Z / np.maximum(np.linalg.norm(Z, axis=1, keepdims=True), 1e-9)
    emb = Z[[idx[a_] for a_ in pairs_df.a]] * Z[[idx[b_] for b_ in pairs_df.b]]

FEATS = ["common", "adamic_adar", "jaccard", "pref_attach", "same_community", "same_ic", "both_ds", "one_ds"]
X = pairs_df[FEATS].astype(float).to_numpy()
tr, te = train_test_split(np.arange(len(pairs_df)), test_size=0.3, random_state=SEED, stratify=pairs_df.y)
yv = pairs_df.y.to_numpy()
scores = {
    "Adamic-Adar score (baseline)": pairs_df.adamic_adar.to_numpy()[te],
    "Logistic regression (features)": LogisticRegression(max_iter=2000).fit(X[tr], yv[tr]).predict_proba(X[te])[:, 1],
    "Gradient boosting (features)": HistGradientBoostingClassifier(random_state=SEED).fit(X[tr], yv[tr])
    .predict_proba(X[te])[:, 1],
    "Graph embedding + logistic regression": LogisticRegression(max_iter=2000).fit(emb[tr], yv[tr])
    .predict_proba(emb[te])[:, 1],
}
lr = LogisticRegression(max_iter=2000).fit((X[tr] - X[tr].mean(0)) / X[tr].std(0), yv[tr])
coef = pd.Series(lr.coef_[0], index=FEATS).sort_values()
coef.rename("standardized_coefficient").to_csv(OUT / "ds_network_link_coefficients.csv")
print(coef.round(2).to_string())
lp = pd.DataFrame([{"model": k, "auc": roc_auc_score(yv[te], s), "average_precision": average_precision_score(yv[te], s)}
                   for k, s in scores.items()])
lp["test_pairs"] = len(te)
lp.to_csv(OUT / "ds_network_link_prediction.csv", index=False)
print(lp.round(3).to_string())

# Who forms new ties: among new FY2022–FY2026 ties involving a data science PI, share with a non-data science PI
nd = new.assign(a_ds=new.a.map(dsd).fillna(False), b_ds=new.b.map(dsd).fillna(False))
nd = nd[nd.a_ds | nd.b_ds]
new_cross = pd.Series({"new_ties_with_ds_pi": len(nd), "share_cross_field": (nd.a_ds != nd.b_ds).mean(),
                       "share_in_same_fy2021_community": np.mean([cid0[a_] == cid0[b_] for a_, b_ in zip(nd.a, nd.b)])})
new_cross.to_csv(OUT / "ds_network_new_ties.csv")
print(new_cross.round(3).to_string())

# %% [markdown]
# ## Chart 5. Link prediction model comparison

# %%
fig, ax = plt.subplots(figsize=(8, 3.2))
lps = lp.sort_values("auc")
yy = np.arange(len(lps))
best = lps.auc.idxmax()
cols = [pal.PROJECTS if i == best else pal.MUTED for i in lps.index]
ax.hlines(yy, 0.5, lps.auc, color=pal.GRID, lw=2)
ax.scatter(lps.auc, yy, color=cols, s=80, zorder=3)
for yi, (i, r) in zip(yy, lps.iterrows()):
    ax.annotate(f"AUC {r.auc:.2f} · AP {r.average_precision:.2f}", (r.auc, yi), xytext=(8, 0),
                textcoords="offset points", va="center", fontsize=pal.SIZES["axis"],
                fontweight="bold" if i == best else "normal")
ax.set_yticks(yy, lps.model)
ax.set_xlim(0.5, 1.0)
ax.set_xlabel("AUC on held-out pairs (0.5 = chance, 1.0 = perfect)")
ax.set_title("Shared co-PIs barely predict who teams up next; models that add who the PIs are do much better", pad=10)
source_note(ax, "Trained on ties from FY2016 to FY2021 awards; predicts ties first seen FY2022 to FY2026. AP = average\n"
            "precision. Features: shared co-PIs, number of co-PIs each, same community, same institute, data\n"
            "science status. Non-ties are random pairs, so scores run high. Source: NIH RePORTER API.", y=-0.3)
save(fig, "05_link_prediction")
print("Charts saved to", FIG)
