# Analysis outlines

**Laura Ellis** · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · Draft, October 25, 2026

Six pieces of work, each with a site page (md), a script (py), and a deck. Each one names the question, the sections, the data, the models compared, and the deck outline for approval. All of them use the NIH Data Science Taxonomy labels, NIH institutes only, FY2016 to FY2026 (FY2026 preliminary), administering IC, and attributed cost. Person-level results are aggregate only, with groups under 11 suppressed.

| | Analysis | Folder | Status |
|---|---|---|---|
| A | PI analysis: who does data science, how they get there, who they work with | `analyses/ds_pis/` | Parts 1 to 5 drafted; one page (`pi_analysis.md`) |
| B | Topics, opportunities, and areas | `analyses/topics/` | Done ([page](topics/topics_analysis.md)) |
| C | Methods deck: how the taxonomy and dataset were built | `analyses/methods/` | Planned |
| D | Global research: NIH data science at foreign institutions | `analyses/global/` | Planned; first numbers in hand |
| E | Data science programs (DS-I Africa first) | `analyses/programs/` | Planned |
| F | Institute profiles: one page per IC | `analyses/ic_profiles/` | Planned |

---

## A. PI analysis

**Question:** Who does data science at NIH, how do they get there, and who do they work with?

**Bottom line:** About 1 in 12 active NIH PIs does mostly data science, up from 1 in 16 in FY2016 and flat since FY2022. Data science K awardees reach data science research 3.1 times as fast as other K awardees and reach an R01 at the same pace. Data science PIs team up across institutes, and infrastructure builders connect the most research communities; AI developers publish fewer papers but more in software and data journals.

### Sections

1. **Who counts** (drafted): PI groups and definitions (data science PI, AI developer, infrastructure builder, contributor); cutoff check.
2. **Growth and where** (drafted): share of active PIs by year; share by institute; cross-institute PIs and common IC pairs.
3. **Builders and credit** (drafted): AI mix; papers vs. matched data science PIs; software and data journal share; Strategic Plan and NOT-OD-26-087 context; outputs-beyond-papers pilot (`pilot_outputs_beyond_papers.md`).
4. **How they get there** (done; entrants in `entrants.md`):
    - Training pipeline: F, K, R00 trainees; T, R25 program directors, plus survival models and R01 benchmarks (`training.py`, section 4 of `pi_analysis.md`). Networks in `networks.py`, section 5.
    - Time to data science research: Kaplan-Meier curves, Cox regression, random survival forest.
    - Effect check: propensity score matching of data science vs. other K awardees on institute, field, and start year.
    - Benchmarks (undecided): R01-equivalent outcome with 5- and 7-year windows against published K-to-R01 rates.
5. **Who they work with** (done, `networks.py`):
    - PI network from shared projects; communities (Louvain or Leiden clustering); whether builders sit between communities (betweenness centrality).
    - Link prediction for new collaborations: common-neighbors baseline vs. logistic regression on network features vs. graph embeddings (node2vec).

### Data

RePORTER applications and PI IDs; taxonomy labels and categories; ExPORTER publication, patent, and clinical study links; iCite; journal names (cached); later DataCite and NCBI BioProject.

### Charts

Cutoff grid · share by year · share by institute · AI mix · papers by portfolio size · builders vs. matched · trainee outcomes · survival curves · network map (aggregate, by institute or group).

### Deck (8 slides, built November 19, 2026: "What Data Science at NIH Works On", files in `deck/topics/`)

1. Data science at NIH follows NIH's priorities, with one method spreading on its own (cover)
2. Topics sort data science by disease; the taxonomy sorts it by method
3. Dementia, opioids, and cancer immunotherapy rise with their institutes, while single-cell omics rises everywhere
4. Musculoskeletal, respiratory, and heart disease get the least data science for their burden, and NIH funds them lightly overall
5. Funding opportunities that ask for data science fund more of it
6. Plain word matching beats newer language models at finding a project's funding opportunity
7. Research area predicts trials and patents more than data science method does
8. Where NIH could draw data science in next (links slides 4 and 5)

Code: `analyses/topics/` (topics.py, topic_themes.py, gaps.py, nofo_match.py, impact_models.py).

Inputs from Laura's machine: GBD export of U.S. DALYs (`data/raw/gbd/`) and NOFO text (`src/nofo_pull.py`). Everything runs locally; no paid API calls.

---

## C. Methods deck: how the taxonomy and dataset were built

**Question:** How was the NIH Data Science Taxonomy designed, how was the dataset built from it, how good is it, and can it be made cheaper and more accurate?

### Sections

