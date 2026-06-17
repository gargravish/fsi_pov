-- =====================================================================
-- FSI Helix — BigQuery AI / embeddings / vector / graph layer
-- Project: raves-altostrat   Dataset: FSI_POV   Region: us-central1
-- Connection: us-central1.vertex_conn  (Vertex AI User)
--
-- Run AFTER synthetic_data/make_all.py --gcp has loaded the curated tables.
--   bq --project_id=raves-altostrat --location=us-central1 query \
--      --use_legacy_sql=false < infra/setup_bq.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Remote models (Vertex AI via the Cloud-resource connection)
-- ---------------------------------------------------------------------
CREATE OR REPLACE MODEL `raves-altostrat.FSI_POV.embedding_model`
REMOTE WITH CONNECTION `raves-altostrat.us-central1.vertex_conn`
OPTIONS (endpoint = 'text-embedding-005');

CREATE OR REPLACE MODEL `raves-altostrat.FSI_POV.gemini_model`
REMOTE WITH CONNECTION `raves-altostrat.us-central1.vertex_conn`
OPTIONS (endpoint = 'gemini-2.5-flash');

-- ---------------------------------------------------------------------
-- 2) Client profile text -> autonomous embeddings (ML.GENERATE_EMBEDDING)
--    A natural-language profile per client makes vector look-alikes
--    behaviourally meaningful (segment, region, risk, holdings mix).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW `raves-altostrat.FSI_POV.client_profile` AS
WITH acct AS (
  SELECT client_id, STRING_AGG(DISTINCT account_type, ', ') AS account_types
  FROM `raves-altostrat.FSI_POV.accounts` GROUP BY client_id
),
asset_rank AS (
  SELECT client_id, asset_class,
         ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY SUM(market_value_usd) DESC) rn
  FROM `raves-altostrat.FSI_POV.holdings` GROUP BY client_id, asset_class
),
asset AS (
  SELECT client_id, STRING_AGG(asset_class, ', ' ORDER BY asset_class) AS top_assets
  FROM asset_rank WHERE rn <= 3 GROUP BY client_id
)
SELECT
  c.client_id,
  CONCAT(
    c.segment_tier, ' client in ', c.region,
    ' booked at ', c.booking_centre,
    '. Risk profile ', c.risk_profile,
    '. Total AuM USD ', CAST(ROUND(c.total_aum_usd) AS STRING),
    '. Tenure days ', CAST(c.tenure_days AS STRING),
    '. KYC ', c.kyc_status,
    '. Languages ', c.languages,
    '. Holds account types: ', IFNULL(acct.account_types, 'none'),
    '. Dominant asset classes: ', IFNULL(asset.top_assets, 'none'), '.'
  ) AS content
FROM `raves-altostrat.FSI_POV.clients` c
LEFT JOIN acct  USING (client_id)
LEFT JOIN asset USING (client_id);

CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.client_embeddings` AS
SELECT
  client_id,
  ml_generate_embedding_result AS embedding,
  content
FROM ML.GENERATE_EMBEDDING(
  MODEL `raves-altostrat.FSI_POV.embedding_model`,
  (SELECT client_id, content FROM `raves-altostrat.FSI_POV.client_profile`),
  STRUCT(TRUE AS flatten_json_output)
);

-- Product description embeddings (small table -> brute-force VECTOR_SEARCH)
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.product_embeddings` AS
SELECT
  product_id, product_type, name, target_segment_hint,
  ml_generate_embedding_result AS embedding
FROM ML.GENERATE_EMBEDDING(
  MODEL `raves-altostrat.FSI_POV.embedding_model`,
  (SELECT product_id, product_type, name, target_segment_hint,
          CONCAT(name, '. ', description) AS content
   FROM `raves-altostrat.FSI_POV.products`),
  STRUCT(TRUE AS flatten_json_output)
);

-- Document chunk embeddings for Research Brain (AI.SEARCH-style RAG)
CREATE OR REPLACE TABLE `raves-altostrat.FSI_POV.doc_search` AS
SELECT
  document_id, doc_type, client_id, title, parsed_text AS chunk_text, gcs_uri,
  ml_generate_embedding_result AS embedding
