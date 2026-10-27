# %% [markdown]
# # 12 Citation impact, patents, and clinical trials: AI vs. matched non-AI projects
#
# Run on your own machine (the APIs are not reachable from Claude's workspace). Inputs:
# - `data/processed/matched_projects.parquet` from notebook 11 (extramural core projects starting
#   FY2016–2020, with match weights)
# - ExPORTER publication links (`C:\data\nih\combined\pub_links`)
# - ExPORTER **Patents** and **Clinical Studies** downloads, saved anywhere under `C:\data\nih`
#   (CSV or zip; https://reporter.nih.gov/exporter)
#
# APIs (cached in `data/interim/`, so reruns are free and resume where they stopped):
# - **iCite** (NIH): Relative Citation Ratio for every linked paper. 200 papers per request.
# - **OpenAlex**: field-weighted citation impact (FWCI) for a random sample of papers per group;
#   uses the "### OpenAlex" key in ~/KEYS.md.
#
# **Definitions**
# - RCR (Relative Citation Ratio) = a paper's citations per year ÷ the expected rate for its field;
#   1.0 = the median NIH-funded paper. Project RCR = mean RCR of its papers.
# - FWCI (field-weighted citation impact) = citations ÷ the average for papers of the same field,
#   type, and year; 1.0 = world average.
# - Linked to a patent = the core project number appears in ExPORTER's patent table; linked to a
#   trial = it appears in ExPORTER's clinical studies table.
# - All group values are weighted so non-AI projects match the AI projects' IC, activity code, first
#   fiscal year, and size band (notebook 11).

# %%
import json
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
from llm_label import get_key  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED, INTERIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "interim", ROOT / "reports" / "results"
from settings import source  # noqa: E402  # pyright: ignore[reportMissingImports]

LINK_TABLES = source("link_tables")  # ExPORTER Patents.csv and ClinicalStudies.csv
EMAIL = "laura.ellis.data@gmail.com"
OPENALEX_SAMPLE = 20_000  # papers per group (scope x treated/comparison) for FWCI

# One row per scope (Data science, AI) and matched project; notebook 11 keeps only matched strata
proj = pd.read_parquet(PROCESSED / "matched_projects.parquet")
LABELS = {"Data science": ("Data science", "Matched non-data-science"), "AI": ("AI-related", "Matched non-AI")}


def by_group(df: pd.DataFrame, col: str) -> list[dict]:
    """Weighted stats of col for each scope's treated and comparison groups."""
    out = []
    for scope, (t_lab, c_lab) in LABELS.items():
        d = df[df.scope == scope]
        out += [{"scope": scope, "group": t_lab, **wstats(d[d.treated], col)},
                {"scope": scope, "group": c_lab, **wstats(d[~d.treated], col)}]
    return out


links = pd.concat(pd.read_parquet(f) for f in sorted(source("pub_links").glob("*.parquet")))
links.columns = links.columns.str.lower()
links = links[links.project_number.isin(proj.core_project_number)].drop_duplicates(["pmid", "project_number"])
links["pmid"] = pd.to_numeric(links.pmid, errors="coerce").dropna().astype("int64")
pmids = links.pmid.dropna().astype("int64").unique()
print(proj.groupby(["scope", "treated"]).size().rename("projects").to_string())
print(f"{len(pmids):,} linked papers")


def wstats(d: pd.DataFrame, col: str) -> dict:
    d = d.dropna(subset=[col]).sort_values(col)
    if d.empty:
        return {"mean": None, "median": None, "n": 0}
    cum = d.weight.cumsum()
    return {"mean": (d[col] * d.weight).sum() / d.weight.sum(),
            "median": d.loc[cum >= d.weight.sum() / 2, col].iloc[0], "n": len(d)}


# %% [markdown]
# ## iCite: Relative Citation Ratio

# %%
ICITE_CACHE = INTERIM / "icite.parquet"
icite = pd.read_parquet(ICITE_CACHE) if ICITE_CACHE.exists() else pd.DataFrame(columns=["pmid", "rcr", "year"])
todo = sorted(set(pmids) - set(icite.pmid))
print(f"iCite: {len(todo):,} papers to fetch ({len(icite):,} cached)")
ICITE_CHUNK = 200  # 1,000 PMIDs makes the URL too long for iCite (HTTP 414); 200 stays under the limit


def get_json(url: str, params: dict, tries: int = 4) -> dict:
    """GET with retries and backoff for rate limits and server errors."""
    for k in range(tries):
        r = requests.get(url, params=params, timeout=120)
        if r.status_code in (429, 500, 502, 503, 504) and k < tries - 1:
            time.sleep(2 ** k * 5)
            continue
        r.raise_for_status()
        return r.json()
    return {}


