"""All FSI Helix API routes. SSE for /ask and /agents/goal."""
from __future__ import annotations

import datetime
import json
import os

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, StreamingResponse

from .. import services
from ..agents import orchestrator
from ..config import settings

router = APIRouter(prefix="/api")


_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}


def _logo_dir_and_default() -> tuple[str | None, str | None]:
    """Resolve BANK_LOGO_PATH to (directory, configured_file) against several
    bases so a relative path like './Logo/x.png' works regardless of the
    process working directory: as-given (cwd), the backend dir, repo root."""
    path = settings.BANK_LOGO_PATH
    if not path:
        return None, None
    if os.path.isabs(path):
        return os.path.dirname(path), path
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # app/routers -> app -> backend
    repo_root = os.path.dirname(backend_dir)
    for base in (os.getcwd(), backend_dir, repo_root):
        cand = os.path.normpath(os.path.join(base, path))
        if os.path.isfile(cand):
            return os.path.dirname(cand), cand
    # file not found yet — still derive the intended directory (repo-root based)
    cand = os.path.normpath(os.path.join(repo_root, path))
    return os.path.dirname(cand), cand


def _resolve_logo_path() -> str | None:
    """Serve the MOST RECENTLY MODIFIED image in the logo directory, so dropping
    a new file into the Logo folder (any name/extension) is picked up on the next
    request. Falls back to the exact configured file if the dir has no images."""
    logo_dir, default = _logo_dir_and_default()
    if not logo_dir:
        return None
    newest, newest_mtime = None, -1.0
    if os.path.isdir(logo_dir):
        for e in os.scandir(logo_dir):
            if e.is_file() and os.path.splitext(e.name)[1].lower() in _LOGO_EXTS:
                m = e.stat().st_mtime
                if m > newest_mtime:
                    newest, newest_mtime = e.path, m
    if newest:
        return newest
    return default if default and os.path.isfile(default) else None


@router.get("/logo")
def get_logo():
    path = _resolve_logo_path()
    if path:
        # no-cache so a refresh always re-validates and picks up a replaced image
        return FileResponse(path, headers={"Cache-Control": "no-cache, must-revalidate"})
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Logo not configured")


def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=json_serial)}\n\n"


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


@router.get("/key-drivers")
def key_drivers(metric: str = "nna"):
    return services.key_drivers(metric)


@router.get("/key-drivers/drilldown")
def key_drivers_drilldown(metric: str = "nna", seg: str = ""):
    return services.key_drivers_drilldown(metric, seg)


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


@router.post("/agents/ca/reply")
def agents_ca_reply(body: dict):
    """Resume a paused Conversational Analytics conversation with the human's reply."""
    token = body.get("conv_token", "")
    reply = body.get("reply", "")

    def gen():
        for item in orchestrator.continue_ca(token, reply):
            yield _sse(item)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/agents/goal")
async def agents_goal(body: dict):
    goal = body.get("goal", "")

    async def gen():
        async for item in orchestrator.run_lifecycle(goal):
            yield _sse(item)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
