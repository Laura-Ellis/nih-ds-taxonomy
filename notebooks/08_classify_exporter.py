# %% [markdown]
# # 08 Classify all NIH projects with keywords (FY2016–FY2026; FY2026 is preliminary)
#
# Based on `00 Import and combine raw data files.ipynb` in github.com/Laura-Ellis/NIH, revised:
# works one fiscal year at a time, classifies **projects** rather than yearly applications, and
# keeps abstract text only for projects the keywords flag.
#
# **Project level.** A project appears once per fiscal year (one application each year). Rows are
# grouped into one record per `core_project_number` + `subproject_id`:
# - `core_project_number`: ExPORTER's `core_project_num` when present, otherwise activity code +
#   2-letter IC code + 6-digit serial number (for example, R01CA123456)
# - `subproject_id`: ExPORTER's subproject ID, blank for the parent project. Subprojects (cores and
#   components of centers and program projects) get their own record with their own abstracts.
# - `fiscal_years`: the fiscal years with an application, concatenated ("2023; 2024; 2025")
# - `nofos`: the funding opportunities (NOFOs, also called FOAs, e.g. PAR-23-123) the record's applications
#   responded to, in fiscal-year order; `exporter_applications.parquet` has `nofo` per application
# - `application_ids`: the record's application IDs in fiscal-year order ("10234567; 10456789"), for
#   matching to other ExPORTER tables (publications, patents, clinical studies) later;
#   `exporter_applications.parquet` has the same link one row per application
#
# Each record gets one combined text: its latest title, any earlier titles that differ, and every
# distinct abstract across years (identical abstracts count once).
#
# **Input:** one projects and one abstracts parquet file per fiscal year (`FY2023.parquet`), in
# ExPORTER's column layout, from the folders in `config/settings.yaml` (`sources.projects`,
# `sources.abstracts`). The shared process builds them from the RePORTER API with
# `notebooks/00_update_reporter.py`; `config/local.yaml` can point to other copies, such as files
# built from ExPORTER downloads. Fiscal years come from `fiscal_years` in settings.yaml (FY2016–FY2026;
# FY2027 is pulled but not analyzed). FY2026 (`preliminary_fy`) is preliminary: NIH is still adding and
# revising its records.
#
# **Outputs**
# - `data/processed/exporter_core_projects.parquet`: one row per `core_project_number` +
#   `subproject_id` (parent projects and subprojects); fiscal years, latest IC and activity code, costs, keyword flags, and the
#   parent–subproject relationship. No abstracts.
#
# **Funding.** A parent award's `total_cost` already includes its subprojects' costs, so adding the
# two double counts. `attributed_cost` gives each subproject its own cost and the parent the
# remainder; sum `attributed_cost` for any total. `award_total_cost` (parents) is the full award.
#
# **Subprojects vs. subawards.** A subproject is a defined component of a multi-component
# application (a core or project within a center or P01) and has its own title and abstract here.
# A subaward passes funds to another organization; ExPORTER does not list subawards.
# - `data/processed/exporter_applications.parquet`: one row per application (project-year); IDs,
#   IC, costs, RCDC spending categories, and other metadata, with the project's flags. No abstracts.
# - `data/processed/exporter_flagged_text.parquet`: combined text for flagged projects only
# - `reports/exporter_summary.csv`: projects, flags, and costs by fiscal year
#
# **Flags** (from `src/taxonomy.py`; method in METHODOLOGY.md)
# - `ds_flag` / `ai_flag`: any keyword match (DS recall 94%, AI recall 100% on the coded sample)
# - `ds_likely` / `ai_likely`: evidence rule (terms repeat or sit near an action phrase)
# - Flagged = `ds_flag`; keywords miss an estimated 2–6% of data science projects, accepted here.
#
# Labels are cached by combined text; reruns only label projects whose text changed.

