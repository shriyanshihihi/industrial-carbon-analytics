# Industrial Carbon Analytics (FIED 2017) - run order
Data: NREL/Argonne Foundational Industry Energy Dataset 2017 (CC BY 4.0), https://data.openei.org/submissions/6158
1. python 01_prepare.py <fied_units.csv>   -> data/emissions_clean.csv + data/fied.db (SQLite)
2. python 02_run_sql.py                     -> runs sql/hotspots.sql, writes outputs/tableau/q*.csv
3. python 03_model.py                       -> ridge + gradient boosting + SHAP; outputs/model_results.json, charts
4. python 04_scenarios.py                   -> scenario results, sensitivity grid, Tableau tables
5. python 05_charts.py                      -> pareto / hotspot / scenario charts
Needs: pandas numpy scikit-learn shap matplotlib statsmodels (sqlite3 is built in)

## Data note
`data/emissions_clean.csv` and `data/fied.db` are derived from NREL/Argonne FIED 2017 (CC BY 4.0). Citation: McMillan, Schoeneberger, Supekar, Thierry (2024), NREL/TP-6A20-90442.
Emission values for NEI-derived rows are modelled estimates; see the cleaning rules in `01_prepare.py`.
Scenario results are projections under stated assumptions, not forecasts.
