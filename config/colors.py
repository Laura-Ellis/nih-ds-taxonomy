# Categorical palette (21 colors)
CATEGORICAL_PALETTE = [
    "#3A6782", "#E97216", "#A13A7E", "#43A287", "#795D25",
    "#6DA243", "#A93D32", "#BC73E7", "#404BE8", "#49A19E",
    "#949494", "#419BD7", "#733708", "#DC6FB1", "#306E51",
    "#E2765F", "#4A6D27", "#B4902D", "#8435D9", "#828BF2",
    "#2B6E68",
]

# Sequential palette (light → dark)
SEQUENTIAL_PALETTE = [
    "#F5F5F5", "#CED9D8", "#98ABB8",
    "#7D94A3", "#5D727D", "#43545C",
]

CATEGORY_COLORS = {
    "NIAID": "#3A6782",
    "AI/ML": "#E97216",
    "CompBio_SysMod": "#A13A7E",
    "Data Repositories / KB": "#43A287",
    "Data Management Centers": "#795D25",
    "Software Engineering": "#A93D32",
    "Career / Workforce Dev": "#6DA243",
}

def get_category_color(name: str, default: str = "#949494") -> str:
    return CATEGORY_COLORS.get(name, default)
