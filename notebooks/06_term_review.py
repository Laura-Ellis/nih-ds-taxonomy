# %% [markdown]
# # 06 Term review: use the LLM to check the keyword terms
#
# The LLM agrees with the coded sample better than keywords or RCDC (substantive AI κ = 0.94,
# `reports/agreement_v0.4.csv`), so here it is the reference for tuning the term lists.
# The keyword terms then classify every NIH project at no cost (nih-ds-kpis, notebook 02).
#
# Steps:
# 1. LLM-label all 749 sampled projects (149 are already cached; about $4 for the rest).
# 2. **Category check:** for each category, how often the LLM agrees with the keyword label.
# 3. **Term check:** for each term, the share of its hits the LLM confirms. Low-precision
#    terms are candidates to drop or demote from strong to weak.
# 4. **Misses:** projects the LLM puts in a category that keywords missed, with the LLM's
#    evidence quote, to find terms to add.
#
# **Definitions**
# - Term precision = projects where the term fired and the LLM assigned that category / projects where the term fired
# - Category precision = keyword and LLM both assign / keyword assigns; recall = both / LLM assigns
# - Wilson 95% CI for a share p from n projects: (p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n), z = 1.96

# %%
import sys
from math import sqrt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import llm_label as llm  # noqa: E402  # pyright: ignore[reportMissingImports]
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]

REPORTS = ROOT / "reports"
CACHE = ROOT / "data" / "interim" / "llm_labels.jsonl"
sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
print(f"{len(sample)} sampled projects")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n)))
    return ((centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n))


# %% [markdown]
# ## 1. Label the sample

# %%
labels = llm.label_projects(sample, CACHE)
kw = tx.label_projects(sample)
x = kw.merge(labels, on="appl_id")
x["llm_cats"] = x.llm_categories.map(set)
x["kw_cats"] = x.categories.map(set)
print(f"{len(x)} projects with both labels")

# %% [markdown]
# ## 2. Category check
# Keyword categories count only for data science projects; the LLM gives categories only
# when it codes data science Y.

# %%
defs = llm.load_definitions()
rows = []
for c in defs["categories"]:
    k, m = x.kw_cats.map(lambda s, c=c["id"]: c in s), x.llm_cats.map(lambda s, c=c["id"]: c in s)
    rows.append({"dimension": c["dimension"], "category": c["id"], "keywords": k.sum(), "llm": m.sum(),
                 "both": (k & m).sum()})
cat = pd.DataFrame(rows)
cat["precision"] = (cat.both / cat.keywords).round(2)
cat["recall"] = (cat.both / cat.llm).round(2)
cat.to_csv(REPORTS / "category_review_v0.4.csv", index=False)
cat.sort_values("llm", ascending=False)

# %% [markdown]
# ## 3. Term check

# %%
def parse_terms(s: str) -> list[tuple[str, str]]:
    """'deep_learning: deep learning; neuroscience: brain imaging' -> [(category, term), ...]"""
    out = []
    for part in str(s or "").split("; "):
        if ": " in part:
            cat_id, terms = part.split(": ", 1)
            out += [(cat_id, t.strip()) for t in terms.split(", ") if t.strip()]
    return out


hits = [(r.appl_id, c, t, c in r.llm_cats, r.llm_ai_related) for r in x.itertuples()
        for c, t in parse_terms(r.matched_terms)]
h = pd.DataFrame(hits, columns=["appl_id", "category", "term", "confirmed", "llm_ai_related"])
# Matched terms are stored lowercase without a trailing "s" (singular and plural count once)
strength = (pd.read_csv(ROOT / "taxonomy" / "terms.csv", dtype=str)
            .assign(term=lambda d: d.term.str.lower().str.replace(r"s$", "", regex=True))
            .drop_duplicates(["term", "category_id"])
            .set_index(["term", "category_id"]).strength)
