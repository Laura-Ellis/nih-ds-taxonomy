"""API tests on a small fake dataset (no real data needed)."""

import importlib
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "reports" / "results").mkdir(parents=True)
    shutil.copytree(REPO / "src", tmp_path / "src")
    shutil.copytree(REPO / "taxonomy", tmp_path / "taxonomy")
    pd.DataFrame({
        "core_project_number": ["R01CA000001", "U54HG000002", "U54HG000002"],
        "subproject_id": ["", "", "7001"],
        "ds_label": ["Y", "Y", "Y"], "ai_label": ["Y", "N", "N"], "ai_role": ["applies_ai", "", ""],
        "groups": ["artificial_intelligence; statistics_analytics", "data_infrastructure", "software_tools"],
        "categories": ["machine_learning; statistical_methods", "cloud_computing", "research_software"],
        "project_title": ["Deep learning for tumors", "Genome data center", "Tools core"],
        "ic": ["CA", "HG", "HG"], "activity": ["R01", "U54", "U54"],
        "first_fy": [2020, 2023, 2023], "last_fy": [2024, 2025, 2025], "extramural_cost": [2e6, 5e6, 1e6],
    }).to_parquet(tmp_path / "data" / "processed" / "ds_projects.parquet", index=False)
    pd.DataFrame({"fy": [2025, 2025], "ds_group": ["data_infrastructure", "software_tools"],
                  "group_label": ["Data infrastructure and computing", "Software and tools"],
                  "projects": [1, 1], "share_of_ds_projects": [0.5, 0.5],
                  "extramural_cost": [5e6, 1e6], "share_of_ds_funding": [0.83, 0.17]}
                 ).to_csv(tmp_path / "reports" / "results" / "ds_groups_by_fy.csv", index=False)
    monkeypatch.setenv("DS_API_DATA", str(tmp_path))
    import api.main as m
    importlib.reload(m)
    return TestClient(m.app)


def test_groups(client):
    r = client.get("/groups").json()
    assert len(r) == 9  # 7 groups + 2 Data infrastructure subgroups
    ai = next(g for g in r if g["group"] == "artificial_intelligence")
    assert ai["projects"] == 1 and any(c["category"] == "machine_learning" for c in ai["categories"])


def test_filters(client):
    assert client.get("/projects", params={"ic": "hg"}).json()["total"] == 2
    assert client.get("/projects", params={"group": "artificial_intelligence", "fy": 2025}).json()["total"] == 0
    assert client.get("/projects", params={"ai_only": True}).json()["total"] == 1
    assert client.get("/projects", params={"group": "nope"}).status_code == 404


def test_summary_and_project(client):
    assert client.get("/groups/summary", params={"fy": 2025}).json()[0]["projects"] == 1
    assert len(client.get("/projects/U54HG000002").json()) == 2
    assert client.get("/groups/data_infrastructure/institutes").json()[0]["ic"] == "HG"
