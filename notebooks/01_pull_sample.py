# %% [markdown]
# # 01 Pull a test sample of NIH projects
#
# Pulls a stratified sample of NIH projects from the NIH RePORTER API to test whether
# the taxonomy categories fit real abstracts.
#
# | Stratum | What | Why |
# |---|---|---|
# | ai_search | Projects matching AI or data science phrases | Check categories and false positives |
# | general | Random research projects (R01, R21, U01, R35) | Check what the taxonomy flags in ordinary projects |
# | training | Training and career projects (T, F, K, R25) | Check the workforce dimension |
#
# Fiscal years 2019, 2022, and 2025. RePORTER asks for no more than one request per second.
#
# Output: `data/raw/reporter_sample_<date>.csv`

# %%
import math
import random
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

API = "https://api.reporter.nih.gov/v2/projects/search"
FISCAL_YEARS = [2019, 2022, 2025]
PER_STRATUM_YEAR = {"ai_search": 100, "general": 100, "training": 50}
SEED = 20261023
random.seed(SEED)

FIELDS = ["ApplId", "ProjectNum", "ProjectTitle", "AbstractText", "FiscalYear",
          "ActivityCode", "AgencyIcAdmin", "AwardAmount", "SpendingCategoriesDesc"]

AI_SEARCH = ('"artificial intelligence" OR "machine learning" OR "deep learning" OR '
             '"neural network" OR "natural language processing" OR "large language model" OR '
             '"data science" OR "computer vision" OR "data commons" OR "cloud computing"')

STRATA = {
    "ai_search": {"advanced_text_search": {"operator": "advanced",
                                           "search_field": "projecttitle,abstracttext",
                                           "search_text": AI_SEARCH}},
    "general": {"activity_codes": ["R01", "R21", "U01", "R35"]},
    "training": {"activity_codes": ["T32", "T15", "F30", "F31", "F32", "K01", "K08",
                                    "K23", "K25", "K99", "R25"]},
}


# %%
def search(criteria: dict, offset: int = 0, limit: int = 1) -> dict:
    body = {"criteria": criteria, "include_fields": FIELDS, "offset": offset, "limit": limit}
    r = requests.post(API, json=body, timeout=60)
    r.raise_for_status()
    time.sleep(1)
    return r.json()


def random_sample(criteria: dict, n: int, page: int = 50) -> tuple[list[dict], int]:
    """Sample about n projects by reading pages at random offsets (API caps offset at 14,999)."""
    total = search(criteria)["meta"]["total"]
    pages = list(range(0, min(total, 15000), page))
    starts = random.sample(pages, k=min(math.ceil(n / page) + 1, len(pages)))
    rows = []
    for s in starts:
        rows += search(criteria, offset=s, limit=page)["results"]
    random.shuffle(rows)
    return rows[:n], total


# %%
records, totals = [], []
for fy in FISCAL_YEARS:
    for stratum, extra in STRATA.items():
        criteria = {"fiscal_years": [fy], **extra}
        rows, total = random_sample(criteria, PER_STRATUM_YEAR[stratum])
        totals.append({"fiscal_year": fy, "stratum": stratum, "total_matching": total, "sampled": len(rows)})
        for r in rows:
            records.append({
                "appl_id": r.get("appl_id"),
                "project_num": r.get("project_num"),
                "fiscal_year": r.get("fiscal_year"),
                "activity_code": r.get("activity_code"),
                "ic": (r.get("agency_ic_admin") or {}).get("abbreviation"),
                "award_amount": r.get("award_amount"),
                "project_title": r.get("project_title"),
                "abstract_text": r.get("abstract_text"),
                "rcdc_categories": r.get("spending_categories_desc"),
                "stratum": stratum,
            })
        print(f"FY{fy} {stratum}: {len(rows)} of {total:,}")

# %%
sample = pd.DataFrame(records).drop_duplicates("appl_id")
sample["rcdc_ml_ai"] = sample.rcdc_categories.fillna("").str.contains(
    "Machine Learning and Artificial Intelligence", case=False)
out = RAW / f"reporter_sample_{date.today():%Y%m%d}.csv"
sample.to_csv(out, index=False)
pd.DataFrame(totals).to_csv(RAW / f"reporter_sample_totals_{date.today():%Y%m%d}.csv", index=False)
print(f"Saved {len(sample):,} projects to {out}")
sample.groupby(["fiscal_year", "stratum"]).size().unstack()
