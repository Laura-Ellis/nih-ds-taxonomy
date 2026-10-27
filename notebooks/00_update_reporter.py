# %% [markdown]
# # 00 Update project data from the NIH RePORTER API (new and changed records only)
#
# The shared way to build and refresh the data this pipeline classifies. Writes, per fiscal year,
# ExPORTER-format parquet files that notebook 08 reads:
# - `data/raw/reporter_api/projects/FY<year>.parquet`: project records, parents and subprojects
# - `data/raw/reporter_api/abstracts/FY<year>.parquet`: abstracts
# - `data/raw/reporter_api/pub_links/links.parquet`: publication links (PMID, core project number);
#   the first run takes about an hour more
# - `data/raw/reporter_api/manifest.csv`: when each year was pulled and what changed
#
# **What gets pulled on each run**
# - Fiscal years with no file yet: everything (first run: about 45 minutes for FY2016–FY2027)
# - The latest `open_years` fiscal years (settings.yaml; 3: FY2025–FY2027): pulled again, because NIH still
#   adds and revises records in them. Only records that are new or changed are counted as changes.
# - Older fiscal years: a one-request check for records RePORTER added since the last pull; the year
#   is pulled again only if there are any.
# - Publication links: for projects active in the last `link_refresh_years` fiscal years and any new
#   projects (papers keep linking to projects for years after they end).
#
# **Records are never discarded.** A record the API no longer returns stays in its fiscal year's file
# with `IN_API = N` and `NOT_IN_API_SINCE` (the first pull it was missing), so it can be found later.
# With `update.compare_dir` set (config/local.yaml), records in another copy of the files (such as
# ExPORTER) that the API never returned are kept the same way. Analyses use only `IN_API = Y` records.
#
# Downstream, notebook 08 relabels only records whose title or abstract text changed (labels are
# cached by text), so the model steps (notebooks 09 and 10) only pay for new or changed text.
#
# **Years:** `pull_years` (FY2016–FY2027) are pulled and kept current; analyses use `fiscal_years`
# (FY2016–FY2026), so FY2027 (started Oct 2026) is stored but not analyzed. FY2026 closed Sept 30,
# 2026, but its records are still settling: results label it "FY2026 (preliminary, as of <pull date>)".
#
# Settings: `config/settings.yaml`; personal overrides in `config/local.yaml` (git-ignored).
# `FORCE_FULL = True` re-pulls every year.

# %%
import gzip
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import reporter_api as api  # noqa: E402  # pyright: ignore[reportMissingImports]
from settings import PRELIMINARY_FY, PULL_YEARS, SETTINGS, default_source, source  # noqa: E402  # pyright: ignore[reportMissingImports]

FORCE_FULL = False
TODAY = date.today().isoformat()
# Always writes to the shared API folders (settings.yaml), whatever config/local.yaml points the pipeline at
PROJ_DIR, ABS_DIR, LINK_DIR = default_source("projects"), default_source("abstracts"), default_source("pub_links")
for d in (PROJ_DIR, ABS_DIR, LINK_DIR):
    d.mkdir(parents=True, exist_ok=True)
MANIFEST = PROJ_DIR.parent / "manifest.csv"
OPEN_YEARS = SETTINGS["update"]["open_years"]
LINK_YEARS = SETTINGS["update"]["link_refresh_years"]
# Optional (config/local.yaml): a folder of raw API pulls (projects_FY<year>.jsonl.gz) to build a
# year from instead of calling the API, e.g. pulls already made by another script
SEED_DIR = SETTINGS["update"].get("seed_dir")
KEY = ["APPLICATION_ID", "SUBPROJECT_ID"]

manifest = pd.read_csv(MANIFEST) if MANIFEST.exists() else pd.DataFrame(
    columns=["table", "fy", "pulled_at", "records", "new", "changed", "removed", "not_in_api", "preliminary", "reason"])
last_pull = {int(r.fy): str(r.pulled_at) for r in manifest[manifest.table == "projects"].itertuples()}
print(f"Pulling fiscal years {PULL_YEARS[0]}–{PULL_YEARS[-1]}; preliminary year: FY{PRELIMINARY_FY}")

# %% [markdown]
# ## Decide which fiscal years to pull

