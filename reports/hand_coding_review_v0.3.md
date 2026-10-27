# Hand-coding review: taxonomy v0.2 → v0.3

**Date:** 2026-10-23
**Coded sample:** 150 projects, 50 per stratum, drafted with ChatGPT (`reports/taxonomy_review_coded.xlsx`); reproduce with `notebooks/03_agreement.py`

## Bottom line

The keywords find data science and AI almost every time it appears (κ = 0.93 for AI, 0.88 for data science, counting mentions). They cannot tell a project built on AI from one that only mentions it: 40% of keyword AI projects were coded as mention only. NIH's RCDC category is stricter and agrees better on substantive AI (κ = 0.72 vs. 0.63), but misses 10% of substantive AI projects and 28% of all AI mentions. Telling substantive use from mentions is the job for the LLM review step.

## Agreement with hand coding

| Label | Method | Coded as | κ | Precision | Recall |
|---|---|---|---|---|---|
| AI | Keywords | Any mention (Y or M) | 0.93 | 92% | 98% |
| AI | RCDC | Any mention (Y or M) | 0.73 | 92% | 72% |
| AI | Keywords | Substantive (Y) | 0.63 | 57% | 100% |
| AI | RCDC | Substantive (Y) | 0.72 | 69% | 90% |
| Data science | Keywords | Any mention (Y or M) | 0.88 | 92% | 93% |
| Data science | Keywords | Substantive (Y) | 0.61 | 60% | 95% |

Coding: data science Y = 39, M = 22, N = 89; AI Y = 30, M = 20, N = 100.

## Can simple signals separate substantive AI from mentions?

Among the 49 keyword AI projects (30 coded Y, 19 coded M):

| Rule | Precision for Y | Recall for Y |
|---|---|---|
| AI term in the title, or 2+ AI terms near "we will", "aim", "develop", "train", or "apply" | 88% | 50% |
| AI term in the title, or 3+ AI term occurrences | 79% | 63% |
| 2+ AI term occurrences | 66% | 83% |

None is good enough on its own. v0.3 adds `ai_in_title` and `ai_term_count` as inputs for the LLM step.

## Changes in v0.3

| Finding | Change |
|---|---|
| Data science (general) was assigned 12 times alongside a specific method, never coded | Counts only when no specific method is named |
| Training and education was coded only for data science training (1 of 7) | Counts only with a data science label; training activity codes become a separate `training_mechanism` flag |
| Research software missed 5 of 6 coded projects | Added 15 terms (software infrastructure, analysis tools, web portal, user interface, mobile app, decision support tool, and others) |
| Weak terms "tool" and "platform" over-fired when tested | Not added |

## Category agreement (39 projects coded Y for data science)

Best: medical imaging, deep learning, computer vision, sensors and wearables (precision 0.8–1.0, recall 0.8–1.0). Weakest: clinical care (0.68 / 0.62), population health (0.29 precision), omics (0.33 precision), and machine learning (0.58 precision, often a mention alongside a specific method). Application areas were coded broadly ("patient", "treatment"), which keywords should not copy.

## Caveats

- One coder; no second coder to measure human agreement.
- The coding was drafted with ChatGPT; see the spot check below.
- 150 projects; category-level numbers rest on 1–26 projects each.

## Spot check of the ChatGPT coding (30 projects)

Laura coded 30 projects blind, oversampling hard cases (`reports/taxonomy_spot_check_coded.xlsx`, `notebooks/04_spot_check.py`). Fourteen codes were revised after review against the written rule (Y = in an aim or the approach); each is flagged in the notes column.

| Label | Exact agreement (Y/M/N) | κ (Y/M/N) | κ (Y vs. M or N) |
|---|---|---|---|
| Data science | 70% | 0.50 | 0.55 |
| AI | 63% | 0.46 | 0.49 |

**ChatGPT under-codes substantive use.** Every project ChatGPT coded AI = Y was also Y by hand, but 7 of 17 hand-coded Y projects were coded M by ChatGPT. On this sample, keyword AI labels have 100% recall and 68% precision for substantive AI; RCDC has 71% recall and 86% precision. So the v0.3 table above likely understates keyword precision and overstates RCDC recall for substantive AI.


## Corrected agreement (v0.3b)

All 28 projects ChatGPT coded M were recoded under the written rule: 15 by Laura in the spot check, 13 by Claude (`reports/taxonomy_recode_M_coded.xlsx`), with Laura deciding the three judgment calls. Coding is now data science Y = 52, M = 7, N = 91; AI Y = 42, M = 6, N = 102. Results in `reports/agreement_v0.3b.csv`.

| Label | Method | Coded as | κ | Precision | Recall |
|---|---|---|---|---|---|
| AI | Keywords | Substantive (Y) | 0.83 | 79% | 100% |
| AI | RCDC | Substantive (Y) | 0.85 | 92% | 86% |
| AI | Keywords | Any mention (Y or M) | 0.93 | 91% | 100% |
| AI | RCDC | Any mention (Y or M) | 0.82 | 97% | 79% |
| Data science | Keywords | Substantive (Y) | 0.77 | 79% | 94% |
| Data science | Keywords | Any mention (Y or M) | 0.88 | 90% | 95% |

**What changed:** ChatGPT's M codes hid substantive use. Once corrected, keyword precision for substantive AI rises from 57% to 79%, and RCDC recall falls from 90% to 86%. Keywords still never miss substantive AI; RCDC is more precise but misses 1 in 7. The case for keywords plus an LLM check for "mention only" still holds, with a smaller mention problem than v0.3 suggested.

**Coding rules settled in review:** Y = in an aim or the approach, even if not the focus; omics counts only with substantial computation (eQTL, networks, integration), not standard sequencing pipelines; validating AI in clinical settings counts as applying AI; studying how people use AI tools is M.

**Remaining caveat:** the 107 projects ChatGPT coded Y or N were not re-checked, except those in the spot check (ChatGPT's Y codes were all confirmed there).
