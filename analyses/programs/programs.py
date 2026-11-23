# %% [markdown]
# # E. NIH data science programs: what they fund and how their projects compare
#
# Analysis E, sections 1 to 4 (second pass: 18 programs). Programs are found by the NOFOs they were funded under, kept per application in
# `exporter_applications.parquet`. A record (core project number + subproject id) belongs to a program when any of
# its applications used one of the program's NOFOs, so administrative supplements on the same record count too.
#
# **Programs and NOFOs** (PROGRAMS below; checked against the Common Fund, ODSS, DPCPSI, and NIH Guide pages, November 22, 2026)
# - 18 programs whose stated purpose is data science or AI: 11 NIH-wide (OD offices, the Common Fund, trans-NIH NOFOs)
#   and 7 institute flagship programs. Candidates came from a scan of every NOFO with 3+ records, a data science share of
#   60%+, and a title naming data science, AI, informatics, computational methods, or data resources.
# - Left out: STRIDES (OTA-24-200, cloud purchasing, not research); HuBMAP's HIVE (OTA-21-012) and other atlas or
#   consortium data centers (data-heavy, but the program's purpose is biology); ODSS AI-readiness and other
#   administrative supplements (they come through parent supplement NOFOs, so a NOFO lookup can't find them).
# - AIM-AHEAD consortium awards are made through the coordinating center, so RePORTER shows one award.
#
# **Measures**
# - Funding = attributed cost (center costs counted once), FY2016–FY2026; FY2026 preliminary.
# - Data science (DS) and AI = substantive (Y) labels from the taxonomy pipeline.
# - Taxonomy groups from the model categories (a record can be in more than one group).
# - Comparison: program records vs. DS records outside any program with the same activity code and first fiscal year
#   within ±1 year (exact match on activity code; all eligible comparison records, weighted equally per program
#   record). Papers = ExPORTER publication links; RCR = iCite Relative Citation Ratio (median per record, papers
#   published FY2016–FY2023). Small groups (n < 30) are reported but not tested.
#
# Outputs in `reports/results/programs/`.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from taxonomy import load_categories  # noqa: E402  # pyright: ignore[reportMissingImports]

PROCESSED = ROOT / "data" / "processed"
RAW_NIH = Path(r"C:\data\nih") if Path(r"C:\data\nih").exists() else Path.home() / "mnt" / "data" / "nih"
OUT = ROOT / "reports" / "results" / "programs"
OUT.mkdir(parents=True, exist_ok=True)

