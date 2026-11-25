-- MYSQL SETUP (MySQL 8.0 or newer: the queries use window functions and NTILE)
-- Run this once to load data/emissions_clean.csv into MySQL, then run sql/hotspots.sql (it works unchanged in MySQL 8).
-- NOTE: written for MySQL 8 but not tested against a live server in the session that created it - run it and check
--       the row count (should be 53648) and the total (707.8 Mt) before relying on it.

CREATE DATABASE IF NOT EXISTS carbon;
USE carbon;

DROP TABLE IF EXISTS emissions;
CREATE TABLE emissions (
  unit_row_id     INT,
  registryID      DOUBLE,
  facility        VARCHAR(255),
  state           VARCHAR(8),
  naics6          INT,
  naics3          INT,
  industry        VARCHAR(80),
  unit_type       VARCHAR(40),
  fuel            VARCHAR(30),
  capacity_mw     DOUBLE,
  weekly_op_hours DOUBLE,
  energy_mj       DOUBLE,
  co2e_t          DOUBLE,
  ef_t_per_mj     DOUBLE,
  source          VARCHAR(20),
  qc_flag         VARCHAR(30),
  capacity_flag   VARCHAR(30),
  latitude        DOUBLE,
  longitude       DOUBLE
);

-- If you get "LOAD DATA LOCAL INFILE is disabled", start the client with --local-infile=1
-- (and run: SET GLOBAL local_infile = 1;). Edit the path below to where the CSV is on YOUR computer.
-- Empty CSV cells are turned into NULL by the NULLIF lines.
LOAD DATA LOCAL INFILE '/path/to/data/emissions_clean.csv'
INTO TABLE emissions
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(unit_row_id, registryID, facility, state, @naics6, @naics3, industry, unit_type, fuel, @capacity_mw,
 @weekly_op_hours, @energy_mj, co2e_t, @ef, source, qc_flag, capacity_flag, @lat, @lon)
SET naics6          = NULLIF(@naics6, ''),
    naics3          = NULLIF(@naics3, ''),
    capacity_mw     = NULLIF(@capacity_mw, ''),
    weekly_op_hours = NULLIF(@weekly_op_hours, ''),
    energy_mj       = NULLIF(@energy_mj, ''),
    ef_t_per_mj     = NULLIF(@ef, ''),
    latitude        = NULLIF(@lat, ''),
    longitude       = NULLIF(@lon, '');

-- Sanity check: expect 53648 rows and about 707.8 (million tonnes)
SELECT COUNT(*) AS n_rows, ROUND(SUM(co2e_t)/1e6, 1) AS total_mt FROM emissions;