1. **Creating the taxonomy:** why it was needed (no shared view of data science and AI across NIH; RCDC has one AI category); sources it builds on (NIH Strategic Plan for Data Science 2025 to 2030 goals, NOT-OD-25-117 AI RFI, earlier term lists); structure (dimensions, 7 reporting groups, 36 categories, AI roles, application areas); term lists and weak vs. strong terms; dropped terms and why; testing on 749 sampled projects and 150 hand-coded ones; versions (0.1 to 0.5) and what changed.
2. **Data:** RePORTER API pull (FY2016 to FY2027; FY2026 preliminary; FY2027 not analyzed); records not in the API kept and marked; centers counted once (attributed cost); funding methods appendix.
3. **Labeling pipeline:** keyword flags, then Jev, then ChatGPT for calls under 0.90 confidence; agreement with hand coding (κ = 0.86 data science, 0.92 AI); costs; caching.
4. **A small, cheap labeling model:** compare TF-IDF plus logistic regression (baseline), a fine-tuned biomedical BERT model, and a small instruction-tuned model against Jev, ChatGPT, and the hand-coded set; accuracy, κ, and cost per 10,000 texts; model card.
5. **Projecting the preliminary year:** current completeness method vs. gradient boosting and quantile regression on how fast RePORTER adds records, by institute and activity code; back-tests on FY2021 to FY2025; ranges.
6. **Work so far:** dashboard, deck, site pages, API, Tableau extracts, analyses A to E.

### Deck (10 slides, for approval)

1. Title: "Building an NIH data science taxonomy and dataset: 258,000 records, three models, one taxonomy"
2. Why a taxonomy: what funders couldn't see before
3. How the taxonomy was designed: Strategic Plan alignment, groups, categories, AI roles
4. From terms to labels: keyword lists, strong and weak terms, what was dropped, and testing
5. Sources and scope
6. The labeling pipeline and its accuracy
7. Cost and caching
8. A small model that labels for nearly free
9. Projecting a year that isn't over
10. What the taxonomy and dataset power, limits, and next steps

---

## D. Global research: NIH data science at foreign institutions

**Question:** Where outside the United States does NIH fund data science, directly and through subawards?

**First numbers:** 1,832 directly funded foreign projects in 80 countries, $2.7B, FY2016 to FY2026; 20.4% are data science vs. 16.3% for all NIH projects. Top countries: Canada, South Africa, United Kingdom, Uganda, Australia, Nigeria, Ghana, Kenya.

### Sections

1. **Direct awards:** countries, institutions, institutes, data science and AI shares, by year and administration period.
2. **Subawards:** USAspending.gov subaward data linked to NIH project numbers; subrecipient country, institution, and amount; coverage check (only subawards above the reporting threshold are reported).
3. **Direct vs. subaward:** which countries get NIH data science money directly and which only through U.S. partners.
4. **Programs:** how much is DS-I Africa (links to E).

### Charts

Map of projects or funding by country (symbols for counts, fills for shares) · top countries and institutions · direct vs. subaward by region · trend by administration period.

### Deck (5 slides, for approval)

1. Title: finding to come
2. Where NIH funds data science abroad (map)
3. Direct awards vs. subawards
4. Data science share vs. domestic projects, and the role of DS-I Africa
5. So what and next

---

## E. Data science programs

**Question:** What have NIH's dedicated data science programs funded, and how do their projects and people compare with data science projects outside them?

### Sections

1. **Program lookup:** program-to-NOFO table from NIH program pages (DS-I Africa first, then Bridge2AI and AIM-AHEAD); project lists from NOFO numbers already kept per record.
2. **Profile each program:** projects, funding, institutions and countries, institutes, taxonomy groups and categories, AI role mix.
3. **Outputs:** papers, citation rates, software and data journals, later DOIs and NCBI deposits (A, pilot).
4. **Comparison:** program projects vs. matched data science projects outside the program (matching on institute, activity code, start year, and cost).
5. **People:** trainees and PIs from program awards into later data science research (links to A).

### Charts

Program funding over time · program portfolios by taxonomy group · outputs vs. matched projects · trainee and PI paths.

### Deck (6 slides, for approval)

1. Title: finding to come
2. The programs and what they fund
3. DS-I Africa in detail
4. Outputs vs. similar projects
5. Where the people go next
6. So what and next

---

## F. Institute profiles: one page per IC

**Question:** For each NIH institute or center, how did data science grow, what brought it there, and where could it do more?

### Sections

1. **Growth and entry:** data science and AI projects, funding, and portfolio share by fiscal year vs. the rest of NIH; new data science PIs each year; first-time vs. returning PIs.
2. **What got them there:** activity codes, NOFOs, and programs behind the IC's data science projects; training awards that fed its data science PIs (from A); PIs who came from other ICs.
3. **Where to improve:** RCDC areas where the IC's data science share trails the rest of NIH; taxonomy categories it rarely funds; builders and AI developers vs. NIH overall; outputs vs. matched projects.
4. **Compared with:** any other IC or the rest of NIH (same template).

### Build

One script loops over ICs and fills a page template (md plus matplotlib charts); a dashboard IC filter shows the same views. Administering IC; no IC singled out in the shared version. Cells under 11 suppressed, so small ICs get shorter pages.

### Deck

One summary deck across ICs (outline later), plus each IC page as a one-pager.
