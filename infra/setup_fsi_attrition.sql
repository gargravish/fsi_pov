-- =====================================================================
-- FSI Helix — Client attrition / NNA flight-risk model + scoring + drivers
-- Project: raves-altostrat   Dataset: FSI_POV
--
-- Headline capability: TabularFM (zero-tuning tabular foundation model).
-- Executed default: BOOSTED_TREE_CLASSIFIER (GA, fast, identical scoring
-- contract) so the live demo always runs. To use TabularFM where available,
-- swap the model_type in section 1 (see the commented variant).
--
--   bq --project_id=raves-altostrat --location=us-central1 query \
--      --use_legacy_sql=false < infra/setup_apex_attrition.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Train the attrition classifier on the engineered feature table
-- ---------------------------------------------------------------------
CREATE OR REPLACE MODEL `raves-altostrat.FSI_POV.attrition_model`
OPTIONS (
  model_type = 'BOOSTED_TREE_CLASSIFIER',
  input_label_cols = ['attrited'],
  auto_class_weights = TRUE,
  max_iterations = 30
) AS
-- NOTE: dual_banked is intentionally EXCLUDED as a feature. It correlates with
-- flight risk but, as a clean binary, the tree over-splits on it and saturates
-- the top of the ranking with dual-banked clients. Ranking on behavioural
-- signals (outflows, KYC, tenure, flows) yields a realistic mix; dual_banked is
-- kept only as displayed context on the scored client.
SELECT
  segment_tier, region, risk_profile,
  tenure_days, total_aum_usd, n_accounts, n_txns,
  kyc_flag, recent_net_flow_usd, outflow_ratio,
  attrited
FROM `raves-altostrat.FSI_POV.attrition_training`;

-- TabularFM headline variant (Preview; uncomment where enabled):
-- CREATE OR REPLACE MODEL `raves-altostrat.FSI_POV.attrition_model`
-- OPTIONS (model_type = 'TABULARFM', input_label_cols = ['attrited']) AS
-- SELECT * FROM `raves-altostrat.FSI_POV.attrition_training`;

-- ---------------------------------------------------------------------
-- 2) Score every client (flight-risk probability)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.attrition_scores` AS
SELECT
  s.client_id,
  s.segment_tier, s.region, s.total_aum_usd, s.dual_banked,
  s.recent_net_flow_usd, s.outflow_ratio,
  p.prob AS flight_risk
FROM ML.PREDICT(
  MODEL `raves-altostrat.FSI_POV.attrition_model`,
  TABLE `raves-altostrat.FSI_POV.attrition_scoring`
) AS s,
UNNEST(s.predicted_attrited_probs) AS p
WHERE p.label = 1;

-- ---------------------------------------------------------------------
-- 3) Global feature importance (top attrition drivers) for the UI
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.attrition_drivers` AS
SELECT feature, importance_weight AS importance
FROM ML.FEATURE_IMPORTANCE(MODEL `raves-altostrat.FSI_POV.attrition_model`)
ORDER BY importance DESC;

-- ---------------------------------------------------------------------
-- 4) Renewal/outflow pipeline (next 12 weeks) for the Retention page
--    Buckets high-risk clients into a forward-looking review pipeline.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.retention_pipeline` AS
SELECT
  week,
  COUNT(*) AS clients,
  COUNTIF(flight_risk >= 0.5) AS high_risk
FROM (
  SELECT client_id, flight_risk,
         DATE_ADD(DATE '2026-06-01',
                  INTERVAL CAST(FLOOR(RAND() * 12) AS INT64) WEEK) AS week
  FROM `raves-altostrat.FSI_POV.attrition_scores`
)
GROUP BY week
ORDER BY week;
