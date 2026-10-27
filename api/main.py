"""NIH Data Science Taxonomy API: data science projects and trends by taxonomy group.

Run locally (from the repo root, after notebook 13):
    uvicorn api.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive docs.

Data: `data/processed/ds_projects.parquet` and `reports/results/ds_groups_by_fy.csv`
(set DS_API_DATA to another repo root to point elsewhere).

Definitions
- Group = one of seven taxonomy groups (statistics and analytics, computational modeling, artificial
  intelligence, software and tools, data infrastructure, responsible AI, workforce). Data infrastructure
  has two subgroups (computing and platforms; data management and sharing), also queryable by id.
  A project can be in several groups.
- Share of data science projects = group projects / all substantive data science records that year
- Funding = extramural attributed cost (center funding counted once); intramural (Z) excluded
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

ROOT = Path(os.environ.get("DS_API_DATA", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / "src"))
from taxonomy import load_categories  # noqa: E402  # pyright: ignore[reportMissingImports]

GROUP_LABELS = {
    "statistics_analytics": "Statistics and analytics",
    "computational_modeling": "Computational modeling",
    "artificial_intelligence": "Artificial intelligence",
    "software_tools": "Software and tools",
    "data_infrastructure": "Data infrastructure",
    "responsible_ai": "Responsible AI",
    "workforce": "Workforce",
    "computing_platforms": "Computing and platforms",   # subgroup of Data infrastructure
    "data_sharing": "Data management and sharing",      # subgroup of Data infrastructure
}
SUBGROUPS = {"computing_platforms": "data_infrastructure", "data_sharing": "data_infrastructure"}

app = FastAPI(title="NIH Data Science Taxonomy API", version="0.1.0",
              description="Substantive data science NIH projects, FY2016–2025, by taxonomy group, "
                          "category, institute, and fiscal year. Source: NIH ExPORTER.")


@lru_cache
def projects() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "processed" / "ds_projects.parquet")
    df["group_list"] = df.groups.fillna("").str.split("; ")
    df["category_list"] = df.categories.fillna("").str.split("; ")
    return df


@lru_cache
def trend() -> pd.DataFrame:
    return pd.read_csv(ROOT / "reports" / "results" / "ds_groups_by_fy.csv")


@lru_cache
def categories() -> pd.DataFrame:
    c = load_categories()
    c = c[c.dimension.isin(["methods", "software_tools", "data_infrastructure", "data_sharing",
                            "responsible_ai", "workforce"])].copy()
    c["ds_subgroup"] = c.group.where(c.dimension == "methods", c.dimension).replace(
        {"data_infrastructure": "computing_platforms"})
    c["ds_group"] = c.ds_subgroup.map(lambda g: SUBGROUPS.get(g, g))
    return c


def check_group(group: str) -> None:
    if group not in GROUP_LABELS:
        raise HTTPException(404, f"Unknown group '{group}'. Valid groups: {', '.join(GROUP_LABELS)}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "records": len(projects())}


@app.get("/groups")
def list_groups() -> list[dict]:
    """The eight groups, their categories, and how many projects each has (FY2016–2025)."""
    c, p = categories(), projects()
    counts = p.explode("group_list").group_list.value_counts()
    return [{"group": g, "label": label, "level": "subgroup" if g in SUBGROUPS else "group",
             "parent": SUBGROUPS.get(g), "projects": int(counts.get(g, 0)),
             "categories": [{"category": r.category_id, "label": r.label}
                            for r in c[(c.ds_group == g) | (c.ds_subgroup == g)].itertuples()]}
            for g, label in GROUP_LABELS.items()]


@app.get("/groups/summary")
def summary(fy: int = Query(2025, ge=2016, le=2025)) -> list[dict]:
    """Projects, share of data science projects, and extramural funding per group in one fiscal year."""
    t = trend()[lambda d: d.fy == fy]
    cols = ["ds_group", "group_label", "projects", "share_of_ds_projects", "extramural_cost", "share_of_ds_funding"]
    return t.sort_values("projects", ascending=False)[cols].round(4).to_dict("records")


@app.get("/groups/{group}/trend")
def group_trend(group: str) -> list[dict]:
    """One group by fiscal year."""
    check_group(group)
    cols = ["fy", "projects", "share_of_ds_projects", "extramural_cost", "share_of_ds_funding"]
    return trend()[lambda d: d.ds_group == group].sort_values("fy")[cols].round(4).to_dict("records")


@app.get("/groups/{group}/institutes")
def group_institutes(group: str, limit: int = Query(10, ge=1, le=60)) -> list[dict]:
    """Institutes with the most projects in a group, FY2016–2025."""
    check_group(group)
    p = projects()
    p = p[p.group_list.map(lambda gs: group in gs)]
    out = p.groupby("ic").agg(projects=("core_project_number", "size"), extramural_cost=("extramural_cost", "sum"))
    return out.sort_values("projects", ascending=False).head(limit).reset_index().round(0).to_dict("records")


@app.get("/projects")
def list_projects(group: str | None = None, category: str | None = None, ic: str | None = None,
                  nofo: str | None = None,
                  fy: int | None = Query(None, ge=2016, le=2025), ai_only: bool = False,
                  limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    """Data science projects, filtered by group, category, institute code (e.g. CA), funding opportunity
    (NOFO) number, active fiscal year, or substantive AI. Paged with limit and offset."""
    p = projects()
    if group:
        check_group(group)
        p = p[p.group_list.map(lambda gs: group in gs)]
    if category:
        p = p[p.category_list.map(lambda cs: category in cs)]
    if ic:
        p = p[p.ic.str.upper() == ic.upper()]
    if nofo and "nofos" in p.columns:  # funding opportunity number, e.g. PAR-23-123 (partial match)
        p = p[p.nofos.fillna("").str.upper().str.contains(nofo.upper(), regex=False)]
    if fy:
        p = p[(p.first_fy <= fy) & (p.last_fy >= fy)]
    if ai_only:
        p = p[p.ai_label == "Y"]
    cols = [c for c in ["core_project_number", "subproject_id", "project_title", "ic", "activity", "org_name",
                        "first_fy", "last_fy", "groups", "categories", "nofos", "ai_label", "ai_role", "extramural_cost"]
            if c in p.columns]
    page = p.sort_values(["last_fy", "core_project_number"], ascending=[False, True]).iloc[offset:offset + limit]
    return {"total": len(p), "limit": limit, "offset": offset,
            "results": page[cols].fillna("").to_dict("records")}


@app.get("/projects/{core_project_number}")
def get_project(core_project_number: str) -> list[dict]:
    """A project's parent record and any subprojects."""
    p = projects()
    rows = p[p.core_project_number == core_project_number.upper()]
    if rows.empty:
        raise HTTPException(404, f"No data science record for {core_project_number}")
    return rows.drop(columns=["group_list", "category_list"]).fillna("").to_dict("records")