# %%
import gc
import hashlib
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import FISCAL_YEARS, PRELIMINARY_FY, find_fy_file, source  # noqa: E402  # pyright: ignore[reportMissingImports]
from progress import say, start  # noqa: E402  # pyright: ignore[reportMissingImports]

INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
for d in (INTERIM, PROCESSED):
    d.mkdir(parents=True, exist_ok=True)


# Metadata kept for every project (ExPORTER column names, lowercased)
META = ["application_id", "fy", "activity", "administering_ic", "funding_ics", "funding_mechanism",
        "core_project_num", "full_project_num", "subproject_id", "application_type", "support_year",
        "org_name", "org_state", "org_country", "pi_ids", "project_title", "project_start", "project_end",
        "total_cost", "total_cost_sub_project", "direct_cost_amt", "indirect_cost_amt", "nih_spending_cats",
        "serial_number", "in_api", "opportunity number"]

# Labels are cached per taxonomy version: editing terms.csv or categories.yaml relabels everything
TAXONOMY_HASH = hashlib.md5(b"".join((ROOT / "taxonomy" / f).read_bytes()
                                     for f in ("terms.csv", "categories.yaml"))).hexdigest()[:8]
LABEL_CACHE = INTERIM / f"keyword_labels_{TAXONOMY_HASH}.parquet"


def find_file(kind: str, fy: int) -> Path | None:
    """kind: 'projects' or 'abstracts'. The fiscal year's parquet file in the configured folder, or the
    shared API folder when the configured one doesn't have that year."""
    return find_fy_file(kind, fy)


