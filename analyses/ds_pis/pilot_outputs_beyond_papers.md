# Pilot: crediting software, models, and data to data science PIs

**Laura Ellis** · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · Status: planned (future work for [Who does data science at NIH?](pi_analysis.md))

The data science PI analysis shows that AI developers have 27% fewer linked papers than similar data science PIs. Papers are the only output it can count today. This pilot adds outputs that papers miss, datasets and software with persistent identifiers and data deposited at NCBI, and tests whether builders produce more of them than other data science PIs.

## Question

Do AI developer PIs and infrastructure builder PIs produce more datasets and software than matched data science PIs, and does counting those outputs close the paper gap?

## Why it matters

- The NIH Strategic Plan for Data Science, 2025 to 2030, commits NIH to "enhance programs providing credit and incentives for sharing data" (Objective 1-1), supports persistent identifiers through DataCite so researchers can "cite and reuse research outputs" (Objective 1-2), and tracks "citations of datasets deposited" (Goal 1) and "increased citation of NIH software" (Goal 3).
- NOT-OD-26-087 (June 18, 2026) asks how NIH should measure and reward data, software, and model sharing beyond publication and citation counts.
- If builders' non-paper outputs are large, the paper gap is a measurement gap, not a productivity gap.

## Groups

The same groups as the main analysis (definitions in [pi_analysis.md](pi_analysis.md)):

| Group | PIs |
|---|---|
| AI developer PIs | 334 |
| Infrastructure builder PIs | 2,943 |
| Matched data science PIs (comparison) | weighted to each group's portfolio size and first data science year |

## Sources, in pilot order

| Step | Output | Source | How it links to a PI | Notes |
|---|---|---|---|---|
| 1 | Datasets and software with DOIs | DataCite REST API (covers Zenodo, Figshare, Dryad, and most data and software repositories) | Funding reference with an NIH award number → project number → the project's PIs in RePORTER | Main source. Check how award numbers are written (full number, core number, with or without spaces and suffixes) |
| 1b | Same, cross-check | OpenAlex works of type dataset or software with NIH awards | Same | Coverage check only; outputs are not counted from OpenAlex |
| 2 | Data deposited at NCBI | NCBI BioProject (sequencing data in SRA, expression data in GEO) through E-utilities | Grant number on the BioProject record → project → PIs | Strong for omics data; weak for clinical and imaging data |
| Later | Software named in papers | Chan Zuckerberg Initiative software mentions dataset; tool papers in software journals | Paper → project → PIs | Shows software in use; needs a rule to separate "built" from "used" |
| Later | AI models | Hugging Face model cards and GitHub repositories that cite an NIH project number | Text match on project numbers | Sparse and experimental |
| Later | Registered resources | Research Resource Identifiers (RRIDs, SciCrunch registry), bio.tools | Funding listed on the registry entry | Good for tools and databases |

Query syntax for each API (field names, filters, rate limits) gets confirmed against current documentation in the first step; none is assumed here.

## Method

1. **Project list:** every project record for the PIs in the three groups, FY2016 to FY2026, as core project numbers (for example R01CA123456) from `exporter_applications.parquet`.
2. **Pull:** query DataCite and BioProject by core project number, cache raw responses in `data/interim/outputs_beyond_papers/` so reruns only fetch new projects, and log projects with no match.
3. **Normalize:** parse award numbers into core project numbers; drop records that only name NIH with no award number; keep one row per DOI or BioProject.
4. **Classify:** dataset, software, model (DataCite resource type and keywords), or NCBI data deposit.
5. **Attribute to PIs:** each output counts for every PI on the linked project, the same way papers do. A contact-PI-only count is reported as a check.
6. **Compare:** median outputs per PI and share of PIs with at least one output, for each builder group vs. matched data science PIs; then papers plus outputs combined, to see whether the gap closes.
7. **Check coverage:** for a sample of 50 builder PIs, look up their repositories by hand (GitHub, Zenodo, institutional pages) and record what the pilot found vs. missed.

## Definitions

- Output with a persistent identifier: a dataset, software release, or model with a DOI registered at DataCite.
- NCBI data deposit: a BioProject that lists an NIH award number.
- Outputs per PI: distinct DOIs and BioProjects linked to any of the PI's projects, FY2016 to FY2026.
- Coverage rate: share of hand-checked outputs that the pilot found.

## Outputs

- `analyses/ds_pis/outputs_beyond_papers.py` (pilot script, run on Laura's machine; the APIs aren't reachable from the cloud workspace)
- `reports/results/ds_pis_outputs_by_group.csv` (aggregate; groups under 11 PIs suppressed)
- A chart for the main page: papers and non-paper outputs side by side for each builder group vs. matched data science PIs
- A short section added to [pi_analysis.md](pi_analysis.md) and a slide in the data science PI deck

## Limits to state up front

- Award numbers are missing from many DOIs and BioProjects, so counts are a floor, not a total. The coverage check estimates how much is missing.
- Outputs link to projects, not people; a PI on a large center gets credit for the center's outputs.
- DataCite resource types are self-reported and sometimes wrong; spot-check the classification.
- A DOI is not a measure of use. Citation and download counts (DataCite event data, Make Data Count) are a possible second step.

## Effort and decisions

- Estimate: about a day to build and run steps 1 and 2, plus a few hours for the coverage check.
- Decided (October 25, 2026): OpenAlex is a cross-check only: it measures how much DataCite misses, and outputs are still counted from DataCite and NCBI so nothing is counted twice. Outputs count for every PI on the linked project, the same way papers do, so papers and outputs compare directly; a contact-PI-only count is reported as a check.
