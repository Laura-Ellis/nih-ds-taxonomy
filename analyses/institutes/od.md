# Data science at the NIH Office of the Director (OD)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

OD funded 759 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 30% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 53% of its dollars, compared with 28% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.7 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at OD](../../reports/figures/institutes/od.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | OD | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 65% | 50% |
| Parent or other PA | 12% | 42% |
| None listed | 23% | 8% |

| Activity group | OD | Rest of NIH |
|---|---:|---:|
| R01-type | 2% | 30% |
| Other R | 15% | 15% |
| Cooperative (U) | 22% | 15% |
| Centers (P) | 11% | 17% |
| Training (K, F, T) | 4% | 14% |
| Other | 46% | 8% |

OD is the main institute for 137 data science PIs. 12% had NIH projects before their first data science project. 80% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 65, FY2019–21 26, FY2022–25 46. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Research cores, centers, and data resources (25%); Genomics and gene regulation (21%); Training and workforce (9%); Environmental health (6%); Infectious disease (4%); Imaging (4%).

Fastest-rising topics: Metabolomics and proteomics (4.3×); Data management and coordinating centers (1.6×); Mouse phenotyping resources (1.1×); Genomics and sequencing cores (1.1×).

## Where it could do more

These research areas are where OD puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 OD applications.

| Area | OD data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Biomedical Imaging | 22% | 36% | -13.5 |
| HIV/AIDS | 19% | 25% | -5.6 |
| Infectious Diseases | 25% | 25% | -0.1 |

Where it leads: Genetics (+31.5); Human Genome (+27.1); Clinical Research (+22.9).

Kinds of data science OD funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): statistical methods (0.24); training education (0.48); computational modeling (0.49); nlp (0.57); sensors wearables (0.62).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/od/`.

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
