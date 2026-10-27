"""Offline tests for the RePORTER API mapping and change detection (no network)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import reporter_api as api  # noqa: E402

PARENT = {"appl_id": 10715000, "subproject_id": None, "fiscal_year": 2025, "core_project_num": "U54AG062334",
          "project_num": "2U54AG062334-06", "activity_code": "U54",
          "project_num_split": {"appl_type_code": "2", "serial_num": "062334", "support_year": "06"},
          "agency_ic_admin": {"code": "AG", "abbreviation": "NIA", "name": "National Institute on Aging"},
          "principal_investigators": [{"profile_id": 7724587, "is_contact_pi": True, "full_name": "A B"}],
          "award_amount": 1500000, "abstract_text": "Parent abstract", "project_title": "Center",
          "spending_categories_desc": "Aging;Neurosciences", "project_start_date": "2018-09-30T00:00:00Z"}
SUB = {**PARENT, "appl_id": 10715270, "subproject_id": "6239", "award_amount": 282829,
       "abstract_text": "Core abstract", "project_title": "Data core"}


def test_mapping_matches_exporter_layout():
    proj, abst = api.to_tables([PARENT, SUB])
    p = proj.set_index("APPLICATION_ID")
    assert p.loc["10715000", "TOTAL_COST"] == "1500000" and pd.isna(p.loc["10715000", "TOTAL_COST_SUB_PROJECT"])
    assert pd.isna(p.loc["10715270", "TOTAL_COST"]) and p.loc["10715270", "TOTAL_COST_SUB_PROJECT"] == "282829"
    assert p.loc["10715270", "SERIAL_NUMBER"] == "62334" and p.loc["10715270", "SUPPORT_YEAR"] == "6"
    assert p.loc["10715270", "ADMINISTERING_IC"] == "AG" and p.loc["10715270", "PI_IDS"] == "7724587 (contact)"
    assert p.loc["10715270", "PROJECT_START"] == "2018-09-30"
    assert set(abst.ABSTRACT_TEXT) == {"Parent abstract", "Core abstract"}


def test_row_hash_detects_changes_only():
    a, _ = api.to_tables([PARENT, SUB])
    b, _ = api.to_tables([PARENT, {**SUB, "award_amount": 300000}])
    ha, hb = api.row_hash(a), api.row_hash(b)
    assert ha.iloc[0] == hb.iloc[0] and ha.iloc[1] != hb.iloc[1]


def test_empty_pull():
    proj, abst = api.to_tables([])
    assert proj.empty and list(abst.columns) == ["APPLICATION_ID", "ABSTRACT_TEXT", "FY", "SOURCE_FILE"]
    assert isinstance(proj, pd.DataFrame)
