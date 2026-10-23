# Data Sources

Data in this repo keeps each source's own terms; it is not covered by the code license.

| Source | Endpoint or file | Access date | Records | Terms |
|---|---|---|---|---|
| NIH RePORTER API v2 | https://api.reporter.nih.gov/v2/projects/search | [run date] | ~750 (sample) | Public U.S. government data |
| NIH Strategic Plan for Data Science, 2025–2030 | https://datascience.nih.gov/nih-strategic-plan-data-science | 2026-10-23 | n/a | Public |
| NIH AI Strategy RFI (NOT-OD-25-117) | https://grants.nih.gov/grants/guide/notice-files/NOT-OD-25-117.html | 2026-10-23 | n/a | Public |
| 2024 term lists | https://github.com/Laura-Ellis/NIH | 2026-10-23 | 415 terms | Author's own work |

## Folder rules

- `data/raw/`: untouched downloads; never edited by hand
- `data/processed/`: outputs of code in `src/` or `notebooks/`; reproducible from raw
- Large files stay out of git (see `.gitignore`); this file records how to rebuild them
