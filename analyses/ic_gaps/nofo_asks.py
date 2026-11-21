# %% [markdown]
# # NOFO asks: which NOFOs ask for data science, which groups, issuer, and when they were open
#
# Input for `nofo_panel.py`. Taxonomy keyword rules on each NOFO's Section I (same as `analyses/topics/nofo_match.py`);
# open and expiration dates parsed from the full NIH Guide text. When a date is missing, the NOFO is treated as open
# from its issue year (from the number, e.g. RFA-HL-20-015 = 2020) for 1 year (RFA) or 3 years (PA, PAR).
# Participating ICs come from "Components of Participating Organizations".
# Output: `reports/internal/ic_gaps/nofo_asks.csv`.

# %%
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]

NOFO = ROOT / "data" / "raw" / "nofo"
OUT = ROOT / "reports" / "internal" / "ic_gaps"
OUT.mkdir(parents=True, exist_ok=True)
GROUP = {"statistical_methods": "Statistics and analytics", "data_science_general": "Statistics and analytics",
         "data_exploration": "Statistics and analytics", "data_visualization": "Statistics and analytics",
         "network_analysis": "Statistics and analytics", "computational_modeling": "Computational modeling",
         "machine_learning": "Artificial intelligence", "deep_learning": "Artificial intelligence", "nlp": "Artificial intelligence",
         "computer_vision": "Artificial intelligence", "generative_ai": "Artificial intelligence", "other_ai": "Artificial intelligence",
         "research_software": "Software and tools", "ml_frameworks": "Software and tools", "analysis_platforms": "Software and tools",
         "visualization_tools": "Software and tools", "cloud_computing": "Data infrastructure", "hpc_compute": "Data infrastructure",
         "data_platforms": "Data infrastructure", "data_engineering": "Data infrastructure", "fair_data": "Data infrastructure",
         "data_management_sharing": "Data infrastructure", "human_data_linkage": "Data infrastructure",
         "fairness_bias": "Responsible AI", "privacy_security": "Responsible AI", "transparency_reproducibility": "Responsible AI",
         "training_education": "Workforce", "community_capacity": "Workforce"}


def fy_of(date):
    d = pd.to_datetime(date, errors="coerce")
    return None if pd.isna(d) else d.year + (d.month >= 10)


# Caches of what's parsed from the full NIH Guide text (reading ~3,000 files is slow): open and expiration dates,
# and the participating ICs (acronyms under "Components of Participating Organizations")
DATES, PICS = OUT / "nofo_dates.csv", OUT / "nofo_ics.csv"
if not (DATES.exists() and PICS.exists()):
    rows, ics = [], []
    for f in (NOFO / "text").glob("*.txt"):
        t = f.read_text(encoding="utf-8", errors="ignore")
        o = re.search(r"Open Date \(Earliest Submission Date\)\s+([A-Z][a-z]+ \d{1,2}, \d{4})", t)
        e = re.search(r"Expiration Date\s+([A-Z][a-z]+ \d{1,2}, \d{4})", t)
        rows.append((f.stem, o.group(1) if o else None, e.group(1) if e else None))
        m = re.search(r"Components\s+of\s+Participating\s+Organizations(.{0,5000}?)(Assistance\s+Listing|Catalog\s+of\s+Federal|"
                      r"Funding\s+Opportunity\s+Title|Announcement\s+Type|Title\s+of\s+Announcement)", t, re.S)
        ics.append((f.stem, ";".join(sorted(set(re.findall(r"\(([A-Z]{2,7})\)", m.group(1) if m else ""))))))
    pd.DataFrame(rows, columns=["nofo", "open_date", "expiration_date"]).to_csv(DATES, index=False)
    pd.DataFrame(ics, columns=["nofo", "participating_ics"]).to_csv(PICS, index=False)
dt = pd.read_csv(DATES).drop_duplicates("nofo").set_index("nofo")
pics = pd.read_csv(PICS).drop_duplicates("nofo").set_index("nofo").participating_ics.fillna("")


def dates(n):
    if n not in dt.index:
        return None, None
    return fy_of(dt.at[n, "open_date"]), fy_of(dt.at[n, "expiration_date"])


man = pd.read_csv(NOFO / "manifest.csv").drop_duplicates("nofo", keep="last")
n = man[man.status == 200][["nofo"]].copy()
n["text"] = [(NOFO / "section1" / f"{x}.txt").read_text(encoding="utf-8") if (NOFO / "section1" / f"{x}.txt").exists() else ""
             for x in n.nofo]
n = n[n.text.str.len() > 200].reset_index(drop=True)
lab = tx.label_projects(n.assign(project_title="", abstract_text=n.text))
n["asks_ds"] = lab.data_science_related.values
n["categories"] = ["; ".join(cs) for cs in lab.categories]
n["groups"] = [("; ".join(sorted({GROUP[c] for c in cs if c in GROUP}))) for cs in lab.categories]
m = n.nofo.str.extract(r"^(RFA|PAR|PA|NOT)-([A-Z]{2})?-?(\d{2})-")
n["kind"], n["issuer"] = m[0], m[1].fillna("NIH")
n["issue_fy"] = 2000 + pd.to_numeric(m[2], errors="coerce")
dd = n.nofo.map(dates)
n["open_fy"] = [d[0] for d in dd]
n["expire_fy"] = [d[1] for d in dd]
n["open_fy"] = n.open_fy.fillna(n.issue_fy)
n["expire_fy"] = n.expire_fy.fillna(n.open_fy + n.kind.eq("RFA").map({True: 0, False: 2}))
n["participating_ics"] = n.nofo.map(pics).fillna("")
n.drop(columns="text").to_csv(OUT / "nofo_asks.csv", index=False)
print(len(n), "NOFOs;", f"{n.asks_ds.mean():.0%} ask for data science;", f"dates parsed for {n.open_fy.notna().mean():.0%}")
print(n.kind.value_counts().to_string()); print(n.issuer.value_counts().head(12).to_string())
