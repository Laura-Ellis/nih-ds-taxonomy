# NIH Data Science Taxonomy

A taxonomy for classifying NIH-funded projects by the data science methods they use (statistics and analytics, computational modeling, and AI), the software and infrastructure they build, how they manage data and use AI responsibly, the workforce they train, and the biomedical area they apply it to.

**Status:** draft v0.1.0. Categories are being tested on a sample of NIH projects; terms will change.

**Portfolio page:** https://laura-ellis.github.io/skills/nlp-llms.html

## Question

Where does data science show up across NIH projects, how much of it is AI, and which parts of NIH's data science strategy do those projects support?

## Structure

Eight dimensions and 39 categories: seven assigned by keywords (35 categories) and one assigned by LLM review (role of AI, 4 categories). A project can have several categories. Definitions are in [`taxonomy/categories.yaml`](taxonomy/categories.yaml); terms are in [`taxonomy/terms.csv`](taxonomy/terms.csv).

| Dimension | Categories | Aligns with |
|---|---|---|
| Data science methods: statistics and analytics | Statistical methods development · Data preparation and exploration · Data visualization · Network and graph analysis | Strategic Plan Goal 3 |
| Data science methods: computational modeling | Computational and simulation modeling (including digital twins) | Strategic Plan Goal 3 |
| Data science methods: artificial intelligence | Machine learning · Deep learning · NLP · Computer vision · Generative AI and LLMs · Other AI | Strategic Plan Goal 3 |
| Software and tools | Research software development · ML frameworks · Analysis and workflow platforms · Visualization tools | Strategic Plan Goal 3 |
| Data infrastructure and computing | Cloud computing · High-performance computing · Data platforms and repositories · Data engineering | Strategic Plan Goal 4 |
| Data management and sharing | FAIR data and standards · Data management and sharing · Human-derived data access and linkage | Strategic Plan Goals 1 and 2 |
| Responsible AI | Fairness and bias · Privacy and security · Transparency and reproducibility | AI Strategy RFI: Reproducibility and Trust |
| Workforce and training | Training and education · Community and capacity building | Strategic Plan Goal 5 |
| Biomedical application area | Medical imaging · Omics · Clinical care and EHR · Drug discovery · Population health · Mental and behavioral health · Neuroscience · Sensors and wearables | Context for the above |

An eighth dimension, **role of AI** (develops, applies, studies, or supports AI), is assigned by LLM review rather than keywords.

**Abbreviations:** NLP = natural language processing; LLM = large language model; EHR = electronic health record; FAIR = findable, accessible, interoperable, reusable; RCDC = Research, Condition, and Disease Categorization; IC = NIH Institute or Center.

## How labels are assigned

Keyword baseline (`src/taxonomy.py`):

- Text = project title + abstract
- A category is assigned when the text has **at least 1 strong term or at least 2 distinct weak terms** from it
- Strong terms are specific on their own ("convolutional neural network"); weak terms are common in other contexts ("classification", "bias") and need a second term
- Acronyms are case-sensitive; some have exclusions (for example, "AI" next to "AI/AN" or "American Indian" is ignored, and "GPT" near "transaminase" is ignored)
- Routine statistics (t-tests, regression, p-values) do not count; statistical methods count when the project develops or uses advanced methods
- Application areas count only when the project has a methods, software, infrastructure, or data sharing label, since nearly every NIH project has a biomedical area
- Two summary flags: `data_science_related` (any methods, software, infrastructure, or data sharing label) and `ai_related` (any method in the artificial intelligence group)

The keyword baseline is the comparison point for LLM labeling, and both are checked against a hand-coded sample and the RCDC category "Machine Learning and Artificial Intelligence."

## Testing on NIH projects

1. `notebooks/01_pull_sample.py` pulls about 750 projects from the NIH RePORTER API for FY2019, FY2022, and FY2025, in three strata: AI search hits, random research projects, and training projects.
2. `notebooks/02_review_sample.py` labels them, compares with RCDC, charts how often each category fires, and exports `reports/taxonomy_review_sample.xlsx` for hand-coding 150 projects.

Agreement measures:

- Precision = projects both keyword and RCDC flag as AI / projects the keywords flag as AI
- Recall = projects both flag as AI / projects RCDC flags as AI
- Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement), for keyword or LLM labels vs. hand coding

## Changes from the 2024 term lists

This revises the term lists in [Laura-Ellis/NIH](https://github.com/Laura-Ellis/NIH) (`01 Term lists.ipynb`): 16 lists and 415 terms. 238 terms were kept and assigned to categories; 177 were dropped with a reason in [`taxonomy/dropped_terms.csv`](taxonomy/dropped_terms.csv). The revised taxonomy has 684 terms. Main changes:

- Lists organized into dimensions that follow the NIH Strategic Plan for Data Science, 2025–2030
- Software and tools separated into its own dimension
- Methods grouped into statistics and analytics, computational modeling, and AI, with data science as the umbrella
- New categories: network analysis, computational modeling, NLP, computer vision, human-derived data linkage, workforce, and application areas
- Routine statistics terms (t-test, p-value, regression) dropped, since they appear in most NIH projects; advanced methods kept as statistical methods development
- Two terms merged by missing commas fixed ("ETL" and "Extract, Transform, Load"; "generative adversarial network" and "GAN")
- Each term given a strength, match type, and exclusions

## Quick start

```bash
python tasks.py create-venv
# Windows (PowerShell)
.venv\Scripts\Activate
# macOS / Linux
source .venv/bin/activate
python tasks.py install
python -m pytest tests
```

## Repo structure

```
taxonomy/categories.yaml   dimensions, categories, definitions, labeling rule
taxonomy/terms.csv         terms with category, match type, strength, exclusions
taxonomy/dropped_terms.csv 2024 terms not carried over, with reasons
src/taxonomy.py            keyword labeler
notebooks/                 sample pull and review (.py files with notebook cells)
tests/                     checks on the labeler and taxonomy files
data/                      sources and data dictionary
reports/                   AI workflow log, charts, review workbook
```

## Related work

- Le et al. (2026). [NIH-funded artificial intelligence and machine learning research, 2019–2023: cross-sectional study](https://www.jmir.org/2026/1/e84861). *JMIR* 28:e84861. Uses the RCDC category alone.

## License and citation

Code: MIT ([`LICENSE`](LICENSE)). Taxonomy files (`taxonomy/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Data: NIH RePORTER terms of use ([`data/DATA_SOURCES.md`](data/DATA_SOURCES.md)). To cite: [`CITATION.cff`](CITATION.cff).
