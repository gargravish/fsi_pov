# FSI Helix — Agentic Wealth & Banking Intelligence Platform (Google Cloud POV)

> **Purpose.** A single, self-contained, vibe-code-ready blueprint for a C‑level workshop demo that shows how the **BigQuery Agentic Data Platform** on **Google Cloud**, with BigQuery as the intelligence core, solves Apex Bank's most valuable business problems — built natively on **BigQuery AI** (autonomous embeddings, AI.FORECAST/TimesFM, TabularFM, BigQuery Graph/GQL, Conversational Analytics, BigFrames) and a layer of **collaborating agents** (a Data Engineering agent and a Data Scientist agent talking over **A2A**, plus a Conversational Analytics agent), orchestrated with **ADK**.
>
> **Audience.** Apex Bank Group/divisional CxOs (CEO/CIO/COO/CDO of GWM, P&C, Asset Management) and their architects — and the engineer (or AI pair‑programmer) who will build the demo from this doc.
>
> **Status.** Design blueprint — POV / demo. Not production. **All data is synthetic.** No real Apex Bank or Summit Bank data is used.
>
> **Target cloud.** Project `raves-altostrat`, region `us-central1`, BigQuery connection `us-central1.vertex_conn` (already provisioned).
>
> **Last updated.** 2026-06-03.

---

## 0. TL;DR

We will build **"FSI Helix"** — an agentic wealth-and-banking intelligence web app on the BigQuery Agentic Data Platform (Google Cloud). A unified BigQuery lakehouse ingests *deliberately fragmented* synthetic data from **two legacy estates — "Apex Bank" and "Summit Bank"** (the real-world integration completing end‑2026) — and a set of **collaborating agents** sit on top to deliver the outcomes Apex Bank cares about most:

1. **Unified Client 360 (post‑merger integration)** — collapse two banks' fragmented client/account data into one governed truth. **AI.GENERATE_TABLE** schema mapping + **autonomous embeddings** + **VECTOR_SEARCH** entity resolution, run by a **Data Engineering agent**.
2. **Next‑Best‑Action / Cross‑sell for wealth** — grow share‑of‑wallet across the household & family‑office network. **BigQuery Graph (GQL)** + **VECTOR_SEARCH** look‑alikes + **AI.GENERATE** advisor rationale.
3. **Client attrition / Net‑New‑Money flight risk** — protect the asset base through the integration. **TabularFM** classification + **AI.GENERATE** retention play.
4. **AuM / NNA / revenue forecasting** — plan capacity and growth toward the $200bn NNA/yr ambition. **AI.FORECAST (TimesFM 2.5)**, multi‑series by division × region × booking centre.
5. **Conversational analytics — "Ask Helix"** — any banker/exec queries the whole estate in English. **Conversational Analytics API (Gemini Data Analytics agent)**.
6. **Investment research & advice intelligence** — ground answers in CIO research, KYC and suitability documents. **Autonomous embeddings + AI.SEARCH** RAG.
7. **AML / financial‑crime & UBO network** — surface layering, structuring, circular flows and ultimate‑beneficial‑owner risk. **BigQuery Graph** multi‑hop GQL.
8. **Behavioral client segmentation** — move beyond wealth-tier buckets. **BigFrames** + KMeans + **AI.GENERATE** naming.
9. **The agentic core** — a **Data Engineering agent** and a **Data Scientist agent** that collaborate over the **Agent‑to‑Agent (A2A) protocol** under an **ADK orchestrator**, with **Conversational Analytics** as the natural-language surface.

Stack: **React + TypeScript (Vite, Tailwind, shadcn/ui)** front end, **FastAPI (Python)** back end, **BigQuery + Vertex AI Gemini** as the brain, agents on **Google ADK + A2A + the BigQuery MCP/ADK toolset**, deployed on **Cloud Run**. Runs in **Demo mode** (fixtures, no cloud) or **Live mode** (real BigQuery AI on `raves-altostrat`).

---

## 1. Customer Context — Apex Bank Group (Research Findings)

This grounds the synthetic data and the narrative so the demo feels authentic to a Apex Bank audience.

### 1.1 Who they are
- The world's largest truly global **wealth manager**, plus a leading Swiss universal bank, a global asset manager, and an investment bank. Headquartered in Zürich, ~110k employees, operating across the major booking centres: **Zürich, Geneva, Basel, Lugano (CH), London (UK/EMEA), New York (Americas), Hong Kong & Singapore (APAC)**.
- **Five reporting divisions:** **Global Wealth Management (GWM)**, **Personal & Corporate Banking (P&C, Switzerland)**, **Asset Management (AM)**, the **Investment Bank (IB)**, and a **Non‑core & Legacy (NCL)** unit.
- **Scale (FY2025):** ~**$7tn** invested assets across the Group; **GWM ~$4.8tn**; **Asset Management surpassed $2tn** for the first time; **APAC invested assets passed $1tn**.

### 1.2 The defining event — the Summit Bank integration
- Apex Bank acquired **Summit Bank** (2023) and is on track to **sapextantially complete the integration by end‑2026**, with the remaining work centred on **client‑account migrations** and **decommissioning duplicate infrastructure**.
- Cumulative gross cost savings reached **~$8.4bn (≈65%)** of the **~$13bn** targeted by end‑2026 — savings that fund investment in **talent, technology and AI**.
- Financial ambitions framing the demo: **~$200bn Net New Assets per year by 2028** and an **underlying cost/income ratio below 70%**.

> **Why this is the perfect POV spine.** Two giant banks, two of everything — two client masters, two product catalogues, two booking systems, two document stores, overlapping clients who bank with *both*. The integration is fundamentally a **data‑unification + AI‑activation** problem. FSI Helix tells exactly that story: *fragmentation → one governed BigQuery truth → agents that drive wealth growth, retention, forecasting, compliance and advisor productivity.*

### 1.3 The opening for the BigQuery Agentic Data Platform
- A bank-scale integration forces a once-in-a-generation **data-unification** programme — the ideal moment to make the **warehouse** the centre of gravity for both the data *and* the AI that reasons over it, rather than standing up yet another disconnected stack.
- **Our angle (not a rip‑and‑replace):** show the **BigQuery Agentic Data Platform** (Google Cloud) as the **data‑and‑AI gravity centre** — where AI runs *inside the warehouse, on governed data, with no data movement and no separate vector DB / graph DB / feature store / model‑serving stack to operate**. It gives any AI assistant your people use a *governed, structured, real* enterprise-data core to reason over.

