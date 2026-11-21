# Data science at the National Institute on Deafness and Other Communication Disorders (NIDCD)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIDCD funded 666 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 22% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 25% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.5 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIDCD](../../reports/figures/institutes/nidcd.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIDCD | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 23% | 51% |
| Parent or other PA | 71% | 41% |
| None listed | 5% | 8% |

| Activity group | NIDCD | Rest of NIH |
|---|---:|---:|
| R01-type | 58% | 29% |
| Other R | 16% | 15% |
| Cooperative (U) | 2% | 16% |
| Centers (P) | 5% | 17% |
| Training (K, F, T) | 14% | 14% |
| Other | 6% | 9% |

NIDCD is the main institute for 90 data science PIs. 17% had NIH projects before their first data science project. 56% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 59, FY2019–21 19, FY2022–25 12. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Neurodevelopment, language, and communication (77%); Neuroscience (11%); Training and workforce (2%); Aging, dementia, and neurodegeneration (2%); Research cores, centers, and data resources (1%); Imaging (1%).

Fastest-rising topics: .

## Where it could do more

These research areas are where NIDCD puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIDCD applications.

| Area | NIDCD data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Minority Health | 20% | 30% | -9.3 |
| Mental Health | 22% | 29% | -6.9 |
| Genetics | 25% | 31% | -6.7 |
| Pediatric | 19% | 25% | -5.8 |
| Clinical Trials and Supportive Activities | 21% | 26% | -4.9 |

Where it leads: Neurodegenerative (+10.8); Hearing Loss (+10.1); Aging (+6.0).

Kinds of data science NIDCD funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): human data linkage (0.08); drug discovery (0.17); data engineering (0.19); community capacity (0.21); hpc compute (0.23).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nidcd/`.

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
