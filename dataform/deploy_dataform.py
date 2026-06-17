"""
deploy_dataform.py — Provision the Dataform repository + workspace and push the
FSI_POV pipeline files via the Dataform REST API, then compile to validate the DAG.

Result: a Dataform repository `fsi_pov_pipeline` (us-central1) the customer can
open in the BigQuery/Dataform console to see the full lineage:

  declarations (clients, accounts, holdings, transactions, attrition_*, ts_nna_*)
    -> client_features -> client_kmeans (KMEANS) -> client_segments -> client_segments_summary
    -> forecast_nna (TimesFM) ;  attrition_model -> attrition_scores

Run:  cd backend && source .venv/bin/activate && python ../dataform/deploy_dataform.py
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

import google.auth
import google.auth.transport.requests as gart

PROJECT = "raves-altostrat"
REGION = "us-central1"
REPO = "fsi_pov_pipeline"
WORKSPACE = "dev"
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = f"https://dataform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/repositories/{REPO}"


def _token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(gart.Request())
    return creds.token


def _post(url: str, body: dict | None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else b"{}"
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Authorization": f"Bearer {_token()}",
                                          "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _iter_files():
    for dirpath, _dirs, files in os.walk(ROOT):
        for f in files:
            if f.endswith((".py", ".md")) or f == "deploy_dataform.py":
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, ROOT)
            yield rel, full


def main() -> None:
    # 1) repository (idempotent)
    code, _ = _post(f"https://dataform.googleapis.com/v1beta1/projects/{PROJECT}/locations/{REGION}/repositories?repositoryId={REPO}",
                    {"displayName": "FSI Helix — FSI_POV pipeline"})
    print(f">> repository: {'created' if code == 200 else f'exists/'+str(code)}")

    # 2) workspace (idempotent)
    code, _ = _post(f"{BASE}/workspaces?workspaceId={WORKSPACE}", {})
    print(f">> workspace '{WORKSPACE}': {'created' if code == 200 else 'exists/'+str(code)}")

    # 3) push files
    n = 0
    for rel, full in _iter_files():
        with open(full, "rb") as fh:
            contents = base64.b64encode(fh.read()).decode()
        code, resp = _post(f"{BASE}/workspaces/{WORKSPACE}:writeFile",
                           {"path": rel, "contents": contents})
        status = "ok" if code == 200 else f"ERR {code}: {resp[:120]}"
        print(f"   writeFile {rel} -> {status}")
        n += 1
    print(f">> pushed {n} files")

    # 4) compile (validate the DAG). The `workspace` field is the bare resource
    # name (no https:// host prefix).
    ws_resource = (f"projects/{PROJECT}/locations/{REGION}/repositories/{REPO}"
                   f"/workspaces/{WORKSPACE}")
    code, resp = _post(f"{BASE}/compilationResults", {"workspace": ws_resource})
    if code == 200:
        cr = json.loads(resp)
        errs = cr.get("compilationErrors", [])
        print(f">> compilation: {'OK' if not errs else str(len(errs))+' errors'}")
        for e in errs[:5]:
            print("   !", e.get("message", "")[:160])
        print(f">> open: https://console.cloud.google.com/bigquery/dataform/locations/{REGION}/repositories/{REPO}/workspaces/{WORKSPACE}?project={PROJECT}")
    else:
        print(f">> compile error {code}: {resp[:200]}")


if __name__ == "__main__":
    main()
