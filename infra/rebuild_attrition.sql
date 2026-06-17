-- =====================================================================
-- FSI Helix — rebuild attrition features with a BLENDED flight-risk label
-- so the high-risk list is realistic (a mix of dual-banked + single-bank
-- clients), not saturated on dual-banked alone.
--
-- Recomputes attrition_training + attrition_scoring directly from the live
-- BigQuery tables, then re-run infra/setup_apex_attrition.sql to retrain + score.
--
--   bq --project_id=raves-altostrat --location=us-central1 query \
--      --use_legacy_sql=false < infra/rebuild_attrition.sql
--   bq ... < infra/setup_apex_attrition.sql
-- =====================================================================

CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.attrition_features` AS
WITH flows AS (
  SELECT client_id,
         SUM(IF(month >= DATE_SUB(DATE '2026-06-01', INTERVAL 6 MONTH),
                net_new_money_usd, 0)) AS recent_net_flow_usd,
         SAFE_DIVIDE(SUM(outflow_usd), SUM(inflow_usd) + SUM(outflow_usd) + 1) AS outflow_ratio
  FROM `raves-altostrat.FSI_POV.client_flows` GROUP BY client_id
),
acc AS (SELECT client_id, COUNT(*) n_accounts FROM `raves-altostrat.FSI_POV.accounts` GROUP BY client_id),
txn AS (SELECT client_id, COUNT(*) n_txns FROM `raves-altostrat.FSI_POV.transactions` GROUP BY client_id),
feat AS (
  SELECT c.client_id, c.segment_tier, c.region, c.risk_profile,
         c.tenure_days, c.total_aum_usd,
         IFNULL(acc.n_accounts, 0) AS n_accounts,
         IFNULL(txn.n_txns, 0) AS n_txns,
         CAST(c.dual_banked AS INT64) AS dual_banked,
         CAST(c.kyc_status IN ('expired', 'review_required') AS INT64) AS kyc_flag,
         ROUND(IFNULL(f.recent_net_flow_usd, 0), 2) AS recent_net_flow_usd,
         ROUND(IFNULL(f.outflow_ratio, 0), 4) AS outflow_ratio
  FROM `raves-altostrat.FSI_POV.clients` c
  LEFT JOIN acc USING (client_id)
  LEFT JOIN txn USING (client_id)
  LEFT JOIN flows f USING (client_id)
)
SELECT *,
  -- blended propensity: outflows dominate; dual-banked is ONE factor among many
  ( 0.06
    + 0.45 * outflow_ratio
    + 0.12 * dual_banked
    + 0.07 * kyc_flag
    + IF(recent_net_flow_usd < 0, 0.08, 0)
    + CASE risk_profile WHEN 'Aggressive' THEN 0.06 WHEN 'Growth' THEN 0.04
                        WHEN 'Balanced' THEN 0.02 ELSE 0 END
    + IF(tenure_days < 730, 0.05, 0)
    + (RAND() - 0.5) * 0.18
  ) AS risk_score
FROM feat;

CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.attrition_training` AS
SELECT segment_tier, region, risk_profile, tenure_days, total_aum_usd,
       n_accounts, n_txns, dual_banked, kyc_flag, recent_net_flow_usd, outflow_ratio,
       CAST(risk_score > 0.42 AS INT64) AS attrited
FROM `raves-altostrat.FSI_POV.attrition_features`
WHERE MOD(ABS(FARM_FINGERPRINT(client_id)), 10) < 8;   -- 80% train split

CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.attrition_scoring` AS
SELECT client_id, segment_tier, region, risk_profile, tenure_days, total_aum_usd,
       n_accounts, n_txns, dual_banked, kyc_flag, recent_net_flow_usd, outflow_ratio
FROM `raves-altostrat.FSI_POV.attrition_features`;
