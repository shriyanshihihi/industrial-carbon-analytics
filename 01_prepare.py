"""
STEP 1 - PREPARE: turn the raw FIED file into one clean, trustworthy table.

IN PLAIN WORDS
  The raw data has many blank and wrong values. This step fixes that and writes ONE clean table that every
  later step reads. If this step is wrong, everything after it is wrong.

INPUT   : fied_units.csv (unit-level FIED 2017 rows; make it with 00_extract_units.py)
OUTPUT  : data/emissions_clean.csv and data/fied.db (SQLite table "emissions")

WHAT HAPPENS (in order)
  1. Take CO2e from the reported column; where blank, use the NEI median estimate (Q2 column).
     -> usable rows go from 12,967 to 55,568.  (supports the "50K+ records" claim)
  2. Drop zero-emission rows (1,702).
  3. RULE A - plausibility cap: 3 Mt per unit for GHGRP-reported rows, 1 Mt for modelled rows (218 dropped).
     Why: before the cap the total was ~79,600 Mt, far above the real industrial figure, so the NEI file
     contains unit-conversion errors. The biggest reported unit is 1.6 Mt, so modelled values above 1 Mt are suspect.
  4. RULE B - flags (rows are KEPT, only marked): emission factor outside 1e-5..3e-4 t/MJ, and energy above
     100x nameplate capacity at full load. Capacities are often placeholders, so we flag instead of deleting.
  5. Build features: industry from the NAICS code, capacity in MW, average weekly operating hours.

CV LINK : "Analyzed 50K+ industrial emission records" -> final count 53,648 records, 707.8 Mt CO2e.
SAY IT  : "Most of the work was making the data trustworthy: I capped impossible values and flagged doubtful rows."
IF REMOVED: hotspots would be fake (a coffee roaster at 2 Mt, total 79,600 Mt).
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))   # project folder, so the scripts run from anywhere

import pandas as pd, numpy as np, sqlite3, sys
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "raw", "fied_units.csv")
if not os.path.exists(SRC):
    sys.exit(f"Input not found: {SRC}\nRun 00_extract_units.py first, or pass the path: python 01_prepare.py <fied_units.csv>")
OUT = ROOT

df = pd.read_csv(SRC, low_memory=False)
print("unit-level rows loaded:", len(df))

# CO2e / energy: GHGRP-reported value where available, else NEI-derived median estimate (Q2)
df["co2e_t"]   = df.ghgsTonneCO2e.fillna(df.ghgsTonneCO2eQ2)
df["energy_mj"] = df.energyMJ.fillna(df.energyMJq2)
df["source"]   = df.ghgsEstimateSource.fillna("ghgrp_unit_est")   # blank = derived from GHGRP fuel use
df = df[df.co2e_t.notna()].copy()
print("rows with an emissions value:", len(df))

# --- data-quality rules -------------------------------------------------------------
df = df[df.co2e_t > 0]
print("after dropping zero CO2e:", len(df))
# Rule A: plausibility cap. Measured GHGRP values may go up to 3 Mt (max reported ~1.6 Mt);
#         modelled NEI-derived values are capped at 1 Mt (~1.5x the GHGRP 99th percentile of 0.67 Mt).
cap = np.where(df.source == "ghgrp", 3e6, 1e6)
n_over = (df.co2e_t > cap).sum()
df = df[df.co2e_t <= cap]
print(f"Rule A: dropped {n_over} rows above the plausibility cap; kept {len(df)}")

# Rule B (FLAG only): nameplate capacities in the source are often placeholders (e.g. 2.93 MW = default 10 MMBtu/hr),
#   so we do not delete on it. Units claiming >100x full-load energy at nameplate are flagged and kept out of model training.
cap_mw = np.where(df.designCapacityUOM == "MW", df.designCapacity, np.nan)
full_load_mj = cap_mw * 3600 * 8760
df["capacity_flag"] = np.where((df.energy_mj / full_load_mj) > 100, "capacity_implausible", "ok")
print("capacity_flag:", df.capacity_flag.value_counts().to_dict())

ef = df.co2e_t / df.energy_mj                      # t CO2e per MJ
df["ef_t_per_mj"] = ef
df["qc_flag"] = np.where(ef.isna(), "no_energy",
                 np.where((ef >= 1e-5) & (ef <= 3e-4), "ok", "energy_inconsistent"))
print(df.qc_flag.value_counts().to_string())

# --- features ------------------------------------------------------------------------
df["naics6"] = df.naicsCode.astype("Int64")
df["naics3"] = (df.naicsCode // 1000).astype("Int64")
NAICS3 = {211:"Oil & gas extraction",212:"Mining (non-oil)",221:"Utilities",311:"Food mfg",312:"Beverage & tobacco",
 313:"Textile mills",321:"Wood products",322:"Paper",324:"Petroleum & coal products",325:"Chemicals",326:"Plastics & rubber",
 327:"Nonmetallic minerals (cement, lime)",331:"Primary metals",332:"Fabricated metals",333:"Machinery",334:"Computers & electronics",
 335:"Electrical equipment",336:"Transportation equipment",337:"Furniture",339:"Misc. mfg",486:"Pipeline transport",562:"Waste mgmt",
 622:"Hospitals",611:"Education",928:"National security",221:"Utilities",454:"Nonstore retail",488:"Transport support"}
df["industry"] = df.naics3.map(NAICS3).fillna("Other (NAICS " + df.naics3.astype(str) + ")")
df["capacity_mw"] = np.where(df.designCapacityUOM == "MW", df.designCapacity, np.nan)
hrs = df[["weeklyOpHours_q1","weeklyOpHours_q2","weeklyOpHours_q3","weeklyOpHours_q4"]]
df["weekly_op_hours"] = hrs.mean(axis=1)
df["unit_type"] = df.unitTypeStd.fillna("unknown")
df["fuel"] = df.fuelTypeStd.fillna("unknown")
df["state"] = df.stateCode.fillna("NA")
df["facility"] = df["name"].fillna("(unnamed)")
df = df.reset_index(drop=True); df["unit_row_id"] = df.index + 1

keep = ["unit_row_id","registryID","facility","state","naics6","naics3","industry","unit_type","fuel","capacity_mw",
        "weekly_op_hours","energy_mj","co2e_t","ef_t_per_mj","source","qc_flag","capacity_flag","latitude","longitude"]
clean = df[keep]
clean.to_csv(f"{OUT}/data/emissions_clean.csv", index=False)

con = sqlite3.connect(f"{OUT}/data/fied.db")
clean.to_sql("emissions", con, if_exists="replace", index=False)
con.execute("CREATE INDEX ix_fuel ON emissions(fuel)"); con.execute("CREATE INDEX ix_unit ON emissions(unit_type)")
con.commit(); con.close()
print("saved", len(clean), "rows; total CO2e (Mt):", round(clean.co2e_t.sum()/1e6, 1))
