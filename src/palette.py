"""Laura Ellis personal palette (Behr 2026) and fixed color roles for every chart.

One measure = one color, everywhere (deck, site figures, dashboard, Tableau). Projects and funding keep
their colors whether the scope is data science or AI; the section or title says which. When data
science appears only as context on an AI chart, it is warm gray.

| Measure / role              | Color            | Hex     |
|-----------------------------|------------------|---------|
| Projects (counts, share)    | Hidden Gem       | #596D69 |
| Funding ($, share)          | Nocturne Blue    | #344D58 |
| Data science, as context    | Warm gray        | #B9B2A6 |
| Role: applies AI            | Sage             | #72908D |
| Role: develops AI           | Terra cotta      | #B06F60 |
| Role: supports AI           | Gold             | #E1B781 |
| Role: studies AI            | Plum             | #744245 |
| Everything else / non-AI    | Light neutral    | #CDC4B7 |

Taxonomy groups (only on charts that compare groups with each other; never on the same chart as the
AI role colors, which they reuse). Drawn from the AI section colors so group charts match it; AI uses the
AI projects color. Always label groups directly; use dash patterns for lines; Light gold is for bars and areas.

| Group                                   | Color            | Hex     |
|-----------------------------------------|------------------|---------|
| Artificial intelligence                 | Hidden Gem       | #596D69 |
| Statistics and analytics                | Nocturne Blue    | #344D58 |
| Computational modeling                  | Sage             | #72908D |
| Software and tools                      | Terra cotta      | #B06F60 |
| Data infrastructure                     | Gold             | #E1B781 |
|   Computing and platforms (subgroup)    | Gold             | #E1B781 |
|   Data management and sharing (subgroup)| Light gold       | #F0D9B8 |
| Responsible AI                          | Plum             | #744245 |
| Workforce                               | Ecological       | #808367 |

Generative AI is a subset of AI projects, so it uses the AI projects color. A highlight takes the
color of the measure it highlights, never a role color.

Highlighting an institute: no institute is built in. The chosen IC (`focus_ic` in config, or a
dashboard filter) takes the measure's color and every other IC is light neutral, so the same chart
works for any IC.

Typography: Arial everywhere (charts, deck, dashboard, Tableau, site), since every viewer has it.
- Weights: regular and bold only; no italics in charts
- Sizes (pt): page title 20 · chart title 14 · body and labels 12–13 · axis labels and sources 11
- Text colors: titles HEADING, labels and notes MUTED, sources and fine print SOURCE
- Numbers in tables are right-aligned
"""

PROJECTS = AI_PROJECTS = "#596D69"
FUNDING = AI_FUNDING = "#344D58"
DATA_SCIENCE = "#B9B2A6"
ROLE_COLORS = {"applies_ai": "#72908D", "develops_ai": "#B06F60", "supports_ai": "#E1B781", "studies_ai": "#744245"}
ROLE_LABELS = {"applies_ai": "Applies", "develops_ai": "Develops", "supports_ai": "Supports", "studies_ai": "Studies"}
NEUTRAL = "#CDC4B7"
GROUP_COLORS = {  # taxonomy group ids (taxonomy/reporting_groups.yaml); group-comparison charts only
    "artificial_intelligence": "#596D69", # Hidden Gem (same as AI projects)
    "statistics_analytics": "#344D58",    # Nocturne Blue (same as AI funding)
    "computational_modeling": "#72908D",  # Sage (same as applies AI)
    "software_tools": "#B06F60",          # Terra cotta (same as develops AI)
    "data_infrastructure": "#E1B781",     # Gold (same as supports AI)
    "computing_platforms": "#E1B781",     # Gold (subgroup of data infrastructure)
    "data_sharing": "#F0D9B8",            # Light gold (subgroup of data infrastructure)
    "responsible_ai": "#744245",          # Plum (same as studies AI)
    "workforce": "#808367",               # Ecological
}
BG = "#F1EDE1"
PANEL = "#FAF7F0"
INK = "#4F5152"
MUTED = "#6A6C6D"
HEADING = "#344D58"
GRID = "#E3DCCF"

SOURCE = "#8A8C8D"

FONT = "Arial"
FONT_STACK = "Arial, Helvetica, sans-serif"  # CSS for the dashboard and site
SIZES = {"page_title": 20, "chart_title": 14, "body": 12, "label": 12, "axis": 11, "source": 11}


def use_style() -> None:
    """Apply the house chart style to matplotlib: Arial, house sizes and text colors, no top/right spines."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [FONT, "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": SIZES["body"], "axes.titlesize": SIZES["chart_title"], "axes.titleweight": "bold",
        "axes.titlecolor": HEADING, "axes.titlelocation": "left", "axes.labelsize": SIZES["axis"],
        "axes.labelcolor": MUTED, "xtick.labelsize": SIZES["axis"], "ytick.labelsize": SIZES["axis"],
        "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": GRID,
        "legend.fontsize": SIZES["label"], "legend.frameon": False,
    })
