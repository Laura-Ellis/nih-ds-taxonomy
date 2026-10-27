"""NIH RePORTER API v2 client: project records (with abstracts) and publication links, mapped to
ExPORTER column names so the rest of the pipeline reads API and ExPORTER files the same way.

API: https://api.reporter.nih.gov (no key). Limits: 500 records per request, offsets up to 14,999,
about one request per second.
"""

from __future__ import annotations

import hashlib
import json
import time

import numpy as np
import pandas as pd
import requests

PROJECTS_URL = "https://api.reporter.nih.gov/v2/projects/search"
PUBS_URL = "https://api.reporter.nih.gov/v2/publications/search"
PAGE, MAX_OFFSET, PAUSE = 500, 14_500, 1.0

# Administering agencies (NIH institutes and centers plus the other agencies RePORTER lists)
AGENCIES = ["NCI", "NHLBI", "NIAID", "NIGMS", "NIA", "NINDS", "NIMH", "NIDDK", "NICHD", "NIDA", "NIAAA",
            "NIEHS", "NEI", "NIDCD", "NIDCR", "NIAMS", "NIBIB", "NHGRI", "NLM", "NIMHD", "NINR", "NCCIH",
            "NCATS", "FIC", "OD", "CC", "CIT", "AHRQ", "CDC", "FDA", "VA", "ACF", "HRSA", "SAMHSA", "IHS"]
EXCLUDE = ["PhrText", "PrefTerms"]  # large text fields the pipeline doesn't use


def post(url: str, body: dict, tries: int = 5) -> dict:
    """POST with retries and backoff for rate limits and server errors."""
    for k in range(tries):
        r = requests.post(url, json=body, timeout=120)
        if r.status_code in (429, 500, 502, 503, 504) and k < tries - 1:
            time.sleep(5 * 2 ** k)
            continue
        r.raise_for_status()
        return r.json()
    return {}


def search(criteria: dict, url: str = PROJECTS_URL, exclude: list[str] | None = EXCLUDE) -> tuple[list[dict], int]:
    """All results for one query (up to the API's offset limit). Returns results and the reported total."""
    out, offset = [], 0
    while True:
        body = {"criteria": criteria, "offset": offset, "limit": PAGE}
        if exclude and url == PROJECTS_URL:
            body["exclude_fields"] = exclude
        data = post(url, body)
        total = data.get("meta", {}).get("total", 0)
        out += data.get("results", [])
        offset += PAGE
        time.sleep(PAUSE)
        if offset >= total or offset > MAX_OFFSET or not data.get("results"):
            return out, total


def count(criteria: dict) -> int:
    return post(PROJECTS_URL, {"criteria": criteria, "offset": 0, "limit": 1}).get("meta", {}).get("total", 0)


# Contracts and interagency agreements have no application type, so a split by application type
# misses them; they are pulled by activity code instead
CONTRACT_CODES = ["N01", "N02", "N03", "N43", "N44", "N4C", "Y01", "Y02", "Y3", "Y4"]


def pull_fiscal_year(fy: int, log=print) -> list[dict]:
    """Every project record for a fiscal year, one query per administering agency. An agency with more
    than the API's 15,000-record window is split by application type (1–9) plus contract activity
    codes; the run warns if the parts don't add up to the agency's total."""
    records, seen = [], 0
    for ag in AGENCIES:
        crit = {"fiscal_years": [fy], "agencies": [ag], "is_agency_admin": True}
        recs, total = search(crit)
        if total > MAX_OFFSET:
            parts = {}
            for t in "123456789":
                for r in search({**crit, "award_types": [t]})[0]:
                    parts[(r.get("appl_id"), r.get("subproject_id"))] = r
            for r in search({**crit, "activity_codes": CONTRACT_CODES})[0]:
                parts[(r.get("appl_id"), r.get("subproject_id"))] = r
            recs = list(parts.values())
            if len(recs) < total:
                log(f"  WARNING FY{fy} {ag}: split pulled {len(recs):,} of {total:,} records")
        records += recs
        seen += total
    all_total = count({"fiscal_years": [fy]})
    log(f"FY{fy}: {len(records):,} records pulled; the API reports {all_total:,}"
        + ("" if seen >= all_total else f" ({all_total - seen:,} under agencies not listed)"))
    return records


# ---------------------------------------------------------------------------------------------
# Mapping to ExPORTER columns

