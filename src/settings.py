"""Pipeline settings: config/settings.yaml (shared), overridden by config/local.yaml (personal, git-ignored)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load() -> dict:
    cfg = yaml.safe_load((CONFIG / "settings.yaml").read_text(encoding="utf-8"))
    local = CONFIG / "local.yaml"
    if local.exists():
        cfg = _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return cfg


SETTINGS = load()
FIRST_FY, LAST_FY = SETTINGS["fiscal_years"]
FISCAL_YEARS = range(FIRST_FY, LAST_FY + 1)          # analyzed
_pull = SETTINGS.get("pull_years", SETTINGS["fiscal_years"])
PULL_YEARS = range(_pull[0], _pull[1] + 1)             # pulled and kept current (may run past the analysis)
PRELIMINARY_FY: int | None = SETTINGS.get("preliminary_fy", SETTINGS.get("partial_fy"))
PARTIAL_FY = PRELIMINARY_FY  # older name, kept so existing code runs


ADMIN_PERIODS = SETTINGS.get("admin_periods", [])


def admin_period(fy: int) -> str | None:
    """Administration in office for most of the fiscal year (settings.yaml admin_periods)."""
    for p in ADMIN_PERIODS:
        if p["first_fy"] <= int(fy) <= p["last_fy"]:
            return p["name"]
    return None


def default_source(name: str) -> Path:
    """The shared (settings.yaml) folder for a table, ignoring config/local.yaml."""
    base = yaml.safe_load((CONFIG / "settings.yaml").read_text(encoding="utf-8"))
    p = Path(base["sources"][name])
    return p if p.is_absolute() else ROOT / p


def find_fy_file(name: str, fy: int) -> Path | None:
    """FY<year>.parquet from the configured folder, falling back to the shared API folder (for example
    FY2026 abstracts, which ExPORTER doesn't publish until the year closes)."""
    for folder in (source(name), default_source(name)):
        f = folder / f"FY{fy}.parquet"
        if f.exists():
            return f
    return None


def source(name: str) -> Path:
    """Folder for a table ('projects', 'abstracts', 'pub_links', 'link_tables'); relative paths from the repo root."""
    p = Path(SETTINGS["sources"][name])
    return p if p.is_absolute() else ROOT / p


def fy_label(fy: int, as_of: str | None = None) -> str:
    """'FY2025', or 'FY2026 (preliminary, as of 2026-10-24)' for the year whose records are still settling."""
    if PRELIMINARY_FY is not None and int(fy) == int(PRELIMINARY_FY):
        return f"FY{fy} (preliminary{', as of ' + as_of if as_of else ''})"
    return f"FY{fy}"


def as_of() -> str | None:
    """Date of the latest RePORTER API pull for the preliminary year, from the update manifest."""
    m = source("projects").parent / "manifest.csv"
    if not m.exists() or PARTIAL_FY is None:
        return None
    import pandas as pd
    d = pd.read_csv(m)
    d = d[(d.table == "projects") & (d.fy == PARTIAL_FY)]
    return str(d.pulled_at.max())[:10] if len(d) else None
