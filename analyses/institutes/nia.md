# Data science at the National Institute on Aging (NIA)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NIA funded 4,019 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 24% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 28% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.5 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIA](../../reports/figures/institutes/nia.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NIA | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 60% | 49% |
| Parent or other PA | 35% | 43% |
| None listed | 5% | 8% |

| Activity group | NIA | Rest of NIH |
|---|---:|---:|
| R01-type | 28% | 30% |
| Other R | 14% | 15% |
| Cooperative (U) | 16% | 16% |
| Centers (P) | 24% | 16% |
| Training (K, F, T) | 12% | 15% |
| Other | 5% | 9% |

### Linking projects to calls

Every grant record names the funding call it answered. For projects that name only a broad call, a ranking model found the targeted call each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-call)). Weak fit = no targeted call comes close, so that data science came in without a call that asked for it. Shares of data science projects.

| Call on the grant record | NIA | All NIH |
|---|---:|---:|
| Targeted call on record | 62% | 53% |
| Broad call, strong fit | 5% | 4% |
| Broad call, weak fit | 31% | 37% |
| No funding call (intramural, VA, contract) | 2% | 5% |

Targeted calls its broad-call projects fit best (strong fits, 11 or more projects): PAR-15-359 (Novel Approaches to Diagnosing Alzheimer's Disease & Predicting Progression (R01, 19); PAR-18-588 (Assistive Technology for Persons with Alzheimer's Disease and Related Dementias , 15); PAR-18-519 (Sensory and motor system changes as predictors of preclinical Alzheimer’s diseas, 14).

NIA is the main institute for 565 data science PIs. 12% had NIH projects before their first data science project. 52% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 248, FY2019–21 178, FY2022–25 135. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Aging, dementia, and neurodegeneration (67%); Research cores, centers, and data resources (10%); Clinical care and population health (5%); Musculoskeletal, pain, and rehabilitation (4%); Neuroscience (2%); Metabolism, microbiome, and gut (1%).

Fastest-rising topics: Technology for dementia care (AD/ADRD pilots) (8.5×); Cellular senescence (2.2×); Mitochondria and muscle metabolism (2.0×); Dementia care and caregivers (1.9×); Bone, joint, and cartilage (1.4×); Genomics and sequencing cores (1.4×).

## Where it could do more

These research areas are where NIA puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NIA applications.

| Area | NIA data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Coronaviruses | 32% | 50% | -18.0 |
| Health Services | 29% | 43% | -14.1 |
| Mental Health | 17% | 30% | -12.2 |
| Digital Health | 44% | 56% | -11.8 |
| Clinical Trials and Supportive Activities | 15% | 27% | -11.7 |

Where it leads: Geroscience (+14.2); Neurodegenerative (+7.9); Acquired Cognitive Impairment (+6.8).

Kinds of data science NIA funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): hpc compute (0.40); community capacity (0.46); computational modeling (0.48); mental behavioral (0.52); data science general (0.72).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nia/`.

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

## How the methods work, in plain terms

- **Counts and shares, no model.** Each project counts once in every year it's active, under the institute that manages it. Data science share = data science projects ÷ all projects; growth = share now ÷ share in FY2016–18.
- **Data science labels.** Projects are tagged by the NIH Data Science Taxonomy: keyword rules first, then two large language models (AI systems that read text) that decide whether data science is central to the project.
- **Themes and rising topics.** A topic-grouping method (BERTopic) sorts project summaries into groups that share meaning, like sorting mail by subject when nothing is labeled.
- **Area gaps.** For each research area, the institute's data science share of funding minus the rest of NIH's share in the same area. Negative means the institute does less data science there.
- **Call links.** A ranking model (LightGBM LambdaMART) looks at 150 candidate calls for each project and sorts them so the best fit comes first. It's built from 300 small decision trees, each a short chain of yes-or-no questions ("Does the call allow this grant type?"), and it finds a project's actual call in the top 10 for 95% of projects whose call we know.