# %%
def added_since(fy: int, since: str) -> int | None:
    """Records RePORTER added to a fiscal year since a date; None if the API won't answer that query."""
    try:
        return api.count({"fiscal_years": [fy], "date_added": {"from_date": since, "to_date": TODAY}})
    except requests.HTTPError:
        return None


plan = {}
for fy in PULL_YEARS:
    if FORCE_FULL or not (PROJ_DIR / f"FY{fy}.parquet").exists():
        plan[fy] = "no file yet" if not FORCE_FULL else "full refresh"
    elif fy > PULL_YEARS[-1] - OPEN_YEARS:
        plan[fy] = "open year"
    else:
        n = added_since(fy, last_pull.get(fy, "2000-01-01"))
        if n:
            plan[fy] = f"{n:,} records added since {last_pull.get(fy)}"
        elif n is None:
            print(f"FY{fy}: the API didn't answer the date-added check; skipped (set FORCE_FULL to re-pull)")
print("\n".join(f"FY{fy}: pull ({why})" for fy, why in plan.items()) or "Nothing to pull")

# %% [markdown]
# ## Pull, compare with what's stored, and save

# %%
def load_seed(fy: int) -> list[dict] | None:
    """A saved pull for a fiscal year, used only when the abstracts come from elsewhere for that year
    (saved pulls may not include abstracts)."""
    other_abstracts = source("abstracts") != ABS_DIR and (source("abstracts") / f"FY{fy}.parquet").exists()
    if not SEED_DIR or not other_abstracts:
        return None
    f = Path(SEED_DIR) / f"projects_FY{fy}.jsonl.gz"
    if not f.exists():
        return None
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


FLAG_COLS = ["IN_API", "NOT_IN_API_SINCE"]
# Optional (config/local.yaml): folder of another copy of the projects files (for example built from
# ExPORTER). Records there that the API doesn't return are kept and marked, never analyzed.
COMPARE_DIR = SETTINGS["update"].get("compare_dir")
changes, rows = [], []
for fy, why in plan.items():
    recs = None if why != "no file yet" else load_seed(fy)
    if recs is not None:
        print(f"FY{fy}: building from saved pull in {SEED_DIR}")
    else:
        recs = api.pull_fiscal_year(fy)
    proj, abst = api.to_tables(recs)
    if proj.empty:
        print(f"FY{fy}: no records yet")
        continue
    proj["SUBPROJECT_ID"] = proj.SUBPROJECT_ID.fillna("")
    proj["_hash"] = api.row_hash(proj)
    proj["IN_API"], proj["NOT_IN_API_SINCE"] = "Y", None
    old_path = PROJ_DIR / f"FY{fy}.parquet"
    kept = proj.iloc[0:0]
    if old_path.exists():
        old = pd.read_parquet(old_path)
        old["SUBPROJECT_ID"] = old.SUBPROJECT_ID.fillna("")
        for c in FLAG_COLS:
            if c not in old.columns:
                old[c] = "Y" if c == "IN_API" else None
        old["_hash"] = api.row_hash(old.drop(columns=[c for c in ["_hash", *FLAG_COLS] if c in old.columns]))
        m = proj[KEY + ["_hash"]].merge(old[KEY + ["_hash", "IN_API"]], on=KEY, how="outer", suffixes=("", "_old"),
                                        indicator=True)
        new = m[m._merge == "left_only"]
        changed = m[(m._merge == "both") & (m._hash != m._hash_old)]
        removed = m[(m._merge == "right_only") & (m.IN_API == "Y")]  # newly missing from the API
        # Keep every record the API no longer returns, marked, with the date it was first missing
        kept = old.merge(m.loc[m._merge == "right_only", KEY], on=KEY)
        kept["NOT_IN_API_SINCE"] = kept.NOT_IN_API_SINCE.where(kept.IN_API == "N", TODAY)
        kept["IN_API"] = "N"
    else:
        new, changed, removed = proj[KEY], proj[KEY].iloc[0:0], proj[KEY].iloc[0:0]
    # Records in the comparison copy (ExPORTER) that the API never returned: kept and marked too
    other = Path(COMPARE_DIR) / f"FY{fy}.parquet" if COMPARE_DIR else None
    if other is not None and other.exists():
        o = pd.read_parquet(other)
        o["SUBPROJECT_ID"] = o.SUBPROJECT_ID.fillna("")
        seen = pd.concat([proj[KEY], kept[KEY]])
        o = o.merge(seen.assign(_s=1), on=KEY, how="left")
        o = o[o._s.isna()].drop(columns="_s")
        o["IN_API"], o["NOT_IN_API_SINCE"] = "N", TODAY
        kept = pd.concat([kept, o], ignore_index=True)
        if len(o):
            print(f"FY{fy}: {len(o):,} records in {other.parent.name} but not in the API, kept and marked")
    changes += [new[KEY].assign(fy=fy, change="new"), changed[KEY].assign(fy=fy, change="changed"),
                removed[KEY].assign(fy=fy, change="no longer in API")]
    out = pd.concat([proj, kept], ignore_index=True).drop(columns="_hash", errors="ignore")
    out.astype({c: "string" for c in out.columns}).to_parquet(old_path, index=False)
    if len(abst):  # a saved pull without abstracts leaves the abstracts file as it is
        abst.to_parquet(ABS_DIR / f"FY{fy}.parquet", index=False)
    rows.append({"table": "projects", "fy": fy, "pulled_at": TODAY, "records": len(proj), "new": len(new),
                 "changed": len(changed), "removed": len(removed), "not_in_api": len(kept),
                 "preliminary": fy == PRELIMINARY_FY, "reason": why})
    print(f"FY{fy}: {len(proj):,} records in the API; {len(new):,} new, {len(changed):,} changed, "
          f"{len(removed):,} no longer in the API; {len(kept):,} kept and marked IN_API = N")

