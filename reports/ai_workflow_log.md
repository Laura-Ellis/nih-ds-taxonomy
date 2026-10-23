# AI Workflow Log

How AI coding assistants and LLMs were used in this project, and how their output was checked.

| Date | Task | Tool | Prompt (short) | What it got wrong | How I validated |
|---|---|---|---|---|---|
| 2026-10-23 | Review 2024 term lists and draft v0.1 taxonomy | Claude | "Review my term lists against the NIH data science plan; software and tools on its own" | Proposed tool names (Hive, Pig, Spark) and generic terms (neuron, layer) that collide with biomedical words | Moved to dropped_terms.csv with reasons; acronym exclusions added; unit tests for AI/AN, GPT, neural network vs. neuroscience |
| 2026-10-23 | Write sample pull and review notebooks | Claude | "Stratified RePORTER sample with RCDC comparison" | pandas groupby.apply dropped the stratum column | Ran both notebooks end to end against a mocked API; fixed sampling |
| 2026-10-23 | Test v0.1 on 749 real projects and revise to v0.2 | Claude | "Review where categories fit or miss" | Proposed keeping "neural network" as strong; it matched biological networks in neuroscience abstracts | Read 10 keyword-only AI abstracts by hand; added exclusions and tests; documented the trade-off in sample_review_v0.2.md |
| 2026-10-23 | Compare labels with 150 hand-coded projects; revise to v0.3 | Claude | "See file taxonomy_review_coded" | First research software fix (weak "tool", "platform") over-fired: 14 labeled vs. 6 coded | Re-ran agreement after each change; kept only terms that improved it; results in hand_coding_review_v0.3.md |
| 2026-10-23 | Draft the 150-project review coding | ChatGPT (drafted); Claude (spot-check design) | "Code ds_related, ai_related, and categories per the Instructions sheet" | Coding drafted by an AI tool cannot serve as human validation on its own; notes repeat stock phrases | Blind human spot check of 30 projects, oversampling disagreements and mentions (taxonomy_spot_check.xlsx, notebooks/04_spot_check.py) |
| 2026-10-23 | Review Laura's 30 spot-check codes | Claude | "Push back on any you disagree with one by one" | Laura's first pass held AI = Y to "AI is central," stricter than the written rule | Claude quoted the abstract text for each of 14 proposed changes; Laura accepted all; changes flagged in the notes column, so the spot check is human coding revised with Claude input, not fully independent |
| 2026-10-23 | Recode the 13 remaining ChatGPT "M" projects | Claude | "Skip the step where I manually code and ask me questions" | n/a | Claude coded under the written rule with a reason per row; Laura decided 3 judgment calls (AI validation core, standard sequencing, MVPA); rules added to the Instructions sheet |

## Validation checklist

- [ ] Row counts match the source
- [ ] Spot-checked 10 records by hand
- [ ] Summary statistics recomputed independently
- [ ] Generated SQL or code reviewed line by line before use
- [ ] LLM labels compared with a hand-coded sample (report agreement, e.g. Cohen's kappa)
