# Data science at the National Institute of Biomedical Imaging and Bioengineering (NIBIB)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIBIB funded 1,263 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 38% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 43% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.4 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIBIB](../../reports/figures/institutes/nibib.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIBIB | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 47% | 50% |
| Parent or other PA | 50% | 42% |
| None listed | 3% | 8% |

| Activity group | NIBIB | Rest of NIH |
|---|---:|---:|
| R01-type | 43% | 29% |
| Other R | 18% | 15% |
| Cooperative (U) | 9% | 16% |
| Centers (P) | 16% | 17% |
| Training (K, F, T) | 9% | 14% |
| Other | 4% | 9% |

NIBIB is the main institute for 215 data science PIs. 11% had NIH projects before their first data science project. 75% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 115, FY2019–21 65, FY2022–25 32. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Imaging (35%); Neuroscience (14%); Clinical care and population health (8%); Musculoskeletal, pain, and rehabilitation (7%); Training and workforce (7%); Heart, lung, kidney, and liver (5%).

Fastest-rising topics: Radiation and medical image reconstruction (1.7×); Rehabilitation, gait, and wearables (1.6×); Microscopy and optical imaging (1.5×); Clinical care and EHR (1.2×); Cancer imaging (PET and MRI) (1.1×); Brain tumor imaging (1.0×).

## Where it could do more

These research areas are where NIBIB puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIBIB applications.

| Area | NIBIB data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Genetics | 26% | 31% | -4.8 |

Where it leads: Cardiovascular (+19.6); Neurosciences (+18.9); Brain Disorders (+16.4).

Kinds of data science NIBIB funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): human data linkage (0.16); omics (0.24); drug discovery (0.24); data platforms (0.26); population health (0.33).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nibib/`.

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
