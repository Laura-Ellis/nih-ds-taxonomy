# Data science at the National Human Genome Research Institute (NHGRI)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md) · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf)

NHGRI funded 1,165 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 63% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 67% of its dollars, compared with 28% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.2 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NHGRI](../../reports/figures/institutes/nhgri.png)

## How data science came in

Most projects answer a NOFO (notice of funding opportunity). Targeted NOFOs (RFAs and PARs) ask for work in an area; broad NOFOs (PAs), such as the parent R01, let the researcher pick the topic.

| Route | NHGRI | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 49% | 50% |
| Parent or other PA | 40% | 42% |
| None listed | 11% | 8% |

| Activity group | NHGRI | Rest of NIH |
|---|---:|---:|
| R01-type | 25% | 30% |
| Other R | 18% | 15% |
| Cooperative (U) | 34% | 15% |
| Centers (P) | 0% | 17% |
| Training (K, F, T) | 11% | 14% |
| Other | 12% | 9% |

### Linking projects to NOFOs

Every grant record names the NOFO (notice of funding opportunity) it answered. For researcher-initiated projects, which name only a broad NOFO such as the parent R01, a ranking model found the targeted NOFO each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-nofo)). Weak fit = no targeted NOFO comes close, so that data science came in without a NOFO that asked for it. Shares of data science projects.

| NOFO on the grant record | NHGRI | All NIH |
|---|---:|---:|
| Targeted NOFO (RFA, PAR) | 51% | 53% |
| Researcher-initiated, strong fit | 5% | 4% |
| Researcher-initiated, weak fit | 39% | 37% |
| Not through a NOFO (intramural, VA, contract) | 5% | 5% |

Targeted NOFOs its researcher-initiated projects fit best (strong fits, 11 or more projects): RFA-HG-13-013 (Interpreting Variation in Human Non-Coding Genomic Regions Using Computational A, 11).

NHGRI is the main institute for 257 data science PIs. 9% had NIH projects before their first data science project. 69% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 175, FY2019–21 41, FY2022–25 40. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Genomics and gene regulation (58%); Research cores, centers, and data resources (11%); Training and workforce (9%); Single-cell and spatial omics (8%); Heart, lung, kidney, and liver (2%); Mental health and substance use (2%).

Fastest-rising topics: Single-cell and spatial omics (4.3×); Chromatin and DNA replication (1.9×); Genetic variation and traits (1.3×); RNA splicing (1.1×); Genomic medicine (1.1×); Biomedical training programs (1.0×).

## Where it could do more

These research areas are where NHGRI puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NHGRI applications.

| Area | NHGRI data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|

Where it leads: Prevention (+34.6); Genetics (+34.4); Clinical Research (+21.3).

Kinds of data science NHGRI funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): sensors wearables (0.14); medical imaging (0.20); human data linkage (0.21); neuroscience (0.27); computer vision (0.35).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nhgri/`.

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
