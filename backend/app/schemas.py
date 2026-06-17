"""Pydantic response models for the FSI Helix API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Kpis(BaseModel):
    clients: int
    aum_usd_bn: float
    accounts: int
    dual_banked_pct: float
    advisors: int
    nna_ytd_usd_m: float
    er_accuracy: float


class Source(BaseModel):
    bank: str
    entity: str
    format: str
    rows: int
    status: str


class UnifyResult(BaseModel):
    mapped_fields: int
    dual_banked_clusters: int
    accuracy: float
    before: dict[str, Any]
    after: dict[str, Any]


class ClientHit(BaseModel):
    client_id: str
    full_name: str
    segment_tier: str
    booking_centre: str
    total_aum_usd: float


class NbaAction(BaseModel):
    product: str
    score: float
    signals: list[str]
    rationale: str


class NbaResult(BaseModel):
    client: ClientHit
    graph: dict[str, Any]
    actions: list[NbaAction]


class RetentionScore(BaseModel):
    client_id: str
    full_name: str
    segment_tier: str
    flight_risk: float
    drivers: list[str]
    play: str


class ForecastPoint(BaseModel):
    ts: str
    yhat: float
    lo: Optional[float] = None
    hi: Optional[float] = None
    actual: Optional[float] = None


class ForecastResult(BaseModel):
    metric: str
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    commentary: str


class DocHit(BaseModel):
    document_id: str
    title: str
    doc_type: str
    snippet: str
    score: float
    gcs_uri: str


class Segment(BaseModel):
    id: int
    label: str
    size: int
    avg_aum_usd: float
    dominant_asset: str
    attrition_index: float


class AgentStep(BaseModel):
    agent: str
    skill: str
    detail: str
    tool_calls: list[str] = []
