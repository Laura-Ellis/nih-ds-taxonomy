# Roadmap: future analyses

Ideas to build on the taxonomy. Each needs a scoping conversation before code.

## Biomedical research workforce

**Question:** How are applicant age, career stage, and other workforce traits changing, and how do they differ for data science and AI projects?

- Career stage from public data: first NIH award year per PI (`PI_IDS` across FY2008+ project records), award type (F, K, R00, first R01), and early-stage investigator flags where RePORTER reports them. RePORTER doesn't publish age, so career stage stands in for it.
- Trends: share of data science and AI projects led by early-career PIs, by fiscal year and IC; K-to-R transitions (KPI G5.2) for data science PIs vs. others.

## Who is doing data science: PI profiles

**Status:** first version in `notebooks/15_pi_profiles.py` (every PI on a project counts; data science PI = data science is at least 50% of their records, with 2+ records; aggregate tables for the site, counts under 11 suppressed).

**Question:** Which investigators lead data science and AI work across multiple projects, and what do they produce?

- Link: `PI_IDS` (RePORTER profile IDs; "(contact)" marks the contact PI) on every project record → the taxonomy's labels for each project.
- Measures per PI: data science and AI projects (counts, FY range), roles (develops vs. applies AI), groups and categories, ICs, organizations, linked publications (pub links → PMIDs), citation impact (iCite RCR), patents, and trials.
- Segments: PIs with 2+ data science projects, AI developers vs. appliers, multi-IC PIs, newly entering vs. long-standing.
- Notes: report results in aggregate on public pages; individual PI lists stay internal. Multi-PI projects count once per PI, and contact-PI-only views are an option.

## FY2025–FY2026 funding shifts (Trump second term)

Compare within and across administration periods (`admin_periods` in config/settings.yaml: Trump first term FY2017–FY2020, Biden FY2021–FY2024, Trump second term FY2025–).

- Competing vs. ongoing awards: new (type 1) and competing renewal (type 2) awards vs. noncompeting continuations (type 5), by fiscal year, for data science, AI, and each group. The data science and AI share of *new* awards shows where the field is heading when new-award volume drops. Parent extramural grants have 16,086 competing awards in FY2026 to date vs. 13,560 in FY2025 and 17,617 in FY2023.
- Terminated and shortened projects: projects on terminated topics (health disparities, DEI, social determinants) that drop out of later fiscal years early or are marked `IN_API = N`; how many are data science or AI, by IC. Separate early endings (project end date moved earlier) from normal completions.
- Award length: project and budget period lengths by award type and fiscal year, to test whether FY2026 awards are shorter or restructured.
- Projection: `notebooks/18_fy_projection.py` projects the preliminary year from same-administration lag patterns (FY2025 for FY2026); extend it to data science and AI counts once FY2026 is labeled.

## Records removed from RePORTER

**Question:** Which NIH projects disappeared from the RePORTER API after the administration's topic restrictions (for example DEI, health disparities, gender identity), and how many were data science or AI?

- Source: records kept with `IN_API = N` (notebook 00), with `NOT_IN_API_SINCE` dating when each went missing. Each refresh adds to this list, so run the update regularly to date removals closely.
- Separate real removals from noise: most current `IN_API = N` records are CDC and other non-NIH agencies the API pull doesn't cover; restrict to NIH institutes. Compare with ExPORTER copies downloaded before and after a removal date.
- Topic signal: the taxonomy's labels on the removed records plus keyword flags for restricted topics (DEI, diversity, equity, inclusion, health disparities, minority health, gender identity, social determinants), using the titles and abstracts kept in the ExPORTER files.
- Context: terminated projects often stay in RePORTER with earlier end dates rather than disappearing. Pair this with the terminated-projects analysis above and with public termination lists, so removals, early endings, and terminations are counted separately.
- Outputs: removed records by fiscal year, institute, topic flag, and data science group; internal list of records; aggregate counts for the site.

## Funding IC vs. administering IC

**Feature:** a dashboard and Tableau filter, **"Count dollars by: Funding IC | Administering IC"**, that switches per-IC dollar figures. Project counts always use the administering IC. Default: **Administering IC**, which every main analysis uses; funding IC stays a short standalone analysis until this filter is built.

