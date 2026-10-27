"""Load the 150-project validation set with the reviewed codes applied."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Reviewed codes replace the drafted codes for these projects (later files win)
OVERRIDES = [("taxonomy_spot_check_coded.xlsx", "Spot check", "human_"),
             ("taxonomy_recode_M_coded.xlsx", "Recode", "new_")]


def load_coded(reports: Path) -> pd.DataFrame:
    """Return appl_id, my_ds_related, my_ai_related, my_categories for the 150 coded projects."""
    reports = Path(reports)
    coded = pd.read_excel(reports / "taxonomy_review_coded.xlsx")
    for file, sheet, prefix in OVERRIDES:
        if not (reports / file).exists():
            continue
        o = pd.read_excel(reports / file, sheet_name=sheet).dropna(
            subset=[f"{prefix}ds_related", f"{prefix}ai_related"]).set_index("appl_id")
        idx = coded.appl_id.isin(o.index)
        for label in ["ds", "ai"]:
            coded.loc[idx, f"my_{label}_related"] = (
                coded.loc[idx, "appl_id"].map(o[f"{prefix}{label}_related"]).str.upper().str.strip())
    return coded[["appl_id", "my_ds_related", "my_ai_related", "my_categories"]]


def kappa(a, b) -> float:
    """Cohen's kappa for two label series of any type: (po - pe) / (1 - pe)."""
    a, b = pd.Series(a).reset_index(drop=True), pd.Series(b).reset_index(drop=True)
    po = (a == b).mean()
    pe = sum((a == v).mean() * (b == v).mean() for v in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0
