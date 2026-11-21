# Data science at the National Institute of Mental Health (NIMH)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIMH funded 2,978 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 29% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 35% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.5 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIMH](../../reports/figures/institutes/nimh.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIMH | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 38% | 51% |
| Parent or other PA | 56% | 41% |
| None listed | 6% | 8% |

| Activity group | NIMH | Rest of NIH |
|---|---:|---:|
| R01-type | 44% | 29% |
| Other R | 15% | 15% |
| Cooperative (U) | 7% | 16% |
| Centers (P) | 8% | 17% |
| Training (K, F, T) | 20% | 14% |
| Other | 6% | 9% |

NIMH is the main institute for 536 data science PIs. 13% had NIH projects before their first data science project. 58% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 302, FY2019–21 150, FY2022–25 82. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Mental health and substance use (43%); Neuroscience (25%); Neurodevelopment, language, and communication (14%); HIV (7%); Training and workforce (3%); Clinical care and population health (2%).

Fastest-rising topics: Suicide prevention (2.5×); Mental health care and interventions (1.7×); Memory and sensory neuroscience (1.4×); Anxiety and depression (1.3×); Child brain development (1.3×); Deep brain stimulation and Parkinson's (1.3×).

## Where it could do more

These research areas are where NIMH puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIMH applications.

| Area | NIMH data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Pediatric - AIDS | 10% | 38% | -27.5 |
| Women's Health Research | 15% | 26% | -10.4 |
| Health Services | 33% | 43% | -9.9 |
| Comparative Effectiveness Research | 17% | 26% | -9.6 |
| Dissemination and Implementation Research | 19% | 28% | -9.4 |

Where it leads: Bipolar Disorder (+37.6); Serious Mental Illness (+19.5); Stem Cell Research (+19.3).

Kinds of data science NIMH funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): drug discovery (0.32); data management sharing (0.53); omics (0.53); fair data (0.54); data science general (0.56).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nimh/`.

**Source:** NIH RePORTER API and ExPORTER, FY2016 to FY2025; NIH Data Science Taxonomy.

## Glossary

| Term | Meaning |
|---|---|
| Activity group | The kind of award: R01-type research grants, other R grants, cooperative agreements (U), centers (P), training (K, F, T) |
| Administering institute | The NIH institute or center that manages a project |
| Data science project | An NIH project whose aims or approach rely on data science, per the NIH Data Science Taxonomy |
| Data science PI | A PI with 2 or more project records, more than half with substantive data science |
| Growth | Data science share in FY2023–25 ÷ share in FY2016–18 |
| NOFO | Notice of funding opportunity. RFA and PAR = targeted calls for an area; PA = broad, such as the parent R01 |
| PI | Principal investigator: a person who leads an NIH-funded project |
| RCDC | NIH's research, condition, and disease categories, used to tag every project |
| Rest of NIH | Every other NIH institute and center |
