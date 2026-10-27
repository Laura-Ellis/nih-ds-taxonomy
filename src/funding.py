"""Split funding by the institutes and centers (ICs) that paid for it.

RePORTER lists two kinds of IC for every award:
- Administering IC: the one IC that manages the award (its code is in the project number, e.g. R01AI...).
- Funding ICs: every IC that put money into the award that fiscal year, with its amount
  (`agency_ic_fundings`, saved as FUNDING_ICS = "NCI:507918.0\\NIAID:20000.0\\").

`by_funding_ic` gives each application one row per funding IC, with its share of the award:
    funding share = that IC's amount / the sum of all funding ICs' amounts on the application
    funded cost   = attributed cost × funding share
Applications with no funding ICs listed keep their administering IC (share 1).
"""

import re

import pandas as pd

# Administering IC code (2 letters) → abbreviation used in FUNDING_ICS and in reports
IC_NAMES = {"CA": "NCI", "HL": "NHLBI", "AI": "NIAID", "GM": "NIGMS", "AG": "NIA", "NS": "NINDS", "MH": "NIMH",
            "DK": "NIDDK", "HD": "NICHD", "DA": "NIDA", "AA": "NIAAA", "ES": "NIEHS", "EY": "NEI", "DC": "NIDCD",
            "DE": "NIDCR", "AR": "NIAMS", "EB": "NIBIB", "HG": "NHGRI", "LM": "NLM", "MD": "NIMHD", "NR": "NINR",
            "AT": "NCCIH", "TR": "NCATS", "TW": "FIC", "OD": "OD", "RR": "NCRR", "CL": "CC", "RM": "OD"}
PAIR = re.compile(r"([A-Za-z&]+):\s*(-?[\d.]+)")


def parse(text) -> list[tuple[str, float]]:
    """'NCI:100.0\\OD:50.0\\' → [('NCI', 100.0), ('OD', 50.0)]; one IC listed twice is summed."""
    if not isinstance(text, str):
        return []
    out: dict[str, float] = {}
    for ic, amount in PAIR.findall(text):
        out[ic.upper()] = out.get(ic.upper(), 0.0) + float(amount)
    return list(out.items())


def by_funding_ic(apps: pd.DataFrame, cost: str = "attributed_cost") -> pd.DataFrame:
    """One row per application × funding IC: `admin_ic`, `funding_ic`, `funding_share`, `funded_cost`.

    Needs columns administering_ic, funding_ics, and `cost`. Keeps every other column of `apps`.
    """
    admin = apps.administering_ic.map(IC_NAMES).fillna(apps.administering_ic)
    rows = []
    for i, text, adm in zip(apps.index, apps.funding_ics, admin):
        pairs = [(ic, a) for ic, a in parse(text) if a > 0]
        total = sum(a for _, a in pairs)
        if not pairs or total <= 0:
            rows.append((i, adm, 1.0))
        else:
            rows.extend((i, ic, a / total) for ic, a in pairs)
    split = pd.DataFrame(rows, columns=["_i", "funding_ic", "funding_share"]).set_index("_i")
    out = apps.join(split, how="inner")
    out["admin_ic"] = admin.reindex(out.index)
    out["funded_cost"] = pd.to_numeric(out[cost], errors="coerce").fillna(0) * out.funding_share
    out["same_ic"] = out.funding_ic == out.admin_ic
    return out.reset_index(drop=True)
