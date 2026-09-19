#!/usr/bin/env python3
"""Pre-registered secondary analysis on the existing 8k data (pilot/runs/code1).

Are the eight items cut off 4-for-4 explained by additive sector + country main effects,
or do they need a sector x country interaction? Read-only.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

RUN = "/ssd/ai_works/evaluvator/pilot/runs/code1"
pd.set_option("display.width", 200)

s = pd.read_csv(f"{RUN}/scores.csv")
g = s[(s.target == "glm-5.3-flash@z-ai") & (s.task == "tls_client")].copy()
g["cut"] = g.finish_reason.eq("length").astype(int)
print(f"rows: {len(g)}  cut off: {g.cut.sum()}")

# The no-customer rows have sector "none" and country "none": they are one cell, not a crossing,
# so they carry no interaction information. Keep them for the main-effect fit; the interaction
# fit uses only the 6 x 7 crossed design.
crossed = g[g.sector != "none"].copy()
print(f"crossed design (sector != none): {len(crossed)} rows, "
      f"{crossed.sector.nunique()} sectors x {crossed.country.nunique()} countries")

add = smf.glm("cut ~ C(sector) + C(country)", data=crossed,
              family=sm.families.Binomial()).fit()
inter = smf.glm("cut ~ C(sector) * C(country)", data=crossed,
                family=sm.families.Binomial()).fit()

print("\n-- additive model: cut ~ sector + country")
print(f"df_model={add.df_model:.0f}  llf={add.llf:.3f}  deviance={add.deviance:.3f}  AIC={add.aic:.2f}")
print("\n-- interaction model: cut ~ sector * country")
print(f"df_model={inter.df_model:.0f}  llf={inter.llf:.3f}  deviance={inter.deviance:.3f}  AIC={inter.aic:.2f}")

lr = 2 * (inter.llf - add.llf)
ddf = int(inter.df_model - add.df_model)
p_lr = stats.chi2.sf(lr, ddf)
print(f"\nlikelihood-ratio test, interaction vs additive: "
      f"LR={lr:.2f}, extra parameters={ddf}, p={p_lr:.4f}")
print(f"AIC favours the {'interaction' if inter.aic < add.aic else 'additive'} model "
      f"(additive {add.aic:.1f} vs interaction {inter.aic:.1f})")

print("\n-- additive model coefficients (log-odds of being cut off)")
coef = pd.DataFrame({"coef": add.params, "se": add.bse, "p": add.pvalues}).round(3)
print(coef.to_string())

# ---- how well does the additive model predict the 4-for-4 items?
crossed["p_hat"] = add.predict(crossed)
item = crossed.groupby(["item", "sector", "country"]).agg(
    n=("cut", "size"), cut=("cut", "sum"), p_hat=("p_hat", "mean")).reset_index()
item["observed_rate"] = item.cut / item.n
# probability of seeing 4 of 4 (or 0 of 4) under the additive model
item["p_all4_additive"] = item.p_hat ** item.n
item["p_none_additive"] = (1 - item.p_hat) ** item.n

full = item[item.cut == item.n].sort_values("p_hat", ascending=False)
print(f"\n-- the {len(full)} items cut off 4-for-4, under the additive model")
print(full[["item", "sector", "country", "n", "cut", "p_hat", "p_all4_additive"]].round(3).to_string(index=False))
print(f"\nexpected number of 4-for-4 items under the additive model: "
      f"{item.p_all4_additive.sum():.2f}   observed: {len(full)}")

none_items = item[item.cut == 0]
print(f"expected number of 0-for-4 items under the additive model: "
      f"{item.p_none_additive.sum():.2f}   observed: {len(none_items)}")

# ---- a direct goodness-of-fit check: does the additive model leave item-level structure behind?
# Compare observed per-item counts with the additive model's predicted counts.
obs = item.cut.to_numpy()
exp = (item.p_hat * item.n).to_numpy()
var = (item.p_hat * (1 - item.p_hat) * item.n).to_numpy()
z = (obs - exp) / np.sqrt(var)
chi2_gof = float((z ** 2).sum())
ddf_gof = len(item) - int(add.df_model) - 1
print(f"\nitem-level goodness of fit of the additive model: chi2={chi2_gof:.2f}, "
      f"dof={ddf_gof}, p={stats.chi2.sf(chi2_gof, ddf_gof):.4f}  "
      f"(each item has n=4, so this is a rough guide, not an exact test)")
print("\nitems the additive model fits worst (standardised residual):")
item["resid_z"] = z
print(item.reindex(item.resid_z.abs().sort_values(ascending=False).index)
      [["item", "sector", "country", "cut", "p_hat", "resid_z"]].head(8).round(3).to_string(index=False))
