# Data Sources

Data in this repo keeps each source's own terms; it is not covered by the code license.

| Source | Endpoint or file | Access date | Records | Terms |
|---|---|---|---|---|
| NIH RePORTER API v2, projects and abstracts | https://api.reporter.nih.gov/v2/projects/search | see `data/raw/reporter_api/manifest.csv` | all NIH project records, FY2016–FY2027 (FY2026 preliminary; FY2027 pulled, not analyzed) | Public U.S. government data |
| NIH RePORTER API v2, publication links | https://api.reporter.nih.gov/v2/publications/search | see manifest | PMID–core project links | Public U.S. government data |
| NIH ExPORTER link tables (patents, clinical studies) | https://reporter.nih.gov/exporter | download date | all | Public U.S. government data |
| NIH Strategic Plan for Data Science, 2025–2030 | https://datascience.nih.gov/nih-strategic-plan-data-science | 2026-10-23 | n/a | Public |
| NIH AI Strategy RFI (NOT-OD-25-117) | https://grants.nih.gov/grants/guide/notice-files/NOT-OD-25-117.html | 2026-10-23 | n/a | Public |
| 2024 term lists | https://github.com/Laura-Ellis/NIH | 2026-10-23 | 415 terms | Author's own work |

## Folder rules

- `data/raw/`: untouched downloads; never edited by hand
- `data/processed/`: outputs of code in `src/` or `notebooks/`; reproducible from raw
- Large files stay out of git (see `.gitignore`); this file records how to rebuild them

## Building and updating the project data

The shared process uses only the RePORTER API, so anyone can rebuild the data the same way.

1. `python notebooks/00_update_reporter.py`
   - First run: pulls every fiscal year in `pull_years` (FY2016–FY2027), about 45 minutes,
     plus about an hour for publication links.
   - Later runs pull only what can change: the latest three fiscal years (NIH still revises them), older
     years only if RePORTER added records since the last pull, and publication links for recent and new
     projects. The run writes `data/raw/reporter_api/manifest.csv` (pull date, records, new, changed,
     removed per year) and `changes_<date>.csv` (which records changed).
2. Download ExPORTER's Patents and Clinical Studies tables into `data/raw/exporter_links/` (notebook 12).
3. Run notebooks 08, 09, 10, 11, 12, 13, and 16. Labels are cached by project text, so the model steps
   only pay for new or changed text.

**Preliminary year.** FY2026 closed on Sept 30, 2026, but NIH is still adding and revising its records
(`preliminary_fy` in settings.yaml). Every results table has a `preliminary` column, and charts label it
"FY2026 (preliminary, as of <pull date>)". Snapshot comparisons (for example AI share by institute) use
FY2025, the latest settled year. Set `preliminary_fy: null` once the records settle.

**FY2027** started Oct 1, 2026. It is pulled and kept current (`pull_years`) but not analyzed
(`fiscal_years` ends at FY2026).

**Records are never discarded.** A record the API stops returning stays in its year's file with
`IN_API = N` and `NOT_IN_API_SINCE`; analyses use only `IN_API = Y` records.

**Local overrides.** `config/local.yaml` (git-ignored) can point any table at other copies, such as
files built from ExPORTER bulk downloads. Notebook 08 falls back to the shared API folder for any
fiscal year the local folder doesn't have.