# %% [markdown]
# ## Publication links

# %%
PULL_LINKS = SETTINGS["update"].get("pull_links", True)
link_file = LINK_DIR / "links.parquet"
links = pd.read_parquet(link_file) if link_file.exists() else pd.DataFrame(columns=["PMID", "PROJECT_NUMBER"])
recent = [fy for fy in PULL_YEARS if fy > PULL_YEARS[-1] - LINK_YEARS]
cores = set()
for fy in recent:
    f = PROJ_DIR / f"FY{fy}.parquet"
    if f.exists():
        cores |= set(pd.read_parquet(f, columns=["CORE_PROJECT_NUM"]).CORE_PROJECT_NUM.dropna())
for fy in PULL_YEARS:  # projects never linked before (first run: all of them)
    f = PROJ_DIR / f"FY{fy}.parquet"
    if f.exists() and fy not in recent:
        c = set(pd.read_parquet(f, columns=["CORE_PROJECT_NUM"]).CORE_PROJECT_NUM.dropna())
        cores |= c - set(links.PROJECT_NUMBER)
cores = sorted(cores) if PULL_LINKS else []
if PULL_LINKS:  # first run: every core project, about an hour; later runs: recent and new projects only
    print(f"Publication links: refreshing {len(cores):,} core projects")
    fresh = api.pull_pub_links(cores)
    links = pd.concat([links[~links.PROJECT_NUMBER.isin(cores)], fresh], ignore_index=True).drop_duplicates()
    links.to_parquet(link_file, index=False)
    rows.append({"table": "pub_links", "fy": None, "pulled_at": TODAY, "records": len(links), "new": None,
                 "changed": None, "removed": None, "preliminary": None, "reason": f"{len(cores):,} core projects refreshed"})
    print(f"Publication links: {len(links):,} in all")
else:
    print("Publication links: skipped (update.pull_links is false)")

# %% [markdown]
# ## Manifest and change log

# %%
if rows:
    upd = pd.DataFrame(rows)
    keep = manifest[~manifest.set_index(["table", "fy"]).index.isin(upd.set_index(["table", "fy"]).index)]
    manifest = pd.concat([keep, upd], ignore_index=True).sort_values(["table", "fy"])
    manifest.to_csv(MANIFEST, index=False)
if changes:
    log = pd.concat(changes)
    log.to_csv(PROJ_DIR.parent / f"changes_{TODAY}.csv", index=False)
    print(log.groupby(["fy", "change"]).size().unstack(fill_value=0))
manifest
