# Data science at the National Institute of Neurological Disorders and Stroke (NINDS)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NINDS funded 2,484 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 18% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 22% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.6 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NINDS](../../reports/figures/institutes/ninds.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NINDS | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 45% | 50% |
| Parent or other PA | 48% | 42% |
| None listed | 7% | 8% |

| Activity group | NINDS | Rest of NIH |
|---|---:|---:|
| R01-type | 39% | 29% |
| Other R | 12% | 15% |
| Cooperative (U) | 23% | 15% |
| Centers (P) | 4% | 18% |
| Training (K, F, T) | 16% | 14% |
| Other | 7% | 9% |

### Linking projects to calls

Every grant record names the funding call it answered. For projects that name only a broad call, a ranking model found the targeted call each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-call)). Weak fit = no targeted call comes close, so that data science came in without a call that asked for it. Shares of data science projects.

| Call on the grant record | NINDS | All NIH |
|---|---:|---:|
| Targeted call on record | 50% | 53% |
| Broad call, strong fit | 4% | 4% |
| Broad call, weak fit | 44% | 37% |
| No funding call (intramural, VA, contract) | 2% | 5% |

Targeted calls its broad-call projects fit best (strong fits, 11 or more projects): RFA-NS-21-007 (Mechanisms of Selective Vulnerability in LBD and FTD (R01 Clinical Trial Not All, 11).

NINDS is the main institute for 442 data science PIs. 17% had NIH projects before their first data science project. 67% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 202, FY2019–21 136, FY2022–25 101. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Neuroscience (40%); Brain injury and stroke (11%); Aging, dementia, and neurodegeneration (8%); Musculoskeletal, pain, and rehabilitation (6%); Training and workforce (6%); Neurodevelopment, language, and communication (5%).

Fastest-rising topics: Chronic pain (3.1×); Alzheimer's disease (1.6×); Sleep and circadian rhythms (1.4×); Memory and sensory neuroscience (1.1×); Brain tumor imaging (1.1×); Stroke (1.1×).

## Where it could do more

These research areas are where NINDS puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NINDS applications.

| Area | NINDS data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|
| Traumatic Brain Injury (TBI) | 17% | 45% | -27.8 |
| Human Genome | 29% | 52% | -23.1 |
| Brain Cancer | 9% | 26% | -17.8 |
| Genetics | 15% | 32% | -17.0 |
| Intellectual and Developmental Disabilities (IDD) | 10% | 27% | -16.8 |

Where it leads: Substance Misuse (+6.6); Multiple Sclerosis (+5.6); Physical Rehabilitation (+5.3).

Kinds of data science NINDS funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): population health (0.29); community capacity (0.32); human data linkage (0.32); nlp (0.37); statistical methods (0.45).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/ninds/`.

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
