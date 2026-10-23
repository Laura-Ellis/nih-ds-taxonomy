"""Keyword baseline for the NIH Data Science Taxonomy.

Loads taxonomy/categories.yaml and taxonomy/terms.csv, then labels project text.

Rule: a category is assigned when the text has at least one strong term, or at least
two distinct weak terms, from that category, after exclusions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_DIR = ROOT / "taxonomy"
EXCLUDE_WINDOW = 60  # characters on each side of a match checked against exclude_pattern


@dataclass
class Term:
    term: str
    category_id: str
    strength: str
    pattern: re.Pattern
    exclude: re.Pattern | None


def load_categories(path: Path = TAXONOMY_DIR / "categories.yaml") -> pd.DataFrame:
    """One row per category with its dimension."""
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = []
    for dim in spec["dimensions"]:
        for cat in dim["categories"]:
            rows.append({
                "dimension": dim["id"],
                "category_id": cat["id"],
                "group": cat.get("group", ""),
                "label": cat["label"],
                "method": dim.get("method", "keyword"),
            })
    return pd.DataFrame(rows)


def _compile(term: str, match_type: str) -> re.Pattern:
    escaped = re.escape(term)
    # Allow hyphen or space variants: "fine-tuning" matches "fine tuning"
    escaped = escaped.replace(r"\-", r"[-\s]?").replace(r"\ ", r"[-\s]+")
    if match_type == "acronym":
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])")
    # Phrases: case-insensitive, whole words, optional plural "s"
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}s?(?![A-Za-z0-9])", re.IGNORECASE)


def load_terms(path: Path = TAXONOMY_DIR / "terms.csv") -> list[Term]:
    df = pd.read_csv(path, dtype=str).fillna("")
    terms = []
    for r in df.itertuples(index=False):
        exclude = re.compile(r.exclude_pattern, re.IGNORECASE) if r.exclude_pattern else None
        terms.append(Term(r.term, r.category_id, r.strength, _compile(r.term, r.match_type), exclude))
    return terms


def match_terms(text: str, terms: list[Term]) -> dict[str, dict[str, set[str]]]:
    """Return {category_id: {"strong": {...}, "weak": {...}}} for terms found in text."""
    found: dict[str, dict[str, set[str]]] = {}
    for t in terms:
        for m in t.pattern.finditer(text):
            if t.exclude:
                window = text[max(0, m.start() - EXCLUDE_WINDOW): m.end() + EXCLUDE_WINDOW]
                if t.exclude.search(window):
                    continue
            # Singular and plural forms count as one term
            key = re.sub(r"s$", "", t.term.lower())
            found.setdefault(t.category_id, {"strong": set(), "weak": set()})[t.strength].add(key)
            break
    return found


def assign(found: dict, strong_required: int = 1, weak_required: int = 2) -> list[str]:
    return sorted(
        cat for cat, hits in found.items()
        if len(hits["strong"]) >= strong_required or len(hits["weak"]) >= weak_required
    )


@lru_cache(maxsize=1)
def _training_codes() -> tuple[tuple[str, ...], tuple[str, ...]]:
    spec = yaml.safe_load((TAXONOMY_DIR / "categories.yaml").read_text(encoding="utf-8"))
    ac = next(d for d in spec["dimensions"] if d["id"] == "workforce")["activity_codes"]
    return tuple(ac["codes"]), tuple(ac["prefixes"])


def _is_training_code(code: str) -> bool:
    codes, prefixes = _training_codes()
    return code in codes or code.startswith(prefixes)


def label_projects(df: pd.DataFrame, text_cols=("project_title", "abstract_text")) -> pd.DataFrame:
    """Add category labels, matched terms, and dimension flags to a projects table."""
    terms = load_terms()
    cats = load_categories()
    dim_of = dict(zip(cats.category_id, cats.dimension))
    text = df[list(text_cols)].fillna("").agg(" ".join, axis=1)

    found = text.map(lambda s: match_terms(s, terms))
    out = df.copy()
    out["categories"] = found.map(assign)
    out["training_mechanism"] = (out["activity_code"].fillna("").map(_is_training_code)
                                 if "activity_code" in out else False)
    # The umbrella category counts only when no specific method is named
    specific = set(cats.loc[(cats.dimension == "methods") & (cats.category_id != "data_science_general"),
                            "category_id"])
    out["categories"] = [[c for c in cs if c != "data_science_general"] if set(cs) & specific else cs
                         for cs in out.categories]
    out["matched_terms"] = found.map(
        lambda f: "; ".join(f"{c}: {', '.join(sorted(h['strong'] | h['weak']))}" for c, h in sorted(f.items()))
    )
    for dim in cats.dimension.unique():
        out[f"dim_{dim}"] = out.categories.map(lambda cs, d=dim: any(dim_of.get(c) == d for c in cs))
    ai_cats = set(cats.loc[cats.group == "artificial_intelligence", "category_id"])
    out["ai_related"] = out.categories.map(lambda cs: any(c in ai_cats for c in cs))
    out["data_science_related"] = out[[f"dim_{d}" for d in
                                       ("methods", "software_tools", "data_infrastructure", "data_sharing")]].any(axis=1)
    # Application areas and training only count for data science projects
    area_cats = set(cats.loc[cats.dimension == "application_area", "category_id"]) | {"training_education"}
    out["categories"] = [
        cs if ds else [c for c in cs if c not in area_cats]
        for cs, ds in zip(out.categories, out.data_science_related)
    ]
    out["dim_application_area"] &= out["data_science_related"]
    out["dim_workforce"] = out.categories.map(lambda cs: any(dim_of.get(c) == "workforce" for c in cs))
    out["ds_workforce"] = out["data_science_related"] & (
        out.categories.map(lambda cs: "training_education" in cs) | out["training_mechanism"])
    # Signals of how central AI is (the LLM review decides substantive vs. mention)
    ai_terms = [t for t in terms if t.category_id in ai_cats]
    titles = df[text_cols[0]].fillna("")
    out["ai_in_title"] = titles.map(lambda s: any(t.pattern.search(s) for t in ai_terms))
    out["ai_term_count"] = text.map(lambda s: sum(len(t.pattern.findall(s)) for t in ai_terms))
    return out
