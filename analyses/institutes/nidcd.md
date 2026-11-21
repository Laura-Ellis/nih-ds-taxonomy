# Data science at the National Institute on Deafness and Other Communication Disorders (NIDCD)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md) · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)

NIDCD funded 666 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 22% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 25% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.5 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIDCD](../../reports/figures/institutes/nidcd.png)

## How data science came in

Most projects answer a NOFO (notice of funding opportunity). Targeted NOFOs (RFAs and PARs) ask for work in an area; broad NOFOs (PAs), such as the parent R01, let the researcher pick the topic.

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

### Linking projects to NOFOs

Every grant record names the NOFO (notice of funding opportunity) it answered. For researcher-initiated projects, which name only a broad NOFO such as the parent R01, a ranking model found the targeted NOFO each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-nofo)). Weak fit = no targeted NOFO comes close, so that data science came in without a NOFO that asked for it. Shares of data science projects.

| NOFO on the grant record | NIDCD | All NIH |
|---|---:|---:|
| Targeted NOFO (RFA, PAR) | 30% | 53% |
| Researcher-initiated, strong fit | 7% | 4% |
| Researcher-initiated, weak fit | 61% | 37% |
| Not through a NOFO (intramural, VA, contract) | 2% | 5% |

Targeted NOFOs its researcher-initiated projects fit best (strong fits, 11 or more projects): RFA-DC-16-001 (Open Design Tools for Speech Signal Processing (R01), 12).

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
| NOFO | Notice of funding opportunity: NIH's public request for grant proposals. RFA and PAR = targeted (NIH asks for a topic); PA = broad, such as the parent R01 (the researcher picks) |
| PI | Principal investigator: a person who leads an NIH-funded project |
| RCDC | NIH's research, condition, and disease categories, used to tag every project |
| Rest of NIH | Every other NIH institute and center |

## How the methods work, in plain terms

- **Counts and shares, no model.** Each project counts once in every year it's active, under the institute that manages it. Data science share = data science projects ÷ all projects; growth = share now ÷ share in FY2016–18.
- **Data science labels.** Projects are tagged by the NIH Data Science Taxonomy: keyword rules first, then two large language models (AI systems that read text) that decide whether data science is central to the project.
- **Themes and rising topics.** A topic-grouping method (BERTopic) sorts project summaries into groups that share meaning, like sorting mail by subject when nothing is labeled.
- **Area gaps.** For each research area, the institute's data science share of funding minus the rest of NIH's share in the same area. Negative means the institute does less data science there.
- **NOFO links.** A ranking model (LightGBM LambdaMART) looks at 150 candidate NOFOs for each project and sorts them so the best fit comes first. It's built from 300 small decision trees, each a short chain of yes-or-no questions ("Does the NOFO allow this grant type?"), and it finds a project's actual NOFO in the top 10 for 95% of projects whose NOFO we know.
