# Tableau build spec: IC vs. rest of NIH (data science and AI)

**Bottom line:** one data source (`tableau_ic_benchmark.csv`, notebook 16), one IC filter, and four sheets give any institute's comparison with the rest of NIH. Set the filter to NIAID for the NIAID vs. NIH report.

**Keep it internal:** Tableau Public publishes everything. Build and save the NIAID view in Tableau Desktop (or a private Tableau Server/Cloud site). Only publish a version to Tableau Public after deciding the content can be public.

## Data

| File | Grain | Use |
|---|---|---|
| `reports/results/tableau_ic_benchmark.csv` | IC × fiscal year × level × item | Every sheet in this report |
| `reports/results/tableau_ds_groups.csv` | record × fiscal year × group | Optional drill-down (project counts by activity code, state, AI role) |
| `reports/results/tableau_rcdc_bridge.csv` | record × fiscal year × RCDC category | Optional RCDC filter; relate to `tableau_ds_groups.csv` on `record` and `fy` |

Benchmark columns: `ic`, `fy`, `level` (Overall, Group, Category, AI role), `item`, `group` (categories only), `ic_projects`, `ic_total_projects`, `rest_projects`, `rest_total_projects`, `ic_share`, `rest_share`, `ratio`, `to_parity`, `rank`, `of`.

## Filters and parameters

- **IC** (`ic`): single-value dropdown, default NIAID. Apply to all sheets that use this data source.
- **Fiscal year** (`fy`): single-value slider, default 2025, for the snapshot sheets. The trend sheet ignores it.
- **Level** (`level`): fixed per sheet (Overall, Group, Category, AI role), not shown to readers.

## Calculated fields

```
// Gap label (text): "0.46× · 349 to parity"
STR(ROUND([ratio], 2)) + "× · " + STR(INT([to_parity])) + " to parity"

// Rank label: "15 of 15"
IF NOT ISNULL([rank]) THEN STR(INT([rank])) + " of " + STR(INT([of])) END

// Gap (share points), for sorting
[rest_share] - [ic_share]

// Selected IC label for titles
ATTR([ic])
```

Format `ic_share` and `rest_share` as percent (1 decimal), `ratio` as number (2 decimals) with a "×" suffix.

## Sheets

1. **Headline (KPI text):** level = Overall, fy = filter. Show IC share and rest-of-NIH share for Data science and AI, with the rank label. Title: `<IC> vs. rest of NIH, FY<fy>`.
2. **Groups (dumbbell):** level = Group. Rows: `item` sorted by `rest_share` descending. Columns: dual axis with `ic_share` (circle, Projects color) and `rest_share` (circle, warm gray), synchronized; add a line mark between them (Measure Values on a path, or a Gantt bar from `ic_share` with size = gap). Label = gap label. Tooltip: projects, totals, rank.
3. **Categories (bar, biggest gaps):** level = Category. Bars = `to_parity`, sorted descending, top 15 (Top N filter on `to_parity`). Color: categories in the Artificial intelligence group = terra cotta (Develops color); others = Projects color. Label = gap label. Optional `group` quick filter.
4. **Trend (line):** level = Overall (or Group, via a parameter swap). X = `fy`, Y = `ic_share` and `rest_share` (Measure Values), two lines: IC in Projects color, rest of NIH in warm gray. Label line ends only.
5. **AI roles (bar):** level = AI role. Side-by-side bars of `ic_share` vs. `rest_share` per role; IC in its role color, rest of NIH in warm gray.

## Dashboard

- Title (top left), filter dropdowns (IC, fiscal year) top right
- Row 1: Headline
- Row 2: Groups (left), AI roles (right)
- Row 3: Categories (full width)
- Row 4: Trend (full width)
- Footer: definitions (below) and source

## Colors (from `src/palette.py`)

| Role | Hex |
|---|---|
| Selected IC, projects | #596D69 |
| Funding (if added) | #344D58 |
| Rest of NIH (context) | #B9B2A6 |
| AI categories / develops AI | #B06F60 |
| Applies AI | #72908D |
| Supports AI | #E1B781 |
| Studies AI | #744245 |
| Background | #F1EDE1 |

## Definitions (footer text)

- Share of projects = records with the item / all records at the IC (or the rest of NIH) that fiscal year. AI role shares use AI projects as the denominator.
- Ratio = IC share / rest-of-NIH share (1.0 = parity).
- Projects to parity = (rest-of-NIH share − IC share) × IC records: projects the IC would add to match the rest of NIH's rate. A sizing aid, not a target.
- Rank = among ICs with 1,000+ records that year (1 = highest share).
- Source: NIH ExPORTER FY2016–FY2025; NIH Data Science Taxonomy labels (keywords, Jev, ChatGPT; κ = 0.92 AI, 0.86 data science against 150 hand-coded projects).