# NIH-wide = OD offices, the Common Fund, and trans-NIH NOFOs; institute = one institute's flagship data science program.
PROGRAMS = {
    # ---- NIH-wide
    "BD2K": {"RFA-HG-13-009": "Centers of Excellence for Big Data Computing (U54)", "RFA-HG-14-001": "BD2K-LINCS data coordination center (U54)",
             "RFA-HG-14-020": "Software and analysis methods (U01)", "RFA-CA-15-017": "Software tools and methods (U01)",
             "RFA-CA-15-006": "Crowdsourcing and interactive digital media (U01)", "RFA-ES-16-010": "Data and metadata standards (R24)",
             "RFA-LM-17-001": "Digital curation (R01)", "RFA-HG-14-004": "Predoctoral training (T32)",
             "RFA-HG-14-007": "Mentored career development (K01)", "RFA-ES-16-002": "Mentored career development (K01)",
             "RFA-HG-14-008": "Skills courses (R25)", "RFA-HG-14-009": "Open educational resources (R25)",
             "RFA-MD-15-005": "Enhancing diversity in data science (R25)", "RFA-MD-16-002": "Enhancing diversity in data science (R25)"},
    "NIH Data Commons pilot": {"RFA-RM-17-026": "Data Commons pilot phase (OT3)"},
    "CFDE": {"OTA-20-005": "Data coordinating center engagement (OT2)", "RFA-RM-23-002": "Integration and coordination center (U54)",
             "RFA-RM-23-013": "Partnerships with CFDE resources (U24)", "OTA-23-004": "Data resource and knowledge centers (OT2)",
             "OTA-24-004": "Training center (OT2)", "OTA-24-005": "Cloud workspace (OT2)",
             "RFA-RM-19-012": "Pilot projects using Common Fund data (R03)", "RFA-RM-21-007": "Pilot projects using Common Fund data (R03)",
             "RFA-RM-22-007": "Pilot projects using Common Fund data (R03)", "RFA-RM-23-015": "Pilot projects using Common Fund data (R03)",
             "RFA-RM-24-006": "Pilot projects using Common Fund data (R03)"},
    "DS-I Africa": {"RFA-RM-20-015": "Research hubs (U54)", "RFA-RM-20-016": "Research training (U2R)",
                    "RFA-RM-20-017": "ELSI research (U01)", "RFA-RM-20-018": "Data science platform and coordinating center (U2C)",
                    "RFA-RM-22-022": "Research education (UE5)", "RFA-RM-22-023": "Partnership for innovation research (U01)"},
    "AIM-AHEAD": {"OTA-21-017": "Coordinating center (OT2)"},
    "Bridge2AI": {"OTA-21-008": "Data generation projects (OT2)", "RFA-RM-21-023": "BRIDGE center (U54)"},
    "Repositories and knowledgebases": {"PAR-20-089": "Biomedical data repository (U24)", "PAR-23-079": "Biomedical data repository (U24)",
                                        "PAR-20-097": "Biomedical knowledgebase (U24)", "PAR-23-236": "Early-stage repositories and knowledgebases (R24)",
                                        "PAR-23-237": "Established repositories and knowledgebases (U24)"},
    "Multimodal AI": {"OTA-24-015": "Advancing Health Research through Ethical, Multimodal AI (OT2)"},
    "ODSS software and RSE": {"RFA-OD-24-010": "Sustainable software tools for open science (R03)",
                              "RFA-OD-24-011": "Research software engineer award (R50)"},
    "Autism Data Science Initiative": {"OTA-25-006": "Autism Data Science Initiative (OT2)"},
    "Hormone Homeostasis modeling": {"OTA-26-004": "Computational Modeling of Hormone Homeostasis (OT2)"},
    # ---- institute programs
    "NCI ITCR": {n: d for d, ns in {
        "Advanced development (U24)": ["PAR-12-287", "PAR-13-294", "PAR-15-331", "RFA-CA-19-040", "RFA-CA-20-009", "RFA-CA-21-015", "RFA-CA-22-023", "RFA-CA-23-016"],
        "Early-stage development (U01)": ["PAR-12-288", "PAR-15-332", "RFA-CA-19-039", "RFA-CA-20-008", "RFA-CA-21-014", "RFA-CA-22-022", "RFA-CA-23-015"],
        "Sustained support (U24)": ["PAR-15-333", "RFA-CA-20-010", "RFA-CA-22-024", "RFA-CA-23-017"],
        "Innovative methods and algorithms (R21)": ["PAR-15-334", "RFA-CA-20-007", "RFA-CA-21-013", "RFA-CA-22-021"]}.items() for n in ns},
    "NLM informatics and data science": {n: d for d, ns in {
        "Research grants (R01)": ["PAR-13-300", "PAR-16-404", "PAR-18-896", "PAR-23-034", "PAR-25-238", "PAR-17-159", "PAR-19-072", "PAR-18-796", "PAR-20-304"],
        "Career development (K01)": ["PAR-13-284", "PAR-16-204"],
        "Institutional training (T15)": ["RFA-LM-11-001", "RFA-LM-16-001", "RFA-LM-21-001"]}.items() for n in ns},
    "NHGRI computational genomics": {"PAR-18-844": "Computational genomics and data science (R01)", "PAR-21-254": "Computational genomics and data science (R01)",
                                     "RFA-HG-23-002": "Computational genomics and data science education (UE5)"},
    "NIMH computational psychiatry": {"RFA-MH-19-242": "Computational approaches for dimensional constructs (R01)",
                                      "PAR-21-263": "Computational approaches for dimensional constructs (R01)",
                                      "RFA-MH-23-105": "IMPACT-MH (U01)"},
    "NIA AITC": {"RFA-AG-21-009": "AI and Technology Collaboratories (P30)", "RFA-AG-26-006": "AI and Technology Collaboratory (P30)"},
    "NIAID data science": {"PA-15-273": "Harnessing Big Data to Halt HIV (R01)", "PAR-18-764": "Harnessing Big Data to Halt HIV (R01)",
                           "RFA-AI-19-011": "Computational Models of Immunity (U01)", "RFA-AI-23-056": "Computational Models of Influenza Immunity (U01)",
                           "RFA-AI-21-020": "Early-stage data science technologies (U01)", "RFA-AI-23-032": "Bioinformatics Resource Centers (U24)"},
    "NCATS Translator": {"OTA-19-009": "Biomedical Data Translator (OT2)"},
}
INSTITUTE = {"NCI ITCR", "NLM informatics and data science", "NHGRI computational genomics", "NIMH computational psychiatry",
             "NIA AITC", "NIAID data science", "NCATS Translator"}
