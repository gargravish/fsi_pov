"""
build_segments.py — REAL behavioural segmentation, fully traceable in BigQuery.

Produces auditable artifacts in raves-altostrat.UBS_POV:
  • client_features            — engineered numeric feature table
  • client_kmeans              — a real BQML KMEANS model (BigFrames KMeans uses
                                 this same engine under the hood)
  • client_segments            — client_id -> segment (CENTROID_ID) assignments
  • client_segments_summary    — per-segment size, avg AuM, dominant asset class,
                                 attrition index, and a Gemini-generated name

The Data Scientist agent in the Agent Console reads client_segments_summary, so
the agentic result is the output of this real pipeline — traceable to the model,
the BQ jobs, and (via Dataform) the lineage.

Run:  cd backend && source .venv/bin/activate && \
      python ../infra/build_segments.py
"""
from __future__ import annotations

import json

from google.cloud import bigquery

PROJECT = "raves-altostrat"
DS = f"{PROJECT}.UBS_POV"
client = bigquery.Client(project=PROJECT, location="us-central1")


def run(sql: str, label: str) -> str:
    job = client.query(sql)
    job.result()
    print(f"   [{label}] job={job.job_id} bytes={job.total_bytes_processed}")
    return job.job_id


def main() -> None:
    print(">> 1/5 feature engineering -> client_features")
    run(f"""
    CREATE OR REPLACE TABLE `{DS}.client_features` AS
    WITH amix AS (
      SELECT client_id,
        SAFE_DIVIDE(SUM(IF(asset_class='equity', market_value_usd,0)), SUM(market_value_usd)) equity_ratio,
        SAFE_DIVIDE(SUM(IF(asset_class='fixed_income', market_value_usd,0)), SUM(market_value_usd)) fi_ratio,
        SAFE_DIVIDE(SUM(IF(asset_class='alternative', market_value_usd,0)), SUM(market_value_usd)) alt_ratio
      FROM `{DS}.holdings` GROUP BY client_id),
    txn AS (SELECT client_id, COUNT(*) n_txns FROM `{DS}.transactions` GROUP BY client_id),
    acc AS (SELECT client_id, COUNT(*) n_accounts FROM `{DS}.accounts` GROUP BY client_id)
    SELECT c.client_id,
           c.tenure_days,
           LN(c.total_aum_usd + 1) AS log_aum,
           IFNULL(acc.n_accounts, 0) AS n_accounts,
           IFNULL(txn.n_txns, 0) AS n_txns,
           IFNULL(amix.equity_ratio, 0) AS equity_ratio,
           IFNULL(amix.fi_ratio, 0) AS fi_ratio,
           IFNULL(amix.alt_ratio, 0) AS alt_ratio
    FROM `{DS}.clients` c
    LEFT JOIN acc USING (client_id)
    LEFT JOIN txn USING (client_id)
    LEFT JOIN amix USING (client_id)
    """, "client_features")

    print(">> 2/5 train BQML KMEANS -> client_kmeans (8 clusters)")
    run(f"""
    CREATE OR REPLACE MODEL `{DS}.client_kmeans`
    OPTIONS (model_type='KMEANS', num_clusters=8, standardize_features=TRUE) AS
    SELECT tenure_days, log_aum, n_accounts, n_txns, equity_ratio, fi_ratio, alt_ratio
    FROM `{DS}.client_features`
    """, "client_kmeans")

    print(">> 3/5 assign segments -> client_segments")
    run(f"""
    CREATE OR REPLACE TABLE `{DS}.client_segments` AS
    SELECT client_id, CENTROID_ID AS segment
    FROM ML.PREDICT(MODEL `{DS}.client_kmeans`, TABLE `{DS}.client_features`)
    """, "client_segments")

    print(">> 4/5 per-segment stats")
    stats = list(client.query(f"""
    SELECT s.segment,
           COUNT(*) AS size,
           ROUND(AVG(c.total_aum_usd), 2) AS avg_aum_usd,
           ROUND(AVG(f.equity_ratio), 3) AS equity,
           ROUND(AVG(f.fi_ratio), 3) AS fixed_income,
           ROUND(AVG(f.alt_ratio), 3) AS alternative,
           ROUND(AVG(IFNULL(a.flight_risk, 0)), 3) AS attrition_index,
           ROUND(AVG(c.tenure_days)/365, 1) AS avg_tenure_years,
           ANY_VALUE(c.segment_tier) AS sample_tier
    FROM `{DS}.client_segments` s
    JOIN `{DS}.clients` c USING (client_id)
    JOIN `{DS}.client_features` f USING (client_id)
    LEFT JOIN `{DS}.attrition_scores` a USING (client_id)
    GROUP BY s.segment ORDER BY s.segment
    """).result())

    print(">> 5/5 name segments with Gemini -> client_segments_summary")
    try:
        from google import genai
        gc = genai.Client(vertexai=True, project=PROJECT, location="us-central1")

        def name_it(st) -> str:
            dom = max([("equity", st["equity"]), ("fixed income", st["fixed_income"]),
                       ("alternatives", st["alternative"])], key=lambda x: x[1])[0]
            prompt = (f"Give a short (3-5 word) marketing name for a UBS wealth-management client "
                      f"segment. Stats: avg AuM USD {st['avg_aum_usd']:.0f}, dominant asset {dom}, "
                      f"avg tenure {st['avg_tenure_years']} years, attrition index {st['attrition_index']}, "
                      f"typical tier {st['sample_tier']}. Return only the name.")
            r = gc.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return (r.text or "").strip().strip('"')[:60]
    except Exception as e:
        print(f"   (Gemini naming unavailable: {e}; using descriptive labels)")
        def name_it(st):
            dom = max([("Equity", st["equity"]), ("Fixed-Income", st["fixed_income"]),
                       ("Alternatives", st["alternative"])], key=lambda x: x[1])[0]
            return f"{st['sample_tier']} · {dom}-led"

    rows = []
    for st in stats:
        dom = max([("equity", st["equity"]), ("fixed_income", st["fixed_income"]),
                   ("alternative", st["alternative"])], key=lambda x: x[1])[0]
        rows.append({
            "id": int(st["segment"]), "label": name_it(st), "size": int(st["size"]),
            "avg_aum_usd": float(st["avg_aum_usd"]), "dominant_asset": dom,
            "attrition_index": float(st["attrition_index"]),
        })
        print(f"   segment {st['segment']}: {rows[-1]['label']}  (n={st['size']})")

    schema = [
        bigquery.SchemaField("id", "INTEGER"), bigquery.SchemaField("label", "STRING"),
        bigquery.SchemaField("size", "INTEGER"), bigquery.SchemaField("avg_aum_usd", "FLOAT"),
        bigquery.SchemaField("dominant_asset", "STRING"),
        bigquery.SchemaField("attrition_index", "FLOAT"),
    ]
    job = client.load_table_from_json(
        rows, f"{DS}.client_segments_summary",
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"))
    job.result()
    print(f">> done. client_segments_summary: {len(rows)} segments")


if __name__ == "__main__":
    main()
