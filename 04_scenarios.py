"""Step 4 - decarbonization scenarios, targeted at hotspot units. All assumptions are explicit parameters."""
import pandas as pd, numpy as np, json
OUT="/home/claude/project"
d = pd.read_csv(f"{OUT}/data/emissions_clean.csv", low_memory=False)
base_total = d.co2e_t.sum()

HEAT_UNITS = ["boiler","furnace","heater","dryer","kiln","oven","other combustion"]
ELEC_UNITS = ["boiler","heater","dryer","oven"]                    # low/medium-temperature heat -> electrifiable
# observed median emission factors in THIS dataset (t CO2e per MJ), per fuel
EF = d[d.qc_flag=="ok"].groupby("fuel").ef_t_per_mj.median()
EF_GAS = EF["naturalGas"]
GRID_T_PER_MWH = 0.37          # ASSUMPTION: US average grid intensity (verify against latest eGRID)
def run(top_share=0.20, eff=0.10, cop=3.0, grid=GRID_T_PER_MWH, switch=True, elec=True, effic=True):
    x = d.copy(); x["factor"] = 1.0
    elig = x.unit_type.isin(HEAT_UNITS) & (x.fuel != "biomass") & (x.fuel != "unknown")
    # hotspot targeting: top `top_share` of eligible units by CO2e within each unit_type
    rank = x[elig].groupby("unit_type").co2e_t.rank(pct=True, ascending=False)
    tgt = pd.Series(False, index=x.index); tgt[rank.index] = rank <= top_share
    x["target"] = tgt
    # (1) fuel switching: coal/coke/resid oil/diesel/'other' -> natural gas (ratio of observed EFs)
    fs = tgt & x.fuel.isin(["coal","coke","resFuelOil","diesel","gasoline","other"])
    ratio = (EF_GAS / x.fuel.map(EF)).clip(upper=1.0)
    if switch: x.loc[fs,"factor"] *= ratio[fs]
    # (2) electrification: gas-fired low/medium-temp units -> heat pumps (COP), grid-powered
    el = tgt & (x.fuel=="naturalGas") & x.unit_type.isin(ELEC_UNITS)
    ef_elec = (grid/3600.0)/cop                                   # t CO2e per MJ of heat delivered
    if elec: x.loc[el,"factor"] *= min(ef_elec/EF_GAS, 1.0)
    # (3) efficiency: energy use down by `eff` on all targeted units
    if effic: x.loc[tgt,"factor"] *= (1-eff)
    x["co2e_after"] = x.co2e_t * x.factor
    x["lever_fuel_switch"] = fs & switch; x["lever_electrify"] = el & elec
    return x
def pct(x): return round(100*(1 - x.co2e_after.sum()/base_total), 2)

out = {"baseline_Mt": round(base_total/1e6,1), "EF_t_per_MJ": {k: float(f"{v:.3e}") for k,v in EF.items() if k in ["naturalGas","coal","coke","resFuelOil","diesel","biomass","other"]}}
steps = {}
for nm,kw in [("S1 efficiency only",dict(switch=False,elec=False)),
              ("S2 efficiency + fuel switching",dict(elec=False)),
              ("S3 efficiency + fuel switching + electrification",{})]:
    steps[nm] = pct(run(**kw))
out["base_case_reduction_pct"] = steps
# sensitivity: targeting depth x grid intensity x efficiency (full package)
sens=[]
for ts in [0.10,0.20,0.30,0.50]:
    for eff in [0.05,0.10,0.15]:
        for g,lbl in [(0.37,"grid today 0.37"),(0.20,"grid cleaner 0.20")]:
            sens.append(dict(top_share=ts, efficiency=eff, grid=lbl, reduction_pct=pct(run(top_share=ts,eff=eff,grid=g))))
sens=pd.DataFrame(sens); sens.to_csv(f"{OUT}/outputs/tableau/scenario_sensitivity.csv", index=False)
out["sensitivity_range_pct"] = [float(sens.reduction_pct.min()), float(sens.reduction_pct.max())]
base = run()                                              # = S3 base case
out["units_targeted"] = int(base.target.sum()); out["share_of_units_targeted_pct"]=round(100*base.target.mean(),1)
out["share_of_baseline_emissions_in_targeted_units_pct"] = round(100*base.loc[base.target,"co2e_t"].sum()/base_total,1)
out["reduction_by_lever_Mt"] = {
  "fuel_switch": round((base[base.lever_fuel_switch].co2e_t - base[base.lever_fuel_switch].co2e_after).sum()/1e6,2),
  "electrification": round((base[base.lever_electrify].co2e_t - base[base.lever_electrify].co2e_after).sum()/1e6,2)}
out["total_reduction_Mt"] = round((base_total-base.co2e_after.sum())/1e6,1)
# non-targeted comparison: same package but spread randomly across the same NUMBER of eligible units
rng=np.random.default_rng(0); r=[]
for _ in range(20):
    x=base.copy(); elig=x.index[x.unit_type.isin(HEAT_UNITS)&~x.fuel.isin(["biomass","unknown"])]
    pick=rng.choice(elig, size=int(base.target.sum()), replace=False)
    t=pd.Series(False,index=x.index); t[pick]=True
    f=pd.Series(1.0,index=x.index); 
    f[t & x.fuel.isin(["coal","coke","resFuelOil","diesel","gasoline","other"])] *= (EF_GAS/x.fuel.map(EF)).clip(upper=1.0)
    f[t & (x.fuel=="naturalGas") & x.unit_type.isin(ELEC_UNITS)] *= min(((0.37/3600)/3)/EF_GAS,1.0)
    f[t]*=0.9; r.append(100*(1-(x.co2e_t*f).sum()/base_total))
out["same_package_random_targeting_pct"] = round(float(np.mean(r)),2)
json.dump(out, open(f"{OUT}/outputs/scenario_results.json","w"), indent=2)
print(json.dumps(out, indent=1))
# tableau tables
g = base.groupby("unit_type")[["co2e_t","co2e_after"]].sum().assign(reduction_t=lambda t:t.co2e_t-t.co2e_after).sort_values("reduction_t",ascending=False)
g.to_csv(f"{OUT}/outputs/tableau/scenario_by_unit_type.csv")
base.groupby("industry")[["co2e_t","co2e_after"]].sum().assign(reduction_t=lambda t:t.co2e_t-t.co2e_after).sort_values("reduction_t",ascending=False).to_csv(f"{OUT}/outputs/tableau/scenario_by_industry.csv")
base.to_csv(f"{OUT}/outputs/tableau/units_with_scenario.csv", index=False)
print(g.head(8).round(0))