def _s(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return str(v)


def _nz(v):
    """Drop leading zeros, as ExPORTER does ('062334' -> '62334')."""
    v = _s(v)
    return (v.lstrip("0") or "0") if v and v.isdigit() else v


def _date(v):
    return _s(v)[:10] if v else None


def to_exporter(r: dict) -> dict:
    """One API project record as an ExPORTER projects row (all values text)."""
    org = r.get("organization") or {}
    split = r.get("project_num_split") or {}
    admin = r.get("agency_ic_admin") or {}
    sub = _s(r.get("subproject_id"))
    pis = r.get("principal_investigators") or []
    award = r.get("award_amount")
    return {
        "APPLICATION_ID": _s(r.get("appl_id")), "ACTIVITY": _s(r.get("activity_code")),
        "ADMINISTERING_IC": _s(admin.get("code")),
        "APPLICATION_TYPE": _s(split.get("appl_type_code") or r.get("award_type")),
        "ARRA_FUNDED": "Y" if r.get("arra_funded") == "Y" else "N",
        "AWARD_NOTICE_DATE": _date(r.get("award_notice_date")),
        "BUDGET_START": _date(r.get("budget_start")), "BUDGET_END": _date(r.get("budget_end")),
        "CFDA_CODE": _s(r.get("cfda_code")), "CORE_PROJECT_NUM": _s(r.get("core_project_num")),
        "OPPORTUNITY NUMBER": _s(r.get("opportunity_number")), "FULL_PROJECT_NUM": _s(r.get("project_num")),
        "FUNDING_ICs": "".join(f"{f.get('abbreviation')}:{f.get('total_cost')}\\"
                               for f in (r.get("agency_ic_fundings") or [])) or None,
        "FUNDING_MECHANISM": _s(r.get("funding_mechanism")), "FY": _s(r.get("fiscal_year")),
        "IC_NAME": _s(admin.get("name")), "NIH_SPENDING_CATS": _s(r.get("spending_categories_desc")) or None,
        "ORG_CITY": _s(org.get("org_city")), "ORG_COUNTRY": _s(org.get("org_country")),
        "ORG_NAME": _s(org.get("org_name")), "ORG_STATE": _s(org.get("org_state")),
        "ORG_ZIPCODE": _s(org.get("org_zipcode")),
        "PI_IDS": ";".join(f"{p.get('profile_id')}{' (contact)' if p.get('is_contact_pi') else ''}" for p in pis) or None,
        "PI_NAMEs": ";".join(p.get("full_name", "") for p in pis) or None,
        "PROGRAM_OFFICER_NAME": ";".join(p.get("full_name", "") for p in (r.get("program_officers") or [])) or None,
        "PROJECT_START": _date(r.get("project_start_date")), "PROJECT_END": _date(r.get("project_end_date")),
        "PROJECT_TERMS": _s(r.get("terms")), "PROJECT_TITLE": _s(r.get("project_title")),
        "SERIAL_NUMBER": _nz(split.get("serial_num")), "SUBPROJECT_ID": sub, "SUFFIX": _s(split.get("suffix_code")),
        "SUPPORT_YEAR": _nz(split.get("support_year")),
        "DIRECT_COST_AMT": _s(r.get("direct_cost_amt")), "INDIRECT_COST_AMT": _s(r.get("indirect_cost_amt")),
        # ExPORTER puts a parent's cost in TOTAL_COST and a subproject's in TOTAL_COST_SUB_PROJECT
        "TOTAL_COST": _s(award) if sub is None else None,
        "TOTAL_COST_SUB_PROJECT": _s(award) if sub else None,
        "SOURCE_FILE": "RePORTER API v2",
    }


def to_tables(records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Projects and abstracts tables (ExPORTER layout) from API records."""
    proj = pd.DataFrame([to_exporter(r) for r in records])
    if proj.empty:
        return proj, pd.DataFrame(columns=["APPLICATION_ID", "ABSTRACT_TEXT", "FY", "SOURCE_FILE"])
    proj = proj.drop_duplicates(["APPLICATION_ID", "SUBPROJECT_ID"])
    abst = pd.DataFrame([{"APPLICATION_ID": _s(r.get("appl_id")), "ABSTRACT_TEXT": r.get("abstract_text"),
                          "FY": _s(r.get("fiscal_year")), "SOURCE_FILE": "RePORTER API v2"}
                         for r in records if r.get("abstract_text")]).drop_duplicates("APPLICATION_ID")
    return proj, abst


def row_hash(df: pd.DataFrame, exclude: tuple[str, ...] = ("SOURCE_FILE", "IN_API", "NOT_IN_API_SINCE")) -> pd.Series:
    """Stable hash of each row's values, to tell changed records from unchanged ones."""
    cols = [c for c in df.columns if c not in exclude]
    return df[cols].astype("string").fillna("").agg("\x1f".join, axis=1).map(
        lambda s: hashlib.md5(s.encode("utf-8")).hexdigest())


# ---------------------------------------------------------------------------------------------
# Publication links

def pull_pub_links(core_project_nums: list[str], batch: int = 100, log=print) -> pd.DataFrame:
    """PMID links for core project numbers, as ExPORTER's link table (PMID, PROJECT_NUMBER)."""
    rows = []
    for i in range(0, len(core_project_nums), batch):
        recs, _ = search({"core_project_nums": core_project_nums[i:i + batch]}, url=PUBS_URL, exclude=None)
        rows += [{"PMID": _s(r.get("pmid")), "PROJECT_NUMBER": _s(r.get("coreproject"))} for r in recs]
        if (i // batch) % 50 == 0:
            log(f"  publication links: {min(i + batch, len(core_project_nums)):,} of {len(core_project_nums):,} projects")
    return pd.DataFrame(rows, columns=["PMID", "PROJECT_NUMBER"]).drop_duplicates()


def dumps(records: list[dict]) -> str:
    return "\n".join(json.dumps(r) for r in records)