**Definition to show next to the filter:**

> **Administering IC** (default): each award's full dollars go to the one institute that manages it. Use this for "how big is the portfolio an institute manages."
> **Funding IC**: dollars go to each institute that paid for the award, in proportion to what it paid. Use this for "how much does an institute spend."
> NIH-wide totals are the same either way; only the split between institutes changes. About 8% of dollars move, mostly to the Office of the Director (OD) for Common Fund programs.

- Data: `tableau_funding_pairs.csv` already has both (`admin_ic`, `funding_ic`, `funded_cost`); add an `ic_basis` column (Funding | Administering) to the per-IC extracts so one filter drives them.
- Explain it once: FUNDING_METHODS.md and the funding appendix doc carry the long version; the filter's tooltip carries the short one above.
- Related analysis: `notebooks/14_funding_ic_relationships.py` (self-funded share by IC, common co-funding pairs, data science vs. not).

## Comparing institutes in the dashboard and Tableau

**Feature:** two comparison modes, driven by filters, that work for any IC:

- IC vs. IC: pick two or more ICs and see them side by side on every chart and table.
- IC vs. rest of NIH: pick one IC and compare it with all other NIH ICs combined. "Rest of NIH" leaves the chosen IC out, so a large IC isn't compared partly with itself.

**Display:** the chosen IC takes the measure's color; the comparison takes light neutral (rest of NIH) or a second shade of the same measure (a second IC). Shares compare directly; counts and dollars show both values, since ICs differ a lot in size.

**Data:** `tableau_ic_benchmark.csv` already holds each IC and NIH overall by year, level, and AI role. Add rest-of-NIH columns (NIH total minus the IC) for counts, dollars, and shares, so Tableau doesn't have to compute them. The dashboard does the same with its IC filter. The internal NIAID vs. NIH report becomes this view with IC = NIAID.

## Crediting software, models, and data to PIs

**Question:** Do AI developer and infrastructure builder PIs produce more datasets and software than matched data science PIs, and does counting them close the paper gap?

- Plan: [analyses/ds_pis/pilot_outputs_beyond_papers.md](analyses/ds_pis/pilot_outputs_beyond_papers.md). DataCite DOIs and NCBI BioProjects linked by NIH award number first; software mentions, models, and registries later.
- Ties to: the data science PI analysis (`analyses/ds_pis/`), Strategic Plan Goals 1 and 3, and NOT-OD-26-087.

## Analysis plan: three analyses and a methods deck

Machine learning work is grouped into three analyses plus a deck on how the dataset was built. Each uses more than one kind of model so the results can be compared: predictive, descriptive, and, where the question is about effects, causal methods (matching, weighting, difference-in-differences). Person-level work is published in aggregate, with groups under 11 suppressed.

### A. PI analysis: who does data science, how they get there, and who they work with (`analyses/ds_pis/`)

Combines the data science PI analysis and the training pipeline.

- Data science PIs and builders (done in draft): PI groups, AI developers, infrastructure builders, matched comparisons, and the outputs-beyond-papers pilot (`pilot_outputs_beyond_papers.md`).
- Training pipeline (done in draft): F, K, R00 trainees and T, R25 program directors (`training.py`); combined page `pi_analysis.md`.
- Time to data science research (ML roadmap 7): survival analysis comparing models: Kaplan-Meier curves, Cox regression, and a random survival forest; plus propensity score matching to compare data science and other K awardees with similar institute, field, and start year.
- Collaboration networks (ML roadmap 6): PI networks from shared projects; community detection; centrality of builders; link prediction comparing a heuristic baseline (common neighbors), logistic regression on network features, and a graph embedding model.

### B. Topic, opportunity, and area analysis (`analyses/topics/`, done: [topics_analysis.md](analyses/topics/topics_analysis.md))

