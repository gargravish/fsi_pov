-- =====================================================================
-- FSI Helix — AuM / NNA / revenue forecasting with AI.FORECAST (TimesFM 2.5)
-- Project: raves-altostrat   Dataset: FSI_POV
--
-- Zero-training, multi-series forecasting (id_cols = division x region).
-- Results are cached into tables so the app reads instantly.
--
--   bq --project_id=raves-altostrat --location=us-central1 query \
--      --use_legacy_sql=false < infra/setup_apex_forecast.sql
-- =====================================================================

-- Net New Money (the $200bn/yr ambition lever)
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.forecast_nna` AS
SELECT * FROM AI.FORECAST(
  (SELECT division, region, TIMESTAMP(month) AS month, net_new_money_usd_bn
   FROM `raves-altostrat.FSI_POV.ts_nna_monthly`),
  data_col => 'net_new_money_usd_bn',
  timestamp_col => 'month',
  id_cols => ['division', 'region'],
  model => 'TimesFM 2.5',
  horizon => 12,
  confidence_level => 0.9
);

-- Assets under Management
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.forecast_aum` AS
SELECT * FROM AI.FORECAST(
  (SELECT division, region, TIMESTAMP(month) AS month, aum_usd_bn
   FROM `raves-altostrat.FSI_POV.ts_aum_monthly`),
  data_col => 'aum_usd_bn',
  timestamp_col => 'month',
  id_cols => ['division', 'region'],
  model => 'TimesFM 2.5',
  horizon => 12,
  confidence_level => 0.9
);

-- Revenue
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.forecast_revenue` AS
SELECT * FROM AI.FORECAST(
  (SELECT division, region, TIMESTAMP(month) AS month, revenue_usd_bn
   FROM `raves-altostrat.FSI_POV.ts_revenue_monthly`),
  data_col => 'revenue_usd_bn',
  timestamp_col => 'month',
  id_cols => ['division', 'region'],
  model => 'TimesFM 2.5',
  horizon => 12,
  confidence_level => 0.9
);
