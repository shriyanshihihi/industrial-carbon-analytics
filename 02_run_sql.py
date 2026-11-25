"""
STEP 2 - RUN THE SQL: answer "WHERE is the carbon coming from?"

IN PLAIN WORDS
  Runs the nine queries in sql/hotspots.sql against the SQLite database and saves each result as a CSV
  (for Tableau) and prints it (saved to outputs/sql_results.txt).

INPUT   : data/fied.db, sql/hotspots.sql
OUTPUT  : outputs/tableau/q1..q9 CSV files

THE NINE QUERIES: by data source, fuel, unit type, industry, state; Pareto concentration (window functions);
  unit-type x fuel combinations; top facilities; within-industry hotspot decile (NTILE).

CV LINK : "using SQL ... to identify carbon hotspots across process units".
KEY RESULT : top 5% of units = 76.4% of CO2e; natural gas 53%; boilers 20%; chemicals 20%.
SAY IT  : "SQL answers aggregation questions; the Pareto uses a running total so I can say what share the top units hold."
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))   # project folder, so the scripts run from anywhere

import sqlite3, pandas as pd, re
con = sqlite3.connect(os.path.join(ROOT,"data","fied.db"))
sql = open(os.path.join(ROOT,"sql","hotspots.sql")).read()
blocks = [b.strip() for b in re.split(r"-- =====", sql) if b.strip()]
for i, b in enumerate(blocks, 1):
    title, query = b.split("\n", 1)
    df = pd.read_sql(query, con)
    df.to_csv(f"{ROOT}/outputs/tableau/q{i}_{re.sub(r'[^a-z0-9]+','_',title.lower().split('=')[0].strip())[:30]}.csv", index=False)
    print(f"\n### Q{i}: {title.strip(' =')}"); print(df.to_string(index=False))
