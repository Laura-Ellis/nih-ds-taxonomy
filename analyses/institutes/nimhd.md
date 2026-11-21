# Data science at the National Institute on Minority Health and Health Disparities (NIMHD)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIMHD funded 526 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 23% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 27% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.7 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIMHD](../../reports/figures/institutes/nimhd.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIMHD | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 64% | 50% |
| Parent or other PA | 31% | 42% |
| None listed | 6% | 8% |

| Activity group | NIMHD | Rest of NIH |
|---|---:|---:|
| R01-type | 26% | 30% |
| Other R | 15% | 15% |
| Cooperative (U) | 33% | 15% |
| Centers (P) | 7% | 17% |
| Training (K, F, T) | 11% | 14% |
| Other | 8% | 9% |

NIMHD is the main institute for 72 data science PIs. 12% had NIH projects before their first data science project. 67% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 23, FY2019–21 22, FY2022–25 27. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Clinical care and population health (35%); Training and workforce (21%); Mental health and substance use (10%); Cancer screening and risk (6%); Environmental health (5%); Infectious disease (4%).

Fastest-rising topics: Clinical care and EHR (2.5×); Diabetes, obesity, and nutrition (2.4×).

## Where it could do more

These research areas are where NIMHD puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIMHD applications.

| Area | NIMHD data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Health Services | 19% | 43% | -23.9 |
| Mental Health | 10% | 29% | -18.6 |
| Clinical Trials and Supportive Activities | 11% | 26% | -14.9 |
| Translational Research | 16% | 26% | -10.7 |
| Pediatric | 15% | 25% | -10.4 |

Where it leads: Infectious Diseases (+1.7); Basic Behavioral and Social Science (+-0.9); Nutrition (+-1.7).

Kinds of data science NIMHD funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): deep learning (0.19); neuroscience (0.23); computer vision (0.24); medical imaging (0.26); data management sharing (0.49).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nimhd/`.

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
