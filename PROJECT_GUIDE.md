# Industrial Carbon Analytics - read this first

You do not need to remember anything about how this was built. This page tells you what each part does,
what it proves, and how to talk about it accurately.

## One-paragraph summary
Public US data on ~54,000 industrial combustion units (boilers, furnaces, kilns...). SQL shows **where** the carbon
is (top 5% of units = 76% of CO2e). Regression + SHAP show **what drives** a unit's emissions (fuel and size).
A scenario model shows **what if** the worst units are cut (12.1% today, 16.0% on a cleaner grid).

## Run order (each script starts with a plain-language header explaining itself)
| Step | File | Question it answers | Key output |
|---|---|---|---|
| 0 | `00_extract_units.py` | (one-time) shrink the raw download | `data/raw/fied_units.csv` |
| 1 | `01_prepare.py` | Can I trust the data? | 53,648 clean records, 707.8 Mt |
| 2 | `02_run_sql.py` + `sql/hotspots.sql` | Where is the carbon? | top 5% of units = 76.4% |
| 3 | `03_model.py` | Why do units differ? | R2 0.62 without energy; SHAP drivers |
| 4 | `04_scenarios.py` | What if we cut? | 12.1% / 16.0% / range 8.4-19.6% |
| 5 | `05_charts.py` | Show me | 3 charts + totals self-check |

## The numbers to know
644,881 raw rows -> 165,298 unit-level -> 55,568 with CO2e -> **53,648 kept**. Total 707.8 Mt CO2e.
Sources of emissions kept: GHGRP-reported 14.6%, unit-estimated 45.4%, NEI-modelled 40.0%.
Natural gas 53%, boilers 20%, chemicals 20%. Texas 105 Mt, California 72 Mt.
Model with energy R2 0.999 (arithmetic, only a consistency check); **without energy 0.62** (Ridge 0.53).
Scenario: 5,596 targeted units (10.4% of units, 50.6% of emissions); random targeting of the same count gives 2.6%.

## CV claim -> where it lives -> safe wording
| CV claim | Evidence in this project | Say it like this |
|---|---|---|
| Analyzed 50K+ industrial emission records using SQL & Python | 53,648 clean records; `sql/hotspots.sql`; steps 1-2 | "53,648 unit-level records after cleaning, out of 55,568 with an emission value." |
| identify carbon hotspots across process units | Pareto and unit-type, fuel, industry cuts | "The top 5% of units hold 76% of CO2e; boilers, furnaces and other combustion units lead." |
| Built regression models & SHAP feature analysis on fuel, energy and operating variables | `03_model.py` | "Ridge and gradient boosting on log CO2e, split by facility. Fuel and capacity matter most. SHAP shows what the model relies on, not cause." |
| Tableau dashboards | Tableau-ready CSVs in `outputs/tableau/` | **Only claim dashboards you have built.** The data tables are ready; the workbook is not in this repo. |
| 15%+ projected emission reduction | `04_scenarios.py` | "A projection: 12.1% on today's grid and up to about 16% on a cleaner grid, with assumptions listed." |

## Limits to state yourself
Most emissions are modelled (40% NEI-derived). One year (2017). No cost model. Some capacities are placeholders.
The 15% figure needs a cleaner-grid assumption. "Process units" are combustion units; "CO2" is CO2-equivalent.

## Provenance
Data: NREL/Argonne FIED 2017 (CC BY 4.0). Citation: McMillan, Schoeneberger, Supekar, Thierry (2024), NREL/TP-6A20-90442.
This codebase was created in November 2026; the git history shows that. Questions about when or with whom a project
was done are about you, not this code - answer those from your own experience.

## SQLite vs MySQL
The scripts run the SQL in **SQLite** (a file database, no server) so the project works with no setup.
The queries are standard SQL, so the same `sql/hotspots.sql` also runs in **MySQL 8+**: load the data with
`sql/mysql_setup.sql`, then run `sql/hotspots.sql` in MySQL. Say you used MySQL only if you have actually run it there.
