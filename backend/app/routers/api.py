"""All UBS Helix API routes. SSE for /ask and /agents/goal."""
from __future__ import annotations

import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from .. import services
from ..agents import orchestrator

router = APIRouter(prefix="/api")


@router.get("/kpis")
def kpis():
    return services.kpis()


@router.get("/sources")
def sources():
    return services.sources()


@router.post("/unify/run")
def unify_run():
    return services.unify_result()


@router.get("/clients/search")
def clients_search(q: str = Query("")):
    return services.client_search(q)


@router.get("/nba/{client_id}")
def nba(client_id: str):
    return services.nba(client_id)


@router.post("/nba/{client_id}/draft")
def nba_draft(client_id: str, body: dict):
    return services.nba_draft(client_id, body.get("product", ""))


@router.get("/retention/pipeline")
def retention_pipeline():
    return services.retention_pipeline()


@router.get("/retention/scores")
def retention_scores():
    return services.retention_scores()


@router.get("/retention/campaign/{client_id}")
def retention_campaign(client_id: str):
    return services.retention_campaign(client_id)


@router.get("/forecast")
def forecast(metric: str = "nna", division: str = "all", region: str = "all"):
    return services.forecast(metric, division, region)


@router.get("/research/search")
def research_search(q: str = Query("")):
    return services.research_search(q)


@router.post("/research/answer")
def research_answer(body: dict):
    return services.research_answer(body.get("q", ""))


@router.get("/segments")
def segments():
    return services.segments()


@router.get("/network/patterns")
def network_patterns():
    return services.network_patterns()


@router.get("/agents/cards")
def agent_cards():
    return orchestrator.AGENT_CARDS


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/ask")
def ask(body: dict):
    q = body.get("q", "")

    def gen():
        for block in services.ask(q):
            yield _sse(block)
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/agents/goal")
async def agents_goal(body: dict):
    goal = body.get("goal", "")

    async def gen():
        async for item in orchestrator.run_lifecycle(goal):
            yield _sse(item)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
