-- ===== Q1: overall picture by data source =====
SELECT source, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e,
       ROUND(100.0*SUM(co2e_t)/(SELECT SUM(co2e_t) FROM emissions),1) AS pct_total
FROM emissions GROUP BY source ORDER BY mt_co2e DESC;

-- ===== Q2: emissions by fuel =====
SELECT fuel, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e,
       ROUND(100.0*SUM(co2e_t)/(SELECT SUM(co2e_t) FROM emissions),1) AS pct_total,
       ROUND(AVG(co2e_t),0) AS avg_t_per_unit
FROM emissions GROUP BY fuel ORDER BY mt_co2e DESC;

-- ===== Q3: emissions by process unit type =====
SELECT unit_type, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e,
       ROUND(100.0*SUM(co2e_t)/(SELECT SUM(co2e_t) FROM emissions),1) AS pct_total,
       ROUND(AVG(co2e_t),0) AS avg_t_per_unit
FROM emissions GROUP BY unit_type ORDER BY mt_co2e DESC;

-- ===== Q4: emissions by industry (NAICS-3) =====
SELECT industry, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e,
       ROUND(100.0*SUM(co2e_t)/(SELECT SUM(co2e_t) FROM emissions),1) AS pct_total
FROM emissions GROUP BY industry ORDER BY mt_co2e DESC LIMIT 15;

-- ===== Q5: top 15 states =====
SELECT state, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e
FROM emissions WHERE state <> 'NA' GROUP BY state ORDER BY mt_co2e DESC LIMIT 15;

-- ===== Q6: Pareto - how concentrated are emissions? (window functions) =====
WITH ranked AS (
  SELECT co2e_t,
         ROW_NUMBER() OVER (ORDER BY co2e_t DESC) AS rn,
         COUNT(*) OVER () AS n,
         SUM(co2e_t) OVER (ORDER BY co2e_t DESC ROWS UNBOUNDED PRECEDING) AS cum,
         SUM(co2e_t) OVER () AS total
  FROM emissions)
SELECT 'top 1% of units' AS slice, ROUND(100.0*MAX(cum)/MAX(total),1) AS pct_of_co2e FROM ranked WHERE rn <= n*0.01
UNION ALL SELECT 'top 5% of units', ROUND(100.0*MAX(cum)/MAX(total),1) FROM ranked WHERE rn <= n*0.05
UNION ALL SELECT 'top 10% of units', ROUND(100.0*MAX(cum)/MAX(total),1) FROM ranked WHERE rn <= n*0.10
UNION ALL SELECT 'top 20% of units', ROUND(100.0*MAX(cum)/MAX(total),1) FROM ranked WHERE rn <= n*0.20;

-- ===== Q7: hotspot combos - unit type x fuel (min 30 units) =====
SELECT unit_type, fuel, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,2) AS mt_co2e,
       ROUND(AVG(co2e_t),0) AS avg_t_per_unit
FROM emissions GROUP BY unit_type, fuel HAVING COUNT(*) >= 30 ORDER BY mt_co2e DESC LIMIT 15;

-- ===== Q8: top 20 facilities =====
SELECT facility, state, industry, COUNT(*) AS units, ROUND(SUM(co2e_t)/1e6,2) AS mt_co2e
FROM emissions GROUP BY registryID, facility, state, industry ORDER BY mt_co2e DESC LIMIT 20;

-- ===== Q9: units that are hotspots WITHIN their industry (top decile via NTILE) =====
WITH t AS (SELECT *, NTILE(10) OVER (PARTITION BY naics3 ORDER BY co2e_t DESC) AS decile FROM emissions)
SELECT industry, COUNT(*) AS hotspot_units, ROUND(SUM(co2e_t)/1e6,1) AS mt_co2e
FROM t WHERE decile = 1 GROUP BY industry ORDER BY mt_co2e DESC LIMIT 10;
