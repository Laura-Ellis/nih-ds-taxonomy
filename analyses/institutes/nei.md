# Data science at the National Eye Institute (NEI)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NEI funded 954 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 19% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 21% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.3 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NEI](../../reports/figures/institutes/nei.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NEI | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 29% | 51% |
| Parent or other PA | 62% | 41% |
| None listed | 9% | 8% |

| Activity group | NEI | Rest of NIH |
|---|---:|---:|
| R01-type | 47% | 29% |
| Other R | 10% | 15% |
| Cooperative (U) | 3% | 16% |
| Centers (P) | 16% | 17% |
| Training (K, F, T) | 15% | 14% |
| Other | 9% | 9% |

NEI is the main institute for 113 data science PIs. 18% had NIH projects before their first data science project. 36% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 55, FY2019–21 39, FY2022–25 16. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Eye and vision (65%); Neuroscience (23%); Musculoskeletal, pain, and rehabilitation (3%); Imaging (2%); Research cores, centers, and data resources (2%); Neurodevelopment, language, and communication (1%).

Fastest-rising topics: Retina and glaucoma (1.1×); Rehabilitation, gait, and wearables (1.0×).

## Where it could do more

These research areas are where NEI puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NEI applications.

| Area | NEI data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Macular Degeneration | 16% | 59% | -43.3 |
| Eye Disease and Disorders of Vision | 19% | 40% | -21.4 |
| Clinical Trials and Supportive Activities | 13% | 26% | -13.3 |
| Diabetes | 9% | 20% | -11.5 |
| Brain Disorders | 16% | 25% | -9.0 |

Where it leads: Basic Behavioral and Social Science (+6.3); Behavioral and Social Science (+6.1); Biomedical Imaging (+1.0).

Kinds of data science NEI funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): human data linkage (0.22); fair data (0.39); drug discovery (0.40); data engineering (0.42); population health (0.43).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nei/`.

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