### 1.4 The strategic narrative we sell
> *"You're merging the two largest pools of private wealth on earth into one bank. Your data lives in two of everything. FSI Helix turns that into your biggest asset: a single, governed, AI‑native lakehouse in BigQuery where collaborating agents drive net‑new‑money, retention, cross‑sell, forecasting and financial‑crime defence — without armies of pipelines or a separate ML platform to run."*

---

## 2. Business Objectives → Agentic Use Cases (Mapping)

| # | Apex Bank business objective | Agentic use case (demo) | Primary GCP / BigQuery AI capability |
|---|---|---|---|
| 1 | **Finish the Summit integration** | "Unify & Resolve" builds one Client 360 from two banks | **AI.GENERATE_TABLE** mapping + **autonomous embeddings** + **VECTOR_SEARCH** + **AI.GENERATE_BOOL** entity resolution → run by the **Data Engineering agent** |
| 2 | **Grow share‑of‑wallet (NNA)** | "Next‑Best‑Action" for advisors across the household / family‑office graph | **BigQuery Graph (GQL)** + **VECTOR_SEARCH** look‑alikes + **AI.GENERATE** |
| 3 | **Protect the asset base** | "Flight‑Risk Sentinel" predicts client attrition & NNA outflow + drafts the save | **TabularFM** classification + **AI.GENERATE** |
| 4 | **Plan toward $200bn NNA/yr** | "Forecast Room" projects AuM, NNA and revenue by division × region | **AI.FORECAST (TimesFM 2.5)** |
| 4b | **Explain the move (what→why)** | "Driver Lens" pinpoints which client segments drove a flow metric's change | **AI.KEY_DRIVERS** (key‑driver analysis) |
| 5 | **Democratise analytics** | "Ask Helix" — chat with the whole estate in plain English | **Conversational Analytics API (Gemini Data Analytics agent)** |
| 6 | **Advisor & research productivity** | "Research Brain" — grounded answers from CIO research / KYC / suitability docs | **AI.PARSE_DOCUMENT** + **Autonomous embeddings** + **AI.SEARCH** (RAG) |
| 7 | **Financial‑crime defence** | "Network Guard" — layering, structuring, circular flows, UBO risk | **BigQuery Graph** multi‑hop GQL |
| 8 | **Know the client** | "Segment Studio" — behavioral micro‑segments | **BigFrames** + KMeans + **AI.GENERATE** naming |
| 9 | **Agentic operating model** | "Agent Console" — DE + DS agents collaborate over **A2A** under an ADK orchestrator | **ADK** + **A2A protocol** + **BigQuery MCP/ADK toolset** + **Conversational Analytics** |

Each is a **route/panel** in the web app (Section 9).

---

## 3. Reference Architecture (GCP)

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                       Apex Bank HELIX (Web App)                    │
                    │   React + TS (Vite, Tailwind, shadcn/ui)  ── Cloud Run       │
                    └───────────────▲───────────────────────────▲─────────────────┘
                                    │ REST/SSE                   │ Conversational Analytics SDK
                    ┌───────────────┴───────────────┐   ┌────────┴──────────────────┐
                    │   FastAPI (Python) — Cloud Run │   │ Gemini Data Analytics     │
                    │   ADK Orchestrator             │   │ (Conversational Analytics │
                    │   ├─ Data Engineering agent ◄──┼─► │  agent)  "Ask Helix"        │
                    │   └─ Data Scientist agent      │   └───────────────────────────┘
                    │      (collaborate via  A2A)    │
                    │   BigQuery MCP / ADK toolset   │
                    └───────────────▲────────────────┘
                                    │  google-cloud-bigquery / bigframes
            ┌───────────────────────┼───────────────────────────────────────────────┐
            │                       │   BigQuery (the brain) — dataset FSI_POV        │
            │  ┌─────────────┐  ┌───┴─────────────┐  ┌──────────────────┐  ┌────────┐ │
            │  │ RAW zone    │  │ CURATED (canon.)│  │ AI / ML layer    │  │ GRAPH  │ │
            │  │ Apex + Summit    │→ │ clients,accounts│→ │ autonomous embeds│  │ client │ │
            │  │ multi-format│  │ portfolios,     │  │ TabularFM churn, │  │ + AML  │ │
            │  │ (CSV/JSON/  │  │ holdings, txns, │  │ AI.FORECAST TS,  │  │ PROPERTY│ │
            │  │  XML/FW/    │  │ advisors, NNA   │  │ vector indexes,  │  │ GRAPH  │ │
            │  │  parquet/   │  │ + entity res.   │  │ AI.SEARCH docs   │  │ + GQL  │ │
            │  │  PDF)       │  └─────────────────┘  └──────────────────┘  └────────┘ │
            │  └─────────────┘            ▲                    ▲                       │
            └─────────────────────────────┼────────────────────┼──────────────────────┘
                         BigFrames (pandas@BQ scale)   Remote models → Vertex AI
                ┌────────┴─────────┐                 ┌────────┴────────────────────┐
                │ Synthetic Data   │                 │ Vertex AI: Gemini 2.5 Flash, │
                │ Generator (Python│                 │ text-embedding-005           │
                │ + Faker + Gemini)│                 │ (via us-central1.vertex_conn)│
                └──────────────────┘                 └──────────────────────────────┘
            Cloud Storage: gs://fsi_pov  (raw fragmented files: Apex Bank/* and SummitBank/*)
