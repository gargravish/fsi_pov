"""
make_all.py — End-to-end synthetic data orchestrator for UBS Helix.

Modes:
  python make_all.py            # --local (default): write everything to ./output
  python make_all.py --local
  python make_all.py --gcp      # also upload to GCS and load BigQuery (UBS_POV)

--local needs ZERO GCP credentials and is how you develop offline.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import config
from config import (curated_output_dir, ts_output_dir, bank_output_dir, seed_all)
from identities import (get_master_pool, assign_banks, get_advisors,
                        get_legal_entities, write_ground_truth)
import curated_builder
import markets
import documents_pdf

from banks import (ubs_clients_csv, ubs_portfolios_fixedwidth,
                   ubs_positions_parquet, ubs_advisors_xlsx,
                   cs_clients_json, cs_accounts_xml, cs_transactions_ndjson)


def _write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        open(path, "w").close()
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def run_local() -> dict:
    seed_all()
    print(f">> Building master client pool (scale={config.DATA_SCALE}) ...")
    clients_m = get_master_pool()
    assign_banks(clients_m)
    get_advisors()
    get_legal_entities()

    print(">> Building curated canonical objects (Client 360) ...")
    curated = curated_builder.build_all()
    cdir = curated_output_dir()
    for name, rows in curated.items():
        _write_csv(os.path.join(cdir, f"{name}.csv"), rows)
        print(f"   curated/{name}.csv  ({len(rows):,} rows)")

    print(">> Building time-series marts ...")
    marts = markets.build_marts()
    tdir = ts_output_dir()
    for name, rows in marts.items():
        _write_csv(os.path.join(tdir, f"{name}.csv"), rows)
        print(f"   timeseries/{name}.csv  ({len(rows):,} rows)")

    print(">> Writing RAW fragmented two-bank source files ...")
    ubs_dir = bank_output_dir("ubs")
    cs_dir = bank_output_dir("credit_suisse")
    raw_stats = []
    for mod, d in [
        (ubs_clients_csv, ubs_dir), (ubs_portfolios_fixedwidth, ubs_dir),
        (ubs_positions_parquet, ubs_dir), (ubs_advisors_xlsx, ubs_dir),
        (cs_clients_json, cs_dir), (cs_accounts_xml, cs_dir),
        (cs_transactions_ndjson, cs_dir),
    ]:
        stat = mod.write(clients_m, d)
        raw_stats.append(stat)
        print(f"   {os.path.relpath(stat['file'], config.OUTPUT_ROOT)}  "
              f"({stat['rows']:,} rows, {stat['format']})")

    print(">> Generating documents (PDF) + manifest ...")
    manifest = documents_pdf.generate(curated["clients"])
    print(f"   documents/  ({len(manifest):,} docs)")

    print(">> Writing ground-truth identity map (offline scoring only) ...")
    truth_rows = [{"master_client_id": c.master_client_id,
                   "source_banks": "|".join(sorted(c.in_banks)),
                   "dual_banked": len(c.in_banks) == 2}
                  for c in clients_m]
    write_ground_truth(truth_rows)

    print(f"\n>> LOCAL generation complete -> {config.OUTPUT_ROOT}")
    return {"clients": len(curated["clients"]),
            "dual_banked": sum(1 for c in clients_m if len(c.in_banks) == 2),
            "raw_files": raw_stats}


def run_gcp() -> None:
    run_local()
    print("\n>> Uploading to GCS ...")
    import upload_gcs
    upload_gcs.upload_all()
    print("\n>> Loading BigQuery (UBS_POV) ...")
    import load_raw_bq
    load_raw_bq.load_all()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gcp", action="store_true", help="upload to GCS + load BigQuery")
    ap.add_argument("--local", action="store_true", help="local files only (default)")
    args = ap.parse_args()
    if args.gcp:
        run_gcp()
    else:
        run_local()


if __name__ == "__main__":
    main()