FROM ML.GENERATE_EMBEDDING(
  MODEL `raves-altostrat.FSI_POV.embedding_model`,
  (SELECT document_id, doc_type, client_id, title, parsed_text, gcs_uri,
          parsed_text AS content
   FROM `raves-altostrat.FSI_POV.documents`),
  STRUCT(TRUE AS flatten_json_output)
);

-- ---------------------------------------------------------------------
-- 3) Vector index on client embeddings (ANN at scale; async build)
--    Requires >=5000 rows; safe at DATA_SCALE=1 (~40k clients).
-- ---------------------------------------------------------------------
CREATE VECTOR INDEX IF NOT EXISTS client_emb_idx
ON `raves-altostrat.FSI_POV.client_embeddings`(embedding)
OPTIONS (index_type = 'IVF', distance_type = 'COSINE');

-- ---------------------------------------------------------------------
-- 4) Property graph — household / account / advisor network
--    Powers Next-Best-Action (cross-sell) and the AML/UBO network.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROPERTY GRAPH `raves-altostrat.FSI_POV.client_graph`
NODE TABLES (
  `raves-altostrat.FSI_POV.clients` AS Client
    KEY (client_id)
    LABEL Client PROPERTIES (client_id, full_name, segment_tier, region,
                             booking_centre, total_aum_usd, household_id,
                             primary_advisor_id, dual_banked),
  `raves-altostrat.FSI_POV.households` AS Household
    KEY (household_id)
    LABEL Household PROPERTIES (household_id, member_count, total_aum_usd),
  `raves-altostrat.FSI_POV.accounts` AS Account
    KEY (account_id)
    LABEL Account PROPERTIES (account_id, account_type, booking_centre, balance_usd),
  `raves-altostrat.FSI_POV.advisors` AS Advisor
    KEY (advisor_id)
    LABEL Advisor PROPERTIES (advisor_id, name, desk, booking_centre)
)
EDGE TABLES (
  `raves-altostrat.FSI_POV.clients` AS BelongsTo
    KEY (client_id)
    SOURCE KEY (client_id) REFERENCES Client (client_id)
    DESTINATION KEY (household_id) REFERENCES Household (household_id)
    LABEL BELONGS_TO,
  `raves-altostrat.FSI_POV.accounts` AS Holds
    KEY (account_id)
    SOURCE KEY (client_id) REFERENCES Client (client_id)
    DESTINATION KEY (account_id) REFERENCES Account (account_id)
    LABEL HOLDS,
  `raves-altostrat.FSI_POV.clients` AS AdvisedBy
    KEY (client_id)
    SOURCE KEY (client_id) REFERENCES Client (client_id)
    DESTINATION KEY (primary_advisor_id) REFERENCES Advisor (advisor_id)
    LABEL ADVISED_BY
);

-- ---------------------------------------------------------------------
-- 5) KPI view for the Home page
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW `raves-altostrat.FSI_POV.v_kpis` AS
SELECT
  (SELECT COUNT(*) FROM `raves-altostrat.FSI_POV.clients`) AS clients,
  (SELECT ROUND(SUM(total_aum_usd)/1e9, 1) FROM `raves-altostrat.FSI_POV.clients`) AS aum_usd_bn,
  (SELECT COUNT(*) FROM `raves-altostrat.FSI_POV.accounts`) AS accounts,
  (SELECT ROUND(100*AVG(CAST(dual_banked AS INT64)), 1)
   FROM `raves-altostrat.FSI_POV.clients`) AS dual_banked_pct,
  (SELECT COUNT(*) FROM `raves-altostrat.FSI_POV.advisors`) AS advisors,
  (SELECT ROUND(SUM(net_new_money_usd_bn)*1000, 1)
   FROM `raves-altostrat.FSI_POV.ts_nna_monthly`
   WHERE EXTRACT(YEAR FROM month) = 2026) AS nna_ytd_usd_m;
