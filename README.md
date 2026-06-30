# FSI Helix

**An agentic wealth-&-banking intelligence demo on the Google Cloud Agentic Data Platform.**

FSI Helix takes the reality of the **Apex Bank + Summit Bank integration** — two banks, two
of everything, fragmented formats, overlapping clients — and turns it into a unified,
conversational, agent-driven decision surface. Every screen is powered by a native
**BigQuery AI** capability: autonomous embeddings, vector search, a client property
graph, TimesFM forecasting, a TabularFM/BQML attrition model, Conversational Analytics, and
grounded document RAG — all running *inside* the warehouse.

The agentic layer uses **real Google Cloud data agents**: the **Conversational Analytics
agent** powers *Ask Helix*, and the genuine **Google Cloud Data Engineering Agent** (an A2A
agent operating on a live **Dataform** workspace) is orchestrated alongside a BigQuery‑ML
**Data Scientist** step — visible end‑to‑end in the *Agent Console* data‑lifecycle view.

It runs in two modes:

| Mode | Flags | What happens | Needs GCP? |
|---|---|---|---|
| **Demo** | `USE_BQ=false` / `VITE_USE_MOCKS=true` | Realistic fixtures, zero cloud calls | ❌ No |
| **Live** | `USE_BQ=true` / `VITE_USE_MOCKS=false` | Real BigQuery AI / Vertex AI / graph / forecasting | ✅ Yes |

> Full design rationale, Apex Bank research and the use-case mapping live in
> [`Apex Bank_AGENTIC_POV_PLAN.md`](Apex Bank_AGENTIC_POV_PLAN.md). The CxO walk-through is in
> [`SPEAKER_PITCH.md`](SPEAKER_PITCH.md).

---

## What it demonstrates

| Page | Business question | BigQuery AI capability |
|---|---|---|
| **Home** | What does the unified estate look like? | Federated KPIs across the two-bank estate |
| **Unify & Resolve** | Can we collapse Apex + Summit into one truth? | `AI.GENERATE_TABLE` mapping + autonomous embeddings + `VECTOR_SEARCH` entity resolution |
| **Next-Best-Action** | What should this household hold next? | **Property graph** (GQL `MATCH`) + `VECTOR_SEARCH` look-alikes |
| **Flight-Risk Sentinel** | Which clients will we lose — and the campaign to save them? | **TabularFM/BQML** attrition → click a client → **GQL** household 360 + holdings/flows → **Gemini** drafts a targeted campaign + ready-to-send email |
| **Forecast Room** | Where are AuM / NNA / revenue heading? | `AI.FORECAST` (**TimesFM 2.5**) — zero-training, multi-series |
| **Driver Lens** | *Why* did Net New Money / flows move? | `AI.KEY_DRIVERS` — automatic key-driver analysis: ranks the client segments (tier × region × booking centre × risk × banking) that most over-/under-shot the bankwide trend, recent 6m vs prior 6m |
| **Ask Helix** | Let anyone query the estate in English | **Conversational Analytics agent** (real) — streams thinking → text + table + chart + SQL |
| **Research Brain** | Answer from CIO / KYC / suitability docs | Autonomous embeddings + `AI.SEARCH` grounded RAG |
| **Network Guard** | Where is the financial-crime risk? | **Property graph** multi-hop GQL — click a pattern (structuring / UBO / cross-bank) → its subgraph + records |
| **Segment Studio** | What natural client groups exist? | **BigFrames/BQML** KMeans + `AI.GENERATE` naming |
| **Agent Console** | One goal → watch the personas coordinate | Data-lifecycle: Raw → **real Google DE Agent (A2A)** → **Data Scientist (BigQuery ML)** → **real Conversational Analytics agent** → Business User, each with live output + BigQuery/Dataform links |

---

## Use-case & capability flow

Read it **bottom-up** — the foundation sits at the bottom and value rises to the users at the top:
two fragmented legacy estates (Apex Bank + Summit Bank) land in one BigQuery dataset (the data
foundation), a set of **warehouse-native AI capabilities** turn that data into intelligence,
each capability powers a concrete **business use case**, and everything is consumed through one
conversational, agent-driven surface. Every box in the blue layer is a BigQuery / Vertex AI
primitive; there is **no separate vector DB, graph DB, feature store, or model-serving stack.**