```

Everything AI/ML happens **inside BigQuery** through one Cloud‑resource connection to Vertex AI. **No separate vector database, graph database, feature store, or model‑serving stack.**

### 3.1 GCP feature inventory (what each does — for the build)
| Feature | What it does | Where used in FSI Helix |
|---|---|---|
| **AI.GENERATE / _BOOL / _INT / _DOUBLE** | Typed generation over rows | Retention plays, segment names, source‑field mapping, entity‑match decisions |
| **AI.GENERATE_TABLE** | Structured (typed columns) output from a prompt | Normalising messy Apex Bank/Summit records → canonical client/account fields |
| **AI.PARSE_DOCUMENT** | OCR + layout parse + chunk PDFs | CIO research, KYC, suitability & advice docs |
| **Autonomous embeddings** (`GENERATED ALWAYS AS AI.EMBED(...)`) | Auto‑maintained, auto‑indexed embedding columns | Client profiles, products, document chunks |
| **AI.SEARCH** | One‑call semantic search over an autonomous‑embedding column | Research Brain, product/look‑alike search |
| **VECTOR_SEARCH + CREATE VECTOR INDEX** | ANN similarity at scale (`TREE_AH`, `COSINE`) | Entity resolution, client look‑alikes for NBA |
| **CREATE PROPERTY GRAPH + GQL (`GRAPH_TABLE`, `MATCH`)** | Graph modelling + multi‑hop traversal | Household/family‑office NBA, AML/UBO networks |
| **AI.FORECAST (TimesFM 2.5)** | Zero‑training multi‑series time‑series forecasting | AuM / NNA / revenue forecasting |
| **AI.KEY_DRIVERS** | Automatic key‑driver analysis — ranks the dimensional segments behind a metric change between two groups (`unexpected_difference` vs the population trend) | "Driver Lens": why NNA / inflows / outflows moved |
| **TabularFM** | Zero‑tuning classification/regression foundation model | Client attrition & NNA‑outflow risk |
| **BigFrames** | pandas/scikit‑learn API executing in BigQuery | Behavioral segmentation, feature pipelines |
| **Conversational Analytics API** | NL data agent (text/tables/charts + SQL) over BQ | "Ask Helix" |
| **ADK + A2A + BigQuery MCP toolset** | Agent runtime; agent‑to‑agent delegation; governed BQ tools | DE agent ⇄ DS agent ⇄ orchestrator |
| **ObjectRef** | Reference + process unstructured files alongside structured data | Linking PDFs to clients/accounts |

---

## 4. Synthetic Data Strategy (Two Banks, One Mess → One Truth)

The credibility of the demo depends on data that *looks like a post‑acquisition integration* and then gets unified. We generate two legacy estates — **Apex Bank** and **Summit Bank** — in **different formats with intentionally inconsistent schemas**, land them in GCS, and let the platform conform them.

> Hosted on: `gs://fsi_pov/raw/Apex Bank/...` and `gs://fsi_pov/raw/SummitBank/...`; loaded into BigQuery dataset **`FSI_POV`** (`us-central1`).

### 4.1 Design principles
1. **Two source banks.** Same concept ("relationship manager", "portfolio", "client") spelled and structured differently in each estate.
2. **Format diversity.** CSV, JSON (nested), XML, fixed‑width (mainframe extract), Parquet, Excel `.xlsx`, NDJSON event stream, and PDF (docs).
3. **Realistic dirtiness.** Missing values, multiple date formats (`DD.MM.YYYY` CH style, `YYYYMMDD`, ISO), currency mix (CHF/USD/EUR/HKD/SGD/GBP), inconsistent name/title casing, German/French/Italian/English field names, partial addresses.
4. **Cross‑bank overlap (the integration signal).** ~**20–25%** of clients are **dual‑banked** — they exist in *both* Apex Bank and Summit with mutated attributes. The platform must *rediscover* this (entity resolution) — we never write the true id into the source files.
5. **Household & family‑office links.** Shared address / surname / legal‑entity ownership → multi‑member households and family‑office structures (drive NBA + UBO graph).
6. **Time series with trend + seasonality + shocks** for forecasting realism (market drawdowns, post‑merger NNA dip then recovery). ≥ 48 monthly points per series.
7. **Volume knobs.** Default demo size (`SCALE=1`): ~**40k clients**, ~**90k accounts/portfolios**, ~**1.2m positions/holdings**, ~**600k transactions**, ~**400k market/telemetry points**, ~**1.5k documents**. Scale via `DATA_SCALE`.

### 4.2 Source → format mapping (the "fragmentation matrix")

| Source bank | Domain | File format | Quirks injected |
|---|---|---|---|
| **Apex Bank** | Clients | CSV | `client_id`, CH dates `DD.MM.YYYY`, CHF, German field names (`nachname`, `wohnort`) |
| **Apex Bank** | Portfolios / mandates | Fixed‑width (mainframe) | column positions, `YYYYMMDD`, mandate codes not labels |
| **Apex Bank** | Positions / holdings | Parquet | ISIN, asset‑class codes, CHF valuation |
| **Apex Bank** | Advisors (CA/RM) | Excel `.xlsx` | desk, booking centre, AuM book, language skills |
| **Summit Bank** | Clients | JSON (nested) | nested `client{}`/`address{}`, ISO dates, `cifNumber`, mixed CHF/USD |
| **Summit Bank** | Accounts / mandates | XML | `<Account>` elements, product code lists, EUR/USD |
| **Summit Bank** | Transactions | NDJSON event stream | per‑txn events, value date as epoch ms, FX legs |
| **Both** | Market & benchmark series | CSV | index levels, FX rates, asset‑class returns (forecasting context) |
| **Both** | NNA / flows ledger | CSV | inflows/outflows by client × month (NNA truth) |
| **Both (docs)** | CIO research, KYC, suitability, advice notes | **PDF** | text + scanned PDFs for AI.PARSE_DOCUMENT |

### 4.3 Canonical concepts to vary across sources
**Client** (name, DOB/incorporation, domicile, residency, segment tier, risk profile, KYC status, languages, marketing consent) · **Account/Mandate** (type: discretionary/advisory/execution‑only/Lombard/mortgage; booking centre; currency; status; open date) · **Portfolio/Holding** (ISIN, asset class, quantity, market value, currency, weight) · **Transaction** (buy/sell/transfer/fee/FX; amount; value date) · **Advisor** (CA/RM id, desk, booking centre, AuM book, market) · **NNA flow** (client × month inflow/outflow) · **Product** (mandate/fund/structured‑product catalogue with rich descriptions) · **Document** (type, gcs_uri, linked client/account, text) · **Legal entity / UBO** (for family offices & AML).

### 4.4 Generator implementation (`/synthetic_data`)
**Stack:** `faker` (locales `de_CH`, `fr_CH`, `en_GB`, `en_US`, `zh_TW`), `numpy`, `pandas`, `pyarrow` (Parquet), `openpyxl` (xlsx), `lxml`/`dicttoxml` (XML), `reportlab` (PDFs), `google-cloud-storage`, `google-cloud-bigquery`, optional **Gemini** (`google-genai`) for free‑text realism (research summaries, advice notes, KYC narratives).

