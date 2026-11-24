import pandas as pd, numpy as np, matplotlib, sqlite3
matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT="/home/claude/project"; d=pd.read_csv(f"{OUT}/data/emissions_clean.csv", low_memory=False)
C="#2a6f97"
# 1 Pareto
s=np.sort(d.co2e_t.values)[::-1]; cum=np.cumsum(s)/s.sum(); x=np.arange(1,len(s)+1)/len(s)*100
fig,ax=plt.subplots(figsize=(6.5,3.8)); ax.plot(x,cum*100,color=C,lw=2)
for p in (5,10): ax.annotate(f"top {p}% of units = {cum[int(len(s)*p/100)-1]*100:.0f}%", (p,cum[int(len(s)*p/100)-1]*100), (p+12,cum[int(len(s)*p/100)-1]*100-18), arrowprops=dict(arrowstyle="-",color="grey"))
ax.set_xlabel("% of units (ranked by CO2e)"); ax.set_ylabel("Cumulative % of CO2e"); ax.set_title("Emissions are highly concentrated"); plt.tight_layout(); plt.savefig(f"{OUT}/outputs/charts/pareto.png",dpi=160); plt.close()
# 2 unit type / fuel bars
fig,axs=plt.subplots(1,2,figsize=(10,3.8))
for ax,col,t in [(axs[0],"unit_type","By unit type"),(axs[1],"fuel","By fuel")]:
    g=(d.groupby(col).co2e_t.sum()/1e6).sort_values().tail(8); g.plot.barh(ax=ax,color=C); ax.set_title(t); ax.set_xlabel("Mt CO2e")
plt.tight_layout(); plt.savefig(f"{OUT}/outputs/charts/hotspots_unit_fuel.png",dpi=160); plt.close()
# 3 scenario steps
import json; r=json.load(open(f"{OUT}/outputs/scenario_results.json"))["base_case_reduction_pct"]
fig,ax=plt.subplots(figsize=(6.5,3.6)); ax.bar([k.replace(" + ","\n+ ") for k in r],list(r.values()),color=C)
ax.set_ylim(0,17); ax.axhline(15,ls="--",color="grey"); ax.text(-0.45,15.4,"15% CV target",ha="left",color="grey")
for i,v in enumerate(r.values()): ax.text(i,v+.3,f"{v:.1f}%",ha="center")
ax.set_ylabel("% reduction vs baseline"); ax.set_title("Scenario build-up (today's grid)"); plt.tight_layout(); plt.savefig(f"{OUT}/outputs/charts/scenario_steps.png",dpi=160); plt.close()
# independent verification of headline numbers (pandas vs SQLite)
con=sqlite3.connect(f"{OUT}/data/fied.db"); q=lambda s:con.execute(s).fetchone()[0]
assert q("select count(*) from emissions")==len(d)==53648
assert abs(q("select sum(co2e_t) from emissions")-d.co2e_t.sum())<1
print("verified: rows",len(d),"| total Mt",round(d.co2e_t.sum()/1e6,1),"| top5% share",round(cum[int(len(s)*.05)-1]*100,1))
