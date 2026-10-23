# AI Workflow Log

How AI coding assistants and LLMs were used in this project, and how their output was checked.

| Date | Task | Tool | Prompt (short) | What it got wrong | How I validated |
|---|---|---|---|---|---|
| 2026-10-23 | Review 2024 term lists and draft v0.1 taxonomy | Claude | "Review my term lists against the NIH data science plan; software and tools on its own" | Proposed tool names (Hive, Pig, Spark) and generic terms (neuron, layer) that collide with biomedical words | Moved to dropped_terms.csv with reasons; acronym exclusions added; unit tests for AI/AN, GPT, neural network vs. neuroscience |
| 2026-10-23 | Write sample pull and review notebooks | Claude | "Stratified RePORTER sample with RCDC comparison" | pandas groupby.apply dropped the stratum column | Ran both notebooks end to end against a mocked API; fixed sampling |

## Validation checklist

- [ ] Row counts match the source
- [ ] Spot-checked 10 records by hand
- [ ] Summary statistics recomputed independently
- [ ] Generated SQL or code reviewed line by line before use
- [ ] LLM labels compared with a hand-coded sample (report agreement, e.g. Cohen's kappa)