GROUP = {p: "Institute" if p in INSTITUTE else "NIH-wide" for p in PROGRAMS}
NOFO_PROGRAM = {n: p for p, ns in PROGRAMS.items() for n in ns}
assert len(NOFO_PROGRAM) == sum(len(v) for v in PROGRAMS.values()), "a NOFO is listed under two programs"
GROUPS = {"statistics_analytics": "Statistics and analytics", "computational_modeling": "Computational modeling",
          "artificial_intelligence": "Artificial intelligence", "software_tools": "Software and tools",
          "data_infrastructure": "Data infrastructure", "responsible_ai": "Responsible AI", "workforce": "Workforce"}

# %% [markdown]
# ## 1. Program lookup

# %%
key = ["core_project_number", "subproject_id"]
a = pd.read_parquet(PROCESSED / "exporter_applications.parquet",
                    columns=key + ["fy", "nofo", "activity", "administering_ic", "org_name", "org_country", "attributed_cost",
                                   "pi_ids", "project_title"])
core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet",
                       columns=key + ["first_fy", "ds_label", "ai_label", "ai_role", "model_categories"])
a["fy"] = pd.to_numeric(a.fy, errors="coerce")
a = a[a.fy.between(2016, 2026)]
a["subproject_id"] = a.subproject_id.fillna("")
core["subproject_id"] = core.subproject_id.fillna("")
a["record"] = a.core_project_number + "|" + a.subproject_id
a["program"] = a.nofo.map(NOFO_PROGRAM)
rec_prog = a.dropna(subset=["program"]).groupby("record").program.first()
a["program"] = a.record.map(rec_prog)
lookup = pd.DataFrame([(GROUP[p], p, n, d) for p, ns in PROGRAMS.items() for n, d in ns.items()], columns=["group", "program", "nofo", "component"])
n_by = a[a.nofo.isin(NOFO_PROGRAM)].groupby("nofo").agg(records=("record", "nunique"), cost=("attributed_cost", "sum"))
lookup = lookup.merge(n_by, left_on="nofo", right_index=True, how="left").fillna({"records": 0, "cost": 0})
lookup.to_csv(OUT / "program_nofos.csv", index=False)
print(lookup.to_string(index=False))

# %% [markdown]
# ## 2. Program profiles

# %%
cats = load_categories()
cats = cats[cats.dimension.isin(["methods", "software_tools", "data_infrastructure", "data_sharing", "responsible_ai", "workforce"])]
grp_of = {r.category_id: ("data_infrastructure" if r.dimension in ("data_infrastructure", "data_sharing")
                          else r.group if r.dimension == "methods" else r.dimension) for r in cats.itertuples()}
core["groups"] = core.model_categories.fillna("").str.split("; ").map(lambda cs: {grp_of[c] for c in cs if c in grp_of})

recs = (a.sort_values("fy").groupby("record")
        .agg(core_project_number=("core_project_number", "first"), subproject_id=("subproject_id", "first"),
             program=("program", "first"), activity=("activity", "last"), ic=("administering_ic", "last"),
             org=("org_name", "last"), country=("org_country", "last"), first_fy=("fy", "min"),
             cost=("attributed_cost", "sum"), title=("project_title", "last"))
        .reset_index().merge(core.drop(columns="first_fy"), on=key, how="left"))
recs["ds"], recs["ai"] = recs.ds_label.eq("Y"), recs.ai_label.eq("Y")
recs["country"] = recs.country.fillna("UNITED STATES")
pr = recs[recs.program.notna()]

prof = pr.groupby("program").agg(records=("record", "size"), cost=("cost", "sum"), ds=("ds", "mean"), ai=("ai", "mean"),
                                 orgs=("org", "nunique"), countries=("country", "nunique"),
                                 first_fy=("first_fy", "min")).reset_index()
prof.insert(1, "group", prof.program.map(GROUP))
for g, lab in GROUPS.items():
    prof[lab] = prof.program.map(pr.groupby("program")["groups"].apply(lambda s: s.map(lambda x: g in x).mean()))