- Emerging topics (ML roadmap 2): compare topic models: LDA (word-count topics), BERTopic (embeddings plus clustering), and the taxonomy's own categories; track topics by fiscal year and flag fast risers.
- Where data science is thin relative to need (ML roadmap 3): embedding similarity between projects and RCDC categories, compared with disease burden data; rank gaps.
- Funding opportunities that attract data science (ML roadmap 4): text similarity between NOFOs (9,135) and data science abstracts, comparing TF-IDF, sentence embeddings, and a cross-encoder; which NOFOs draw data science, and which areas have no matching NOFO.
- What goes with high-impact outputs (ML roadmap 5): compare logistic regression, random forest, and gradient boosting with SHAP values on citation rate, patents, and trials; then a causal check (matching or doubly robust estimation) for the one or two features that matter most.

### C. Methods deck: how this dataset was built

The pipeline so far (RePORTER API, keyword flags, Jev, ChatGPT resolver, hand coding, attributed cost, FY2026 projection) plus two models:

- A small, cheap labeling model (ML roadmap 1): fine-tune small text classifiers (for example a logistic regression on TF-IDF as a baseline, a fine-tuned biomedical BERT model, and a small instruction model), compare them with Jev, ChatGPT, and the hand-coded set (κ = 0.86 data science, 0.92 AI), and report cost per 10,000 texts. Includes a model card.
- Better preliminary-year projections (ML roadmap 8): compare the current completeness method with gradient boosting and quantile regression on how fast RePORTER adds records, by institute and activity code, with back-tests on FY2021 to FY2025.

### D. Global research analysis: NIH data science at foreign institutions (planned)

- Direct foreign awards (in hand): RePORTER organization country and name. FY2016 to FY2026: 1,832 foreign projects in 80 countries, $2.7B; 20.4% are data science vs. 16.3% for all NIH projects. Top countries: Canada, South Africa, United Kingdom, Uganda, Australia, Nigeria, Ghana, Kenya.
- Foreign subawards on U.S. awards: most foreign NIH-funded work is a subaward or foreign component of a U.S. award, which RePORTER lists under the U.S. recipient. Trace these through USAspending.gov subaward data (the prime award's FAIN maps to the NIH project number; subrecipient name, country, and amount are reported). Check coverage, since only subawards over the federal reporting threshold are reported.
- Questions: which countries and institutions receive NIH data science funding directly vs. through subawards; how this changed by administration period; which ICs fund it; data science and AI shares vs. domestic projects.

### E. Data science programs report (planned)

A separate report on NIH's dedicated data science programs, starting with **DS-I Africa** (Data Science for Health Discovery and Innovation in Africa, Common Fund), and including programs such as Bridge2AI and AIM-AHEAD.

- Find program projects by NOFO number (kept per record, `ds_by_nofo.csv`), program-specific activity codes, and project titles; build a program-to-NOFO lookup table from NIH program pages.
- Describe each program: projects, funding, institutions and countries, ICs, taxonomy groups and categories, AI role mix, and outputs (papers, citation rates, and later the outputs-beyond-papers pilot).
- Compare program projects with matched data science projects outside the program, and track trainees and PIs from program awards into later data science research (links to analysis A).
- Check: whether DS-I Africa explains the higher data science share among direct foreign awards (analysis D).

### F. Institute profiles: one page per IC (planned)

One page for each NIH institute and center, built from the same template so any IC can be read on its own or compared with another IC or the rest of NIH. Uses the administering IC; no IC is singled out in the shared version.

- Growth and entry: data science and AI projects, funding, and share of the IC's portfolio by fiscal year; when the IC's growth started; new data science PIs entering each year; first-time vs. returning data science PIs.
- What got them there: activity codes, funding opportunities (NOFOs), and programs behind the IC's data science projects; training awards that fed its data science PIs (analysis A); PIs who moved into the IC's data science work from other ICs.
- Where to improve: research areas (RCDC categories) where the IC's data science share trails the rest of NIH; taxonomy categories it rarely funds; builders and AI developers it funds vs. NIH overall; outputs vs. matched projects.
- Build: a page template (md, matplotlib charts) filled by one script looped over ICs, plus a dashboard IC filter for the same views. Small ICs get suppressed cells (fewer than 11) and fewer charts.
