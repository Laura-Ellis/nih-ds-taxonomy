"""PI groups for the PI analysis (analyses/ds_pis): data science PIs, AI developers, infrastructure builders.

Same rules as analyses/ds_pis/ds_pis.py, in one place so every PI script uses identical groups.

- Data science PI = substantive data science in more than half of the PI's records, at least 2 records
- AI developer PI = develops AI in more than half of the PI's records
- Infrastructure builder PI = more than half of the PI's records are substantive data science with an
  infrastructure category (research software, analysis platforms, data platforms, data engineering, FAIR
  data, data management and sharing, human-derived data linkage)
- Group (one per PI, for comparisons): AI developer, then infrastructure builder, then other data science
  PI, then other PI (at least 2 records); PIs with 1 record have no group
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

INFRA = ["research_software", "analysis_platforms", "data_platforms", "data_engineering", "fair_data",
         "data_management_sharing", "human_data_linkage"]
GROUPS = ["AI developer PIs", "Infrastructure builder PIs", "Other data science PIs", "Other PIs"]


def explode_pis(df: pd.DataFrame) -> pd.DataFrame:
    """One row per PI per input row; `pi` = RePORTER profile ID without the '(contact)' tag."""
    out = df.assign(pi=df.pi_ids.fillna("").str.split(";")).explode("pi")
    out["pi"] = out.pi.str.replace("(contact)", "", regex=False).str.strip()
    return out[out.pi.str.fullmatch(r"\d+")]


def load_tiers(processed: Path) -> pd.DataFrame:
    """PI profiles (notebook 15) plus infra_records, the tier flags, and `group`, indexed by PI."""
    pi = pd.read_parquet(processed / "pi_profiles.parquet").set_index("pi")
    key = ["core_project_number", "subproject_id"]
    core = pd.read_parquet(processed / "exporter_core_projects_labeled.parquet",
                           columns=key + ["ds_label", "model_categories"])
    core["record"] = core.core_project_number + "|" + core.subproject_id.fillna("")
    core["infra"] = core.ds_label.eq("Y") & core.model_categories.fillna("").str.split("; ").map(
        lambda cats: any(c in cats for c in INFRA))
    rec = pd.read_parquet(processed / "exporter_applications.parquet", columns=key + ["pi_ids"])
    rec["record"] = rec.core_project_number + "|" + rec.subproject_id.fillna("")
    rp = explode_pis(rec)
    rp = rp[rp.pi.isin(pi.index)][["pi", "record"]].drop_duplicates().merge(core[["record", "infra"]], on="record",
                                                                            how="left")
    pi["infra_records"] = rp.groupby("pi").infra.sum()
    pi = pi.fillna({"infra_records": 0})
    two = pi.records >= 2
    pi["ds_pi"] = two & (pi.ds_share > 0.5)
    pi["ai_developer"] = two & (pi.develops_records / pi.records > 0.5)
    pi["infra_builder"] = two & (pi.infra_records / pi.records > 0.5)
    pi["group"] = np.select([pi.ai_developer, pi.infra_builder, pi.ds_pi, two], GROUPS, None)
    return pi
