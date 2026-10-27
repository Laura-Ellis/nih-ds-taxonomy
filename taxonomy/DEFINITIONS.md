# Definitions: data science and its parts

**Version:** 0.4.0 · **Updated:** 2026-10-24 · **Author:** Laura Ellis · **GitHub:** [github.com/Laura-Ellis/nih-ds-taxonomy](https://github.com/Laura-Ellis/nih-ds-taxonomy)

These definitions match `taxonomy/categories.yaml` and the labeling rules the models follow (`src/llm_label.py`). The YAML file is the source of truth; this page explains it in plain language.

## Data science

**Data science** is the use or development of computational and statistical methods, software, data infrastructure, or data practices to get knowledge from data. In this taxonomy, a project does data science when it **uses or builds data science as part of its own work**: in an aim or the stated approach, even if it is not the main focus.

It covers seven groups, aligned with the five goals of the NIH Strategic Plan for Data Science, 2025–2030. Data infrastructure has two subgroups, reported together or separately:

| Group | What it covers | NIH plan goal |
|---|---|---|
| Statistics and analytics | Advanced statistics, data preparation, visualization, and network analysis | Goal 3 |
| Computational modeling | Mathematical, mechanistic, and simulation models | Goal 3 |
| Artificial intelligence | Machine learning, deep learning, language and image AI, generative AI | Goal 3 |
| Software and tools | Research software and shared analysis tools | Goal 3 |
| **Data infrastructure** | The systems and practices that store, connect, compute on, and share research data | Goals 1, 2, and 4 |
| ↳ Computing and platforms | Cloud and high-performance computing, data platforms and repositories, data engineering | Goal 4 |
| ↳ Data management and sharing | Making data findable, reusable, and linkable, including human-derived data | Goals 1 and 2 |
| Responsible AI | Fairness, privacy, transparency, and reproducibility of AI and data use | AI Strategy (NOT-OD-25-117) |
| Workforce | Training and community building in data science and AI | Goal 5 |

A project in either subgroup counts once in Data infrastructure. The rollup lives in `taxonomy/reporting_groups.yaml`.

### What does not count

- Routine statistics: t-tests, regression or ANOVA on an experiment, standard clinical trial analysis
- Standard sequencing pipelines: single-cell RNA-seq or ATAC-seq processing on their own. Omics counts when the computation is substantial (eQTL mapping, co-expression or regulatory networks, multi-omics integration).
- Mentions only: data science in background, prior work, a center's general capabilities, or a future possibility

### How strongly a project does data science

| Label | Meaning |
|---|---|
| **Substantive (Y)** | Data science is in an aim or the stated approach. All counts and shares in the results use this label. |
| **Mention (M)** | Data science appears only as background, a general capability, prior work, or a future possibility. |
| **None (N)** | No data science, or only routine statistics. |

Building data infrastructure, research software, or data sharing resources counts as substantive. So do training programs whose curriculum centers on data science.

## Artificial intelligence (AI)

**AI** is a subset of data science: methods that learn patterns from data or generate content, plus other approaches that reason or act autonomously. A project is **AI-related** under the same Y / M / N rule, and a project that does not do data science cannot be AI-related.

- "Neural network" describing the brain or cultured neurons is not AI.
- Testing or validating AI algorithms in clinical settings counts as applying AI.
- Studying how people use AI tools, without building or applying them, is a mention.

### Role of AI

Each AI-related project gets one role, the best fit:

| Role | Definition |
|---|---|
| **Develops AI** | The main aim is a new or improved AI method. |
| **Applies AI** | Uses existing AI methods to answer a biomedical question. |
| **Supports AI** | Builds data, software, infrastructure, or workforce that AI work depends on. |
| **Studies AI** | Evaluates AI's safety, bias, ethics, policy, or effect on care or research. |

## Groups and categories

A project can have several categories. Categories are assigned only to substantive data science projects and describe work the project does, not background.

### Statistics and analytics

Analytic methods beyond routine statistics.

| Category | Definition |
|---|---|
| Data science (general) | The project names data science, data analytics, informatics, or computational methods without naming a more specific method. |
| Statistical methods development | New or advanced statistical methods, such as Bayesian hierarchical models, causal inference, high-dimensional statistics, and statistical learning. Routine hypothesis tests and regression do not count. |
| Data preparation and exploration | Data cleaning, wrangling, harmonization for analysis, feature engineering, and exploratory data analysis as a stated part of the work. |
| Data visualization | Visual and interactive exploration or communication of data, including dashboards and visual analytics. |
| Network and graph analysis | Analysis of networks and graphs, such as biological, social, or collaboration networks. |

### Computational modeling

| Category | Definition |
|---|---|
| Computational and simulation modeling | Mathematical, mechanistic, agent-based, and simulation models, including digital twins and hybrid physics- or theory-informed models. |

### Artificial intelligence

| Category | Definition |
|---|---|
| Machine learning | Supervised and unsupervised learning, such as random forests, gradient boosting, support vector machines, and clustering used for prediction or pattern finding. |
| Deep learning | Multi-layer neural networks, including convolutional, recurrent, transformer, and graph neural networks. |
| Natural language processing (NLP) | Methods that extract, classify, or summarize information from text, such as clinical notes or literature. |
| Computer vision | Automated analysis of images and video, such as segmentation, detection, and image classification. |
| Generative AI and large language models (LLMs) | Models that generate text, images, molecules, or other content, including LLMs, diffusion models, and generative adversarial networks (GANs). |
| Other AI | Reinforcement learning, knowledge graphs, AI agents, causal discovery, and expert or rule-based systems. |

### Software and tools

Research software the project builds, maintains, or names as a core tool.

| Category | Definition |
|---|---|
| Research software development | Building, maintaining, or disseminating software, packages, pipelines, or workflows for others to use. |
| ML frameworks and libraries | Named machine learning and data science libraries, such as PyTorch, TensorFlow, and scikit-learn. |
| Analysis and workflow platforms | Shared platforms for running analyses, such as Galaxy, Terra, Jupyter, and workflow languages. |
| Visualization tools | Software for interactive or visual exploration of data, such as dashboards and visualization libraries. |

### Data infrastructure

The systems and practices that store, connect, compute on, and share research data. Two subgroups:

#### Computing and platforms

Systems that store, connect, or compute on research data, including data repositories, data commons, and knowledge bases.

| Category | Definition |
|---|---|
| Cloud computing | Use of commercial or NIH cloud environments for storage or analysis. |
| High-performance computing | High-performance or GPU computing and other advanced computing resources. |
| Data platforms and repositories | Data commons, repositories, knowledge bases, data warehouses, and federated data ecosystems. |
| Data engineering | Pipelines and systems for integrating and processing large data, such as ETL (extract, transform, load), distributed processing, and streaming. |

#### Data management and sharing

How the project makes data findable, reusable, and linkable.

| Category | Definition |
|---|---|
| FAIR data and standards | Metadata, ontologies, common data elements, persistent identifiers, and interoperability standards (FAIR = findable, accessible, interoperable, reusable). |
| Data management and sharing | Data management and sharing plans, data curation, and making data available to others. |
| Human-derived data access and linkage | Access to and linkage of human-derived data, such as real-world data, privacy-preserving record linkage, health IT standards, and data enclaves. |

### Responsible AI

Ethics, privacy, transparency, and evaluation of AI and data use.

| Category | Definition |
|---|---|
| Fairness and bias | Algorithmic bias, fairness, and equity in data and models. |
| Privacy and security | Privacy-preserving methods and data protection, such as federated learning, differential privacy, and de-identification. |
| Transparency and reproducibility | Explainability, interpretability, model reporting, benchmarking, and reproducibility of computational results. |

### Workforce

Building data science and AI skills and community.

| Category | Definition |
|---|---|
| Training and education | Courses, curricula, workshops, mentoring, and training programs in data science or AI. |
| Community and capacity building | Hackathons, communities of practice, and capacity building at institutions new to data science. |

## Biomedical application areas

Where the data science or AI is applied. Reported only for substantive data science projects; a project can have several.

| Area | Definition |
|---|---|
| Medical imaging | Radiology, pathology, microscopy, and other medical images |
| Genomics and other omics | Genomic, transcriptomic, proteomic, metabolomic, and single-cell data |
| Clinical care and EHR | Electronic health records (EHR), clinical decision support, diagnosis, and prognosis |
| Drug discovery and development | Target identification, molecular design, and drug repurposing |
| Population and public health | Epidemiology, surveillance, social determinants, and environmental exposures |
| Mental and behavioral health | Psychiatric, substance use, and behavioral research |
| Neuroscience | Brain structure, function, and neurological disease |
| Sensors and wearables | Physiological signals and data from wearable or mobile devices |

## Related measures

- PI groups (`analyses/ds_pis/ds_pis.py`). Every investigator listed on a project counts as a PI, not only the contact PI.
    - Data science PI: at least 2 project records, with substantive data science in more than half of them.
    - AI developer PI: a data science PI who develops AI in more than half of their records.
    - Infrastructure builder PI: a data science PI who builds data infrastructure in more than half of their records (research software, analysis platforms, data platforms and repositories, data engineering, FAIR data and standards, data management and sharing, or human-derived data linkage).
    - Data science contributor: any PI with at least one data science record who is not a data science PI.
- RCDC coverage: the share of projects in an NIH RCDC (Research, Condition, and Disease Categorization) spending category that are data science, AI, or in a given group (`notebooks/13_ds_groups.py`). RCDC is NIH's own category system and is not part of this taxonomy.
- NOFO: the notice of funding opportunity (also called FOA, e.g. PAR-23-123) an application responded to. Kept per application (`nofo`) and per record (`nofos`, in fiscal-year order) so data science projects can be traced to the opportunities that funded them (`ds_by_nofo.csv`).
- Project record: a core project or one of its subprojects (components of centers and program projects), counted once per fiscal year it has an application.
