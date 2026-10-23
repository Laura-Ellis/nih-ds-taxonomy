# %% [markdown]
# # 04 Spot check: human vs. ChatGPT coding
#
# The 150-project review sample was drafted with ChatGPT. This compares Laura's blind
# coding of 30 of those projects (`reports/taxonomy_spot_check_coded.xlsx`) with
# ChatGPT's codes.
#
# The 30 over-sample hard cases (mentions and disagreements), so agreement here is a
# conservative estimate for the full 150.
#
# - Exact agreement = same Y / M / N answer
# - Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement); 1 = perfect, 0 = chance
# - Binary κ treats Y as positive and M or N as negative (substantive use)

# %%
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
REPORTS = ROOT / "reports"
book = REPORTS / "taxonomy_spot_check_coded.xlsx"
human = pd.read_excel(book, sheet_name="Spot check")
chatgpt = pd.read_excel(book, sheet_name="ChatGPT codes (open after)")
x = human.merge(chatgpt, on=["row", "appl_id"])
missing = x[["human_ds_related", "human_ai_related"]].isna().any(axis=1).sum()
print(f"{len(x)} projects; {missing} not yet coded (dropped)")
x = x.dropna(subset=["human_ds_related", "human_ai_related"]).copy()


# %%
def kappa(a: pd.Series, b: pd.Series) -> float:
    labels = sorted(set(a) | set(b))
    po = (a == b).mean()
    pe = sum((a == lab).mean() * (b == lab).mean() for lab in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


rows = []
for label in ["ds", "ai"]:
    h, g = x[f"human_{label}_related"].str.upper().str.strip(), x[f"chatgpt_{label}_related"]
    rows.append({"label": "Data science" if label == "ds" else "AI",
                 "exact agreement (Y/M/N)": (h == g).mean(),
                 "kappa (Y/M/N)": kappa(h, g),
                 "kappa (Y vs. M or N)": kappa(h.eq("Y"), g.eq("Y"))})
summary = pd.DataFrame(rows).round(2)
summary.to_csv(REPORTS / "spot_check_agreement.csv", index=False)
summary

# %% [markdown]
# ## Disagreements, by selection reason

# %%
x["ai_differs"] = x.human_ai_related.str.upper().str.strip() != x.chatgpt_ai_related
x["ds_differs"] = x.human_ds_related.str.upper().str.strip() != x.chatgpt_ds_related
print(x.groupby("why_selected")[["ds_differs", "ai_differs"]].mean().round(2))
x.loc[x.ai_differs | x.ds_differs,
      ["row", "why_selected", "human_ds_related", "chatgpt_ds_related",
       "human_ai_related", "chatgpt_ai_related", "notes"]]
