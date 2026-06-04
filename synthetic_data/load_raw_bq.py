"""
load_raw_bq.py — Load generated data into BigQuery dataset UBS_POV.

Loads the clean CURATED canonical tables (the "unified result"), the time-series
marts, the per-client flows, the attrition feature/scoring tables, and the
document manifest. Also registers RAW external tables over the native source
files in GCS that BigQuery reads directly (CSV / NDJSON / Parquet) so the
fragmented two-bank estate is queryable. XML / fixed-width originals stay in GCS
for the AI-unification demo.

Requires google-cloud-bigquery. Run after make_all.py --local and upload_gcs.py.
"""
from __future__ import annotations

import os

from config import (GOOGLE_CLOUD_PROJECT, BQ_LOCATION, GCS_BUCKET, OUTPUT_ROOT,
                    BQ_DATASET)

CURATED_TABLES = [
    "clients", "accounts", "portfolios", "holdings", "transactions",
    "advisors", "households", "legal_entities", "products", "client_flows",
    "attrition_training", "attrition_scoring",
]
TS_TABLES = ["ts_aum_monthly", "ts_nna_monthly", "ts_revenue_monthly"]


def _client():
    from google.cloud import bigquery
    return bigquery.Client(project=GOOGLE_CLOUD_PROJECT, location=BQ_LOCATION)


def _ensure_dataset(client) -> None:
    from google.cloud import bigquery
    ref = bigquery.Dataset(f"{GOOGLE_CLOUD_PROJECT}.{BQ_DATASET}")
    ref.location = BQ_LOCATION
    client.create_dataset(ref, exists_ok=True)


# Tables whose schema must be explicit (autodetect is unreliable on small
# tables with long quoted free-text columns).
_EXPLICIT_SCHEMA = {
    "products": [
        ("product_id", "STRING"), ("product_type", "STRING"), ("name", "STRING"),
        ("description", "STRING"), ("target_segment_hint", "STRING"),
        ("origin_platform", "STRING"),
    ],
    "documents": [
        ("document_id", "STRING"), ("gcs_uri", "STRING"), ("doc_type", "STRING"),
        ("client_id", "STRING"), ("title", "STRING"), ("parsed_text", "STRING"),
    ],
    "advisors": [
        ("advisor_id", "STRING"), ("name", "STRING"), ("role", "STRING"),
        ("desk", "STRING"), ("booking_centre", "STRING"), ("market", "STRING"),
        ("languages", "STRING"), ("source_bank", "STRING"),
    ],
}


def _load_csv(client, table_fqn: str, local_csv: str) -> None:
    from google.cloud import bigquery
    table_name = table_fqn.rsplit(".", 1)[-1].strip("`")
    schema = None
    if table_name in _EXPLICIT_SCHEMA:
        schema = [bigquery.SchemaField(n, t) for n, t in _EXPLICIT_SCHEMA[table_name]]
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=schema is None,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )
    with open(local_csv, "rb") as f:
        job = client.load_table_from_file(f, table_fqn, job_config=job_config)
    job.result()
    print(f"   loaded {table_fqn}  ({client.get_table(table_fqn).num_rows:,} rows)")


def load_all() -> None:
    client = _client()
    _ensure_dataset(client)
    ds = f"{GOOGLE_CLOUD_PROJECT}.{BQ_DATASET}"

    curated_dir = os.path.join(OUTPUT_ROOT, "curated")
    for t in CURATED_TABLES:
        path = os.path.join(curated_dir, f"{t}.csv")
        if os.path.exists(path):
            _load_csv(client, f"{ds}.{t}", path)

    ts_dir = os.path.join(OUTPUT_ROOT, "timeseries")
    for t in TS_TABLES:
        path = os.path.join(ts_dir, f"{t}.csv")
        if os.path.exists(path):
            _load_csv(client, f"{ds}.{t}", path)

    manifest = os.path.join(OUTPUT_ROOT, "documents", "document_manifest.csv")
    if os.path.exists(manifest):
        _load_csv(client, f"{ds}.documents", manifest)

    _register_raw_external(client)
    print(">> BigQuery load complete.")


def _register_raw_external(client) -> None:
    ds = f"{GOOGLE_CLOUD_PROJECT}.{BQ_DATASET}"
    specs = {
        "raw_ubs_clients":      ("CSV", f"gs://{GCS_BUCKET}/raw/ubs/ubs_clients.csv"),
        "raw_ubs_positions":    ("PARQUET", f"gs://{GCS_BUCKET}/raw/ubs/ubs_positions.parquet"),
        "raw_cs_clients":       ("NEWLINE_DELIMITED_JSON",
                                 f"gs://{GCS_BUCKET}/raw/credit_suisse/cs_clients.json"),
        "raw_cs_transactions":  ("NEWLINE_DELIMITED_JSON",
                                 f"gs://{GCS_BUCKET}/raw/credit_suisse/cs_transactions.ndjson"),
    }
    for name, (fmt, uri) in specs.items():
        extra = ""
        if fmt == "CSV":
            extra = ", skip_leading_rows = 1, allow_quoted_newlines = TRUE"
        sql = f"""
        CREATE OR REPLACE EXTERNAL TABLE `{ds}.{name}`
        OPTIONS (format = '{fmt}', uris = ['{uri}']{extra})
        """
        try:
            client.query(sql).result()
            print(f"   external table {name} -> {uri}")
        except Exception as e:  # pragma: no cover
            print(f"   (skipped {name}: {e})")


if __name__ == "__main__":
    load_all()
