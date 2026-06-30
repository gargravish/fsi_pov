-- =====================================================================
-- FSI Helix — "From What to Why": key-driver analysis with AI.KEY_DRIVERS
-- Project: raves-altostrat   Dataset: FSI_POV
--
-- The Forecast Room shows *what* Net New Money / flows are doing.
-- AI.KEY_DRIVERS answers *why* a flow metric changed between two periods,
-- automatically surfacing the dimensional segments (segment tier × region ×
-- booking centre × risk profile × banking relationship) most responsible —
-- no GROUP BY sweeps, self-joins or ML pipelines required.
--
-- Input contract (one row per client-month):
--   * a numeric metric column  (net_new_money_usd / inflow_usd / outflow_usd)
--   * a BOOL interest label     (TRUE = recent 6 months, FALSE = prior 6 months)
--   * 1-12 dimension columns    (STRING / INT64 / BOOL)
--
-- Output (one row per driver segment):
--   drivers, metric_interest, metric_reference, difference,
--   relative_difference, unexpected_difference,
--   relative_unexpected_difference, contribution, apriori_support
--
-- Results are cached into tables so the app reads instantly (the live backend
-- can also call AI.KEY_DRIVERS directly — see backend/app/bq.py:key_drivers).
--
--   bq --project_id=raves-altostrat --location=us-central1 query \
--      --use_legacy_sql=false < infra/setup_fsi_key_drivers.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0) Re-usable input view: per-client monthly flows enriched with the
--    client 360 dimensions and a recent-vs-prior interest label.
--    Window: trailing 12 months, split into recent 6 (interest) / prior 6.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW `raves-altostrat.FSI_POV.v_flow_drivers_input` AS
SELECT
  c.segment_tier,
  c.region,
  c.booking_centre,
  c.risk_profile,
  IF(c.dual_banked, 'Dual-banked (Apex + Summit)', 'Single-bank') AS banking,
  f.net_new_money_usd,
  f.inflow_usd,
  f.outflow_usd,
  -- recent 6 months = interest group, prior 6 months = reference group
  f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 6 MONTH) AS is_recent
FROM `raves-altostrat.FSI_POV.client_flows` f
JOIN `raves-altostrat.FSI_POV.clients` c USING (client_id)
WHERE f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH);

-- ---------------------------------------------------------------------
-- 1) Net New Money drivers — the $200bn-NNA-ambition lens (hero metric)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.key_drivers_nna` AS
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT segment_tier, region, booking_centre, risk_profile, banking,
          net_new_money_usd, is_recent
   FROM `raves-altostrat.FSI_POV.v_flow_drivers_input`),
  metric_col          => 'net_new_money_usd',
  dimension_cols      => ['segment_tier', 'region', 'booking_centre', 'risk_profile', 'banking'],
  interest_label_col  => 'is_recent',
  -- NNA is a SIGNED net flow (can be negative); AI.KEY_DRIVERS only accepts
  -- negative metric values when min_apriori_support = 0 (so no top_k here).
  min_apriori_support => 0,
  enable_pruning      => TRUE
);

-- ---------------------------------------------------------------------
-- 2) Gross-inflow drivers — where is new money actually landing?
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.key_drivers_inflow` AS
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT segment_tier, region, booking_centre, risk_profile, banking,
          inflow_usd, is_recent
   FROM `raves-altostrat.FSI_POV.v_flow_drivers_input`),
  metric_col          => 'inflow_usd',
  dimension_cols      => ['segment_tier', 'region', 'booking_centre', 'risk_profile', 'banking'],
  interest_label_col  => 'is_recent',
  top_k               => 20,
  enable_pruning      => TRUE
);

-- ---------------------------------------------------------------------
-- 3) Gross-outflow drivers — which segments are bleeding assets?
--    (Dual-banked integration-overlap clients tend to surface here.)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.key_drivers_outflow` AS
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT segment_tier, region, booking_centre, risk_profile, banking,
          outflow_usd, is_recent
   FROM `raves-altostrat.FSI_POV.v_flow_drivers_input`),
  metric_col          => 'outflow_usd',
  dimension_cols      => ['segment_tier', 'region', 'booking_centre', 'risk_profile', 'banking'],
  interest_label_col  => 'is_recent',
  top_k               => 20,
  enable_pruning      => TRUE
);

-- ---------------------------------------------------------------------
-- Inspect: the segments that most over-/under-shot the population trend
-- (unexpected_difference) are the real story behind a metric move.
--
--   SELECT
--     (SELECT STRING_AGG(d.dimension_value, ' · ' ORDER BY d.dimension_name)
--      FROM UNNEST(drivers) d)               AS segment,
--     ROUND(metric_interest  / 1e6, 1)        AS recent_usd_m,
--     ROUND(metric_reference / 1e6, 1)        AS prior_usd_m,
--     ROUND(relative_difference * 100, 1)     AS rel_change_pct,
--     ROUND(unexpected_difference / 1e6, 1)   AS unexpected_usd_m,
--     ROUND(contribution * 100, 1)            AS contribution_pct,
--     ROUND(apriori_support * 100, 1)         AS support_pct
--   FROM `raves-altostrat.FSI_POV.key_drivers_nna`
--   ORDER BY ABS(unexpected_difference) DESC
--   LIMIT 12;
-- ---------------------------------------------------------------------
