# %% [markdown]
# # RCDC AI tag vs. the taxonomy's AI label, FY2019–FY2025
#
# RCDC's "Machine Learning and Artificial Intelligence" category starts in FY2019. A record counts as RCDC AI
# if any of its applications carries the tag. Taxonomy AI = ai_label Y (substantive AI).
# Output: reports/methods/rcdc_ai_compare.csv (rcdc, taxonomy, both, tax_only, rcdc_only)

# %%
import glob
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
TAG = "Machine Learning and Artificial Intelligence"

lab = pd.read_parquet(ROOT / "data" / "processed" / "exporter_core_projects_labeled.parquet",
                      columns=["core_project_number", "subproject_id", "ai_label", "first_fy", "last_fy"])
lab["subproject_id"] = lab.subproject_id.fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
lab = lab[(lab.last_fy >= 2019) & (lab.first_fy <= 2025)]

tagged = []
for f in sorted(glob.glob(str(ROOT / "data" / "raw" / "reporter_api" / "projects" / "FY20*.parquet"))):
    d = pd.read_parquet(f, columns=["CORE_PROJECT_NUM", "SUBPROJECT_ID", "NIH_SPENDING_CATS"])
    tagged.append(d[d.NIH_SPENDING_CATS.fillna("").str.contains(TAG, regex=False)])
r = pd.concat(tagged)
r["SUBPROJECT_ID"] = r.SUBPROJECT_ID.fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
keys = set(zip(r.CORE_PROJECT_NUM, r.SUBPROJECT_ID))

rc = pd.Series([k in keys for k in zip(lab.core_project_number, lab.subproject_id)], index=lab.index)
tx = lab.ai_label.eq("Y")
out = pd.DataFrame([{"years": "FY2019-FY2025", "rcdc": int(rc.sum()), "taxonomy": int(tx.sum()), "both": int((rc & tx).sum()),
                     "tax_only": int((tx & ~rc).sum()), "rcdc_only": int((rc & ~tx).sum())}])
(ROOT / "reports" / "methods").mkdir(parents=True, exist_ok=True)
out.to_csv(ROOT / "reports" / "methods" / "rcdc_ai_compare.csv", index=False)
print(out.to_string(index=False))