```mermaid
flowchart BT
    %% ---------- Sources (bottom: data foundation) ----------
    subgraph SRC["🏦 Two legacy estates — the Summit Bank integration"]
        direction LR
        S1["Apex Bank<br/>CSV · fixed-width<br/>Parquet · xlsx"]
        S2["Summit Bank<br/>JSON · XML · NDJSON"]
        S3["Documents (PDF)<br/>CIO research · KYC<br/>suitability · advice"]
    end

    GCS["☁️ GCS bucket<br/>gs://fsi_pov<br/><i>raw fragmented files</i>"]
    BQ[("🗄️ BigQuery dataset FSI_POV<br/><b>one governed Client 360</b><br/>curated tables · no data movement")]

    S1 --> GCS
    S2 --> GCS
    S3 --> GCS
    GCS -->|"load / federate"| BQ

    %% ---------- AI / ML capability layer ----------
    subgraph CAP["🧠 Warehouse-native AI capabilities (BigQuery + Vertex AI)"]
        direction LR
        C1["AI.GENERATE_TABLE<br/><i>schema mapping</i>"]
        C2["Autonomous embeddings<br/>ML.GENERATE_EMBEDDING"]
        C3["VECTOR_SEARCH<br/><i>COSINE look-alikes</i>"]
        C4["Property graph<br/>GQL MATCH"]
        C5["BigFrames<br/>KMeans clustering"]
        C6["TabularFM<br/>attrition model"]
        C7["AI.FORECAST<br/>TimesFM 2.5"]
        C7b["AI.KEY_DRIVERS<br/><i>key-driver analysis</i>"]
        C8["AI.GENERATE<br/>Gemini 2.5 Flash"]
        C9["AI.SEARCH<br/>grounded RAG"]
        C10["Conversational<br/>Analytics"]
        C11["ADK + A2A<br/>DE ⇄ DS agents"]
    end

    BQ --> C1 & C2 & C5 & C6 & C7 & C7b & C9 & C10
    C2 --> C3
    C2 --> C4

    %% ---------- Business use cases ----------
    subgraph BIZ["💼 Business use cases"]
        direction LR
        U1["🏢 <b>Finish the integration</b><br/>Apex + Summit → one Client 360"]
        U2["💰 <b>Grow share-of-wallet</b><br/>next-best-action across the household"]
        U3["🛡️ <b>Protect the asset base</b><br/>predict attrition + draft the save"]
        U4["📈 <b>Plan to $200bn NNA/yr</b><br/>AuM · NNA · revenue forecasting"]
        U5["💬 <b>Anyone can ask anything</b><br/>NL → text · tables · charts · SQL"]
        U6["📄 <b>Advisor &amp; research productivity</b><br/>cited answers from CIO/KYC docs"]
        U7["🚨 <b>Defend the bank</b><br/>layering · structuring · UBO networks"]
        U8["🎯 <b>Know the client</b><br/>behavioural micro-segments"]
        U9["🤖 <b>Agentic operating model</b><br/>set a goal, agents do the work"]
    end

    C1 --> U1
    C3 --> U1
    C4 --> U2
    C3 --> U2
    C8 --> U2
    C6 --> U3
    C8 --> U3
    C7 --> U4
    C7b --> U4
    C10 --> U5
    C9 --> U6
    C2 --> U6
    C4 --> U7
    C5 --> U8
    C8 --> U8
    C11 --> U9

    %% ---------- Consumption ----------
    APP["🖥️ FSI Helix app<br/>React + FastAPI · SSE streaming<br/><i>one conversational, agent-driven surface</i>"]
    U1 & U2 & U3 & U4 & U5 & U6 & U7 & U8 & U9 --> APP

    %% ---------- Styling ----------
    classDef src fill:#1e293b,stroke:#475569,color:#e2e8f0;
    classDef store fill:#0f3d2e,stroke:#10b981,color:#d1fae5;
    classDef cap fill:#0b3a53,stroke:#38bdf8,color:#e0f2fe;
    classDef biz fill:#3b1d4e,stroke:#c084fc,color:#f3e8ff;
    classDef app fill:#4a2c0b,stroke:#f59e0b,color:#fff7ed;

    class S1,S2,S3 src;
    class GCS,BQ store;
    class C1,C2,C3,C4,C5,C6,C7,C7b,C8,C9,C10,C11 cap;
    class U1,U2,U3,U4,U5,U6,U7,U8,U9 biz;
    class APP app;
```

