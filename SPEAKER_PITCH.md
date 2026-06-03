# UBS Helix — C-Level Workshop Pitch

> A 12–15 minute narrated walk-through of UBS Helix on the **Google Cloud Agentic Data
> Platform**. The spine is the **Credit Suisse integration**: two banks, two of everything,
> overlapping clients — turned into one governed, agent-driven intelligence layer in BigQuery.
> All data is synthetic.

---

## The one-liner

> *"You're merging the two largest pools of private wealth on earth. Your data lives in two
> of everything. UBS Helix turns that into your biggest asset — a single, governed, AI-native
> lakehouse in BigQuery where collaborating agents drive net-new-money, retention, cross-sell,
> forecasting and financial-crime defence, with no data movement and no separate ML platform."*

## The 60-second elevator version (open with this)

> *"UBS is completing the largest banking integration in history. The hard part isn't the
> balance sheet — it's the data: two client masters, two product catalogues, two of every
> system, and clients who bank with both. Today that fragmentation is a cost and a risk.
> What if it were your single biggest growth asset?*
>
> *UBS Helix unifies the UBS and Credit Suisse estate into one governed Client 360 in BigQuery —
> and then, in the same place the data lives, runs the AI: it finds the dual-banked clients,
> predicts who's about to walk and drafts the save, tells every advisor the next best action
> for each household, forecasts net-new-money toward your $200bn ambition, answers any question
> in plain English, and watches for financial-crime networks. No data movement, no separate ML
> platform — and a team of AI agents that do the analytical legwork while your people decide.
> Let me show you, on a synthetic copy of your own world."*

## Business value — the "so what"

| Lever | Today's pain | What UBS Helix changes | Tied to |
|---|---|---|---|
| **Integration** | Years of manual reconciliation across two estates | AI maps schemas & resolves dual-banked clients automatically | End-2026 completion |
| **Net new money** | Cross-sell trapped in advisor heads & siloed data | Graph + look-alike NBA surfaces the next mandate per household | **$200bn NNA/yr by 2028** |
| **Retention** | Flight risk spotted *after* the outflow | Attrition predicted 60–90 days early + an AI-drafted save play | Protect ~$5tn AuM |
| **Productivity** | Analysts wait days for a BI request; advisors hunt through 60k docs | Plain-English answers + cited research in seconds | **<70% cost/income** |
| **Risk** | Financial-crime patterns hide across booking centres | Multi-hop graph surfaces structuring / UBO networks | Regulatory confidence |
| **Operating model** | Every insight needs a data team round-trip | Agents collaborate over A2A to deliver the answer to a goal | Scales the $13bn savings into capacity |

## Why this lands for UBS

- **Integration completes end-2026** — client-account migration and infrastructure
  decommissioning is fundamentally a **data-unification + AI-activation** problem.
- **$13bn cost-savings programme** funds technology and AI — this is where the gravity should sit.
- **~$200bn NNA/yr by 2028** and a **<70% cost/income** ambition — every screen ties to those numbers.
- It **complements** the existing Azure/UBS-Red assistant strategy by giving agents *governed,
  structured, real* enterprise data to reason over.

---

## The demo flow (10 beats)

1. **Home — the vision.** "From two banks and two of everything to one agentic intelligence
   layer." Point at the live KPIs: 40k clients unified, ~22% dual-banked, NNA tracking toward
   the $200bn ambition, entity-resolution accuracy.

2. **Unify & Resolve — finish the integration.** Show the seven fragmented sources (UBS CSV /
   fixed-width / Parquet / xlsx; CS JSON / XML / NDJSON). Click **Run unification** → watch the
   raw mess collapse into one Client 360; the before/after card shows a messy Credit Suisse JSON
   record resolved to a clean canonical client, and the dual-banked counter ticks up.
   *Capability: AI.GENERATE_TABLE mapping + autonomous embeddings + VECTOR_SEARCH + AI.GENERATE_BOOL — run by the Data Engineering agent.*

3. **Next-Best-Action — grow share-of-wallet.** Pick a family-office client → the household
   graph shows what relatives hold; the agent recommends a **Private Markets** mandate the client
   lacks, with a Gemini-drafted advisor rationale. *Capability: BigQuery Graph (GQL) + VECTOR_SEARCH look-alikes.*

4. **Flight-Risk Sentinel — protect the asset base.** The outflow pipeline lights up; the top
   flight-risk clients are **dual-banked with recent outflows**; Gemini drafts the save play.
   *Capability: TabularFM attrition (boosted-tree default) + AI.GENERATE.*

5. **Forecast Room — plan the growth.** NNA by division/region, 12-month horizon with confidence
   bands, tracking the $200bn ambition; AI explains the drivers. *Capability: AI.FORECAST / TimesFM 2.5 — zero training.*

6. **Ask UBS — democratise analytics.** Type *"Which booking centre grew NNA fastest?"* → get a
   chart, a table, and the **generated SQL**. No BI bottleneck. *Capability: Conversational Analytics.*

7. **Research Brain — advisor productivity.** Search *"CIO view on private credit for UHNW"* →
   cited passages from parsed documents + a grounded answer. *Capability: autonomous embeddings + AI.SEARCH RAG.*

8. **Network Guard — defend the bank.** Surface a structuring ring and a UBO-risk cluster as an
   interactive subgraph with an AI anomaly summary. *Capability: BigQuery Graph multi-hop GQL.*

9. **Segment Studio — know the client.** Behavioural micro-segments ("Globally-Mobile UHNW
   Entrepreneurs", "Conservative Swiss Retirees") named by Gemini. *Capability: BigFrames KMeans + AI.GENERATE.*

10. **Agent Console — the operating model.** Set a goal: *"Which UHNW clients will we lose next
    quarter, and why?"* → watch the **Data Scientist agent ask the Data Engineering agent over
    A2A** for features, then score and explain. *Capability: ADK orchestrator + A2A + BigQuery MCP.*

---

## The close

> *"Everything you just saw runs **inside BigQuery** — embeddings, the graph, forecasting, the
> attrition model, the document index — reasoned over by agents on governed, unified data. No
> data movement. No separate vector DB, graph DB, feature store, or model-serving stack to run.
> That's the Google Cloud Agentic Data Platform: the place your integrated data and your AI
> belong together."*

## Likely questions

- **"Is this real or mocked?"** Live mode runs real BigQuery AI on `raves-altostrat`. Demo mode
  uses fixtures for air-gapped rooms. Same UI, one flag.
- **"What about Azure / UBS Red?"** Complementary — Helix is the *data-and-AI core* that feeds
  governed structured data to whichever assistant surface you choose.
- **"TabularFM / TimesFM maturity?"** TimesFM forecasting is live here; TabularFM ships with a
  GA boosted-tree default and the same scoring contract, so nothing in the UI changes.
- **"Governance?"** All synthetic, no PII. Column-level policy tags, the A2A trace, and
  warehouse-native lineage are the governance story.