def read_file(path: Path, usecols: set[str]) -> pd.DataFrame:
    """Read the columns in usecols (case-insensitive) from a parquet file or an ExPORTER zip."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        names = pq.read_schema(path).names
        df = pd.read_parquet(path, columns=[c for c in names if c.strip().lower() in usecols])
    else:
        with zipfile.ZipFile(path) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            for enc in ("utf-8", "latin-1"):
                try:
                    with zf.open(name) as fh:
                        df = pd.read_csv(fh, encoding=enc, low_memory=False,
                                         usecols=lambda c: c.strip().lower() in usecols)
                    break
                except UnicodeDecodeError:
                    continue
    df.columns = df.columns.str.strip().str.lower()
    return df


def text_hash(title: str, abstract: str) -> str:
    return hashlib.md5(f"{title}\n{abstract}".encode("utf-8", "replace")).hexdigest()


def norm(text) -> str:
    """Whitespace- and case-insensitive form, to treat lightly reformatted text as the same."""
    if not isinstance(text, str):
        if text is None or pd.isna(text):  # None, NaN, or pd.NA
            return ""
        text = str(text)
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def add_core_project_number(df: pd.DataFrame) -> pd.DataFrame:
    """core_project_number = core_project_num, or activity + 2-letter IC + 6-digit serial number."""
    built = (df.get("activity", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
             + df.get("administering_ic", pd.Series("", index=df.index)).fillna("").astype(str).str.strip().str[:2]
             + pd.to_numeric(df.get("serial_number"), errors="coerce").map(
                 lambda n: f"{int(n):06d}" if pd.notna(n) else ""))
    existing = df.get("core_project_num", pd.Series(pd.NA, index=df.index)).astype("string").str.strip()
    df["core_project_number"] = existing.where(existing.notna() & (existing != ""), built)
    # Last resort: no core number and no serial number
    missing = df.core_project_number.isna() | (df.core_project_number.str.len() < 6)
    df.loc[missing, "core_project_number"] = "APPL" + df.loc[missing, "application_id"].astype(str)
    sub = df.get("subproject_id", pd.Series(pd.NA, index=df.index))
    df["subproject_id"] = pd.to_numeric(sub, errors="coerce").astype("Int64").astype("string").fillna("")
    return df


available = {fy: (find_file("projects", fy), find_file("abstracts", fy)) for fy in FISCAL_YEARS}
for fy, (p, a) in available.items():
    print(fy, "projects:", p if p else "MISSING", "| abstracts:", a if a else "MISSING")
if not any(p for p, _ in available.values()):
    raise FileNotFoundError(f"No project files in {source('projects')}; run notebooks/00_update_reporter.py "
                            "or set sources.projects in config/local.yaml")
print(f"FY{PRELIMINARY_FY} is preliminary" if PRELIMINARY_FY else "No preliminary year")

# %% [markdown]
# ## 1. Read each fiscal year
# Keeps metadata for every application and the distinct text for each project.

# %%
_stop = start("1. Read each fiscal year")
applications, texts = [], []
for fy, (p_file, a_file) in available.items():
    if p_file is None:
        continue
    t0 = time.time()
    proj = read_file(p_file, usecols=set(META))
    if "in_api" in proj.columns:  # records no longer in the RePORTER API are kept in the files but not analyzed
        dropped = (proj.in_api == "N").sum()
        proj = proj[proj.in_api != "N"].drop(columns="in_api")
        if dropped:
            say(f"FY{fy}: {dropped:,} records not in the API excluded")
    proj = proj.rename(columns={"opportunity number": "nofo"})  # funding opportunity (NOFO/FOA) number
    if "nofo" not in proj.columns:
        proj["nofo"] = pd.NA
    proj["fy"] = pd.to_numeric(proj["fy"], errors="coerce").fillna(fy).astype(int)
    proj = add_core_project_number(proj)
    abst = read_file(a_file, usecols={"application_id", "abstract_text"}) if a_file else \
        pd.DataFrame(columns=["application_id", "abstract_text"])
    df = proj.merge(abst.drop_duplicates("application_id"), on="application_id", how="left")
    df["has_abstract"] = df.abstract_text.notna()
    # One row per distinct title or abstract within a project
    t = df[["core_project_number", "subproject_id", "fy", "project_title", "abstract_text"]].copy()
    t["title_key"], t["abstract_key"] = t.project_title.map(norm), t.abstract_text.map(norm)
    texts.append(t.drop_duplicates(["core_project_number", "subproject_id", "title_key", "abstract_key"]))
    applications.append(df.drop(columns=["abstract_text"]))
    say(f"FY{fy}: {len(df):,} applications, {df.core_project_number.nunique():,} projects, "
          f"{time.time() - t0:.0f}s")

applications = pd.concat(applications, ignore_index=True)

# Internal record ID (dropped before saving): core project number + subproject ID
applications["_record"] = applications.core_project_number + "|" + applications.subproject_id
applications["is_subproject"] = applications.subproject_id != ""
texts = pd.concat(texts, ignore_index=True)
texts["_record"] = texts.core_project_number + "|" + texts.subproject_id
texts = texts.sort_values(["_record", "fy"])
print(f"{len(applications):,} applications; {applications.core_project_number.nunique():,} core projects; "
      f"{applications._record.nunique():,} records including "
      f"{applications.loc[applications.is_subproject, '_record'].nunique():,} subprojects")
_stop()
# %% [markdown]
# ## 2. Combine text per project
# Title = latest title. Text = earlier titles that differ, then each distinct abstract in
# fiscal-year order.

# %%
_stop = start("2. Combine text per project")
def combine_all(texts: pd.DataFrame) -> pd.DataFrame:
    """Same result as a groupby-apply per record, as a plain loop (much faster on 250k+ records)."""
    rec: dict[str, dict] = {}
    cols = [texts[c].astype(object).where(texts[c].notna(), None).tolist()
            for c in ("_record", "project_title", "title_key", "abstract_text", "abstract_key")]
    for r, title, tkey, abstract, akey in zip(*cols):
        d = rec.setdefault(r, {"titles": {}, "abstracts": {}})
        if tkey:
            d["titles"].setdefault(tkey, str(title))
        if akey:
            d["abstracts"].setdefault(akey, str(abstract))
    rows = []
    for r, d in rec.items():
        titles, abstracts = list(d["titles"].values()), list(d["abstracts"].values())
        latest = titles[-1] if titles else ""
        other_titles = [x for x in titles if norm(x) != norm(latest)]
        rows.append({"_record": r, "project_title": latest, "abstract_text": "\n\n".join(other_titles + abstracts),
                     "n_titles": len(titles), "n_abstracts": len(abstracts)})
    return pd.DataFrame(rows)


t0 = time.time()
project_text = combine_all(texts)
project_text["text_hash"] = [text_hash(a, b) for a, b in zip(project_text.project_title, project_text.abstract_text)]
print(f"{len(project_text):,} records; {(project_text.n_abstracts > 1).mean():.1%} have more than one "
      f"distinct abstract; {time.time() - t0:.0f}s")
del texts  # the per-year text rows aren't needed after combining; frees memory for the keyword step
gc.collect()
_stop()
# %% [markdown]
# ## 3. Label projects with keywords

# %%
_stop = start("3. Label projects with keywords")
for col in ("activity", "administering_ic", "org_name", "org_state", "total_cost", "total_cost_sub_project"):
    if col not in applications:
        applications[col] = pd.NA  # some ExPORTER years or exports lack a column

# Funding without double counting. A parent award's total_cost already includes its subprojects'
# costs (total_cost_sub_project). attributed_cost gives each subproject its own cost and the parent
# the remainder, so attributed_cost sums to the award total and can be split by flag.
applications["total_cost"] = pd.to_numeric(applications.total_cost, errors="coerce").astype("float64")
applications["total_cost_sub_project"] = pd.to_numeric(applications.total_cost_sub_project, errors="coerce").astype("float64")
sub_cost = applications.total_cost_sub_project.where(applications.is_subproject).fillna(0)
parent_cost = applications.total_cost.where(~applications.is_subproject).fillna(0)
key = [applications.core_project_number, applications.fy]
sub_total = sub_cost.groupby(key).transform("sum")
parent_total = parent_cost.groupby(key).transform("sum")
remainder = (parent_total - sub_total).clip(lower=0)  # parent's own share in that year
share = (parent_cost / parent_total.where(parent_total > 0)).fillna(0)  # split across parent applications
applications["attributed_cost"] = sub_cost.where(applications.is_subproject, remainder * share)
over = (sub_total > parent_total) & (parent_total > 0)
if over.any():
    print(f"Note: {applications.loc[over, 'core_project_number'].nunique():,} project-years list subproject "
          "costs above the parent total; parent share set to 0 for those")
core = (applications.sort_values(["fy", "application_id"])
        .groupby("_record")
        .agg(core_project_number=("core_project_number", "first"), subproject_id=("subproject_id", "first"),
             is_subproject=("is_subproject", "first"),
             fiscal_years=("fy", lambda f: "; ".join(str(y) for y in sorted(set(f)))),
             application_ids=("application_id", lambda a: "; ".join(str(i) for i in dict.fromkeys(a))),
             # NOFOs (notices of funding opportunity) behind the record's applications, in fiscal-year order
             nofos=("nofo", lambda n: "; ".join(str(x) for x in dict.fromkeys(n.dropna()) if str(x).strip())),
             first_fy=("fy", "min"), last_fy=("fy", "max"), n_fy=("fy", "nunique"),
             n_applications=("application_id", "nunique"),
             activity=("activity", "last"), administering_ic=("administering_ic", "last"),
             org_name=("org_name", "last"), org_state=("org_state", "last"),
             award_total_cost=("total_cost", "sum"), subproject_cost=("total_cost_sub_project", "sum"),
             attributed_cost=("attributed_cost", "sum"))
        .reset_index())
# award_total_cost (parents only) includes subprojects; use attributed_cost for any sum across records
core.loc[core.is_subproject, "award_total_cost"] = pd.NA
core.loc[~core.is_subproject, "subproject_cost"] = pd.NA
project_text = project_text.merge(core[["_record", "core_project_number", "subproject_id", "application_ids",
                                        "activity"]],
                                  on="_record")

cache = pd.read_parquet(LABEL_CACHE) if LABEL_CACHE.exists() else pd.DataFrame(columns=["text_hash"])
LABEL_COLS = ["text_hash", "categories", "likely_categories", "matched_terms", "data_science_related",
              "ai_related", "ds_likely", "ai_likely", "ai_in_title", "ai_term_count"]
new = project_text[~project_text.text_hash.isin(set(cache.text_hash))].drop_duplicates("text_hash")
print(f"Labeling {len(new):,} unique project texts ({len(project_text) - len(new):,} projects reuse cached or identical text)")
CHUNK = 20_000
for i in range(0, len(new), CHUNK):
    t0 = time.time()
    part = new.iloc[i:i + CHUNK]
    lab = tx.label_projects(part.assign(activity_code=part.activity)
                            [["text_hash", "activity_code", "project_title", "abstract_text"]])[LABEL_COLS]
    for c in ("categories", "likely_categories"):
        lab[c] = lab[c].map("; ".join)
    cache = pd.concat([cache, lab], ignore_index=True)
    cache.to_parquet(LABEL_CACHE, index=False)  # progress is saved after every chunk
    say(f"  {min(i + CHUNK, len(new)):,} of {len(new):,} labeled ({time.time() - t0:.0f}s for this chunk)")

labels = project_text[["_record", "text_hash", "n_titles", "n_abstracts"]].merge(cache, on="text_hash")
labels = labels.rename(columns={"data_science_related": "ds_flag", "ai_related": "ai_flag"})
# Flags come back as object dtype when the cache mixes chunks; make them plain booleans (missing = not flagged)
BOOL_FLAGS = [c for c in ("ds_flag", "ai_flag", "ds_likely", "ai_likely") if c in labels]
labels[BOOL_FLAGS] = labels[BOOL_FLAGS].astype("boolean").fillna(False).astype(bool)
core = core.merge(labels.drop(columns=["matched_terms"]), on="_record", how="left")
core[BOOL_FLAGS] = core[BOOL_FLAGS].astype("boolean").fillna(False).astype(bool)
core["is_subproject"] = core.is_subproject.astype(bool)
core["training_mechanism"] = core.activity.fillna("").map(tx._is_training_code)

# Parent–subproject relationship: on parents, how many subprojects carry each flag; on subprojects,
# the parent's flag. Separates centers that do data science themselves from those whose data science
# sits in a component (for example, a data or bioinformatics core).
subs_only = core[core.is_subproject]
counts = subs_only.groupby("core_project_number").agg(
    n_subprojects=("_record", "count"), n_ds_subprojects=("ds_flag", "sum"),
    n_ai_subprojects=("ai_flag", "sum")).reset_index()
core = core.merge(counts, on="core_project_number", how="left")
for c in ("n_subprojects", "n_ds_subprojects", "n_ai_subprojects"):
    core[c] = core[c].astype("Int64").where(~core.is_subproject)  # blank on subproject records
parents = core.loc[~core.is_subproject, ["core_project_number", "ds_flag", "ai_flag"]].rename(
    columns={"ds_flag": "parent_ds_flag", "ai_flag": "parent_ai_flag"})
core = core.merge(parents, on="core_project_number", how="left")
for c in ("parent_ds_flag", "parent_ai_flag"):
    core[c] = core[c].astype("boolean").where(core.is_subproject)  # blank on parent records
core["ds_location"] = pd.Series("none", index=core.index, dtype="string")
core.loc[~core.is_subproject & core.ds_flag, "ds_location"] = "parent"
core.loc[~core.is_subproject & ~core.ds_flag & (core.n_ds_subprojects > 0), "ds_location"] = "subprojects only"
core.loc[~core.is_subproject & core.ds_flag & (core.n_ds_subprojects > 0), "ds_location"] = "parent and subprojects"
core.loc[core.is_subproject, "ds_location"] = pd.NA
print(f"{core.ds_flag.sum():,} of {len(core):,} records flagged for data science ({core.ds_flag.mean():.1%}); "
      f"{core.ai_flag.sum():,} for AI ({core.ai_flag.mean():.1%})")
_stop()
# %% [markdown]
# ## 4. Save

# %%
_stop = start("4. Save")
FLAGS = ["ds_flag", "ai_flag", "ds_likely", "ai_likely", "categories", "likely_categories"]
applications = applications.merge(core[["_record"] + FLAGS], on="_record", how="left")
flagged = project_text.merge(labels[["_record", "ds_flag", "matched_terms", "likely_categories"]],
                             on="_record")
flagged = flagged[flagged.ds_flag].drop(columns=["ds_flag", "activity"])

core.drop(columns="_record").to_parquet(PROCESSED / "exporter_core_projects.parquet", index=False)
applications.drop(columns="_record").to_parquet(PROCESSED / "exporter_applications.parquet", index=False)
flagged.drop(columns="_record").to_parquet(PROCESSED / "exporter_flagged_text.parquet", index=False)
print(f"Saved {len(core):,} records, {len(applications):,} applications, {len(flagged):,} flagged texts")
_stop()
# %% [markdown]
# ## Summary by fiscal year
# Counts are records (parent projects and subprojects); `core_projects` counts parents only.
# A record counts in each year it has an application. Costs use `attributed_cost`, so a center's
# funding counts once: subprojects get their own cost and the parent the remainder.

# %%
_stop = start("Summary by fiscal year")
applications["cost"] = applications.attributed_cost
by_fy = applications.groupby("fy")
summary = pd.DataFrame({
    "core_projects": by_fy.core_project_number.nunique(),
    "projects": by_fy._record.nunique(),
    "ds_projects": applications[applications.ds_flag].groupby("fy")._record.nunique(),
    "ai_projects": applications[applications.ai_flag].groupby("fy")._record.nunique(),
    "ds_likely_projects": applications[applications.ds_likely].groupby("fy")._record.nunique(),
    "ai_likely_projects": applications[applications.ai_likely].groupby("fy")._record.nunique(),
    "total_cost": by_fy.cost.sum(),
    "ds_cost": applications[applications.ds_flag].groupby("fy").cost.sum(),
    "ai_cost": applications[applications.ai_flag].groupby("fy").cost.sum(),
}).fillna(0).reset_index()
summary["ds_share"] = (summary.ds_projects / summary.projects).round(3)
summary["ai_share"] = (summary.ai_projects / summary.projects).round(3)
summary.to_csv(REPORTS / "exporter_summary.csv", index=False)
summary
_stop()
# %% [markdown]
# ## Cost to label the flagged projects with models
# Per-project costs observed on the 150 coded projects: Jev $0.00014, Claude about $0.006.
# Combined text for multi-year projects is longer, so this scales by text length.
# Claude handles only calls where Jev is less than 90% confident: 11% for AI, about 40% for AI or DS.

# %%
_stop = start("Cost to label the flagged projects with models")
n = len(flagged)
length_factor = flagged.abstract_text.str.len().mean() / 2_800  # sampled abstracts average about 2,800 characters
JEV, CLAUDE = 0.00014, 0.006
estimate = pd.DataFrame([
    {"step": "Jev on flagged projects", "projects": n, "cost": n * JEV * max(1, length_factor)},
    {"step": "Claude on uncertain AI calls (11%)", "projects": round(n * 0.11),
     "cost": n * 0.11 * CLAUDE * max(1, length_factor)},
    {"step": "Claude on uncertain AI or DS calls (40%)", "projects": round(n * 0.40),
     "cost": n * 0.40 * CLAUDE * max(1, length_factor)},
])
estimate["cost"] = estimate.cost.round(2)
print(f"Average combined text is {length_factor:.1f}x a single abstract")
estimate
_stop()
