# Classifying NIH projects: keywords, Claude, and Jev

**Date:** 2026-10-23 · **Taxonomy:** v0.4 · **Reproduce:** `notebooks/05_llm_labels.py`, `notebooks/06_term_review.py`

## Bottom line

Jev plus Claude for uncertain cases matches Claude's accuracy at a fraction of the cost. Jev labels every keyword-flagged project for about $0.14 per 1,000; the 11% of AI calls where Jev is less than 90% confident go to Claude. On the coded sample, this hybrid equals Claude alone (AI κ = 0.94) and cuts the Claude workload by 89%. Keywords still find the candidates, since they cost nothing and miss almost no AI projects (recall 98–100%).

## Results

Substantive = the project uses or builds the method in an aim or its approach, not only mentions it.

| Method | AI precision | AI recall | AI κ | DS precision | DS recall | DS κ | Cost per 1,000 projects |
|---|---|---|---|---|---|---|---|
| Keywords, any match | 79% | 100% | 0.83 | 79% | 94% | 0.77 | $0 |
| Keywords, evidence rule | 88% | 90% | 0.85 | 83% | 85% | 0.75 | $0 |
| Claude Sonnet 5.5 | 91% | 100% | 0.94 | 85% | 96% | 0.84 | ~$6 (~$3 with Batch API) |
| Jev 1.14.0 (Typesafe) | 88% | 100% | 0.90 | 75% | 98% | 0.75 | ~$0.14 |
| **Jev, Claude when Jev confidence < 0.90** | **91%** | **100%** | **0.94** | **85%** | **96%** | **0.84** | **~$0.80 (AI); ~$2.40 (DS)** |
| *RCDC "Machine Learning and AI" (NIH)* | *92%* | *86%* | *0.85* | | | | *n/a* |

Reference: 150 coded projects (42 substantive AI, 52 substantive data science). Jev cost $0.02 for all 150 (about 3,300 input tokens each). Hybrid cost assumes Claude on 11% of projects for AI and 38% for data science, the shares below the confidence cutoff. With these sample sizes, each percentage carries a 95% confidence interval of about ±10 points.

On the full 747-project sample, with Claude as the reference, keywords reach 85% precision and 98% recall for AI; the evidence rule reaches 92% and 89%.

## Methods

**Keywords.** The term list (private; sample in `taxonomy/terms_sample.csv`) held 706 terms in 36 categories for this comparison (755 since October 25, 2026). A category applies when the title and abstract contain 1 strong term or 2 weak terms, after exclusions (for example, "neural network" near "neuron" or "synapse"). The **evidence rule** keeps a category only when its terms appear at least twice, or one appears within 150 characters of an action phrase ("we will", "aim", "develop a", "to predict").

**Claude.** One API call per project returns typed labels: data science and AI (Y, M, or N), AI role, categories, and an evidence quote. The prompt carries the same coding rules as the validation set. Results are cached by project, model, and prompt version.

**Jev.** Jev (`typesafe-ai/jev-1.14.0`, through the Vercel AI Gateway) answers typed questions about a text and returns a probability for each answer. Each project is one request with 39 questions: data science and AI (Y, M, or N, with the same rules), AI role, and a yes/no probability for each category. List price is $0.042 per million input tokens; output is free. The adoption bar was κ ≥ 0.90 on substantive AI; Jev reached 0.90 alone and agreed with Claude at κ = 0.93.

**Confidence.** Jev was right on 99% of AI calls made with at least 90% confidence (134 of 150) and on 75% of the rest (16). For data science the split is 94% and 79%, with more uncertain calls (57). Sending only the uncertain calls to Claude recovers Claude's accuracy.

**Validation set.** We stratified 749 RePORTER projects (FY2019, FY2022, and FY2025) and coded 150 of them. An AI tool drafted the coding; a 30-project blind spot check and a recode of all "mention only" projects corrected it under written rules.

**Measures**
- Precision = flagged and coded substantive / flagged
- Recall = flagged and coded substantive / coded substantive
- Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement)
- Wilson 95% CI for a share p of n projects: (p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n), z = 1.96

## How the pieces fit

1. **Tune terms with Claude.** On the 747-project sample, Claude flags terms that rarely mean what their category says. For example, "big data" and "validation" were almost never confirmed, and "AI" alone is usually filed under machine learning. Details: `reports/term_review_v0.4.csv`.
2. **Classify everything with keywords.** ExPORTER, FY2015–2026, at no cost (`nih-ds-kpis`).
3. **Calibrate with samples.** About 50 keyword-flagged projects per fiscal year. Substantive AI estimate = keyword count × sample precision. Precision differs by population: 87% for AI-focused projects and 56% for general research projects (n = 16), so the factor must come from samples that match the population being counted.
4. **Label flagged projects with Jev, uncertain ones with Claude.** Per-project labels become affordable at full scale, so the correction factor becomes a check instead of the main estimate.

## Limits

- Claude declined one abstract on influenza virus reassortment (a safety refusal); Jev labeled it. Pipelines should log refusals and fall back to another model.
- Jev's data science calls are weaker than its AI calls (κ = 0.75); categories need a separate check before relying on Jev's category probabilities.

- One coder reviewed the validation set; there is no second coder to measure agreement between people.
- On the 747-project sample, Claude serves as the reference, so any shared blind spots of Claude and the coding stay hidden.
- Category recall against Claude is low for broad methods (statistical methods, data exploration), because Claude assigns them to most data projects. Those categories need a narrower definition, not more terms.
