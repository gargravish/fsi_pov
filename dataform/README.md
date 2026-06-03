# UBS Helix — Dataform pipeline (lineage you can show the customer)

This Dataform project expresses the **real** UBS_POV transformation pipeline as
governed, version-controlled SQL with full lineage. It is deployed to a live
Dataform repository in the project:

- **Repository:** `ubs_pov_pipeline` (location `us-central1`)
- **Workspace:** `dev`
- **Open it:** BigQuery console → Dataform → `ubs_pov_pipeline` → `dev`
  (`https://console.cloud.google.com/bigquery/dataform/locations/us-central1/repositories/ubs_pov_pipeline/workspaces/dev?project=raves-altostrat`)

## The DAG

```
declarations (curated Client 360 + raw two-bank sources + attrition_model)
  clients · accounts · holdings · transactions · attrition_scoring · attrition_model · ts_nna_monthly
        │
        ├─► client_features ─► client_kmeans (BQML KMEANS) ─► client_segments ─► client_segments_summary
        │                                                                          (Gemini names added by
        │                                                                           infra/build_segments.py)
        ├─► forecast_nna  (AI.FORECAST / TimesFM 2.5)
        └─► attrition_scores  (ML.PREDICT on attrition_model)
```

Every node is a real BigQuery object the Agent Console links to ("Trace in
BigQuery"). The Data Scientist agent's `segment_clients` skill produces exactly
the `client_kmeans` → `client_segments` → `client_segments_summary` chain shown
here — so the agentic result is auditable end-to-end, from the goal to the model
to the lineage.

## What's real vs. what's the agent narration

- **Real, traceable BigQuery execution:** `client_features`, `client_kmeans`
  (a BQML model), `client_segments`, `client_segments_summary`, `forecast_nna`,
  `attrition_model`/`attrition_scores`, the embeddings tables, the `client_graph`
  property graph, and the Conversational Analytics agent. Open any of them in BQ.
- **The Data Engineering agent is the REAL Google Cloud Data Engineering Agent.**
  The Agent Console delegates to it over A2A
  (`geminidataanalytics.googleapis.com/.../agents/dataengineeringagent:message:stream`),
  passing **this Dataform workspace** as the required `gcpresource` extension. It
  genuinely reads/operates on the pipeline here — its streamed replies show up in
  the trace tagged **LIVE A2A** (`backend/app/de_agent.py`). The Conversational
  Analytics agent (Ask UBS) is likewise the real product.
- **Still our own code:** the Orchestrator routing and the Data Scientist steps
  (real BigQuery ML/TimesFM, invoked by our code). These can move to the literal
  google-adk runtime without changing the API or UI.

## Deploy / refresh

```bash
cd backend && source .venv/bin/activate
python ../dataform/deploy_dataform.py     # creates repo+workspace, pushes files, compiles
```

To materialise the segmentation tables (model + summary with Gemini names):

```bash
python ../infra/build_segments.py
```
