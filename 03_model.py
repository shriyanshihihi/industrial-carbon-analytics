"""
STEP 3 - MODEL: answer "WHY do some units emit so much more?"

IN PLAIN WORDS
  Trains two regression models to predict log10 of a unit's CO2e, then uses SHAP to see which inputs the
  model relies on. Two versions: A uses energy as an input, B does not.

INPUT   : data/emissions_clean.csv (only rows that passed both quality flags: 42,692)
OUTPUT  : outputs/model_results.json, outputs/charts/shap_*.png, outputs/tableau/model_B_pred_vs_actual.csv

KEY DECISIONS (be ready to defend each)
  - Target is log10(CO2e): emissions span a few tonnes to over a million, so errors become relative.
  - Train/test split is BY FACILITY: units in one plant are similar; a random split would leak and inflate the score.
  - Ridge = simple baseline. Gradient boosting (300 trees, depth 4, rate 0.08) = stronger non-linear model.
  - Model A (with energy) scores 0.999 but that is arithmetic (CO2e = energy x emission factor), so it is only a
    consistency check. Model B (no energy) is the REAL result: R2 0.62 (boosting) vs 0.53 (Ridge) on unseen facilities.
  - SHAP (model B): fuel 0.56, capacity 0.51, state 0.27, unit type 0.26, industry 0.25, hours 0.12.
    It shows what the model relies on, NOT what causes emissions.
  - Hyperparameters were set to sensible fixed values, not formally tuned.

CV LINK : "Built regression models & SHAP feature analysis ... fuel, energy and operating variables".
IF REMOVED: no evidence about drivers.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))   # project folder, so the scripts run from anywhere

import pandas as pd, numpy as np, json, shap, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupShuffleSplit
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
OUT=ROOT
d = pd.read_csv(f"{OUT}/data/emissions_clean.csv", low_memory=False)
d = d[(d.qc_flag=="ok") & (d.capacity_flag=="ok")].copy()        # trusted rows only
print("training pool:", len(d))

y = np.log10(d.co2e_t)
X = pd.DataFrame(index=d.index)
X["log_energy_mj"]   = np.log10(d.energy_mj)
X["log_capacity_mw"] = np.log10(d.capacity_mw.where(d.capacity_mw > 0))
X["capacity_missing"]= d.capacity_mw.isna().astype(int)
X["weekly_op_hours"] = d.weekly_op_hours
X["ops_missing"]     = d.weekly_op_hours.isna().astype(int)
def topcat(s, n): 
    keep = s.value_counts().head(n).index; return s.where(s.isin(keep), "other_")
cat = pd.concat([ "fuel_"+d.fuel, "unit_"+d.unit_type, "industry_"+topcat(d.industry.astype(str),12),
                  "state_"+topcat(d.state,12), "src_"+d.source ], axis=1)
dummies = pd.concat([pd.get_dummies(cat[c], dtype=int) for c in cat.columns], axis=1)
X = pd.concat([X, dummies], axis=1)
X["log_capacity_mw"] = X.log_capacity_mw.fillna(X.log_capacity_mw.median())
X["weekly_op_hours"] = X.weekly_op_hours.fillna(X.weekly_op_hours.median())

groups = d.registryID.values                                           # split by FACILITY -> no leakage
tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups))
def group_of(c):
    if c=="log_energy_mj": return "Energy use"
    if c in("log_capacity_mw","capacity_missing"): return "Design capacity"
    if c in("weekly_op_hours","ops_missing"): return "Operating hours"
    for p,n in [("fuel_","Fuel type"),("unit_","Unit type"),("industry_","Industry (NAICS)"),("state_","State"),("src_","Data source")]:
        if c.startswith(p): return n
res = {}
for name, drop in [("A_with_energy", []), ("B_without_energy", ["log_energy_mj"])]:
    Xs = X.drop(columns=drop)
    sc = StandardScaler().fit(Xs.iloc[tr]); 
    ridge = Ridge(alpha=1.0).fit(sc.transform(Xs.iloc[tr]), y.iloc[tr])
    p_r = ridge.predict(sc.transform(Xs.iloc[te]))
    gbr = GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.08, subsample=0.8, random_state=42).fit(Xs.iloc[tr], y.iloc[tr])
    p_g = gbr.predict(Xs.iloc[te])
    yt = y.iloc[te]
    f = lambda p: dict(R2=round(r2_score(yt,p),3), MAE_log10=round(mean_absolute_error(yt,p),3),
                       typical_error_factor=round(10**mean_absolute_error(yt,p),2))
    res[name] = {"ridge": f(p_r), "gbr": f(p_g), "n_train": len(tr), "n_test": len(te)}
    # SHAP on a test sample
    samp = Xs.iloc[te].sample(min(4000,len(te)), random_state=1)
    sv = shap.TreeExplainer(gbr).shap_values(samp)
    imp = pd.Series(np.abs(sv).mean(0), index=Xs.columns)
    grp = imp.groupby(imp.index.map(group_of)).sum().sort_values(ascending=False)
    res[name]["shap_group_importance_log10"] = grp.round(4).to_dict()
    # direction for fuel / unit-type dummies
    sv_df = pd.DataFrame(sv, columns=Xs.columns, index=samp.index)
    eff = {c: round(float(sv_df.loc[samp[c]==1, c].mean() - sv_df.loc[samp[c]==0, c].mean()),3)
           for c in Xs.columns if c.startswith(("fuel_","unit_")) and samp[c].sum()>30}
    res[name]["shap_category_effect_log10"] = dict(sorted(eff.items(), key=lambda kv: -kv[1]))
    fig, ax = plt.subplots(figsize=(7,3.6)); grp[::-1].plot.barh(ax=ax, color="#2a6f97")
    ax.set_xlabel("Mean |SHAP| (log10 tonnes CO2e)"); ax.set_title(f"What drives unit CO2e? ({name.replace('_',' ')})")
    plt.tight_layout(); plt.savefig(f"{OUT}/outputs/charts/shap_{name}.png", dpi=160); plt.close()
    shap.summary_plot(sv, samp, max_display=12, show=False); plt.tight_layout()
    plt.savefig(f"{OUT}/outputs/charts/shap_beeswarm_{name}.png", dpi=140, bbox_inches="tight"); plt.close()
    if name=="B_without_energy":
        pd.DataFrame({"actual_log10":yt.values,"pred_log10":p_g}).to_csv(f"{OUT}/outputs/tableau/model_B_pred_vs_actual.csv", index=False)
json.dump(res, open(f"{OUT}/outputs/model_results.json","w"), indent=2)
print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!="shap_category_effect_log10"} for k,v in res.items()}, indent=1))
print("B fuel/unit effects:", json.dumps(res["B_without_energy"]["shap_category_effect_log10"], indent=0)[:900])
