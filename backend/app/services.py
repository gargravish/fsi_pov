"""
services.py — Facade selecting live BigQuery (USE_BQ=true) or deterministic
fixtures. Live calls fall back to fixtures on any error so the demo never breaks.
"""
from __future__ import annotations

import logging

from .config import settings
from .fixtures import data as fx

log = logging.getLogger("ubs_helix")


def _live(fn_name: str, *args):
    """Call bq.<fn_name>(*args); on any failure return None."""
    if not settings.USE_BQ:
        return None
    try:
        from . import bq
        return getattr(bq, fn_name)(*args)
    except Exception as e:  # pragma: no cover
        log.warning("live %s failed, using fixtures: %s", fn_name, e)
        return None


def kpis():
    return _live("kpis") or fx.kpis()


def raw_overview():
    return _live("raw_overview") or fx.raw_overview()


def sources():
    return _live("sources") or fx.sources()


def unify_result():
    # The before/after + accuracy story; live KPIs reused where available
    return fx.unify_result()


def client_search(q: str):
    return _live("client_search", q) or fx.client_search(q)


def nba(cid: str):
    return _live("nba", cid) or fx.nba(cid)


def nba_draft(cid: str, product: str):
    return _live("nba_draft", cid, product) or fx.nba_draft(cid, product)


def retention_pipeline():
    return _live("retention_pipeline") or fx.retention_pipeline()


def retention_scores():
    return _live("retention_scores") or fx.retention_scores()


def retention_campaign(client_id: str):
    return _live("retention_campaign", client_id) or fx.retention_campaign(client_id)


def forecast(metric: str, division: str, region: str):
    return _live("forecast", metric, division, region) or fx.forecast(metric, division, region)


def research_search(q: str):
    return _live("research_search", q) or fx.research_search(q)


def research_answer(q: str):
    return _live("research_answer", q) or fx.research_answer(q)


def segments():
    return _live("segments") or fx.segments()


def network_patterns():
    return _live("network_patterns") or fx.network_patterns()


def ask(q: str):
    """Stream Ask UBS blocks as they arrive (generator).

    Live: the real Conversational Analytics data agent (true streaming, with
    thinking breadcrumbs). On failure: Gemini NL->SQL, then deterministic fixtures.
    Demo (USE_BQ=false): paced fixtures so the UI still animates.
    """
    if settings.USE_BQ and settings.CA_AGENT_ID:
        yield {"type": "thinking", "text": "Sending your question to the Conversational Analytics data agent…"}
        try:
            from .conversational import ask_conversational
            emitted = False
            for block in ask_conversational(q):
                emitted = True
                yield block
            if emitted:
                return
        except Exception as e:  # pragma: no cover
            log.warning("CA agent failed, falling back: %s", e)
            yield {"type": "thinking", "text": "Conversational Analytics unavailable — using direct query…"}
        # secondary live fallback: Gemini NL->SQL
        nl = _live("ask", q)
        if nl:
            for block in nl:
                yield block
            return
    # demo / final fallback
    for block in fx.ask(q):
        yield block
