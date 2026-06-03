"""
upload_gcs.py — Push generated files to gs://$GCS_BUCKET/raw/...
Run after make_all.py has produced ./output. Requires google-cloud-storage.
"""
from __future__ import annotations

import glob
import os

from config import GCS_BUCKET, OUTPUT_ROOT


def upload_all(bucket_name: str | None = None) -> None:
    from google.cloud import storage  # lazy import so --local needs no GCP

    bucket_name = bucket_name or GCS_BUCKET
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    n = 0
    for path in glob.glob(os.path.join(OUTPUT_ROOT, "**", "*"), recursive=True):
        if os.path.isdir(path):
            continue
        rel = os.path.relpath(path, OUTPUT_ROOT)
        # keep _truth/ out of the cloud demo path
        if rel.startswith("_truth"):
            continue
        blob_name = f"raw/{rel}".replace(os.sep, "/")
        bucket.blob(blob_name).upload_from_filename(path)
        n += 1
        if n % 25 == 0:
            print(f"   uploaded {n} files ...")
    print(f">> Uploaded {n} files to gs://{bucket_name}/raw/")


if __name__ == "__main__":
    upload_all()