terms = h.groupby(["category", "term"]).agg(hits=("appl_id", "nunique"), confirmed=("confirmed", "sum")).reset_index()
terms["strength"] = [strength.get((t, c), "") for c, t in zip(terms.category, terms.term)]
terms["precision"] = (terms.confirmed / terms.hits).round(2)
ci = [wilson(k, n) for k, n in zip(terms.confirmed, terms.hits)]
terms["ci_low"], terms["ci_high"] = [round(a, 2) for a, _ in ci], [round(b, 2) for _, b in ci]


def flag(r):
    if r.hits < 3:
        return ""
    if r.precision < 0.4:
        return "drop or add exclusion"
    if r.strength == "strong" and r.precision < 0.6:
        return "demote to weak"
    return ""


terms["suggestion"] = terms.apply(flag, axis=1)
terms.to_csv(REPORTS / "term_review_v0.4.csv", index=False)
terms[terms.suggestion != ""].sort_values(["suggestion", "precision"])

# %% [markdown]
# ## 4. Misses: LLM category, no keyword category

# %%
miss = [(r.appl_id, c, r.project_title, r.llm_ai_related, r.llm_evidence, str(r.abstract_text)[:600])
        for r in x.itertuples() for c in r.llm_cats - r.kw_cats]
misses = pd.DataFrame(miss, columns=["appl_id", "category", "project_title", "llm_ai_related",
                                     "llm_evidence", "abstract_start"])
misses.to_csv(REPORTS / "category_misses_v0.4.csv", index=False)
misses.category.value_counts()

# %% [markdown]
# ## 5. Calibration: share of keyword AI projects the LLM calls substantive, by stratum
# Used to turn keyword counts into an estimate of substantive AI: estimate = keyword count × precision.

# %%
cal = []
for stratum, g in x[x.ai_related].groupby("stratum"):
    k, n = g.llm_ai_related.eq("Y").sum(), len(g)
    lo, hi = wilson(k, n)
    cal.append({"stratum": stratum, "keyword_ai": n, "llm_substantive": k,
                "precision": round(k / n, 2), "ci_low": round(lo, 2), "ci_high": round(hi, 2)})
pd.DataFrame(cal)

# %% [markdown]
# ## 6. Evidence rule by category
# Every keyword category also gets a stricter "likely" tier: its terms appear at least
# twice, or one sits within 150 characters of an action phrase ("we will", "aim", "develop
# a", "to predict"). This compares both tiers with the LLM, per category and overall.
# Application areas and workforce categories describe context, not methods, so they
# have no stricter tier.

# %%
tiers = []
for c in defs["categories"]:
    m = x.llm_cats.map(lambda s, c=c["id"]: c in s)
    for tier, col in [("any keyword", "kw_cats"), ("likely", "likely_categories")]:
        k = x[col].map(lambda s, c=c["id"]: c in set(s))
        if k.sum() == 0 or c["dimension"] in ("application_area", "workforce"):
            continue
        tiers.append({"category": c["id"], "tier": tier, "flagged": k.sum(),
                      "precision": round((k & m).sum() / k.sum(), 2),
                      "recall": round((k & m).sum() / max(m.sum(), 1), 2)})
for label, any_col, likely_col, llm_col in [("AI (overall)", "ai_related", "ai_likely", "llm_ai_related"),
                                             ("Data science (overall)", "data_science_related", "ds_likely",
                                              "llm_ds_related")]:
    truth = x[llm_col].eq("Y")
    for tier, col in [("any keyword", any_col), ("likely", likely_col)]:
        k = x[col]
        tiers.append({"category": label, "tier": tier, "flagged": k.sum(),
                      "precision": round((k & truth).sum() / k.sum(), 2),
                      "recall": round((k & truth).sum() / truth.sum(), 2)})
tiers = pd.DataFrame(tiers)
tiers.to_csv(REPORTS / "evidence_rule_review_v0.4.csv", index=False)
tiers.pivot(index="category", columns="tier", values=["flagged", "precision", "recall"])
