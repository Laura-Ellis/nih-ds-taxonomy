# Pilot: crediting software, models, and data to data science PIs

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · Status: planned (future work for [Who does data science at NIH?](pi_analysis.md))

AI developers have 27% fewer linked papers than similar data science PIs. Papers are the only output the PI analysis can count today. This pilot adds outputs that papers miss: datasets and software with permanent identifiers (DOIs), and data deposited at NCBI. It tests whether builders produce more of them, and whether counting them closes the paper gap.

Terms are defined in the [glossary](#glossary) at the end.

## Question

Do AI developers and infrastructure builders produce more datasets and software than similar data science PIs? If we count those outputs, does the paper gap close?

## Why it matters

- The NIH Strategic Plan for Data Science, 2025 to 2030, commits NIH to credit data sharing, to support identifiers that let researchers cite datasets and software, and to track how often NIH datasets and software are cited.
- In June 2026, NIH asked how it should measure and reward data, software, and model sharing beyond publication and citation counts (NOT-OD-26-087).
- If builders produce many outputs that aren't papers, the paper gap is a measurement gap, not a productivity gap.

## Groups

The same groups as the main analysis (definitions in [pi_analysis.md](pi_analysis.md)):

| Group | PIs |
|---|---|
| AI developer PIs | 334 |
| Infrastructure builder PIs | 2,943 |
| Similar data science PIs (comparison) | Weighted to each group's number of projects and first data science year |

## Sources, in order

| Step | Output | Source | How it links to a PI |
|---|---|---|---|
| 1 | Datasets and software with DOIs | DataCite, which covers Zenodo, Figshare, Dryad, and most data and software repositories | NIH award number → project → the project's PIs |
| 1b | Same, as a check | OpenAlex datasets and software with NIH awards | Same; used to measure what DataCite misses, not counted |
| 2 | Data deposited at NCBI | NCBI BioProject (sequencing and gene expression data) | Grant number on the record → project → PIs |
| Later | Software named in papers | Chan Zuckerberg Initiative software mentions; tool papers in software journals | Paper → project → PIs |
| Later | AI models | Hugging Face and GitHub pages that cite an NIH project number | Project number in the text |
| Later | Registered tools and databases | Research Resource Identifiers (RRIDs), bio.tools | Funding listed on the entry |

## Method

1. **List projects:** every project for the PIs in the three groups, FY2016 to FY2026.
2. **Pull outputs:** search DataCite and BioProject by project number. Save the raw results so reruns only fetch new projects. Log projects with no match.
3. **Clean:** read award numbers into project numbers; drop records that name NIH but no award; keep one row per DOI or BioProject.
4. **Sort by type:** dataset, software, model, or NCBI data deposit.
5. **Credit PIs:** each output counts for every PI on the linked project, the same way papers do. A count for the contact PI only is a check.
6. **Compare:** outputs per PI, and the share of PIs with at least one output, for each builder group vs. similar data science PIs. Then papers and outputs together, to see whether the gap closes.
7. **Check coverage:** for 50 builder PIs, look up their repositories by hand (GitHub, Zenodo, lab pages) and record what the pilot found and missed.

## Outputs

- `analyses/ds_pis/outputs_beyond_papers.py`, the pilot script
- `reports/results/ds_pis_outputs_by_group.csv`, aggregate results (groups under 11 PIs suppressed)
- A chart of papers and other outputs side by side for each builder group
- A new section in [pi_analysis.md](pi_analysis.md) and a slide in the PI deck

## Limits

- Many DOIs and BioProjects don't list an award number, so counts are a floor, not a total. The coverage check estimates how much is missing.
- Outputs link to projects, not people. A PI on a large center gets credit for the center's outputs.
- Repositories label their own resource types, and some are wrong; spot-check them.
- A DOI shows that something was shared, not that it was used. Citation and download counts are a possible second step.

## Decisions

- About a day to build and run steps 1 and 2, plus a few hours for the coverage check.
- OpenAlex is a check only. Outputs are counted from DataCite and NCBI, so nothing is counted twice.
- Outputs count for every PI on a project, the same way papers do, so papers and outputs compare directly.

## Glossary

| Term | Meaning |
|---|---|
| AI developer PI | A data science PI whose projects mostly build new or better AI methods |
| BioProject | NCBI's record of a research data deposit, such as sequencing data |
| DataCite | The main registry for DOIs on datasets and software |
| DOI | Digital object identifier: a permanent link that lets others cite a dataset, software release, or paper |
| Infrastructure builder PI | A data science PI whose projects mostly build software, platforms, or data resources |
| NCBI | The National Center for Biotechnology Information, which hosts NIH's biological data repositories |
| PI | Principal investigator: a person who leads an NIH-funded project |