```
synthetic_data/
  config.py                 # SCALE, source-bank list, GCS bucket, project/dataset, seeds
  reference.py              # ISINs, asset classes, booking centres, currencies, segments, products
  identities.py             # master client/household/legal-entity pool (the hidden "truth")
  banks/
    apex_clients_csv.py
    apex_portfolios_fixedwidth.py
    apex_positions_parquet.py
    apex_advisors_xlsx.py
    cs_clients_json.py
    cs_accounts_xml.py
    cs_transactions_ndjson.py
  markets.py                # index/FX/asset-class series (forecasting context)
  nna_flows.py              # NNA inflow/outflow ledger w/ trend + seasonality + shocks
  documents_pdf.py          # CIO research / KYC / suitability / advice notes (+Gemini text)
  upload_gcs.py             # push files to gs://fsi_pov/raw/<bank>/...
  load_raw_bq.py            # create RAW tables in FSI_POV (schemas intentionally varied)
  make_all.py               # orchestrate: --local | --gcp (generate → upload → load)
  requirements.txt
```

**Entity‑resolution game:** keep a hidden `master_client_id` in `identities.py`. When writing each bank's file, *project* the client into that bank's schema and **mutate** it (translate name order, drop/abbreviate middle names, vary domicile spelling, change email domain Apex Bank↔Summit, vary CIF/client number). Never write `master_client_id` into the source files. Keep a private `ground_truth_identity_map.csv` (excluded from the demo load path) to score entity‑resolution accuracy and surface it as a KPI.

**Time‑series formula (per division × region × month):**
```
value_t = base_level * (1 + trend*t) * seasonal[month] * shock(t) + noise
# shock(t): 2022 market drawdown, 2023 Summit-acquisition NNA dip, 2024-26 recovery & NNA ramp
```
Generate ≥ 48 monthly points so TimesFM has context.

