# Methodology: NIH Data Science Taxonomy

**Version:** 0.5.0 · **Updated:** 2026-11-22 · **Author:** Laura Ellis · **GitHub:** [github.com/Laura-Ellis/nih-ds-taxonomy](https://github.com/Laura-Ellis/nih-ds-taxonomy)

## Bottom line

The taxonomy classifies NIH projects in three stages. Keyword terms find every project that mentions data science or AI, at no cost and with almost no misses (AI recall 98–100%). Jev then labels each flagged project, and a resolver model relabels the calls where Jev is less than 90% confident. With Claude as the resolver, the pipeline matches Claude alone on AI (κ = 0.94) and beats it on data science (κ = 0.87 vs. 0.84) at about one-eighth of the cost. The pipeline uses ChatGPT (GPT-6 Luna) as the resolver: it comes within 0.02 of Claude on both labels and labels the full FY2016–2026 set for about $24 in total, compared with about $108 using Claude through the Batch API. Gemini Flash-Lite costs more than ChatGPT and falls short on data science.

## 1. Sources and design

**Question.** Where does data science show up across NIH projects, how much of it is AI, and which parts of NIH's data science strategy do those projects support?

**Sources**
- NIH Strategic Plan for Data Science, 2025–2030: the five goals set the dimensions (methods and tools, infrastructure, data management and sharing, and workforce)
- NIH AI Strategy Request for Information (NOT-OD-25-117): adds responsible AI (fairness, privacy, and transparency)
- NIH RCDC category "Machine Learning and Artificial Intelligence": an outside benchmark for AI labels
- 2024 term lists in [Laura-Ellis/NIH](https://github.com/Laura-Ellis/NIH): 16 lists and 415 terms, the starting point for the terms

**Design choices**
- Data science is the umbrella. Methods fall into three groups: statistics and analytics, computational modeling, and AI. AI is one part of data science, not the whole.
- Software and tools stand alone. Building research software is a different contribution from using a method.
- Application areas only count with data science. Nearly every NIH project names a disease or organ system, so an area means something only when the project also has a data science label.
- Role of AI comes from a model, not keywords. Whether a project develops, applies, studies, or supports AI depends on how the abstract describes the work, which a term list cannot read.

The result: 8 dimensions and 40 categories (36 assigned by keywords, 4 by model review). [README](README.md#structure) lists them with their strategic plan goals; [`taxonomy/categories.yaml`](taxonomy/categories.yaml) holds the definitions.

## 2. Term building

**From the 2024 lists.** Of 415 original terms, 237 were kept and assigned to categories; 178 were dropped, each with a reason. Most were routine analysis terms found in almost every abstract (t-test, regression, algorithms) or rare and ambiguous terms. New terms filled the new categories, for 706 term entries in v0.4.0. An institute coverage review (October 25, 2026) added 49 domain computing terms (for example phylogenetics, transmission modeling, bioinformatics, computational neuroscience, pharmacometrics), for 755 entries. The full term list (755 entries) and the tuned labeling prompts are kept private; the repo includes a sample ([`taxonomy/terms_sample.csv`](taxonomy/terms_sample.csv), 3 strong terms per category) and example prompts ([`config/prompts.example.yaml`](config/prompts.example.yaml)). The pipeline runs end to end with them, but labels will differ from the published results. Contact me to collaborate on or license the full taxonomy.

**Each term has**
- a **strength:** strong terms count on their own ("convolutional neural network"); weak terms need a second weak term from the same category ("classification", "bias"). 617 strong, 89 weak.
- a **match type:** phrases match any case and singular or plural; acronyms (53) match case-sensitively.
- an optional **exclusion:** a pattern that cancels a match within 60 characters. For example, "neural network" near "neuron", "synapse", or "brain" refers to the brain, and "AI" next to "American Indian" refers to AI/AN populations.

**Labeling rule.** A category applies when the title and abstract contain 1 strong term or 2 distinct weak terms, after exclusions. Two adjustments follow: "data science (general)" drops when a specific method is named, and training activity codes (T, F, K, D43, R25, and R00) set a separate training flag.

**Evidence rule (precision tier).** A stricter label keeps a category only when its terms appear at least twice, or one appears within 150 characters of an action phrase ("we will", "aim", "develop a", "to predict"). This separates "we will train a deep learning model" from "deep learning has transformed imaging."

**How terms were revised**

| Version | Tested on | What changed |
|---|---|---|
| 0.1 | Design only | 2024 lists reorganized into the new dimensions |
| 0.2 | 749 RePORTER projects vs. RCDC | Exclusions for "neural network" (brain) and "super-resolution" (microscopy); dropped "algorithm", "course", "education", and "community"; plural double counting fixed; training activity codes added |
| 0.3 | 150 coded projects | "Data science (general)" only without a specific method; 15 research software terms added; training limited to data science training |
| 0.4 | 747 projects labeled by Claude | Evidence rule added; term-level review flags low-precision terms ([`reports/term_review_v0.4.csv`](reports/term_review_v0.4.csv)) |

## 3. Validation

**Sample.** We drew 749 projects from the NIH RePORTER API for FY2019, FY2022, and FY2025, in three strata, then coded 150 (50 per stratum).

| Stratum | Sampled | Population (3 years) |
|---|---|---|
| AI search hits | 300 | 12,807 |
| General research (R01, R21, U01, R35) | 299 | 113,148 |
| Training and career (T, F, K, R25) | 150 | 31,518 |

**Coding.** Each project gets two codes, data science and AI:
- Y (substantive): the method appears in an aim or the stated approach, even if it is not the main focus
- M (mention only): background, a core's or center's general capabilities, prior work, or a future possibility
- N: none, or only routine statistics

**Rules settled during review**
- Omics counts as data science only with substantial computation (eQTL mapping, co-expression or regulatory networks, multi-omics integration); standard sequencing analysis is M.
- Testing or validating AI algorithms in clinical settings counts as applying AI.
- A project that studies how people use AI tools, without building or applying them, is M.
- "Neural network" describing the brain or cultured neurons is not AI.

**How the codes were checked.** An AI tool drafted the first coding. A blind spot check of 30 projects, oversampling hard cases, showed that the draft labeled too many substantive projects as mentions (κ = 0.49 for AI). All 28 projects drafted as "mention only" were then recoded under the written rules. Final codes: data science Y = 52, M = 7, N = 91; AI Y = 42, M = 6, N = 102. Files: [`reports/taxonomy_spot_check_coded.xlsx`](reports/taxonomy_spot_check_coded.xlsx) and [`reports/taxonomy_recode_M_coded.xlsx`](reports/taxonomy_recode_M_coded.xlsx).

**Measures**
- Precision = flagged and coded substantive / flagged
- Recall = flagged and coded substantive / coded substantive
- Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement)
- Wilson 95% CI for a share p of n projects: (p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n), z = 1.96

## 4. Classification options

The pipeline runs in three stages: **keywords** find candidates, **Jev** labels each candidate with a confidence for every answer, and a **resolver** model relabels the answers where Jev is less than 90% confident. Claude, Gemini, and ChatGPT were compared as resolvers.

| Method | AI precision | AI recall | AI κ | DS precision | DS recall | DS κ | Cost per 1,000 projects |
|---|---|---|---|---|---|---|---|
| Keywords, any match | 79% | 100% | 0.83 | 79% | 94% | 0.77 | $0 |
| Keywords, evidence rule | 88% | 90% | 0.85 | 83% | 85% | 0.75 | $0 |
| Keywords → Jev | 88% | 100% | 0.90 | 86% | 94% | 0.84 | ~$0.14 |
| **Keywords → Jev → Claude** | **91%** | **100%** | **0.94** | **89%** | **94%** | **0.87** | **~$0.80 (AI); ~$2.40 (DS)** |
| Keywords → Jev → ChatGPT (GPT-6 Luna) | 89% | 100% | 0.92 | 88% | 94% | 0.86 | ~$0.17 (AI); ~$0.26 (DS) |
| Keywords → Jev → Gemini 3.1 Flash-Lite | 86% | 100% | 0.89 | 83% | 94% | 0.81 | ~$0.22 (AI); ~$0.40 (DS) |
| Claude Sonnet 5.5 alone | 91% | 100% | 0.94 | 85% | 96% | 0.84 | ~$6 (~$3 with Batch API) |
| Jev alone | 88% | 100% | 0.90 | 75% | 98% | 0.75 | ~$0.14 |
| ChatGPT (GPT-6 Luna) alone | 89% | 100% | 0.92 | 76% | 98% | 0.77 | ~$0.29 |
| Gemini 3.1 Flash-Lite alone | 84% | 100% | 0.88 | 65% | 100% | 0.63 | ~$0.69 |
| *RCDC "Machine Learning and AI" (NIH)* | *92%* | *86%* | *0.85* | | | | *n/a* |

Reference: the 150 coded projects (42 substantive AI, 52 substantive data science). Each percentage carries a 95% confidence interval of about ±10 points. DS = data science. Jev sent 16 of 150 AI calls and 57 of 150 data science calls to the resolver. Pipeline cost = Jev on every candidate + the resolver on the uncertain share (11% for AI, 38% for data science). Gemini and ChatGPT results come from `notebooks/19_pipeline_compare.py` (run through the Vercel AI Gateway at list price); their costs use measured tokens (about 2,400 input and 70–100 output per project) and list prices.

**Keywords** run locally from `src/taxonomy.py`. **Jev** (Typesafe, model alias `typesafe-ai/jev`, version 1.14.0 at the time of the runs, through the Vercel AI Gateway) answers 39 typed questions per project and returns a probability for each answer (`src/jev_label.py`). It was right on 99% of AI calls made with at least 90% confidence and on 75% of the rest, which is why only the uncertain calls go to a resolver. **Resolvers** get the same prompt, coding rules, and category definitions, and return typed labels plus an evidence quote: Claude through the Anthropic API (`src/llm_label.py`), Gemini and ChatGPT through the AI Gateway (`src/gateway_label.py`). Requiring a keyword flag before Jev raises its data science agreement from κ = 0.75 to 0.84, because keywords screen out projects Jev over-calls.

**Choosing a resolver.** Agreement on the uncertain calls matters most, since those are the only calls a resolver makes. A cheaper resolver is worth using if its pipeline κ is within about 0.02 of Claude's; differences smaller than that are within sampling error on 150 projects. ChatGPT (GPT-6 Luna) meets that bar on both labels (AI 0.92 vs. 0.94; data science 0.86 vs. 0.87) at about one-twentieth of Claude's cost; Gemini Flash-Lite does not (0.89 and 0.81), mainly because it calls mentions substantive. All three models agree with the coding on every substantive AI project (recall 100%); they differ on mentions. Using a second model family also shows the labels do not depend on one vendor.

**Cost at full scale.** These estimates come from an earlier keyword run that flagged 54,806 of 258,321 records (the v0.5 terms flag 60,245; section 6). Their combined texts average 1.7 times a single abstract. Jev's confidence falls below 0.90 on about 11% of AI calls and about 40% of AI or data science calls.

| Resolver | Relabels | Resolver cost | Total with Jev (~$11) | Pipeline AI κ | Pipeline DS κ |
|---|---|---|---|---|---|
| Claude Sonnet 5.5, standard | Uncertain AI or DS (~20,200) | ~$194 | ~$205 | 0.94 | 0.87 |
| Claude Sonnet 5.5, Batch API | Uncertain AI or DS (~20,200) | ~$97 | ~$108 | 0.94 | 0.87 |
| Claude Sonnet 5.5, Batch API | Uncertain AI only (~5,550) | ~$27 | ~$38 | 0.94 | 0.84 |
| Gemini 3.1 Flash-Lite | Uncertain AI or DS (~20,200) | ~$22 | ~$33 | 0.89 | 0.81 |
| **ChatGPT (GPT-6 Luna)** | **Uncertain AI or DS (~20,200)** | **~$9** | **~$21** | **0.92** | **0.86** |
| *Claude alone, Batch API, every flagged record* | *All 50,481* | *~$242* | *n/a* | *0.94* | *0.84* |

Costs are estimates made before the full run: tokens measured on the coded sample × list price × 1.6 for longer texts. The actual v0.5 run cost about $24 through the Vercel AI Gateway (section 6), more than the ~$21 estimate because the v0.5 terms flagged more records (60,245 vs. 54,806) and ChatGPT resolved 37,415 texts, not the ~20,200 estimated: Jev was below 90% confidence on AI or data science for 62% of flagged records, not 40%. Claude ~$0.006 per abstract (standard), ChatGPT ~$0.00029, Gemini ~$0.00069, Jev ~$0.00014.

**Why ChatGPT is the resolver.**
- Accuracy: it comes within 0.02 κ of Claude on both labels (AI 0.92 vs. 0.94; data science 0.86 vs. 0.87), inside the sampling error of a 150-project sample, and finds every substantive AI project (recall 100%).
- Cost: it relabels both AI and data science calls for about $9, about one-tenth of Claude through the Batch API ($97) and less than Claude on AI calls alone ($27), which would leave data science calls with Jev (κ 0.84).
- Gemini 3.1 Flash-Lite costs about twice as much as ChatGPT and agrees less with the coding (AI 0.89; data science 0.81), mainly because it calls mentions substantive. On its own, its data science κ is 0.63.
- Claude remains the reference model: it set the bar the other resolvers were tested against, labeled the 747-project term review, and is available through the Batch API (`src/claude_batch.py`) if a resolver change needs checking.

**Pipeline**
1. **Find candidates with keywords:** all RePORTER projects, FY2016–2026 (FY2026 preliminary), at no cost.
2. **Label candidates with Jev;** send AI or data science calls below 90% confidence to ChatGPT (GPT-6 Luna) (`notebooks/09_label_jev.py`, `notebooks/10_resolve_chatgpt.py`).
3. **Check and tune** on samples each fiscal year: compare keyword, Jev, ChatGPT, and Claude labels, and review low-precision terms.

Full comparison: [`reports/method_comparison.md`](reports/method_comparison.md) and `reports/pipeline_comparison_v0.4.csv`.

## 5. Unit of analysis and funding

**Projects, not yearly applications.** NIH funds a project with a new application each fiscal year, so the same project appears up to once per year. Records are built per project (`notebooks/08_classify_exporter.py`):
- `core_project_number`: ExPORTER's core project number, or activity code + 2-letter IC code + 6-digit serial number when it is missing
- One combined text per record: the latest title, earlier titles that differ, and every distinct abstract across years
- `fiscal_years` and `application_ids` list the years and applications behind each record, for matching to publications, patents, and clinical studies

**Parents and subprojects are classified separately.** A center or program project (P30, P50, P01, U54, and similar) has a parent abstract and a title and abstract for each component. Each subproject gets its own record, identified by `core_project_number` + ExPORTER's `subproject_id` (blank for the parent), so it keeps the link to its parent. A center's data science often sits in one component, such as a bioinformatics or data core, and its parent abstract may not mention it. `ds_location` on each parent records where the data science appears: parent, subprojects only, both, or none. This separates centers that conduct data science research from those that provide data infrastructure or support services through a core.

**Subprojects are not subawards.** A subproject is a defined component of a multi-component application. A subaward passes funds from the awardee to another organization; ExPORTER does not list subawards, and this taxonomy does not classify them.

**Funding is counted once.** A parent award's total cost already includes its subprojects' costs, so adding both overstates funding. `attributed_cost` gives each subproject its own cost and the parent the remainder (parent total cost − subproject costs, in the same fiscal year), so it sums to the award total and can be split by flag without double counting. `award_total_cost` on the parent record keeps the full award amount for reference.

## 6. Results, FY2016–2026

FY2026 is preliminary (RePORTER API pull, October 2026), so comparisons below run FY2016 to FY2025, the latest complete year, with FY2026 shown separately.

**Bottom line:** AI went from 2.2% of NIH project records in FY2016 to 8.0% in FY2025, and from 2.6% to 9.5% of extramural funding ($671M to $3.5B). Data science as a whole rose from 14.8% to 23.0% of records. Most AI projects apply existing methods; about a fifth develop new ones. Generative AI projects grew 79% from FY2023 to FY2025, while AI overall grew 11%.

**Scale of the run**
- 258,321 records (parent projects and subprojects), FY2016–2026, from the RePORTER API
- 60,245 flagged by keywords (v0.5 terms); Jev's label stands for 22,830, and ChatGPT (GPT-6 Luna) resolved the other 37,415, where Jev was less than 90% confident
- 198,076 not flagged, labeled N by keywords
- Total model cost about $24 for the v0.5 run (Jev plus ChatGPT, Vercel AI Gateway)

**Trend** (`reports/results/trend_by_fy.csv`)

| Measure | FY2016 | FY2025 | FY2026 (preliminary) |
|---|---|---|---|
| Records | 63,511 | 68,794 | 63,926 |
| Data science, share of records | 14.8% | 23.0% | 23.5% |
| Data science, share of extramural funding | 21.2% | 27.4% | 27.6% |
| AI, records | 1,414 | 5,489 | 5,545 |
| AI, share of records | 2.2% | 8.0% | 8.7% |
| AI, extramural funding | $671M | $3.5B | $3.7B |
| AI, share of extramural funding | 2.6% | 9.5% | 10.1% |

**AI role, FY2025:** applies AI 69%, develops AI 21%, supports AI 9%, and studies AI 1%.

**By institute** (extramural, FY2016–2026, `ai_by_institute.csv`): NCI spends the most on AI ($3.1B, 5.9% of its extramural funding), followed by NIAID ($2.3B, 4.3%), NIA ($2.3B, 7.1%), NHLBI ($2.3B, 6.2%), and NIMH ($2.1B, 11.7%). NLM (45.7%, on a small portfolio), NIBIB (19.2%), and NHGRI (18.7%) put the largest shares into AI. NIAID has the largest extramural portfolio ($53.6B); among the large institutes, NIAID (4.3%) and NIDDK (3.4%) have the most room to grow their AI share.

**Methods and areas** (`ai_method_by_area.csv`): machine learning appears in every area. Computer vision clusters in imaging (2,759 projects), and language processing in clinical care and electronic health records (740).

**Generative AI** (`genai_by_fy.csv`, `genai_role_area.csv`): 171 projects in FY2023, 306 in FY2025, and 409 in FY2026 so far. Among generative AI projects active since FY2023, 51% develop AI and 41% apply it; clinical care (32%) and imaging (29%) are the most common areas.

**Publications, AI vs. matched projects** (`outputs_matched.csv`): extramural core projects starting FY2016–2020, with non-AI projects weighted to match AI projects on IC, activity code, first fiscal year, and size band (cost tercile within activity code). AI projects have a median of 12 linked papers vs. 8 for matched projects; 91% vs. 89% have at least one. Citation impact (RCR, FWCI), patents, and clinical trials come from `notebooks/12_link_outputs.py`.

**Data science by group:** `notebooks/13_ds_groups.py` splits data science projects into the eight taxonomy groups by fiscal year and IC, for the dashboard, the Tableau extract, and the API (`api/main.py`).

## 7. Method experiments (November 2026)

**A small, free labeling model** (`analyses/methods/small_model.py`). TF-IDF + logistic regression, trained on the pipeline's labels for keyword-flagged records (records holding a coded project dropped), applied after the keyword flag. On the 150 coded projects: AI κ 0.87 (95% CI 0.79–0.96; precision 85%, recall 98%); data science κ 0.81 (0.72–0.91; precision 83%, recall 94%), vs. 0.92 (0.85–0.99) and 0.86 (0.77–0.94) for keywords → Jev → ChatGPT. The intervals overlap: the free model is close to the pipeline, not clearly below it. κ CI = κ ± 1.96 × √(po(1−po) / (n(1−pe)²)). No API cost. Candidate use: a free first screen that sends only its uncertain calls to the resolver.

**Projecting the preliminary year** (`analyses/methods/fy_projection_backtest.py`). Back-test of extramural grants by institute × activity family, FY2021–FY2025, at 24 to 180 days after close. 98–99% of records and funding are in by day 24. Cell error (WAPE) at day 24: completeness 0.8%, gradient boosting 0.7%, quantile regression 0.7%; all-NIH totals within 0.3%. Quantile regression's 80% range covers 90% of cells; the completeness range covers 15%. Contracts and intramural records are not in the back-test.

**Building on RCDC's AI tag** (`analyses/methods/rcdc_compare.py`). NIH's RCDC category "Machine Learning and Artificial Intelligence" starts in FY2019. From FY2019 to FY2025, 8,014 project records carry the tag and the taxonomy identifies 10,863 AI records: 2,849 more (36%). 6,807 are AI in both; 4,056 are identified by the taxonomy only; 1,207 carry the tag but don't meet the taxonomy's bar for substantive AI (often a mention in background). On the 150 coded projects, the RCDC tag is right 92% of the time it tags a project (95% CI 80–97%) and tags 86% of substantive AI projects (72–93%).

**Finding a project's funding opportunity** (`analyses/topics/nofo_match.py`, `nofo_match_bio.py`, `nofo_match_ltr.py`). Can text find the NOFO a project was funded under? Check set: 2,000 data science projects funded under a targeted NOFO (RFA or PAR), ranked against 2,482 targeted NOFOs (Section I text from the NIH Guide). Hit@k = share whose own NOFO is in the top k; MRR = mean of 1 ÷ rank; both are lower bounds, since a project can fit more than one NOFO.
- Text only: TF-IDF puts the right NOFO first for 20% and in the top 10 for 47% (MRR 0.29). Free biomedical and long-text models score lower: PubMedBERT 40%, MedCPT with its reranker 37%, BGE-M3 36% in the top 10. Rank fusion of TF-IDF and PubMedBERT adds nothing (45%); a 0.6/0.4 score blend adds about one point (47%, MRR 0.30). NOFOs and abstracts share distinctive terms (program names, diseases, methods), which word matching rewards directly.
- Text + project details: a learning-to-rank model (LightGBM LambdaMART, 5-fold cross-validated by project) adds whether the NOFO allows the project's activity code, whether the project's institute issued or joined it, and whether it was open in the project's funding years. Top 1 47%, top 10 95% (95% CI 94–96%, Wilson, n = 2,000), MRR 0.65. A plain activity code + institute filter already gets title matching to 84% in the top 10.
- Use: suggest the likely NOFO for projects with none recorded, with a person checking the top picks.

## Limits

- One person reviewed the coded sample; there is no second coder to measure agreement between people.
- On the 747-project term review, Claude is the reference, so blind spots that Claude and the coding share stay hidden.
- Claude declined one abstract on influenza virus reassortment. Failed calls are logged and skipped; at full scale, Jev's label should stand in for any Claude refusal.
- Broad categories (statistical methods, data exploration) have low keyword recall against Claude, because Claude assigns them to most data projects. They need narrower definitions, not more terms.
- Precision differs by population (87% of AI-search projects vs. 56% of general research projects, n = 16), so correction factors must come from matching samples.