prof.to_csv(OUT / "program_profiles.csv", index=False)
print(prof.round(2).to_string(index=False))

by_fy = a[a.program.notna()].groupby(["program", "fy"]).agg(records=("record", "nunique"), cost=("attributed_cost", "sum")).reset_index()
by_fy.to_csv(OUT / "program_by_fy.csv", index=False)
pr.groupby(["program", "country"]).agg(records=("record", "size"), cost=("cost", "sum")).reset_index().sort_values(
    ["program", "cost"], ascending=[True, False]).to_csv(OUT / "program_countries.csv", index=False)
pr.groupby(["program", "org", "country"]).agg(records=("record", "size"), cost=("cost", "sum")).reset_index().sort_values(
    ["program", "cost"], ascending=[True, False]).to_csv(OUT / "program_orgs.csv", index=False)
pr.groupby(["program", "ai_role"]).size().rename("records").reset_index().to_csv(OUT / "program_ai_role.csv", index=False)
pr[["program", "record", "activity", "ic", "org", "country", "first_fy", "cost", "ds", "ai", "title"]].to_csv(
    OUT / "program_records.csv", index=False)

# %% [markdown]
# ## 3–4. Papers and citation impact vs. similar data science records

# %%
pub = pd.concat([pd.read_parquet(f) for f in sorted((RAW_NIH / "combined" / "pub_links").glob("FY*.parquet"))])
pub = pub.rename(columns={"PROJECT_NUMBER": "core_project_number", "PMID": "pmid"}).drop_duplicates()
pub["pmid"] = pd.to_numeric(pub.pmid, errors="coerce")
ic_ = pd.read_parquet(ROOT / "data" / "interim" / "icite.parquet").dropna(subset=["rcr"])
pub = pub.merge(ic_, on="pmid", how="left")
papers = pub.groupby("core_project_number").agg(papers=("pmid", "nunique"),
                                                 rcr=("rcr", lambda s: s[pub.loc[s.index, "year"].between(2016, 2023)].median()))
# papers are linked to the core project, so compare at the core level: parent records only
parents = recs[recs.subproject_id.eq("")].merge(papers, on="core_project_number", how="left").fillna({"papers": 0})
parents["years"] = (2026 - parents.first_fy).clip(lower=1)
parents["papers_per_year"] = parents.papers / parents.years

prog_p = parents[parents.program.notna()]
pool = parents[parents.program.isna() & parents.ds]
rows = []
for r in prog_p.itertuples():
    m = pool[pool.activity.eq(r.activity) & pool.first_fy.between(r.first_fy - 1, r.first_fy + 1)]
    rows.append({"program": r.program, "record": r.record, "activity": r.activity, "matches": len(m),
                 "papers_per_year": r.papers_per_year, "rcr": r.rcr,
                 "m_papers_per_year": m.papers_per_year.mean() if len(m) else np.nan,
                 "m_rcr": m.rcr.median() if len(m) else np.nan})
cmp_ = pd.DataFrame(rows)
cmp_.to_csv(OUT / "program_vs_matched_records.csv", index=False)
summ = cmp_.groupby("program").agg(parents=("record", "size"), matched=("matches", lambda s: (s > 0).sum()),
                                   papers_per_year=("papers_per_year", "mean"), matched_papers_per_year=("m_papers_per_year", "mean"),
                                   median_rcr=("rcr", "median"), matched_median_rcr=("m_rcr", "median")).reset_index()
summ.to_csv(OUT / "program_vs_matched.csv", index=False)
print(summ.round(2).to_string(index=False))

# %% [markdown]
# ## 5. Context: programs' share of all NIH data science funding

# %%
fy_rec = a.groupby(["record", "fy"]).attributed_cost.sum().rename("cost").reset_index().merge(
    recs[["record", "ds", "program"]], on="record", how="left")
ctx = fy_rec[fy_rec.ds].groupby("fy").agg(ds_cost=("cost", "sum")).join(
    fy_rec[fy_rec.ds & fy_rec.program.notna()].groupby("fy").agg(program_ds_cost=("cost", "sum"))).fillna(0)
ctx["share"] = ctx.program_ds_cost / ctx.ds_cost
ctx.loc["all"] = [ctx.ds_cost.sum(), ctx.program_ds_cost.sum(), ctx.program_ds_cost.sum() / ctx.ds_cost.sum()]
ctx.to_csv(OUT / "program_context.csv")
print(ctx.round(3).to_string())
