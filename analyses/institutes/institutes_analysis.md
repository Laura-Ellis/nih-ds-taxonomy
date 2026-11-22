# Data science across NIH institutes: how much, how it got there, and where each can grow next

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · [GitHub](https://github.com/Laura-Ellis/nih-ds-taxonomy) · FY2016 to FY2025 · [Presentation (PDF)](https://laura-ellis.github.io/pdf/data_science_at_each_nih_institute.pdf) · [Institute profiles](README.md)

Every NIH institute grew its data science share from FY2016 to FY2025, by 1.1× to 1.7×. How much data science an institute does mostly follows its mission: institutes built around data (NLM, NHGRI, NCATS, NIBIB) lead, and disease institutes sit near or below the rest of NIH. Institutes also bring data science in through different routes. NCI, OD, NCATS and NIMHD rely on targeted NOFOs. At NHLBI, NIDCD and NEI, most data science comes in through researcher-initiated grants with no close targeted NOFO. Nineteen of 22 institutes have a research area where a smaller share of their funding goes to data science than at the rest of NIH.

This page covers the 22 institutes and centers with at least 500 data science projects. Each has its own [profile](README.md). Terms are defined in the [glossary](#glossary), and the [last section](#how-the-methods-work-in-plain-terms) explains the methods for non-technical readers.

## Contents

1. [How much data science each institute does](#1-how-much-data-science-each-institute-does)
2. [How data science got there](#2-how-data-science-got-there)
3. [Linking projects to NOFOs](#3-linking-projects-to-nofos)
4. [What each institute works on](#4-what-each-institute-works-on)
5. [Where each institute can grow next](#5-where-each-institute-can-grow-next)
6. [So what](#6-so-what)
7. [Glossary](#glossary)
8. [How the methods work, in plain terms](#how-the-methods-work-in-plain-terms)

## 1. How much data science each institute does

Share of each institute's active projects and funding that are data science, averaged over FY2023 to FY2025. Growth = project share in FY2023 to FY2025 ÷ share in FY2016 to FY2018.

| Institute | Share of projects | Share of funding | Growth |
|---|---:|---:|---:|
| NLM | 79% | 96% | 1.1× |
| NHGRI | 63% | 67% | 1.2× |
| NCATS | 39% | 65% | 1.2× |
| NIBIB | 38% | 43% | 1.4× |
| OD | 30% | 53% | 1.7× |
| NIMH | 29% | 35% | 1.5× |
| NIEHS | 26% | 29% | 1.5× |
| NIGMS | 25% | 25% | 1.2× |
| NIA | 24% | 28% | 1.5× |
| NIDA | 24% | 34% | 1.7× |
| NIMHD | 23% | 27% | 1.7× |
| NCI | 23% | 25% | 1.3× |
| NIDCD | 22% | 25% | 1.5× |
| NICHD | 22% | 26% | 1.4× |
| NHLBI | 19% | 30% | 1.6× |
| NEI | 19% | 21% | 1.3× |
| NIAMS | 19% | 20% | 1.6× |
| NINDS | 18% | 22% | 1.6× |
| NIDCR | 18% | 20% | 1.6× |
| NIAAA | 17% | 22% | 1.4× |
| NIDDK | 16% | 20% | 1.4× |
| NIAID | 16% | 23% | 1.3× |
| **Rest of NIH** | **22%** | **29%** | |

- 13 of 22 institutes are above the rest of NIH's project share.
- Funding shares run about 4 points above project shares, because data science projects tend to be larger awards, such as centers and cooperative agreements.
- Institutes with smaller shares grew a little faster on average, but the pattern is weak (rank correlation −0.28).

## 2. How data science got there

Each column is a share of the institute's data science applications (first three) or data science PIs (last two), FY2016 to FY2025.

| Institute | Targeted NOFOs | Training awards | Centers (P) | PIs with earlier NIH work | PIs at 2+ institutes |
|---|---:|---:|---:|---:|---:|
| NCI | 66% | 8% | 31% | 14% | 42% |
| NIGMS | 59% | 9% | 18% | 11% | 61% |
| NIA | 60% | 12% | 24% | 12% | 52% |
| NIAID | 46% | 12% | 13% | 12% | 52% |
| NHLBI | 27% | 27% | 7% | 12% | 54% |
| NIMH | 38% | 20% | 8% | 13% | 58% |
| NINDS | 45% | 16% | 4% | 17% | 67% |
| NICHD | 45% | 17% | 22% | 18% | 58% |
| NIDDK | 45% | 18% | 16% | 9% | 60% |
| NIDA | 50% | 20% | 12% | 12% | 56% |
| NIBIB | 47% | 9% | 16% | 11% | 75% |
| NHGRI | 49% | 11% | 0% | 9% | 69% |
| NIEHS | 52% | 13% | 33% | 12% | 51% |
| NEI | 29% | 15% | 16% | 18% | 36% |
| NIAMS | 41% | 20% | 29% | 15% | 46% |
| OD | 65% | 4% | 11% | 12% | 80% |
| NIDCD | 23% | 14% | 5% | 17% | 56% |
| NLM | 53% | 19% | 0% | 1% | 74% |
| NIAAA | 43% | 22% | 18% | 19% | 52% |
| NCATS | 64% | 22% | 0% | 10% | 71% |
| NIMHD | 64% | 11% | 7% | 12% | 67% |
| NIDCR | 38% | 19% | 1% | 12% | 49% |

- NCI, OD, NCATS and NIMHD bring in the most data science through targeted NOFOs (64% to 66%). NIDCD, NHLBI and NEI bring in the least this way (23% to 29%).
- NHLBI leans on training awards (27% of its data science applications).
- At every institute, most data science PIs started in data science rather than moving in from other NIH work.
- Data science PIs at NLM, NIBIB and OD work across institutes the most.

## 3. Linking projects to NOFOs

Every grant record names the NOFO it answered. When that is a targeted NOFO (RFA or PAR), NIH asked for the topic. When it is a broad NOFO, such as the parent R01, the researcher picked the topic. For those projects, a ranking model found the targeted NOFO each fits best. Strong fit means that NOFO scores as high as a typical correct match; weak fit means no targeted NOFO comes close. Intramural, VA and contract projects never go through a NOFO. Shares are of data science projects, each counted once, so they differ slightly from the application shares in section 2. Rows are ordered by weak-fit share. The method is in [What data science at NIH works on](../topics/topics_analysis.md), section 5.

| Institute | Targeted NOFO | Researcher-initiated, strong fit | Researcher-initiated, weak fit | Not through a NOFO |
|---|---:|---:|---:|---:|
| NHLBI | 31% | 2% | 63% | 3% |
| NIDCD | 30% | 7% | 61% | 2% |
| NEI | 34% | 3% | 59% | 4% |
| NIAMS | 43% | 3% | 53% | 2% |
| NIAAA | 39% | 9% | 50% | 2% |
| NIMH | 43% | 9% | 46% | 2% |
| NICHD | 45% | 5% | 46% | 4% |
| NIBIB | 50% | 3% | 45% | 2% |
| NIDDK | 48% | 4% | 44% | 4% |
| NINDS | 50% | 4% | 44% | 2% |
| NIDCR | 49% | 5% | 42% | 4% |
| NIAID | 48% | 7% | 41% | 3% |
| NHGRI | 51% | 5% | 39% | 5% |
| NIDA | 54% | 5% | 37% | 4% |
| NLM | 52% | 1% | 36% | 11% |
| NIGMS | 64% | 3% | 34% | 0% |
| NIEHS | 58% | 3% | 31% | 8% |
| NIA | 62% | 5% | 31% | 2% |
| NIMHD | 66% | 5% | 25% | 4% |
| NCI | 71% | 3% | 19% | 6% |
| NCATS | 70% | 0% | 12% | 19% |
| OD | 70% | 0% | 5% | 25% |
| **All NIH** | **53%** | **4%** | **37%** | **5%** |

- 37% of NIH data science arrives unasked, with no close targeted NOFO.
- NHLBI, NIDCD and NEI rely most on researcher-initiated data science. A high weak-fit share points to areas where a targeted NOFO could draw more in.
- OD, NCATS and NCI bring it in mostly through targeted NOFOs. At OD only 5% is weak fit; a quarter of its data science is intramural or contracts.

## 4. What each institute works on

The two largest themes in each institute's data science projects, FY2023 to FY2025 (share of its data science projects).

| Institute | Largest themes |
|---|---|
| NCI | Research cores, centers, and data resources (29%); Cancer biology and treatment (28%) |
| NIGMS | Proteins, structure, and chemistry (22%); Genomics and gene regulation (19%) |
| NIA | Aging, dementia, and neurodegeneration (67%); Research cores, centers, and data resources (10%) |
| NIAID | Infectious disease (51%); HIV (13%) |
| NHLBI | Heart, lung, kidney, and liver (44%); Clinical care and population health (19%) |
| NIMH | Mental health and substance use (43%); Neuroscience (25%) |
| NINDS | Neuroscience (40%); Brain injury and stroke (11%) |
| NICHD | Clinical care and population health (15%); Neurodevelopment, language, and communication (12%) |
| NIDDK | Metabolism, microbiome, and gut (28%); Heart, lung, kidney, and liver (28%) |
| NIDA | Mental health and substance use (63%); HIV (12%) |
| NIBIB | Imaging (35%); Neuroscience (14%) |
| NHGRI | Genomics and gene regulation (58%); Research cores, centers, and data resources (11%) |
| NIEHS | Environmental health (56%); Research cores, centers, and data resources (12%) |
| NEI | Eye and vision (65%); Neuroscience (23%) |
| NIAMS | Musculoskeletal, pain, and rehabilitation (56%); Immunology and autoimmunity (15%) |
| OD | Research cores, centers, and data resources (25%); Genomics and gene regulation (21%) |
| NIDCD | Neurodevelopment, language, and communication (77%); Neuroscience (11%) |
| NLM | Clinical care and population health (30%); Training and workforce (20%) |
| NIAAA | Mental health and substance use (64%); Heart, lung, kidney, and liver (13%) |
| NCATS | Training and workforce (49%); Drug discovery and pharmacology (14%) |
| NIMHD | Clinical care and population health (35%); Training and workforce (21%) |
| NIDCR | Reproductive and oral health (31%); Cancer biology and treatment (20%) |

Most institutes' data science sits in one or two themes that match their mission. Research cores, centers, and data resources shows up at nearly every institute.

## 5. Where each institute can grow next

For each institute, the research area (RCDC category with at least 300 of its applications) where the share of its funding going to data science has the most room to grow compared with the rest of NIH. Points = institute's data science funding share − rest of NIH's share in the same area. Categories that describe data science or computing themselves are left out.

| Institute | Area | Points |
|---|---|---:|
| NEI | Macular Degeneration | −43 |
| NIAAA | Fetal Alcohol Spectrum Disorders (FASD) | −38 |
| NIAID | Coronaviruses Disparities and At-Risk Populations | −31 |
| NCI | Digital Health | −29 |
| NIMH | Pediatric - AIDS | −28 |
| NINDS | Traumatic Brain Injury (TBI) | −28 |
| NIGMS | American Indian or Alaska Native | −25 |
| NIMHD | Health Services | −24 |
| NIDDK | Health Services | −23 |
| NIAMS | Rheumatoid Arthritis | −23 |
| NHLBI | Sickle Cell Disease | −22 |
| NIA | Coronaviruses | −18 |
| NIDCR | Human Genome | −18 |
| NICHD | Health Services | −16 |
| NIDA | Methamphetamine | −15 |
| OD | Biomedical Imaging | −13 |
| NIEHS | Human Genome | −10 |
| NIDCD | Minority Health | −9 |
| NIBIB | Genetics | −5 |
| NCATS | Genetics | +5 |
| NHGRI | Human Genome | +15 |
| NLM | Clinical Research | +47 |

Positive numbers (NCATS, NHGRI, NLM) mean the institute leads the rest of NIH in every qualifying area; the area shown is where it leads least. These comparisons don't account for mission: an institute may rightly leave some data science to others. Each [profile](README.md) lists all of an institute's area gaps.

## 6. So what

- **Mission.** Data science follows each institute's mission. Compare an institute with its own past and with similar institutes, not with NLM or NHGRI.
- **Routes.** Targeted NOFOs work for some institutes; others grow data science through training and broad grants. Each institute can use the route that fits.
- **Opportunities.** Most institutes have areas where a smaller share of their funding goes to data science than at the rest of NIH. Those are the places to look first, keeping mission in mind; they are candidates for targeted NOFOs or partnerships.

## Glossary

- **Institute (IC):** one of NIH's 27 institutes and centers. Projects count under the institute that manages them (administering IC).
- **Data science project:** a project where data science is central, labeled by the NIH Data Science Taxonomy.
- **Share of funding:** attributed cost of data science projects ÷ all attributed cost at the institute.
- **NOFO:** Notice of Funding Opportunity, NIH's published request for applications.
- **Targeted NOFO:** a NOFO written for a topic (RFA or PAR); NIH asks for the topic.
- **Researcher-initiated:** an application under a broad NOFO (PA, such as the parent R01); the researcher picks the topic.
- **Not through a NOFO:** intramural (Z), VA (I), contract (N, Y) and other transaction (OT) projects.
- **RCDC category:** NIH's Research, Condition, and Disease Categorization, the standard list of research areas used in public reporting.
- **Training awards:** F, K, T and similar activity codes. **Centers (P):** P activity codes, such as P30 and P50.

## How the methods work, in plain terms

- **Counts and shares.** No model. Each project counts once in every year it's active, under the institute that manages it. Share = data science projects ÷ all projects.
- **Data science labels.** Keyword rules first, then two large language models (AI systems that read text) decide whether data science is central to a project. They agree with hand coding most of the time (kappa 0.86).
- **Themes.** A topic-grouping method (BERTopic) sorts project summaries into groups that share meaning, like sorting mail by subject with no labels. I then grouped the topics into themes by hand.
- **Area opportunities.** No model. An institute's data science share of funding in a research area minus the rest of NIH's share in the same area.
- **NOFO links.** A ranking model (LightGBM LambdaMART) sorts 150 candidate NOFOs for each project so the best fit comes first. It learns from projects whose NOFO is known, using 300 small yes-or-no decision trees, each fixing the mistakes of the ones before. It finds a project's actual NOFO in the top 10 for 95% of known cases.
- **Strong or weak fit.** Strong = the best targeted NOFO scores as high as a typical correct match. The bar is strict on purpose. For researcher-initiated projects, the NOFO shown is the best-fitting one, not the one that funded the project.

Code: [`ic_profiles.py`](ic_profiles.py) (profiles, routes, themes, area opportunities) and [`nofo_link_ltr.py`](../topics/nofo_link_ltr.py) (NOFO links). Source: NIH RePORTER API and ExPORTER, FY2016 to FY2025; NIH Data Science Taxonomy.
