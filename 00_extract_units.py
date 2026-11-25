"""
STEP 0 (one-time) - EXTRACT: shrink the big FIED download into the unit-level file used by Step 1.

HOW TO GET THE DATA
  Download "FIED 2017 Unit- and Facility-level Industrial Energy Data.csv" from
  https://data.openei.org/submissions/6158  (file name: foundational_industry_data_2017.csv, CC BY 4.0).

USAGE   : python 00_extract_units.py <path to foundational_industry_data_2017.csv>
OUTPUT  : data/raw/fied_units.csv  (165,298 unit-level rows, 29 columns)

WHY     : the raw file has 644,881 rows, mostly facility-only rows with no unit data. We keep only the columns we
          need and only unit-level rows. The Q0/Q2/Q3 columns hold the NEI-derived estimates and MUST be kept:
          without them only 12,967 rows have a CO2e value.
"""
import os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python 00_extract_units.py <path to foundational_industry_data_2017.csv>")

COLS = ["registryID","name","stateCode","naicsCode","latitude","longitude",
        "eisUnitID","unitType","unitTypeStd","processDescription",
        "fuelTypeStd","fuelType","designCapacity","designCapacityUOM",
        "energyMJ","energyMJq0","energyMJq2","energyMJq3",
        "ghgsTonneCO2e","ghgsTonneCO2eQ0","ghgsTonneCO2eQ2","ghgsTonneCO2eQ3",
        "throughputTonneQ2","energyEstimateSource","ghgsEstimateSource",
        "weeklyOpHours_q1","weeklyOpHours_q2","weeklyOpHours_q3","weeklyOpHours_q4"]
df = pd.read_csv(sys.argv[1], usecols=COLS, low_memory=False)
df = df[df.unitTypeStd.notna() | df.eisUnitID.notna()]        # unit-level rows only
print("unit-level rows:", len(df))
print("rows with ANY CO2e (reported or NEI Q2):", df[["ghgsTonneCO2e","ghgsTonneCO2eQ2"]].notna().any(axis=1).sum())
os.makedirs(os.path.join(ROOT, "data", "raw"), exist_ok=True)
df.to_csv(os.path.join(ROOT, "data", "raw", "fied_units.csv"), index=False)