### 4.5 Loading into the RAW zone
- **CSV / JSON / Parquet:** `LOAD DATA` or external tables over GCS.
- **XML / fixed‑width / NDJSON:** parsed in the loader to newline‑delimited JSON/Parquet first (BigQuery can't read XML/fixed‑width natively), then loaded — **but keep the original raw file in GCS** so we can still demo "AI parses the messy original" via AI functions / ObjectRef.
- **PDFs:** stay in GCS; referenced via **ObjectRef**; parsed with **AI.PARSE_DOCUMENT**.
- Result: `raw_apex_*` and `raw_cs_*` tables with deliberately different column names/types.

---

## 5. The "Unify & Resolve" Flow (Data Engineering agent)

The first agentic win: **two banks' fragmented RAW → one canonical CURATED Client 360**, driven by the **Data Engineering agent** using BigQuery AI functions.

### 5.1 Schema mapping with AI
```sql
-- Normalise Summit raw clients into canonical shape
CREATE OR REPLACE TABLE FSI_POV.stg_client_cs AS
SELECT
  AI.GENERATE_TABLE(
    ('Extract canonical client fields from this record. Standardize name order, '
     || 'domicile country (ISO-2), client segment tier, and ISO date of birth. '
     || 'Record: ' || TO_JSON_STRING(t)),
    connection_id => 'us-central1.vertex_conn',
    endpoint => 'gemini-2.5-flash',
    output_schema => 'full_name STRING, dob DATE, domicile STRING, '
                  || 'segment_tier STRING, email STRING, primary_ccy STRING'
  ).*,
  'summit' AS source_bank,
  t.cifNumber AS source_key
FROM FSI_POV.raw_summit_clients t;
```
Repeat per source → `stg_client_apex`, `stg_client_cs`, then `UNION ALL` into `FSI_POV.client_inbound`.

> Use **deterministic SQL** for the easy 80% (regex/date/currency parsing) and reserve AI functions for the genuinely messy fields — cheaper and faster.

### 5.2 Entity resolution (dedupe dual‑banked clients)
Two‑stage **blocking → AI adjudication**:
1. Autonomous embedding on `full_name||domicile||dob`, then `VECTOR_SEARCH` for top‑k near‑duplicates within a domicile/dob block.
2. Adjudicate candidate pairs with **AI.GENERATE_BOOL** ("Are these the same person/entity across Apex Bank and Summit Bank?").
3. Cluster matched pairs (connected components) → assign a stable `client_id`. Validate against `ground_truth_identity_map.csv` → **entity‑resolution accuracy KPI**.

### 5.3 Output
Populates the CURATED tables (Section 6). The **"Unify & Resolve"** panel visualizes: sources discovered, % fields mapped, dual‑banked clients found, resolution accuracy, and a before/after record example (messy Summit JSON → clean canonical client).

---

## 6. Canonical BigQuery Data Model (CURATED) — dataset `FSI_POV`

Single consolidated dataset `FSI_POV` (logical zones via table prefixes), portable to a four‑dataset layout if preferred. Core curated tables (PK in **bold**):

- **`clients`** — **client_id**, full_name, dob, segment_tier {Affluent, HNW, UHNW, Family Office, Institutional}, domicile, residency, booking_centre, risk_profile, kyc_status, languages ARRAY, source_banks ARRAY, primary_advisor_id, total_aum_usd NUMERIC, tenure_days, marketing_consent BOOL, **client_embedding** STRUCT (autonomous).
- **`accounts`** — **account_id**, client_id, account_type {discretionary, advisory, execution_only, lombard, mortgage, deposit}, booking_centre, currency, status, open_date, balance_usd.
- **`portfolios`** — **portfolio_id**, account_id, client_id, mandate_type, benchmark, currency, market_value_usd, inception_date.
- **`holdings`** — **holding_id**, portfolio_id, isin, asset_class {equity, fixed_income, fund, structured, alternative, cash, fx}, quantity, market_value_usd, weight_pct.
- **`transactions`** — **txn_id**, account_id, client_id, txn_type {buy, sell, transfer_in, transfer_out, fee, fx}, amount_usd, currency, value_date, counterparty.
- **`advisors`** — **advisor_id**, name, role {CA, RM}, desk, booking_centre, market, aum_book_usd, languages ARRAY.
- **`nna_flows`** — client_id, month DATE, net_new_money_usd, inflow_usd, outflow_usd.
- **`households`** — **household_id**, address_key, member_count, total_aum_usd, lines_held ARRAY.
- **`legal_entities`** — **entity_id**, entity_type {trust, holdco, foundation, spv}, jurisdiction, ubo_client_id, risk_flag (AML/UBO graph).
- **`products`** — **product_id**, product_type, name, description (rich), target_segment_hint, **description_embedding** (autonomous).
- **`documents`** — **document_id**, gcs_uri (ObjectRef), doc_type {cio_research, kyc, suitability, advice_note}, client_id, parsed_text, **text_embedding** (autonomous), chunks.
- **Time‑series marts** — `ts_aum_monthly(month, division, region, booking_centre, aum_usd)`, `ts_nna_monthly(...)`, `ts_revenue_monthly(...)`.

---

## 7. Agentic Use Cases — Detailed Build

Each: **business value → GCP mechanism → SQL/code → web app surface.**

### 7.1 Unified Client 360 — "Unify & Resolve" (Data Engineering agent)
Covered in Section 5. **Surface:** `/unify` — two‑bank source list with format icons + row counts, animated RAW→CURATED flow, dual‑banked clusters, before/after card, entity‑res accuracy gauge, "Re‑run unification" (calls the DE agent).

### 7.2 Next‑Best‑Action / Cross‑sell (BigQuery Graph + Vector Search)
**Value:** grow share‑of‑wallet — the direct lever on the $200bn NNA ambition. Identify the next mandate/product a client (or their household/family office) is most likely to need and *why*.

**Property graph:**
```sql
CREATE PROPERTY GRAPH FSI_POV.client_graph
NODE TABLES (
  FSI_POV.clients   KEY(client_id)   LABEL Client   PROPERTIES(client_id, full_name, segment_tier, booking_centre, household_id),
  FSI_POV.households KEY(household_id) LABEL Household PROPERTIES(household_id, member_count, total_aum_usd),
  FSI_POV.products  KEY(product_id)  LABEL Product  PROPERTIES(product_id, product_type, name),
  FSI_POV.accounts  KEY(account_id)  LABEL Account  PROPERTIES(account_id, account_type, booking_centre),
  FSI_POV.advisors  KEY(advisor_id)  LABEL Advisor  PROPERTIES(advisor_id, name, desk)
)
EDGE TABLES (
  FSI_POV.clients  AS BelongsTo SOURCE KEY(client_id) REFERENCES Client(client_id)
                   DESTINATION KEY(household_id) REFERENCES Household(household_id) LABEL BELONGS_TO,
  FSI_POV.accounts AS Holds     SOURCE KEY(client_id) REFERENCES Client(client_id)
                   DESTINATION KEY(account_id) REFERENCES Account(account_id) LABEL HOLDS,
  FSI_POV.clients  AS AdvisedBy SOURCE KEY(client_id) REFERENCES Client(client_id)
                   DESTINATION KEY(advisor_id) REFERENCES Advisor(advisor_id) LABEL ADVISED_BY
);
```
**Cross‑sell GQL — "what do household‑mates / look‑alikes hold that this client lacks":**
```sql
SELECT * FROM GRAPH_TABLE(
  FSI_POV.client_graph
  MATCH (me:Client {client_id: 'CLI_000123'})-[:BELONGS_TO]->(h:Household)
        <-[:BELONGS_TO]-(mate:Client)-[:HOLDS]->(a:Account)
  RETURN a.account_type AS product, COUNT(*) AS household_signal
  GROUP BY product ORDER BY household_signal DESC
);
```
**Look‑alike propensity (VECTOR_SEARCH on `client_embedding`)** + **AI.GENERATE** advisor‑ready rationale & suggested talking points.

**Surface:** `/nba` — client search → graph canvas (household ↔ accounts ↔ advisor) → ranked next‑best‑actions with confidence + AI rationale + "draft advisor note".

### 7.3 Client Attrition / NNA Flight‑Risk — "Flight‑Risk Sentinel" (TabularFM)
**Value:** the integration is the moment of maximum flight risk; protecting AuM is worth billions. Predict attrition / outflow 60–90 days out and draft the save.
```sql
CREATE OR REPLACE MODEL FSI_POV.attrition_tabularfm
OPTIONS(model_type='TABULARFM', input_label_cols=['attrited']) AS
SELECT * FROM FSI_POV.attrition_training;   -- features: tenure, AuM trend, outflow ratio,
                                            -- dual-banked flag, advisor changes, txn velocity, fees

SELECT client_id, predicted_attrited, predicted_attrited_probs
FROM ML.PREDICT(MODEL FSI_POV.attrition_tabularfm, TABLE FSI_POV.attrition_scoring);
```
> GA fallback: `BOOSTED_TREE_CLASSIFIER` with the identical scoring contract so the UI is unchanged.

**AI.GENERATE** drafts a tailored retention play (relationship gesture, mandate review, fee discussion) grounded in holdings + risk profile. **Surface:** `/retention` — outflow pipeline by week, risk heatmap, per‑client drivers, AI‑drafted save play + channel.

### 7.4 AuM / NNA / Revenue Forecasting — "Forecast Room" (AI.FORECAST / TimesFM)
```sql
SELECT * FROM AI.FORECAST(
  TABLE FSI_POV.ts_nna_monthly,
  data_col => 'net_new_money_usd', timestamp_col => 'month',
  id_cols => ['division','region'], model => 'TimesFM 2.5',
  horizon => 12, confidence_level => 0.9
);
```
Repeat for `ts_aum_monthly` and `ts_revenue_monthly`. **Surface:** `/forecast` — metric/division/region/horizon selectors, history + forecast + confidence band, AI "what's driving it" commentary, portfolio roll‑up vs the $200bn NNA ambition.

### 7.4b "From What to Why" — Key‑Driver Analysis — "Driver Lens" (AI.KEY_DRIVERS)
The Forecast Room shows *what* the flow metrics are doing; **AI.KEY_DRIVERS** explains *why* one moved — automatically ranking the dimensional segments most responsible for a change between two groups, with no `GROUP BY` sweeps, hand‑built self‑joins or a bespoke ML pipeline. We compare the **recent 6 months (interest group) vs the prior 6 months (reference group)** of per‑client monthly flows, enriched with the unified Client 360 dimensions.
```sql
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT c.segment_tier, c.region, c.booking_centre, c.risk_profile,
          IF(c.dual_banked,'Dual-banked (Apex + Summit)','Single-bank') AS banking,
          f.net_new_money_usd,
          f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(),MONTH), INTERVAL 6 MONTH) AS is_recent
   FROM FSI_POV.client_flows f JOIN FSI_POV.clients c USING (client_id)
   WHERE f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(),MONTH), INTERVAL 12 MONTH)),
  metric_col => 'net_new_money_usd',
  dimension_cols => ['segment_tier','region','booking_centre','risk_profile','banking'],
  interest_label_col => 'is_recent', top_k => 20, enable_pruning => TRUE
);
```
Repeat with `metric_col => 'inflow_usd'` / `'outflow_usd'`. The headline column is **`unexpected_difference`** — the part of a segment's move that the *bankwide* trend does **not** explain — so the demo ranks on it: APAC UHNW / Hong Kong over‑shoot the trend upward, while **dual‑banked (Apex + Summit) Swiss clients** (the integration‑overlap cohort) drag NNA down by more than expected — the exact cohort the Flight‑Risk Sentinel then defends. **Build:** `infra/setup_fsi_key_drivers.sql` (+ Dataform `definitions/driver_analysis/`); the live backend calls `AI.KEY_DRIVERS` directly in `backend/app/bq.py:key_drivers`. **Surface:** `/drivers` — metric selector (NNA / inflows / outflows), ranked driver segments with recent‑vs‑prior, relative change, contribution, segment size and the unexpected‑difference bar, plus a Gemini "why it moved" narrative.

### 7.5 Conversational Analytics — "Ask Helix" (Gemini Data Analytics agent)
Create a **DataAgent** scoped to `FSI_POV.*` (+ optionally the property graph); stream NL questions; return text + tables + Vega charts + the generated SQL. *(Live: the demo is wired to a real Conversational Analytics data agent — display name `FSI_POV`, id `agent_a61c018d-fc8f-45b1-ad42-2f70f83cd597`, location `us` — via the `:chat` streaming endpoint; the backend maps its `systemMessage` chunks — FINAL_RESPONSE text, `generatedSql`, `result`, Vega `chart`, follow-ups — into the UI block format. Set `CA_AGENT_ID` / `CA_LOCATION` in `backend/.env`.)* **Demo questions:** *"Which booking centre grew NNA fastest last quarter?"* · *"Top 10 UHNW clients by outflow risk."* · *"Compare discretionary vs advisory mandate AuM by region."* · *"Which households hold equities but no discretionary mandate?"* (graph‑backed). **Surface:** `/ask` — chat thread, rendered charts/tables, "show SQL" expander, "pin to Home".

### 7.6 Investment Research & Advice Intelligence — "Research Brain" (AI.PARSE_DOCUMENT + Autonomous embeddings + AI.SEARCH)
Parse PDFs (CIO research, KYC, suitability, advice notes) → autonomous embeddings on chunks → `AI.SEARCH` → grounded `AI.GENERATE` answer with citations back to `gcs_uri`.
```sql
SELECT base.document_id, base.chunk_text, distance
FROM AI.SEARCH(TABLE FSI_POV.doc_search, 'chunk_text',
               'CIO view on private credit allocation for UHNW clients');
```
**Surface:** `/research` — search → ranked passages with source preview → cited AI answer; "summarize this client's KYC/suitability file".

### 7.7 AML / Financial‑Crime & UBO Network — "Network Guard" (BigQuery Graph)
Reuse the graph with risk edges (`SHARES_ADDRESS`, `SHARES_COUNTERPARTY`, `OWNS_ENTITY`, `TRANSFERS_TO`) and multi‑hop GQL to surface **layering** (rapid sequential transfers), **structuring/smurfing** (sub‑threshold repetitive transfers), **circular flows** (funds returning to origin via intermediaries), and **UBO risk** (retail flows mapping upstream to high‑risk legal entities). Clicking a suspicious hub pulls the exact transactions and runs **AI.GENERATE** to classify the suspicion type from the subgraph topology. *(Pattern adapted from the Fintech AML reference demo.)* **Surface:** `/network` — interactive subgraphs + AI anomaly summaries.

### 7.8 Behavioral Segmentation — "Segment Studio" (BigFrames + KMeans + AI naming)
```python
import bigframes.pandas as bpd
bpd.options.bigquery.project = "raves-altostrat"
df = bpd.read_gbq("FSI_POV.client_features")        # tenure, AuM, asset-mix, txn velocity, ...
from bigframes.ml.cluster import KMeans
m = KMeans(n_clusters=8); m.fit(df); df["segment"] = m.predict(df).to_pandas()
df.to_gbq("FSI_POV.client_segments", if_exists="replace")
```
**AI.GENERATE** names each segment ("Globally‑Mobile UHNW Entrepreneurs", "Conservative Swiss Retirees"). **Surface:** `/segments` — 2D cluster scatter, segment cards (AI name, size, avg AuM, dominant asset class, attrition index), "send to NBA / Retention".

### 7.9 The Agentic Core — "Agent Console" (ADK + A2A: DE agent ⇄ DS agent)
This is the centerpiece the user explicitly wants. An **ADK Orchestrator** receives a free‑form business goal and decomposes it across two specialist agents that **collaborate over the A2A protocol**:

- **Data Engineering agent** — owns pipelines & data readiness: runs Unify & Resolve, builds feature tables, materializes the property graph, refreshes embeddings/indexes. Exposes A2A skills like `build_feature_table`, `refresh_graph`, `run_entity_resolution`.
- **Data Scientist agent** — owns modelling & insight: trains/scores TabularFM, runs AI.FORECAST, BigFrames clustering, and narrates results. Exposes A2A skills like `forecast_series`, `score_attrition`, `segment_clients`, `explain_drivers`.

**A2A flow example:** goal *"Tell me which UHNW clients we'll lose next quarter and why."* → Orchestrator → **DS agent** needs features → emits an **A2A task** to the **DE agent** (`build_feature_table(attrition)`) → DE agent returns a table handle → DS agent scores TabularFM + explains drivers → Orchestrator composes the answer. Each agent is an ADK `LlmAgent` (Gemini) exposing an **A2A AgentCard**; tool calls go through the **BigQuery MCP/ADK toolset** so they're deterministic and governed. The Conversational Analytics agent is the NL surface. **Surface:** `/agents` — a **data-lifecycle view across five persona blocks** that each fill with real output as the goal flows through them: **① Raw Data** (two-bank source counts + dual-banked discovered + sample), **② Data Engineering Agent** (the *real* Google Cloud DE agent over A2A, streaming its reading of the Dataform workspace), **③ Data Scientist** (real BigQuery ML / TimesFM — segment grid / forecast chart / flight-risk list), **④ Conversational Analytics Agent** (the *real* agent answering a business question with text+table+SQL), **⑤ Business User** (a Gemini-composed recommendation). Each block shows working→done status, and BigQuery/Dataform artifacts are linked inline — so a customer literally watches the agents coordinate as different personas across the end-to-end lifecycle.

> **Real vs. narration (be transparent with the customer).**
> - **The Data Engineering agent is the REAL Google Cloud Data Engineering Agent** — a genuine A2A agent at `geminidataanalytics.googleapis.com/v1/a2a/projects/{p}/locations/{loc}/agents/dataengineeringagent`, a "BigQuery + Dataform ELT expert." The orchestrator delegates to it over A2A (`message:stream`, with the required `gcpresource` extension pointing at our live Dataform workspace `fsi_pov_pipeline/dev`); its streamed messages appear in the trace marked **LIVE A2A**. See `backend/app/de_agent.py`.
> - **The Conversational Analytics agent (Ask Helix) is also the real product** (data agent `FSI_POV`).
> - **The data operations are real and auditable**: "Build behavioural segments" runs `infra/build_segments.py` — `client_features` → BQML **`client_kmeans`** → `client_segments` (ML.PREDICT) → `client_segments_summary` with **Gemini names** — all openable in BigQuery, and expressed as lineage in the **live Dataform repository** the DE agent operates on.
> - **What's still our own code:** the top-level **Orchestrator** routing and the **Data Scientist** steps (real BigQuery ML/TimesFM, but invoked by our code, not a packaged "DS agent" product). These can move to the literal `google-adk` runtime without changing the API or UI.

---

## 8. Web Application Design ("FSI Helix")

### 8.1 Tech stack
**Frontend:** React 18 + TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, Recharts, Cytoscape.js (graph), react‑markdown, lucide‑react. **Backend:** FastAPI (Python 3.11), google‑cloud‑bigquery, bigframes, google‑genai, google‑adk + a2a, Conversational Analytics client, pydantic, SSE streaming. **Auth (demo):** shared‑token or Google IAP. **Deploy:** two Cloud Run services (web + api), Artifact Registry + Cloud Build. **Dual mode:** `USE_BQ` / `VITE_USE_MOCKS` master switches (fixtures vs live BigQuery), exactly like the reference demos.

### 8.2 Information architecture (routes)
```
/            Home / Vision + live KPIs (clients, AuM, NNA, dual-banked %, ER accuracy)
/unify       Unify & Resolve (two banks → one Client 360)
/nba         Next-Best-Action (graph + look-alikes)
/retention   Flight-Risk Sentinel (TabularFM attrition)
/forecast    Forecast Room (TimesFM: AuM / NNA / revenue)
/drivers     Driver Lens (AI.KEY_DRIVERS: why a flow metric moved)
/ask         Ask Helix (Conversational Analytics chat)
/research    Research Brain (document intelligence)
/network     Network Guard (AML / UBO graph)
/segments    Segment Studio (BigFrames clustering)
/agents      Agent Console (ADK orchestrator + A2A trace)
```

### 8.3 API contract (FastAPI ⇄ React)
```
GET  /api/kpis                         -> { clients, aum_usd, nna_ytd, dual_banked_pct, er_accuracy }
GET  /api/sources                      -> [{ bank, format, rows, status }]
POST /api/unify/run                    -> SSE { mapped_fields, dual_banked_clusters, accuracy }
GET  /api/clients/search?q=            -> [{ client_id, name, segment_tier, booking_centre }]
GET  /api/nba/{client_id}              -> { graph, actions:[{product, score, signals, rationale}] }
POST /api/nba/{id}/draft               -> { advisor_note }
GET  /api/retention/pipeline           -> [{ week, count, high_risk }]
GET  /api/retention/scores             -> [{ client_id, prob, drivers:[], play }]
GET  /api/forecast?metric=&division=&region=&horizon= -> { history, forecast:[{ts,yhat,lo,hi}], commentary }
POST /api/ask                          -> SSE { text | table | chart_spec | sql }
GET  /api/research/search?q=           -> [{ document_id, gcs_uri, snippet, score }]
POST /api/research/answer              -> { answer, citations:[{document_id, gcs_uri}] }
GET  /api/network/patterns            -> { subgraphs:[...], anomalies:[{type, summary}] }
POST /api/segments/recompute           -> { segments:[{id,label,size,avg_aum,asset_mix,attrition_index}] }
POST /api/agents/goal                  -> SSE { route, a2a_steps:[{agent, skill, tool_calls}], result }
```

### 8.4 Repository layout
```
Apex Bank/
  Apex Bank_AGENTIC_POV_PLAN.md      <- this doc
  README.md                    <- demo + live setup (mirrors reference demos)
  SPEAKER_PITCH.md             <- CxO narrative
  infra/
    setup_bq.sql               # datasets, connection, embeddings, vector indexes, property graph
    setup_apex_attrition.sql    # TabularFM/boosted-tree churn + scoring + AI plays
    setup_apex_forecast.sql     # time-series marts (forward-dated for the demo window)
    deploy_cloudrun.sh
    env.example
  synthetic_data/              # Section 4 package
  backend/
    app/{main.py,config.py,services.py,bq.py,routers/,agents/,fixtures/}
    requirements.txt           # demo deps
    requirements-bq.txt        # live deps (+bigquery, bigframes, adk, a2a)
    Dockerfile
  frontend/
    src/{pages/,components/,lib/}
    package.json, vite.config.ts, tailwind.config.js
    Dockerfile
```

### 8.5 Environment (`infra/env.example`)
```
GOOGLE_CLOUD_PROJECT=raves-altostrat
GCP_REGION=us-central1
BQ_LOCATION=us-central1
BQ_CONNECTION=us-central1.vertex_conn
BQ_DATASET=FSI_POV
GCS_BUCKET=fsi_pov
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-005
DATA_SCALE=1
USE_BQ=false                  # true = live BigQuery
```

---

## 9. Build Roadmap (Phases)

- **Phase 0 — Foundations (Day 1).** Enable APIs (BigQuery, BigQuery Connection, Vertex AI, Storage, Gemini Data Analytics, Cloud Run); create dataset `FSI_POV` + bucket `gs://fsi_pov`; confirm `us-central1.vertex_conn` has Vertex AI User; smoke‑test `AI.GENERATE`.
- **Phase 1 — Synthetic data (Days 1–3).** Build `synthetic_data`; generate two‑bank fragmented files; upload to GCS; load RAW. Verify fragmentation, dual‑banked overlap, time series.
- **Phase 2 — Unify & Resolve (Days 3–5).** AI mapping + embedding/AI.GENERATE_BOOL entity resolution → CURATED + KPIs + ER accuracy.
- **Phase 3 — AI / Graph / ML layer (Days 5–8).** Autonomous embeddings + vector indexes; property graph + GQL (NBA + AML); TabularFM attrition; AI.FORECAST marts; BigFrames segments; AI.PARSE_DOCUMENT + AI.SEARCH doc pipeline.
- **Phase 4 — Backend + agents (Days 8–12).** FastAPI routers; **ADK orchestrator + DE/DS agents over A2A**; Conversational Analytics; SSE.
- **Phase 5 — Frontend (Days 10–16).** All routes against the API; design polish; light/dark; demo mode.
- **Phase 6 — Demo hardening (Days 16–18).** Seed deterministic "hero" clients/segments; scripted narrative; deploy to Cloud Run; dry‑run.

> Thin slice for the workshop (Unify + NBA + Forecast + Ask Helix + Agent Console) is achievable in ~1 week; full polished POV ~2.5–3.5 weeks.

---

## 10. Demo Narrative (the C‑level story)

1. **The two‑bank mess (`/unify`).** "Two banks, two of everything." Run unification → RAW collapses into one Client 360; entity resolution finds the same UHNW client banking with *both* Apex Bank and Summit; accuracy gauge ticks up.
2. **The 360° client (`/nba`).** Pick a hero family‑office client → graph shows the household holds equities + a Lombard loan but **no discretionary mandate** → agent recommends a discretionary mandate (+ private‑credit fund #2) with rationale → draft advisor note.
3. **Protect the base (`/retention`).** Outflow pipeline lights up; top flight‑risk drivers shown (dual‑banked + recent outflows); AI drafts a save play.
4. **Plan the growth (`/forecast`).** NNA by division/region for 12 months with confidence bands vs the $200bn ambition; AI explains drivers.
5. **Anyone can ask (`/ask`).** "Which booking centre grew NNA fastest, and which households hold equities but no discretionary mandate?" → chart + table + SQL, graph‑backed.
6. **Research at your fingertips (`/research`).** Search "CIO view on private credit for UHNW" → cited passages from parsed PDFs + grounded answer.
7. **Defend the bank (`/network`).** Surface a structuring ring and a UBO‑risk cluster as interactive subgraphs + AI anomaly summary.
8. **The agentic operating model (`/agents`).** One goal → watch the **DS agent ask the DE agent over A2A** for features, then forecast + explain. 
9. **Close.** "All of this lives in BigQuery — agents reasoning over governed, unified data, no separate ML platform, no data movement."

---

## 11. Cost, Governance & Caveats
- **Cost control:** keep `DATA_SCALE=1`; deterministic SQL over AI functions on bulk rows; cache forecast/segment/score outputs in tables; set BQ **maximum bytes billed** + budget alerts; AI functions in **Optimized Mode** where available.
- **Governance:** all data synthetic; **no real Apex Bank/Summit or PII**. Column‑level policy tags as a talking point. Record agent actions for the A2A trace panel.
- **Preview features:** TabularFM, some autonomous‑embedding nuances, graph‑in‑Conversational‑Analytics, and A2A tooling may be **Preview** / region‑limited. GA fallbacks: TabularFM→`BOOSTED_TREE_CLASSIFIER`; AI.SEARCH→explicit `VECTOR_SEARCH`; confirm `AI.FORECAST` in `us-central1`. Keep API contracts stable so the UI is unaffected.
- **Determinism for demos:** seed RNG; pre‑warm vector indexes; pre‑bake "hero" entities; forward‑date time series into the demo window.

---

## 12. Sources (Research)

**Apex Bank / customer context**
- [Apex Bank publishes 2025 Annual Report](https://www.apex.com/global/en/media/display-page-ndp/en-20260309-annual-report.html)
- [Annual Report 2025 — Apex Bank Group (PDF)](https://www.apex.com/content/dam/assets/cc/investor-relations/annual-report/2025/annual-report-apex-group-2025.pdf)
- [Apex Group AG — FY2025 investor presentation (SEC 6‑K)](https://www.sec.gov/Archives/edgar/data/0001610520/000161052025000110/investorpresotext2025.htm)
- [Apex Bank Q1 2025 — wealth management drives profit as integration progresses](https://www.investing.com/news/company-news/apex-q1-2025-presentation-wealth-management-drives-profit-as-integration-progresses-93CH-4011779)
- [Apex Bank — AI for Financial Advisors](https://www.apex.com/us/en/wealth-management/financial-advisor-experience/articles/ai-for-financial-advisors.html)
- [Apex Bank Group — business structure & Summit integration summary](https://exceljump.com/en/apex-group-guide/)
- [Apex Bank Global Wealth Report 2025](https://www.apex.com/global/en/media/display-page-ndp/en-20250618-gwr-2025.html)

**Google Cloud capabilities**
- [BigQuery autonomous embedding generation (AI.EMBED / AI.SEARCH)](https://cloud.google.com/blog/products/data-analytics/introducing-bigquery-autonomous-embedding-generation)
- [New BigQuery capabilities for the agentic era](https://cloud.google.com/blog/products/data-analytics/unveiling-new-bigquery-capabilities-for-the-agentic-era)
- [AI.FORECAST function](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-forecast)
- [The TimesFM model (BigQuery)](https://docs.cloud.google.com/bigquery/docs/timesfm-model)
- [BigQuery Graph overview](https://docs.cloud.google.com/bigquery/docs/graph-overview)
- [GQL within SQL / GRAPH_TABLE](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-queries)
- [Conversational Analytics API (Gemini Data Analytics)](https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/overview)
- [AI-based forecasting & analytics in BigQuery via MCP and ADK](https://cloud.google.com/blog/products/data-analytics/ai-based-forecasting-and-analytics-in-bigquery-via-mcp-and-adk/)
- [Agent2Agent (A2A) protocol](https://github.com/google/A2A)
- [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
```
