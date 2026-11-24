import sqlite3, pandas as pd, re
con = sqlite3.connect("/home/claude/project/data/fied.db")
sql = open("/home/claude/project/sql/hotspots.sql").read()
blocks = [b.strip() for b in re.split(r"-- =====", sql) if b.strip()]
for i, b in enumerate(blocks, 1):
    title, query = b.split("\n", 1)
    df = pd.read_sql(query, con)
    df.to_csv(f"/home/claude/project/outputs/tableau/q{i}_{re.sub(r'[^a-z0-9]+','_',title.lower().split('=')[0].strip())[:30]}.csv", index=False)
    print(f"\n### Q{i}: {title.strip(' =')}"); print(df.to_string(index=False))
