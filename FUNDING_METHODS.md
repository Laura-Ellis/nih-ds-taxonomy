# Appendix: How funding is calculated

**Author:** Laura Ellis · **GitHub:** [github.com/Laura-Ellis/nih-ds-taxonomy](https://github.com/Laura-Ellis/nih-ds-taxonomy) · **Applies to:** every table, chart, and figure in this project that reports dollars

All dollar amounts are NIH extramural funding, in nominal dollars, by federal fiscal year, with each center's money counted once. The rest of this page explains each of those choices.

## Source

Funding comes from the NIH RePORTER API (`award_amount`), the total cost (direct plus indirect costs) NIH obligated to an award in a fiscal year. Each fiscal year runs from October 1 to September 30; FY2025 is October 1, 2024, to September 30, 2025.

## What is included

| Included | Not included |
|---|---|
| Extramural awards: research projects, cooperative agreements, centers, training, fellowships, career awards, contracts, and other transactions | Intramural research (activity codes starting with Z) |
| Projects administered by an NIH institute, center, or the Office of the Director | Projects from other agencies listed in RePORTER (CDC, AHRQ, FDA, NIOSH, VA) |
| Projects currently in RePORTER | Records NIH has since removed from RePORTER |

**Why intramural is excluded:** intramural annual reports describe whole lab programs, not individual awards. One of them, NCBI operations, is about $340 million a year and would make up about 13% of all AI funding on its own.

## Centers and other multi-component projects counted once

A **subproject** is one component of a larger multi-component award, such as a research project, core facility, or pilot program inside a center. NIH lists each subproject separately in RePORTER, under the parent award's project number with its own subproject ID and cost, but funds it through the parent award.

Centers and program projects (for example, P30, P50, and U54) list a parent award and its components (subprojects). The parent's total already includes the components' costs, so adding both counts the money twice. Each record gets an **attributed cost** instead:

- Component: its own listed cost.
- Parent: the parent total minus its components' costs in that fiscal year (the parent's own share, such as an administrative core).

Parent attributed cost = max(0, parent total − sum of component costs)

Attributed costs add up to the award total. When components' costs exceed the parent total, the parent's share is set to $0.

## How amounts are assigned

Every award has one **administering IC**, which manages it (its code is in the project number, such as AI in R01AI…), and one or more **funding ICs**, which pay for it. Usually they are the same. In FY2021–FY2025, 8.3% of extramural dollars came from an IC other than the administering one, mostly the Office of the Director (OD), including Common Fund programs such as Bridge2AI.

Results by IC use the **administering IC**: each award's full dollars go to the institute that manages it. A separate analysis (`notebooks/14_funding_ic_relationships.py`) splits dollars by funding IC, each IC's share in proportion to what it paid, and says so where it is shown. NIH-wide totals are the same either way.

| Question | Rule |
|---|---|
| Which institute gets the money? | The administering IC gets the full amount, even when other ICs co-fund the project. Project counts use the administering IC too, so each project counts once. |
| Which year? | The fiscal year of the award, not the project's start year. A 5-year project contributes to each year it is funded. |
| Data science and AI | A project's full attributed cost counts when its data science or AI work is substantive (in an aim or the stated approach). Costs are not split by aim. |
| Groups, categories, and RCDC categories | A project can be in several, and its full cost counts in each. Totals across groups or categories add up to more than the overall total. |
| Shares | Share of funding = data science (or AI, or a group) funding ÷ all NIH extramural funding in the same year (and the same IC, in institute tables). |

## Reading the numbers

- Nominal dollars. Amounts are not adjusted for inflation, so growth over time includes rising research costs.
- Not NIH's official RCDC totals. NIH reports spending by RCDC (Research, Condition, and Disease Categorization) category using its own rules. Here, RCDC categories are a way to filter projects, and dollars follow the rules above, so they will not match NIH's published RCDC tables.
- Data science is not the same as data science spending. A project with substantive data science counts in full, including its lab, clinical, and other costs.
- FY2026 is preliminary. RePORTER keeps adding FY2026 projects for months after September 30, so FY2026 totals are incomplete and labeled *preliminary, as of* the pull date.
- Rounding. Amounts are rounded for display ($1.2B, $340M), so totals may differ slightly from the sum of their parts.

*Code: `src/reporter_api.py` (source fields), `notebooks/08_classify_exporter.py` (attributed cost), `notebooks/11_results.py` and `notebooks/13_ds_groups.py` (totals and shares), `src/funding.py` (funding IC split, separate analysis only).*