> **Read it bottom-up:** two banks' raw files → one warehouse → native AI primitives → business
> outcomes → the users at the top. The same `FSI_POV` dataset feeds every capability, and the
> Conversational Analytics + Data Engineering agents sit between the data and the user so people
> set *intent* while the platform does the heavy lifting.

---

## Architecture

Read **bottom-up** — the cloud foundation sits at the bottom and each layer *serves* the one
above, up to the bankers and executives at the top.

```mermaid
flowchart BT
    %% ===== bottom: cloud foundation =====
    VX["☁️ Vertex AI<br/>Gemini 2.5 Flash · text-embedding-005"]
    GCS["☁️ GCS gs://fsi_pov<br/>raw Apex Bank/* + SummitBank/* + documents"]
    DF["🛠️ Dataform — fsi_pov_pipeline<br/><i>pipeline lineage; the DE agent operates here</i>"]

    subgraph BQ["🗄️ BigQuery — dataset FSI_POV (us-central1)"]
        direction LR
        Z1["Curated Client 360"]
        Z2["Autonomous embeddings<br/>+ vector index"]
        Z3["Client property graph"]
        Z4["BQML attrition · KMeans<br/>TimesFM forecasts"]
        Z5["AI.SEARCH doc index"]
    end

    VX -->|"remote models via<br/>us-central1.vertex_conn"| BQ
    GCS --> BQ

    %% ===== middle: agents + backend =====
    subgraph AGENTS["Agent layer"]
        direction LR
        ORC["Orchestrator (ADK)"]
        DE["Data Engineering Agent<br/><b>real · Google Cloud · A2A</b>"]
        DS["Data Scientist<br/>BigQuery ML"]
        ORC <-->|A2A| DE
        ORC <-->|A2A| DS
    end
    CA["💬 Conversational Analytics Agent<br/><b>real</b> · Ask Helix"]

    BQ -->|"BigQuery MCP / SQL"| AGENTS
    DF --> DE
    BQ --> CA
    AGENTS --> API["Backend — FastAPI (:8080)<br/>config.USE_BQ → fixtures | live"]
    CA --> API

    %% ===== top: app + users =====
    API -->|"/api/* · REST + SSE"| FE["Frontend — React 18 · Vite · Tailwind (:5173)"]
    FE --> USER["🧑‍💼 Bankers · advisors · executives"]

    classDef store fill:#0f3d2e,stroke:#10b981,color:#d1fae5;
    classDef svc fill:#0b3a53,stroke:#38bdf8,color:#e0f2fe;
    classDef ag fill:#3b1d4e,stroke:#c084fc,color:#f3e8ff;
    classDef user fill:#4a2c0b,stroke:#f59e0b,color:#fff7ed;
    class BQ,GCS,VX,DF,Z1,Z2,Z3,Z4,Z5 store;
    class FE,API,CA svc;
    class ORC,DE,DS ag;
    class USER user;
```

Everything AI/ML happens **in BigQuery** via one Cloud-resource connection to Vertex AI.
No separate vector DB, graph DB, feature store, or model-serving stack.

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ (3.9 works for generation; backend targets 3.11) |
| Node.js | 20+ |
| Google Cloud SDK | latest (`gcloud`, `bq`) |

For **live mode**: a GCP project with billing, BigQuery + Vertex AI + Storage +
Gemini Data Analytics APIs enabled, and `gcloud auth application-default login`.

---

## Quick start — Demo mode (no GCP)

```bash
# 1) Backend (fixtures)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080        # http://localhost:8080/healthz

# 2) Frontend (mocks) — new terminal
cd ../frontend
npm install
npm run dev                                       # http://localhost:5173
```

`USE_BQ` defaults to `false` and `VITE_USE_MOCKS` defaults to `true`, so every screen
renders from realistic local data. Done.

---

## Full setup — Live mode (this deployment: `raves-altostrat` / `us-central1`)

```bash
export PROJECT=raves-altostrat REGION=us-central1
export DATASET=FSI_POV BUCKET=fsi_pov CONNECTION=vertex_conn
```

### 1 — Enable APIs & create resources
```bash
gcloud services enable bigquery.googleapis.com bigqueryconnection.googleapis.com \
  aiplatform.googleapis.com storage.googleapis.com geminidataanalytics.googleapis.com \
  --project=$PROJECT
bq --location=$REGION mk --dataset $PROJECT:$DATASET
gcloud storage buckets create gs://$BUCKET --location=$REGION --project=$PROJECT
bq mk --connection --location=$REGION --project_id=$PROJECT \
   --connection_type=CLOUD_RESOURCE $CONNECTION       # or reuse the existing one
# grant the connection SA roles/aiplatform.user (see plan §0/§3)
```

