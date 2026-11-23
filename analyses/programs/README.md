# What NIH's dedicated data science programs fund

**Laura Ellis** · [LinkedIn](https://www.linkedin.com/in/laura-ellis-profile/) · FY2016 to FY2026 (FY2026 preliminary) · Analysis E, second pass

NIH runs 18 programs whose stated purpose is data science or AI: 11 NIH-wide initiatives (Office of the Director, the Common Fund, ODSS, and trans-NIH NOFOs) and 7 institute flagship programs. I found each program's awards by the funding opportunities (NOFOs) they came through, then profiled what they fund, how the NIH-wide line changed over time, the training they pay for, and how their early outputs compare with similar data science projects.

## Findings

- **$2.4B in 18 programs, FY2016–FY2026,** split evenly: NIH-wide $1.2B, institutes $1.2B. The largest are NLM informatics and data science ($357M), NCI ITCR ($297M), trans-NIH repositories and knowledgebases ($286M), NIMH computational psychiatry ($201M), and BD2K ($200M, FY2016 on).
- **A small, growing slice.** The programs hold 2.1% of NIH funding on data science records, up from 1.6% in FY2016 to 3.3% in FY2025. Most data science happens in regular grants; the programs pay for shared data, standards, software, and training.
- **The NIH-wide line moved to AI.** BD2K (big data tools) → NIH Data Commons pilot (shared cloud data) → CFDE (Common Fund data working together) → Bridge2AI (AI-ready data) → Multimodal AI (ethical AI across data types). AI's share of records rose from 26% (BD2K) to 94% (Multimodal AI).
- **DS-I Africa** reaches 27 organizations in 10 African countries (plus 2 US partner records); half its funding is in research hubs. **Bridge2AI** builds the data AI needs: 15 of 17 records support AI rather than apply it. **AIM-AHEAD** reaches its consortium through one coordinating center award ($169M), so RePORTER shows one record.
- **Newest initiatives** (FY2024–FY2026): Multimodal AI ($60M), the Autism Data Science Initiative ($51M), Computational Modeling of Hormone Homeostasis ($22M), and ODSS software tools and research software engineer awards ($17M).
- **Workforce:** $208M (9%) goes to training, career, and education awards, 65% of it NLM's T15 training grants. Workforce labels also reach most Bridge2AI (88%) and DS-I Africa (62%) records.
- **Early outputs are descriptive only.** Paper counts and RCR vs. matched data science records are in `program_vs_matched.csv`; most programs are too new or too small to test.

## Method

- **Program lookup** (`PROGRAMS` in `programs.py`, results in `program_nofos.csv`): candidates came from a scan of every NOFO with 3+ records, 60%+ of them data science, and a title naming data science, AI, informatics, computational methods, or data resources. Each was checked against the NIH Guide, Common Fund, ODSS, and DPCPSI pages, November 22, 2026. A record belongs to a program when any of its applications used one of the program's NOFOs, so supplements on the same record count.
- **Left out:** STRIDES (OTA-24-200, cloud purchasing, not research); atlas and consortium data centers such as HuBMAP's HIVE (OTA-21-012), whose purpose is biology; ODSS AI-readiness and other administrative supplements, which come through parent supplement NOFOs and can't be found by NOFO. BD2K began in FY2014; this dataset starts in FY2016.
- **Funding** = attributed cost (center costs counted once). **Data science** and **AI** = substantive (Y) labels from the taxonomy pipeline. Taxonomy groups come from the model categories; a record can sit in more than one group. **Share of data science funding** (`program_context.csv`) = program funding on data science records ÷ funding on all data science records, by fiscal year.
- **Training awards** = T15, T32, K01, R25, UE5, U2R, R50 records.
- **Comparison** (`program_vs_matched.csv`): each program parent record vs. data science records outside the programs with the same activity code and first fiscal year within ±1. Papers = ExPORTER publication links per year since the first fiscal year; RCR = iCite Relative Citation Ratio (1.0 = field median for NIH-funded papers), papers published FY2016–FY2023.

**Abbreviations:** BD2K = Big Data to Knowledge; CFDE = Common Fund Data Ecosystem; ITCR = Informatics Technology for Cancer Research; AITC = AI and Technology Collaboratories; ODSS = Office of Data Science Strategy; RSE = research software engineer; NOFO = notice of funding opportunity; RFA = request for applications; OTA = other transaction authority; ELSI = ethical, legal, and social implications; RCR = Relative Citation Ratio.

## Next

- People: trainees and PIs from program awards into later data science research (links to analysis A).
- Outputs beyond papers (software, data sets), and ODSS supplements by award number.
- Deck: built (10 slides, private: `deck/programs/build_e_slides.py`).

Code: `programs.py`. Results: `reports/results/programs/`.
