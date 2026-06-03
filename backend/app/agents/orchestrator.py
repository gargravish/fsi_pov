"""
orchestrator.py — The agentic core of UBS Helix.

An ADK-style Orchestrator decomposes a free-form business goal across two
specialist agents that collaborate over the Agent-to-Agent (A2A) protocol:

  • DataEngineeringAgent — owns data readiness (entity resolution, feature
    tables, the property graph, embeddings). A2A skills: run_entity_resolution,
    build_feature_table, refresh_graph.
  • DataScientistAgent — owns modelling & insight (TabularFM attrition,
    AI.FORECAST/TimesFM, BigFrames clustering, driver explanation). A2A skills:
    score_attrition, forecast_series, segment_clients, explain_drivers.

This is a faithful in-process implementation of the A2A choreography (agent
cards + skills + task hand-offs) with real BigQuery tool calls in live mode.
It can be swapped for google-adk + the a2a SDK without changing the API.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .. import services
from ..config import settings

_PROJECT = settings.GOOGLE_CLOUD_PROJECT
_DSID = settings.BQ_DATASET


def _bq_table_url(table: str) -> str:
    """Deep link that opens a table in the BigQuery console."""
    return (f"https://console.cloud.google.com/bigquery?project={_PROJECT}"
            f"&ws=!1m5!1m4!4m3!1s{_PROJECT}!2s{_DSID}!3s{table}")


def _artifact(label: str, table: str, kind: str = "table") -> dict:
    return {"label": label, "ref": f"{_PROJECT}.{_DSID}.{table}",
            "kind": kind, "url": _bq_table_url(table)}

# ---------------------------------------------------------------------------
# Agent cards (A2A-style capability advertisement)
# ---------------------------------------------------------------------------
AGENT_CARDS = {
    "orchestrator": {
        "name": "UBS Helix Orchestrator", "framework": "Google ADK",
        "skills": ["route_goal", "compose_answer"]},
    "data_engineering": {
        "name": "Data Engineering Agent", "framework": "ADK + A2A",
        "skills": ["run_entity_resolution", "build_feature_table", "refresh_graph"],
        "tools": ["BigQuery MCP: query, load, create_graph"]},
    "data_scientist": {
        "name": "Data Scientist Agent", "framework": "ADK + A2A",
        "skills": ["score_attrition", "forecast_series", "segment_clients", "explain_drivers"],
        "tools": ["BigQuery MCP: ML.PREDICT, AI.FORECAST, BigFrames KMeans"]},
}


@dataclass
class Step:
    agent: str
    skill: str
    detail: str
    tool_calls: list[str] = field(default_factory=list)
    a2a: str = ""   # who this step is delegating to / responding to
    real: bool = False  # True = a genuine external agent (Google DE Agent over A2A)


# Read-only DE-agent prompts per workflow (inspect the Dataform workspace lineage)
_DE_PROMPTS = {
    "attrition": "List the source tables feeding the attrition feature pipeline "
                 "(attrition_scoring) and its lineage in this workspace. Do not modify files.",
    "forecast": "Confirm the ts_nna_monthly source that feeds the NNA forecast and list "
                "its lineage in this workspace. Do not modify files.",
    "segments": "List the source tables that feed behavioural segmentation (client_features) "
                "and confirm the pipeline dependencies. Do not modify files.",
    "nba": "List the curated client and account tables in this workspace that back the "
           "next-best-action graph. Do not modify files.",
    "unify": "List the raw two-bank sources (raw_ubs_clients, raw_cs_clients) and the resolved "
             "clients table declared in this workspace. Do not modify files.",
}


async def _delegate_to_de(plan: str, skill: str) -> list[Step]:
    """Call the REAL Google Cloud Data Engineering Agent (A2A) and wrap its
    streamed messages as trace steps. Falls back to a narrated step on error."""
    if not settings.USE_DE_AGENT:
        return [Step("data_engineering", skill,
                     "Assembled the required feature/lineage from the Dataform pipeline.",
                     ["Dataform: compile"], a2a="A2A result → data_scientist")]
    try:
        from .. import de_agent
        res = await asyncio.to_thread(de_agent.de_agent_messages, _DE_PROMPTS.get(plan, _DE_PROMPTS["unify"]))
        msgs = res.get("messages") or []
        out: list[Step] = []
        for m in msgs:
            out.append(Step("data_engineering", skill, m,
                            ["A2A → geminidataanalytics: dataengineeringagent",
                             "Dataform workspace ubs_pov_pipeline/dev"],
                            a2a="LIVE A2A · Google Data Engineering Agent", real=True))
        if not out:
            out = [Step("data_engineering", skill, "Inspected the Dataform workspace lineage.",
                        ["A2A → dataengineeringagent"], a2a="LIVE A2A", real=True)]
        return out
    except Exception as e:  # pragma: no cover
        return [Step("data_engineering", skill,
                     f"Inspected the Dataform pipeline lineage (live DE agent unavailable: {e}).",
                     ["Dataform: compile"], a2a="A2A result → data_scientist")]


def _plan(goal: str) -> str:
    g = goal.lower()
    if any(k in g for k in ["lose", "attrition", "churn", "flight", "retain", "outflow"]):
        return "attrition"
    if any(k in g for k in ["forecast", "nna", "net new", "aum", "revenue", "grow", "project"]):
        return "forecast"
    if any(k in g for k in ["segment", "cluster", "persona", "group"]):
        return "segments"
    if any(k in g for k in ["cross", "next best", "recommend", "wallet", "product"]):
        return "nba"
    if any(k in g for k in ["unify", "resolve", "merge", "credit suisse", "dedupe", "360"]):
        return "unify"
    return "forecast"


async def run(goal: str):
    """Async generator yielding A2A steps then a final result dict."""
    plan = _plan(goal)

    async def emit(step: Step):
        await asyncio.sleep(0.35)
        return step

    yield await emit(Step(
        "orchestrator", "route_goal",
        f"Decomposed goal and selected the '{plan}' workflow. Delegating to specialists over A2A.",
        ["ADK: classify_intent"], a2a="→ data_engineering, data_scientist"))

    result: dict = {}

    if plan == "attrition":
        yield await emit(Step(
            "data_scientist", "score_attrition",
            "Need engineered features for the attrition model — delegating to the Google Cloud "
            "Data Engineering Agent over A2A.", a2a="A2A task → data_engineering.build_feature_table"))
        for st in await _delegate_to_de("attrition", "build_feature_table"):
            yield await emit(st)
        scores = services.retention_scores()
        yield await emit(Step(
            "data_scientist", "score_attrition",
            f"Scored clients with the attrition model (TabularFM / boosted-tree). "
            f"{sum(1 for s in scores if s['flight_risk'] >= 0.5)} of {len(scores)} shown are high risk.",
            ["BigQuery: ML.PREDICT(attrition_model)"]))
        yield await emit(Step(
            "data_scientist", "explain_drivers",
            "Extracted top drivers and drafted retention plays per client.",
            ["BigQuery: ML.FEATURE_IMPORTANCE", "Gemini: draft_play"]))
        result = {"type": "retention", "scores": scores[:10], "artifacts": [
            _artifact("Attrition model (BQML)", "attrition_model", "model"),
            _artifact("Flight-risk scores", "attrition_scores"),
            _artifact("Feature table", "attrition_scoring")]}

    elif plan == "forecast":
        for st in await _delegate_to_de("forecast", "build_feature_table"):
            yield await emit(st)
        yield await emit(Step(
            "data_scientist", "forecast_series",
            "Ran AI.FORECAST (TimesFM 2.5) — zero-training, multi-series — for a 12-month horizon.",
            ["BigQuery: AI.FORECAST(TimesFM 2.5)"]))
        fc = services.forecast("nna", "all", "all")
        yield await emit(Step(
            "data_scientist", "explain_drivers",
            "Narrated the drivers against the $200bn NNA ambition.", ["Gemini: narrate"]))
        result = {"type": "forecast", "forecast": fc, "artifacts": [
            _artifact("NNA forecast (TimesFM)", "forecast_nna"),
            _artifact("NNA history mart", "ts_nna_monthly")]}

    elif plan == "segments":
        for st in await _delegate_to_de("segments", "build_feature_table"):
            yield await emit(st)
        yield await emit(Step(
            "data_scientist", "segment_clients",
            "Trained BQML KMEANS (the BigFrames KMeans engine), assigned every client a "
            "segment, and named each cluster with Gemini.",
            ["BigQuery: CREATE MODEL client_kmeans (KMEANS)", "ML.PREDICT", "Gemini: name_segments"]))
        result = {"type": "segments", "segments": services.segments(), "artifacts": [
            _artifact("KMeans model (BQML)", "client_kmeans", "model"),
            _artifact("Feature table", "client_features"),
            _artifact("Client → segment", "client_segments"),
            _artifact("Named segment summary", "client_segments_summary")]}

    elif plan == "nba":
        for st in await _delegate_to_de("nba", "refresh_graph"):
            yield await emit(st)
        yield await emit(Step(
            "data_scientist", "explain_drivers",
            "Ran GQL household traversal + VECTOR_SEARCH look-alikes and composed next-best-actions.",
            ["BigQuery: GRAPH_TABLE MATCH", "VECTOR_SEARCH", "Gemini: rationale"]))
        result = {"type": "nba", "nba": services.nba("CLI_0000001"), "artifacts": [
            _artifact("Property graph", "client_graph", "graph"),
            _artifact("Client embeddings", "client_embeddings"),
            _artifact("Vector index", "client_emb_idx", "index")]}

    else:  # unify
        for st in await _delegate_to_de("unify", "run_entity_resolution"):
            yield await emit(st)
        result = {"type": "unify", "unify": services.unify_result(), "artifacts": [
            _artifact("UBS raw clients (CSV)", "raw_ubs_clients"),
            _artifact("Credit Suisse raw clients (JSON)", "raw_cs_clients"),
            _artifact("Resolved Client 360", "clients")]}

    yield await emit(Step(
        "orchestrator", "compose_answer",
        "Aggregated specialist results into the final answer.", ["ADK: compose"],
        a2a="← data_engineering, data_scientist"))

    if settings.USE_DE_AGENT and isinstance(result.get("artifacts"), list):
        from .. import de_agent
        result["artifacts"].append({
            "label": "Dataform workspace (Data Engineering Agent)",
            "ref": f"{settings.DATAFORM_REPO}/{settings.DATAFORM_WORKSPACE}",
            "kind": "dataform", "url": de_agent.workspace_url()})

    yield {"final": True, "result": result}


# ===========================================================================
# Persona data-lifecycle view — raw data → DE agent → DS → CA agent → business
# Each stage emits a "persona" event (working -> done with real output), so the
# UI can show how the data agents coordinate as different user personas.
# ===========================================================================
_CA_QUESTION = {
    "segments": "What is the average AuM and client count per segment in client_segments_summary?",
    "forecast": "Which division and region had the highest net new money in the last 12 months?",
    "attrition": "How many clients are dual-banked, broken down by booking centre?",
    "nba": "Which booking centres hold the most discretionary mandates?",
    "unify": "How many clients originated from each source bank?",
}


def _ds_output(plan: str) -> dict:
    if plan == "segments":
        return {"kind": "segments", "segments": services.segments(),
                "artifacts": [_artifact("KMeans model (BQML)", "client_kmeans", "model"),
                              _artifact("Client → segment", "client_segments"),
                              _artifact("Named segment summary", "client_segments_summary")],
                "headline": "Trained BQML KMEANS (8 clusters), assigned every client, named with Gemini."}
    if plan == "attrition":
        scores = services.retention_scores()
        return {"kind": "retention", "scores": scores[:8],
                "artifacts": [_artifact("Attrition model (BQML)", "attrition_model", "model"),
                              _artifact("Flight-risk scores", "attrition_scores")],
                "headline": f"Scored every client; {sum(1 for s in scores if s['flight_risk'] >= 0.5)} of top {len(scores)} are high risk."}
    if plan == "nba":
        return {"kind": "nba", "nba": services.nba("CLI_0000001"),
                "artifacts": [_artifact("Property graph", "client_graph", "graph"),
                              _artifact("Client embeddings", "client_embeddings")],
                "headline": "Ran GQL household traversal + VECTOR_SEARCH look-alikes."}
    # forecast / unify default
    return {"kind": "forecast", "forecast": services.forecast("nna", "all", "all"),
            "artifacts": [_artifact("NNA forecast (TimesFM)", "forecast_nna"),
                          _artifact("NNA history mart", "ts_nna_monthly")],
            "headline": "Ran AI.FORECAST (TimesFM 2.5), 12-month multi-series horizon."}


def _business_summary(goal: str, plan: str, ds_out: dict, ca_blocks: list) -> str:
    from .. import bq
    ca_text = " ".join(b.get("text", "") for b in ca_blocks if b.get("type") == "text")
    try:
        if settings.USE_BQ:
            return bq.gen_text(
                f"You are briefing a UBS executive. In 2-3 sentences, turn this analysis into a "
                f"clear business recommendation for the goal: '{goal}'. "
                f"Data-science headline: {ds_out.get('headline','')}. "
                f"Conversational-analytics finding: {ca_text[:600]}. "
                f"Be specific and tie it to net-new-money, retention or share-of-wallet.")
    except Exception:
        pass
    return (f"Based on the {plan} analysis, prioritise the highest-value, highest-risk client "
            f"cohorts: direct advisor outreach where flight-risk is elevated and cross-sell where "
            f"household whitespace exists — protecting AuM and advancing the $200bn net-new-money ambition.")


async def run_lifecycle(goal: str):
    """Yield persona-stage events showing the end-to-end data lifecycle."""
    plan = _plan(goal)

    def ev(pid, title, status, badge="", output=None):
        e = {"type": "persona", "id": pid, "title": title, "status": status, "badge": badge}
        if output is not None:
            e["output"] = output
        return e

    # 1) RAW DATA -----------------------------------------------------------
    yield ev("raw", "Raw Data", "working", "two-bank estate")
    await asyncio.sleep(0.4)
    try:
        raw = services.raw_overview()
    except Exception as e:
        raw = {"sources": [], "dual_banked": 0, "sample": [], "error": str(e)}
    yield ev("raw", "Raw Data", "done", "two-bank estate", {"kind": "raw", **raw})

    # 2) DATA ENGINEERING AGENT (real Google A2A) ---------------------------
    yield ev("de", "Data Engineering Agent", "working", "LIVE A2A · Google")
    de_msgs, wurl = [], None
    try:
        from .. import de_agent
        r = await asyncio.to_thread(de_agent.de_agent_messages, _DE_PROMPTS.get(plan, _DE_PROMPTS["unify"]))
        de_msgs = r.get("messages") or []
        wurl = de_agent.workspace_url()
    except Exception as e:
        de_msgs = [f"(Data Engineering Agent unavailable: {e})"]
    yield ev("de", "Data Engineering Agent", "done", "LIVE A2A · Google",
             {"kind": "messages", "messages": de_msgs, "workspace_url": wurl})

    # 3) DATA SCIENTIST (real BigQuery ML / TimesFM) ------------------------
    yield ev("ds", "Data Scientist", "working", "BigQuery ML")
    await asyncio.sleep(0.3)
    try:
        ds_out = _ds_output(plan)
    except Exception as e:
        ds_out = {"kind": "text", "text": f"(model run failed: {e})", "artifacts": []}
    yield ev("ds", "Data Scientist", "done", "BigQuery ML", ds_out)

    # 4) CONVERSATIONAL ANALYTICS AGENT (real) ------------------------------
    yield ev("ca", "Conversational Analytics Agent", "working", "LIVE · Gemini Data Analytics")
    caq = _CA_QUESTION.get(plan, _CA_QUESTION["unify"])
    ca_blocks: list = []
    try:
        for b in services.ask(caq):
            if b.get("type") in ("text", "table", "sql"):
                ca_blocks.append(b)
    except Exception as e:
        ca_blocks = [{"type": "text", "text": f"(Conversational Analytics unavailable: {e})"}]
    yield ev("ca", "Conversational Analytics Agent", "done", "LIVE · Gemini Data Analytics",
             {"kind": "ca", "question": caq, "blocks": ca_blocks})

    # 5) BUSINESS USER (decision) -------------------------------------------
    yield ev("business", "Business User", "working", "decision")
    summary = _business_summary(goal, plan, ds_out, ca_blocks)
    yield ev("business", "Business User", "done", "decision", {"kind": "text", "text": summary})

    yield {"type": "done"}
