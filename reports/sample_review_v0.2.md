# Sample review: taxonomy v0.1 → v0.2

**Date:** 2026-10-23
**Sample:** 749 NIH projects from RePORTER, FY2019, FY2022, and FY2025 (`data/raw/reporter_sample_20261023.csv`)

| Stratum | Projects | Population it was drawn from (3 years) |
|---|---|---|
| AI search hits | 300 | 12,807 projects matching AI or data science phrases |
| General research projects (R01, R21, U01, R35) | 299 | 113,148 |
| Training and career projects (T, F, K, R25) | 150 | 31,518 |

## Bottom line

The categories fit real NIH abstracts. The keyword baseline finds almost every project NIH's RCDC category flags as AI (recall 98%), and also flags about 50% more projects that mention AI but that RCDC does not count. A spot check of 10 of those found mostly genuine AI use, a few passing mentions, and three real false positives that v0.2 fixes. Hand review of the 150-project workbook is the next step to separate substantive AI use from passing mentions.

## Keyword baseline vs. RCDC "Machine Learning and Artificial Intelligence"

| | RCDC: AI | RCDC: not AI |
|---|---|---|
| Keywords: AI | 195 | 103 |
| Keywords: not AI | 4 | 447 |

(v0.2 labels.)

- Recall = 195 / 199 = 98%: the keywords miss almost nothing RCDC flags
- Precision = 195 / 298 = 65%: one in three keyword AI projects is not in the RCDC category
- The 4 misses: two copies of a data science workforce project and a biostatistics and data science core, which v0.2 now labels as data science (not AI) through the new "data science (general)" category; and a computational neuroscience project whose "neural network" wording v0.2 now excludes. That last one is the cost of the neural network fix; hand review will show how often it happens

Within the AI search stratum, RCDC's AI share rose from 54% (FY2019) to 75% (FY2025), while the keyword share stayed near 90%. RCDC may be counting AI use more completely in recent years; that gap is worth tracking.

## How common is data science in ordinary NIH projects?

From the general stratum (random R01, R21, U01, and R35 projects), with 95% Wilson confidence intervals:

| Measure | FY2019 | FY2022 | FY2025 | All three years |
|---|---|---|---|---|
| Data science related | 10% | 15% | 19% | 14.7% (11.1%–19.2%) |
| AI related | 2% | 5% | 9% | 5.4% (3.3%–8.5%) |

Each year has about 100 projects, so the year-to-year rise is suggestive, not precise. Training projects were similar: 17.3% data science related, 6.7% AI related.

## Problems found and fixed in v0.2

| Problem | Example | Fix |
|---|---|---|
| "Neural network" used for biological networks | "the enteric nervous system ... a complex neural network embedded in the gut wall" | Excluded when near nervous system, neuron, brain, synapse, circuit, and similar words |
| "Super-resolution" used for microscopy | "super-resolution techniques ... single-molecule fluorescence" | Excluded when near microscopy or fluorescence |
| "Algorithm(s)" matched in 94 projects and drove most research software labels | Clinical algorithms, diagnostic algorithms | Dropped |
| Singular and plural counted as two weak terms | "algorithm" + "algorithms" | Labeler counts them as one term |
| "Course" and "education" triggered training | "time course", "patient education" | Dropped as weak terms |
| "Community" triggered capacity building | "community health" | Dropped as a weak term |
| Training projects without training words were missed | 69 of 150 training projects | T, F, K, D43, and R25 activity codes now add training and education |
| Projects that only said "data science" were missed | "Building a data science workforce" | New category: data science (general) |

## Still open

- **Passing mentions vs. substantive use.** "Cultivate expertise in ... artificial intelligence" in a core description counts the same as a project built on deep learning. The role-of-AI LLM label and hand review should separate these.
- **"Artificial intelligence" alone** (other AI) is the most common single AI term after machine learning. Review whether projects with only this term are substantive.
- **Empty categories:** fairness and bias, visualization tools, and ML frameworks had zero or one hit. Keep them for now since they matter to NIH policy, but review the terms after hand coding.
- **Clinical care fires in 36% of AI search hits**, mostly through "diagnosis" and "clinical data." Check whether it should require a more specific term.

## Next step

Hand-code `reports/taxonomy_review_sample.xlsx` (150 projects, 50 per stratum). The Instructions sheet defines each field; `my_ds_related` and `my_ai_related` use Y (substantive), M (mention only), or N, which answers the passing-mention question above. Then compute Cohen's κ for the keyword labels and RCDC against the coding (M counts as N).
