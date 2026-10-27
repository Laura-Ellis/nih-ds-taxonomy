# %% [markdown]
# # 19 Pipeline: keywords → Jev → Claude, Gemini, or ChatGPT
#
# 1. **Keywords** flag candidates (free).
# 2. **Jev** labels each flagged project and gives a confidence for each answer.
# 3. A **resolver** model relabels the answers where Jev is less than 90% confident.
#
# This compares three resolvers on the 150 coded projects: Claude (Anthropic API), Gemini (Google
# Gemini API), and ChatGPT (OpenAI API). Any of them can instead go through the Vercel AI Gateway
# (route "gateway", model IDs like "google/gemini-3.1-flash-lite"). Each resolver uses the same
# prompt and rules (`src/llm_label.py`). Each one labels all 150 projects, so each also gets a
# stand-alone score.
#
# **Setup:** `pip install openai`. Keys come from ~/KEYS.md: "### Anthropic", "### OpenAI",
# "### Google (Gemini)", and "### Vercel AI Gateway" (Jev). Check the model names in the first
# cell's list and edit `RESOLVERS` if a name differs.
#
# **Definitions**
# - Substantive = coded Y; precision = flagged and coded / flagged; recall = flagged and coded / coded
# - Cohen's κ = (observed agreement − chance agreement) / (1 − chance agreement)
# - Pipeline label = keyword flag AND (Jev answer if Jev confidence ≥ 0.90, else resolver answer)
# - Cost per 1,000 projects = tokens × price; edit `PRICES` (USD per 1M input / output tokens) as prices change

# %%
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import gateway_label as gw  # noqa: E402  # pyright: ignore[reportMissingImports]
import jev_label as jev  # noqa: E402  # pyright: ignore[reportMissingImports]
import llm_label as llm  # noqa: E402  # pyright: ignore[reportMissingImports]
import taxonomy as tx  # noqa: E402  # pyright: ignore[reportMissingImports]
from coding import kappa, load_coded  # noqa: E402  # pyright: ignore[reportMissingImports]

REPORTS, INTERIM = ROOT / "reports", ROOT / "data" / "interim"
CUTOFF = 0.90
JEV_MODEL = jev.DEFAULT_MODEL  # alias "typesafe-ai/jev" (version 1.14.0 at the time)
RESOLVERS = {  # name: (route, model id); routes: anthropic, gemini, openai, gateway
    "Claude": ("anthropic", "claude-sonnet-5-5"),
    "Gemini": ("gemini", "gemini-3.1-flash-lite"),
    "ChatGPT": ("openai", "gpt-6-luna"),
}
PRICES = {  # USD per 1M input / output tokens, standard (non-batch) rates
    "claude-sonnet-5-5": None,  # measured from the Anthropic Console: about $0.006 per project
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gpt-6-luna": (0.10, 0.50),
}

clients = {route: gw.make_client(route) for route, _ in RESOLVERS.values() if route != "anthropic"}
for name, (route, model) in RESOLVERS.items():
    if route == "anthropic":
        continue
    models = gw.available_models(clients[route])
    if model not in models:
        raise ValueError(f"{model} is not available on route '{route}'. Similar names: "
                         f"{[m for m in models if model.split('-')[0] in m][:15]}. Edit RESOLVERS.")
    print(f"{name}: {model} found on {route}")

# %% [markdown]
# ## Label the 150 coded projects

# %%
sample = pd.read_csv(sorted((ROOT / "data" / "raw").glob("reporter_sample_2*.csv"))[-1])
coded = load_coded(REPORTS)
val = sample[sample.appl_id.isin(coded.appl_id)]

x = coded.merge(tx.label_projects(val), on="appl_id").merge(
    jev.label_projects(val, INTERIM / "jev_labels.jsonl", model=JEV_MODEL), on="appl_id", how="left")
for name, (route, model) in RESOLVERS.items():
    if route == "anthropic":
        lab = llm.label_projects(val, INTERIM / "llm_labels.jsonl", model=model).rename(
            columns=lambda c: c.replace("llm_", f"{name.lower()}_"))
    else:
        cache = INTERIM / f"{model.replace('/', '_')}_labels.jsonl"
        lab = gw.label_projects(val, cache, model=model, prefix=name.lower(), client=clients[route])
    x = x.merge(lab, on="appl_id", how="left")
print(f"{len(x)} projects")

# %% [markdown]
# ## Compare: each resolver alone, and in the pipeline

# %%
rows = []
for label, short, kw_col, code_col in [("AI", "ai", "ai_related", "my_ai_related"),
                                       ("Data science", "ds", "data_science_related", "my_ds_related")]:
    truth = x[code_col].eq("Y")
    conf = x[f"jev_{short}_probs"].map(lambda p: max(p.values()) if isinstance(p, dict) and p else 0)
    uncertain = conf < CUTOFF
    candidates = {"Keywords": x[kw_col], "Jev": x[kw_col] & x[f"jev_{short}_related"].eq("Y")}
    for name in RESOLVERS:
        res = x[f"{name.lower()}_{short}_related"]
        candidates[f"{name} alone"] = res.eq("Y")
        final = x[f"jev_{short}_related"].where(~uncertain, res)
        candidates[f"Keywords → Jev → {name}"] = x[kw_col] & final.eq("Y")
    for method, pred in candidates.items():
        pred = pred.fillna(False).astype(bool)
        tp = (pred & truth).sum()
        rows.append({"label": label, "method": method, "kappa": round(kappa(pred, truth), 2),
                     "precision": round(tp / max(pred.sum(), 1), 2), "recall": round(tp / truth.sum(), 2),
                     "sent_to_resolver": int(uncertain.sum()) if "→" in method else None})
comparison = pd.DataFrame(rows)
comparison.to_csv(REPORTS / "pipeline_comparison_v0.4.csv", index=False)
comparison

# %% [markdown]
# ## Cost per 1,000 projects

# %%
cost_rows = []
for name, (route, model) in RESOLVERS.items():
    usage = x[f"{name.lower()}_usage"].dropna() if f"{name.lower()}_usage" in x else pd.Series(dtype=object)
    tin = usage.map(lambda u: (u or {}).get("input_tokens") or 0).mean() if len(usage) else None
    tout = usage.map(lambda u: (u or {}).get("output_tokens") or 0).mean() if len(usage) else None
    price = PRICES.get(model)
    per_project = 0.006 if price is None else (tin * price[0] + tout * price[1]) / 1e6
    cost_rows.append({"resolver": name, "model": model, "input_tokens": tin, "output_tokens": tout,
                      "alone_per_1000": round(per_project * 1000, 2),
                      "pipeline_per_1000": round(0.14 + per_project * 1000 * 0.11, 2)})  # Jev + 11% resolved (AI)
pd.DataFrame(cost_rows)

# %% [markdown]
# ## Where the resolvers disagree with the codes (uncertain AI calls only)

# %%
conf = x.jev_ai_probs.map(lambda p: max(p.values()) if isinstance(p, dict) and p else 0)
cols = ["appl_id", "project_title", "my_ai_related", "jev_ai_related"] + \
       [f"{n.lower()}_ai_related" for n in RESOLVERS]
x.loc[conf < CUTOFF, cols]