for i in range(0, len(todo), ICITE_CHUNK):
    chunk = todo[i:i + ICITE_CHUNK]
    data = get_json("https://icite.od.nih.gov/api/pubs",
                    {"pmids": ",".join(map(str, chunk)), "fl": "pmid,relative_citation_ratio,year"})
    rows = [{"pmid": int(p["pmid"]), "rcr": p.get("relative_citation_ratio"), "year": p.get("year")}
            for p in data.get("data", [])]
    icite = pd.concat([icite, pd.DataFrame(rows)], ignore_index=True)
    if (i // ICITE_CHUNK) % 50 == 0 or i + ICITE_CHUNK >= len(todo):
        icite.to_parquet(ICITE_CACHE, index=False)  # progress saved every 50 requests
        print(f"  {min(i + ICITE_CHUNK, len(todo)):,} of {len(todo):,}")
    time.sleep(0.2)
icite.to_parquet(ICITE_CACHE, index=False)

# Project RCR = mean RCR of its papers (iCite leaves RCR blank for papers under two years old)
paper = links.merge(icite, on="pmid", how="left")
proj_rcr = paper.groupby("project_number").rcr.mean().rename("rcr")
proj = proj.merge(proj_rcr, left_on="core_project_number", right_index=True, how="left")
rcr = pd.DataFrame(by_group(proj, "rcr"))
rcr

# %% [markdown]
# ## OpenAlex: field-weighted citation impact (sample)

# %%
try:
    OA_KEY = get_key("OPENALEX_API_KEY", "OpenAlex")
except RuntimeError:
    OA_KEY = None
OA_CACHE = INTERIM / "openalex_fwci.parquet"
oa = pd.read_parquet(OA_CACHE) if OA_CACHE.exists() else pd.DataFrame(columns=["pmid", "fwci"])
group_of = links.merge(proj[["core_project_number", "scope", "treated", "weight"]], left_on="project_number",
                       right_on="core_project_number")
sample = pd.concat(g.drop_duplicates("pmid").sample(min(OPENALEX_SAMPLE, g.pmid.nunique()), random_state=1)
                   for _, g in group_of.groupby(["scope", "treated"]))
todo = sorted(set(sample.pmid) - set(oa.pmid))
print(f"OpenAlex: {len(todo):,} papers to fetch ({len(oa):,} cached)")
for i in range(0, len(todo), 50):
    chunk = todo[i:i + 50]
    params = {"filter": "pmid:" + "|".join(map(str, chunk)), "select": "ids,fwci", "per-page": 50, "mailto": EMAIL}
    if OA_KEY:
        params["api_key"] = OA_KEY
    data = get_json("https://api.openalex.org/works", params)
    rows = [{"pmid": int(w["ids"]["pmid"].rsplit("/", 1)[-1]), "fwci": w.get("fwci")}
            for w in data.get("results", []) if w.get("ids", {}).get("pmid")]
    oa = pd.concat([oa, pd.DataFrame(rows)], ignore_index=True)
    if (i // 50) % 100 == 0 or i + 50 >= len(todo):
        oa.to_parquet(OA_CACHE, index=False)
        print(f"  {min(i + 50, len(todo)):,} of {len(todo):,}")
    time.sleep(0.1)
oa.to_parquet(OA_CACHE, index=False)
s = sample.merge(oa.drop_duplicates("pmid"), on="pmid", how="left")
fwci = pd.DataFrame(by_group(s, "fwci"))
fwci

# %% [markdown]
# ## Patents and clinical trials (ExPORTER link tables)

# %%
def read_any(pattern: str) -> pd.DataFrame | None:
    files = [f for f in LINK_TABLES.rglob("*") if pattern in f.name.lower() and f.suffix.lower() in (".csv", ".zip")]
    if not files:
        print(f"No file matching '{pattern}' under {LINK_TABLES}; download it from ExPORTER")
        return None
    f = sorted(files)[-1]
    if f.suffix.lower() == ".zip":
        with zipfile.ZipFile(f) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            df = pd.read_csv(z.open(name), encoding="latin-1", low_memory=False)
    else:
        df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
    print(f"{f.name}: {len(df):,} rows; columns {list(df.columns)[:6]}")
    return df


def core_col(df: pd.DataFrame) -> str:
    return next(c for c in df.columns if "project" in c and ("core" in c or c in ("project_id", "project_number")))


translation = []
for label, pattern in [("patent", "patent"), ("clinical trial", "clinical")]:
    df = read_any(pattern)
    if df is None:
        continue
    linked = set(df[core_col(df)].astype(str).str.strip())
    proj[f"has_{label.split()[0]}"] = proj.core_project_number.isin(linked).astype(float)
    translation += [{"output": label, **r} for r in by_group(proj, f"has_{label.split()[0]}")]
translation = pd.DataFrame(translation)
translation

# %% [markdown]
# ## Save

# %%
results = pd.concat([rcr.assign(measure="Project RCR"), fwci.assign(measure="Paper FWCI (sample)"),
                     translation.rename(columns={"output": "measure"}).assign(
                         measure=lambda d: "Share linked to a " + d.measure)], ignore_index=True)
results.to_csv(OUT / "impact_matched.csv", index=False)
results
