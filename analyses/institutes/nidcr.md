# Data science at the National Institute of Dental and Craniofacial Research (NIDCR)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md) · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)

NIDCR funded 515 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 18% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 20% of its dollars, compared with 29% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.6 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NIDCR](../../reports/figures/institutes/nidcr.png)

## How data science came in

Most projects answer a NOFO (notice of funding opportunity). Targeted NOFOs (RFAs and PARs) ask for work in an area; broad NOFOs (PAs), such as the parent R01, let the researcher pick the topic.

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

### Linking projects to NOFOs

Every grant record names the NOFO (notice of funding opportunity) it answered. For researcher-initiated projects, which name only a broad NOFO such as the parent R01, a ranking model found the targeted NOFO each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-nofo)). Weak fit = no targeted NOFO comes close, so that data science came in without a NOFO that asked for it. Shares of data science projects.

| NOFO on the grant record | NIDCR | All NIH |
|---|---:|---:|
| Targeted NOFO (RFA, PAR) | 49% | 53% |
| Researcher-initiated, strong fit | 5% | 4% |
| Researcher-initiated, weak fit | 43% | 37% |
| Not through a NOFO (intramural, VA, contract) | 3% | 5% |

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
