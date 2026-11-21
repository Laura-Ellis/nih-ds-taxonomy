# Data science at the National Institute on Alcohol Abuse and Alcoholism (NIAAA)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIAAA funded 582 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 17% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 22% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.4 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIAAA](../../reports/figures/institutes/niaaa.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIAAA | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 43% | 50% |
| Parent or other PA | 52% | 42% |
| None listed | 5% | 8% |

| Activity group | NIAAA | Rest of NIH |
|---|---:|---:|
| R01-type | 26% | 30% |
| Other R | 11% | 15% |
| Cooperative (U) | 18% | 16% |
| Centers (P) | 18% | 17% |
| Training (K, F, T) | 22% | 14% |
| Other | 5% | 9% |

NIAAA is the main institute for 67 data science PIs. 19% had NIH projects before their first data science project. 52% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 38, FY2019–21 18, FY2022–25 11. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Mental health and substance use (64%); Heart, lung, kidney, and liver (13%); HIV (10%); Research cores, centers, and data resources (4%); Clinical care and population health (3%); Training and workforce (1%).

Fastest-rising topics: Liver disease (1.6×); HIV prevention and care (1.4×).

## Where it could do more

These research areas are where NIAAA puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIAAA applications.

| Area | NIAAA data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Fetal Alcohol Spectrum Disorders (FASD) | 8% | 46% | -37.9 |
| Alcoholism, Alcohol Use and Health | 20% | 49% | -29.4 |
| Conditions Affecting the Embryonic and Fetal Periods | 8% | 36% | -27.3 |
| Intellectual and Developmental Disabilities (IDD) | 8% | 26% | -17.6 |
| Perinatal Period - Conditions Originating in Perinatal Period | 8% | 23% | -14.6 |

Where it leads: Underage Drinking - Prevention & Treatment (NIAAA Only) (+19.0); Liver Disease (+9.1); Underage Drinking (+9.0).

Kinds of data science NIAAA funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): computer vision (0.11); community capacity (0.23); fair data (0.23); cloud computing (0.45); data visualization (0.51).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/niaaa/`.

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
