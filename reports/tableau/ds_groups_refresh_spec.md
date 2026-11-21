# Tableau build spec: data science dashboard refresh (FY2016 to FY2026)

**Bottom line:** reconnect the dashboard to the refreshed `tableau_ds_groups.csv`, switch every font to Arial, mark FY2026 as preliminary, and add an IC filter that drives the highlight plus a new NOFO route filter. Four sheets, one dashboard.

## Data

| File | Grain | Use |
|---|---|---|
| `reports/results/tableau_ds_groups.csv` (notebook 13) | record × fiscal year × group | Every sheet |
| `reports/results/ic_totals_by_fy.csv` | IC × fiscal year | Denominators for shares; relate on `fy` and `ic` |
| `reports/results/tableau_rcdc_bridge.csv` | record × fiscal year × RCDC category | Optional RCDC filter; relate on `record` and `fy` |

485,614 rows, FY2016 to FY2026, 25 ICs. New columns since the last build: `preliminary` (True for FY2026), `admin_period`, `nofo`, `nofo_route` (Targeted NOFO, Researcher-initiated, Not through a NOFO), and `nofo_fit` (Strong fit, Weak fit, Likely funding call; researcher-initiated only).

A record appears once per group it is in. Count projects with `COUNTD([record])`, and sum dollars only after filtering `level` to one value and `ds_group` to one group.

## Calculated fields

```
// Focus IC highlight (parameter [Focus IC], string, list of ICs plus "All NIH", default "All NIH")
[ic] = [Focus IC]

// Projects
COUNTD([record])

// Extramural funding (one group selected)
SUM([extramural_cost])

// Share of IC projects (needs ic_totals_by_fy related)
COUNTD([record]) / SUM([all_projects])

// FY label with preliminary flag
IF [preliminary] THEN STR([fy]) + " (preliminary)" ELSE STR([fy]) END

// Targeted share
COUNTD(IF [nofo_route] = "Targeted NOFO" THEN [record] END) / COUNTD([record])
```

## Sheets

| # | Finding (title) | Category | Chart | Build notes |
|---|---|---|---|---|
| 1 | Data science grew from 14.8% to 23.0% of NIH projects, FY2016 to FY2025 | Change over time | Line | `fy` on Columns, share on Rows. Dual axis: FY2025 to FY2026 segment dashed (calc `IF [fy] >= 2025 THEN share END`, Line pattern dashed). Projects #596D69. |
| 2 | Projects by data science group, latest full year | Magnitude | Bar | `group_label` on Rows sorted descending, Projects on Columns, `level` = Group (fixed). Starts at zero. |
| 3 | Institutes ranked by data science projects | Ranking | Ordered bar | `ic` on Rows sorted by Projects. Color on Focus IC calc: True #596D69, False #CDC4B7. |
| 4 | How data science projects reach NIH: targeted NOFO, researcher-initiated, or neither | Part-to-whole | 100% stacked bar | `ic` on Rows, percent of total along `nofo_route`. Colors: Targeted #344D58, Researcher-initiated #72908D, Not through a NOFO #CDC4B7. Sort by Targeted share. |

Optional sheet 5: AI role mix (100% stacked bar, role colors applies #72908D, develops #B06F60, supports #E1B781, studies #744245), shown when Scope = AI.

Tooltips: Arial 12. Sheet 4 tooltip adds: "For researcher-initiated projects, fit shows how closely the project matches its best-fit NOFO, not the NOFO that funded it."

## House style

- Arial everywhere: Format > Workbook > Fonts > All: Arial. Sizes: 20 dashboard title, 14 sheet title, 12 labels and tooltips, 11 axes and source.
- FY2026 always marked: dashed line segment or lighter bar, plus "FY2026 preliminary, as of October 2026" in the subtitle.
- Source line: "Source: NIH RePORTER API. Administering IC; attributed cost; centers counted once."

## Filters and cross-filtering

| Item | Setting |
|---|---|
| Fiscal year | Slider, FY2016 to FY2026, all years; sheets 2 to 4 default to 2025. Applies to sheets 2 to 4; sheet 1 ignores it. |
| Scope (`group_label`) | Single value dropdown, default Data science. All sheets. |
| Focus IC | Parameter, default All NIH. Drives the highlight on sheet 3 and filters sheets 1, 2, and 4 when not All NIH. |
| NOFO route | Multiple values, all. All sheets. |
| NOFO fit | Multiple values, all. Shown only when NOFO route = Researcher-initiated. |
| Administration period | Multiple values, all. All sheets. |
| Context filter | Scope, so ranks on sheet 3 compute within the selected group. |
| Actions | Click an IC on sheet 3: parameter action sets Focus IC; clearing returns All NIH. Click a year on sheet 1: Highlight action on other sheets. No hover filters. |
| Ignored filters | NIH reference line on sheet 1 uses a FIXED LOD on `fy` and ignores Focus IC. |

Reader note (text box):

> Filter by fiscal year, scope, institute, and NOFO route using the controls above. Click an institute to focus the dashboard on it; click again to clear. FY2026 is preliminary. Dollars use the administering institute and count each center once. For researcher-initiated projects, the NOFO shown is the best fit, not the funding NOFO.

## Publish

Tableau Public shows everything and lets anyone download the data, so publish only the NIH-wide view. Then add the link to `skills/viz-bi.qmd` (replace the TBD embed) and the README.