### 2 — Generate & load the synthetic two-bank estate
```bash
cd synthetic_data
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=$PROJECT GCP_REGION=$REGION BQ_LOCATION=$REGION
export BQ_DATASET=$DATASET GCS_BUCKET=$BUCKET
python make_all.py --gcp        # generate → upload to GCS → load BigQuery
# (python make_all.py --local first if you just want files in ./output)
```

### 3 — Build the AI / graph / model layer
```bash
cd ..
bq --project_id=$PROJECT --location=$REGION query --use_legacy_sql=false < infra/setup_bq.sql
bq --project_id=$PROJECT --location=$REGION query --use_legacy_sql=false < infra/setup_apex_attrition.sql
bq --project_id=$PROJECT --location=$REGION query --use_legacy_sql=false < infra/setup_apex_forecast.sql
```

### 4 — Run the backend (live)
```bash
cd backend && source .venv/bin/activate
pip install -r requirements-bq.txt
cp ../infra/env.example .env     # set USE_BQ=true
uvicorn app.main:app --port 8080
curl http://localhost:8080/healthz       # {"status":"ok","use_bq":true,...}
```

### 5 — Run the frontend (live)
```bash
cd ../frontend
echo "VITE_USE_MOCKS=false" > .env.local
npm run dev                              # proxies /api → :8080
```

---

## Deploy to Cloud Run

```bash
export GOOGLE_CLOUD_PROJECT=$PROJECT GCP_REGION=$REGION
./infra/deploy_cloudrun.sh
```
Builds `fsi-helix-api` and `fsi-helix-web` and deploys both. Ensure the Cloud Run runtime
service account has **BigQuery Job User**, **BigQuery Data Viewer**, **Vertex AI User**,
and access to `us-central1.vertex_conn`.

---

## Project layout

```
Apex Bank/
├── Apex Bank_AGENTIC_POV_PLAN.md     design blueprint + Apex Bank research
├── SPEAKER_PITCH.md            CxO demo narrative
├── README.md                   this file
├── infra/
│   ├── setup_bq.sql            models · embeddings · vector index · property graph · KPIs
│   ├── setup_apex_attrition.sql attrition model + scoring + drivers + pipeline
│   ├── setup_apex_forecast.sql  AI.FORECAST (TimesFM) marts
│   ├── setup_fsi_key_drivers.sql AI.KEY_DRIVERS — flow key-driver analysis marts
│   ├── build_segments.py       real BQML KMeans + Gemini segment naming
│   ├── deploy_cloudrun.sh
│   └── env.example
├── synthetic_data/             two-bank estate generator + GCS/BQ loaders
├── dataform/                   Dataform pipeline (lineage) + deploy_dataform.py (REST push)
├── backend/                    FastAPI (routers, bq.py, services, agents/, de_agent.py,
│                               conversational.py, fixtures)
└── frontend/                   React 18 + TS + Vite + Tailwind (11 routes)
```

---

## Notes & caveats

- **All data is synthetic.** No real Apex Bank or Summit Bank data is used.
- **What's genuinely real vs. ours (be transparent in the room):**
  - **Real Google products:** the **Conversational Analytics agent** (Ask Helix) and the
    **Google Cloud Data Engineering Agent** (A2A, operating on the live Dataform workspace).
  - **Real BigQuery execution:** embeddings, vector index, property graph, BQML KMeans +
    attrition model, TimesFM forecasts — all openable in BigQuery and expressed as Dataform lineage.
  - **Our code:** the Orchestrator routing and the Data Scientist step (real BigQuery compute,
    not a packaged "DS agent" product — none is exposed in the API).
- **Preview features:** TabularFM ships as a documented headline with a GA BQML default in
  `setup_apex_attrition.sql`; autonomous embeddings use the GA `ML.GENERATE_EMBEDDING` path.
- **Cost / latency:** keep `DATA_SCALE=1`; forecast/score outputs are cached in tables; the
  backend falls back to fixtures on any live error so the demo never breaks. A full Agent
  Console run is ~60–100s (the DE and CA agents plan + run real BigQuery jobs) — pre-warm once.
