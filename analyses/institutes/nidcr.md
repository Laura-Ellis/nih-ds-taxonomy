# Data science at the National Institute of Dental and Craniofacial Research (NIDCR)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIDCR funded 515 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 18% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 20% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.6 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIDCR](../../reports/figures/institutes/nidcr.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIDCR | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 38% | 50% |
| Parent or other PA | 50% | 42% |
| None listed | 11% | 8% |

| Activity group | NIDCR | Rest of NIH |
|---|---:|---:|
| R01-type | 37% | 30% |
| Other R | 23% | 15% |
| Cooperative (U) | 10% | 16% |
| Centers (P) | 1% | 17% |
| Training (K, F, T) | 19% | 14% |
| Other | 9% | 9% |

NIDCR is the main institute for 88 data science PIs. 12% had NIH projects before their first data science project. 49% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 44, FY2019–21 17, FY2022–25 25. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Reproductive and oral health (31%); Cancer biology and treatment (20%); Cell biology and development (17%); Musculoskeletal, pain, and rehabilitation (11%); Infectious disease (4%); Immunology and autoimmunity (3%).

Fastest-rising topics: Head and neck cancer and HPV (4.5×); Chronic pain (2.7×).

## Where it could do more

These research areas are where NIDCR puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIDCR applications.

| Area | NIDCR data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Human Genome | 33% | 51% | -18.5 |
| Dental, Oral, and Craniofacial Disease | 17% | 32% | -15.1 |
| Infectious Diseases | 13% | 25% | -12.5 |
| Neurosciences | 12% | 24% | -11.8 |
| Cancer | 15% | 26% | -10.9 |

Where it leads: Digestive Diseases (+5.1); Rare Diseases (+-0.4); Pediatric (+-3.7).

Kinds of data science NIDCR funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): community capacity (0.14); neuroscience (0.16); drug discovery (0.23); mental behavioral (0.23); cloud computing (0.36).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nidcr/`.

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
