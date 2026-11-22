# Data science at the National Institute of Mental Health (NIMH)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md) · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)

NIMH funded 2,978 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 29% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 35% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.5 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIMH](../../reports/figures/institutes/nimh.png)

## How data science came in

Most projects answer a NOFO (notice of funding opportunity). Targeted NOFOs (RFAs and PARs) ask for work in an area; broad NOFOs (PAs), such as the parent R01, let the researcher pick the topic.

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

### Linking projects to NOFOs

Every grant record names the NOFO (notice of funding opportunity) it answered. For researcher-initiated projects, which name only a broad NOFO such as the parent R01, a ranking model found the targeted NOFO each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-nofo)). Weak fit = no targeted NOFO comes close, so that data science came in without a NOFO that asked for it. Shares of data science projects.

| NOFO on the grant record | NIMH | All NIH |
|---|---:|---:|
| Targeted NOFO (RFA, PAR) | 43% | 53% |
| Researcher-initiated, strong fit | 9% | 4% |
| Researcher-initiated, weak fit | 46% | 37% |
| Not through a NOFO (intramural, VA, contract) | 2% | 5% |

Targeted NOFOs its researcher-initiated projects fit best (strong fits, 11 or more projects): PAR-16-136 (Using the NIMH Research Domain Criteria (RDoC) Approach to Understand Psychosis , 16); PAR-18-929 (High-Priority Areas for Research Leveraging EHR and Large-Scale Data (R01 Clinic, 15); RFA-MH-17-300 (The Neural Mechanisms of Multi-Dimensional Emotional and Social Representation (, 15).

NIMH is the main institute for 536 data science PIs. 13% had NIH projects before their first data science project. 58% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 302, FY2019–21 150, FY2022–25 82. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Mental health and substance use (43%); Neuroscience (25%); Neurodevelopment, language, and communication (14%); HIV (7%); Training and workforce (3%); Clinical care and population health (2%).

Fastest-rising topics: Suicide prevention (2.5×); Mental health care and interventions (1.7×); Memory and sensory neuroscience (1.4×); Anxiety and depression (1.3×); Child brain development (1.3×); Deep brain stimulation and Parkinson's (1.3×).

## Where it can grow next

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

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area opportunities compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nimh/`.

**Source:** NIH RePORTER API and ExPORTER, FY2016 to FY2025; NIH Data Science Taxonomy.

## Glossary

| Term | Meaning |
|---|---|
| Activity group | The kind of award: R01-type research grants, other R grants, cooperative agreements (U), centers (P), training (K, F, T) |
| Administering institute | The NIH institute or center that manages a project |
| Data science project | An NIH project whose aims or approach rely on data science, per the NIH Data Science Taxonomy |
| Data science PI | A PI with 2 or more project records, more than half with substantive data science |
| Growth | Data science share in FY2023–25 ÷ share in FY2016–18 |
| NOFO | Notice of funding opportunity: NIH's public request for grant proposals. RFA and PAR = targeted (NIH asks for a topic); PA = broad, such as the parent R01 (the researcher picks) |
| PI | Principal investigator: a person who leads an NIH-funded project |
| RCDC | NIH's research, condition, and disease categories, used to tag every project |
| Rest of NIH | Every other NIH institute and center |

## How the methods work, in plain terms

- **Counts and shares, no model.** Each project counts once in every year it's active, under the institute that manages it. Data science share = data science projects ÷ all projects; growth = share now ÷ share in FY2016–18.
- **Data science labels.** Projects are tagged by the NIH Data Science Taxonomy: keyword rules first, then two large language models (AI systems that read text) that decide whether data science is central to the project.
- **Themes and rising topics.** A topic-grouping method (BERTopic) sorts project summaries into groups that share meaning, like sorting mail by subject when nothing is labeled.
- **Area opportunities.** For each research area, the institute's data science share of funding minus the rest of NIH's share in the same area. Negative means room to grow there.
- **NOFO links.** A ranking model (LightGBM LambdaMART) looks at 150 candidate NOFOs for each project and sorts them so the best fit comes first. It's built from 300 small decision trees, each a short chain of yes-or-no questions ("Does the NOFO allow this grant type?"), and it finds a project's actual NOFO in the top 10 for 95% of projects whose NOFO we know.
