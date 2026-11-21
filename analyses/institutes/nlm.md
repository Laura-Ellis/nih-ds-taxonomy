# Data science at the National Library of Medicine (NLM)

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025, administering IC · [All institutes](README.md)

NLM funded 624 data science projects from FY2016 to FY2025. In FY2023 to FY2025, 79% of its projects used data science, compared with 22% for the rest of NIH. By funding, data science was 96% of its dollars, compared with 28% for the rest of NIH. Funding shares run higher because data science projects tend to be larger awards.

Its share grew 1.1 times since FY2016 to FY2018; the rest of NIH grew 1.4 times.

Terms are defined in the [glossary](#glossary) at the end.

![Data science at NLM](../../reports/figures/institutes/nlm.png)

## How data science came in

Most projects answer a funding call. Targeted calls (RFAs and PARs) ask for work in an area; broad calls (PAs), such as the parent R01, don't.

| Route | NLM | Rest of NIH |
|---|---:|---:|
| Targeted (RFA, PAR) | 53% | 50% |
| Parent or other PA | 31% | 42% |
| None listed | 16% | 8% |

| Activity group | NLM | Rest of NIH |
|---|---:|---:|
| R01-type | 41% | 30% |
| Other R | 15% | 15% |
| Cooperative (U) | 7% | 16% |
| Centers (P) | 0% | 17% |
| Training (K, F, T) | 19% | 14% |
| Other | 18% | 9% |

### Linking projects to calls

Every grant record names the funding call it answered. For projects that name only a broad call, a ranking model found the targeted call each fits best ([how](../topics/topics_analysis.md#linking-every-project-to-a-call)). Weak fit = no targeted call comes close, so that data science came in without a call that asked for it. Shares of data science projects.

| Call on the grant record | NLM | All NIH |
|---|---:|---:|
| Targeted call on record | 52% | 53% |
| Broad call, strong fit | 1% | 4% |
| Broad call, weak fit | 36% | 37% |
| No funding call (intramural, VA, contract) | 11% | 5% |

NLM is the main institute for 183 data science PIs. 1% had NIH projects before their first data science project. 74% have projects at more than one institute.

Data science PIs by when they started data science: FY2016–18 or earlier 115, FY2019–21 35, FY2022–25 32. FY2016 is the first year in the data, so earlier starts count there.

## What it works on

Largest themes, FY2023 to FY2025 (share of the IC's data science projects): Clinical care and population health (30%); Training and workforce (20%); Research cores, centers, and data resources (11%); Genomics and gene regulation (6%); Proteins, structure, and chemistry (5%); Single-cell and spatial omics (3%).

Fastest-rising topics: Clinical care and EHR (1.5×).

## Where it could do more

These research areas are where NLM puts a smaller share of its funding into data science than the rest of NIH does in the same area. Areas come from NIH's RCDC categories; each has at least 300 NLM applications.

| Area | NLM data science share of funding | Rest of NIH | Difference (points) |
|---|---:|---:|---:|

Where it leads: Clinical Research (+46.6).

Kinds of data science NLM funds least often compared with the rest of NIH (1 = as often, 0.5 = half as often): neuroscience (0.36); mental behavioral (0.38); computational modeling (0.52); medical imaging (0.55); data management sharing (0.64).

## Method and limits

Projects are counted once per fiscal year they are active; the administering IC gets the whole project. Data science = the taxonomy's substantive data science label. RCDC categories overlap. Area gaps compare the IC with all other ICs in the same area and don't account for differences in mission. Counts under 11 are suppressed. Code: `analyses/institutes/ic_profiles.py`; tables in `reports/results/institutes/nlm/`.

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
