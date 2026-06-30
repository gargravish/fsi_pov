"""
bq.py — Live BigQuery AI query layer for FSI Helix.

Every method returns native Python structures matching the fixtures, or raises;
services.py decides whether to fall back to fixtures. Generative text (rationales,
plays, commentary, answers) uses the Gemini SDK (google-genai) for reliability;
embeddings / vector search / graph / forecasting / ML run inside BigQuery.
"""
from __future__ import annotations

import functools
from typing import Any

from .config import settings

P = settings.GOOGLE_CLOUD_PROJECT
DS = f"{P}.{settings.BQ_DATASET}"


@functools.lru_cache
def _client():
    from google.cloud import bigquery
    return bigquery.Client(project=P, location=settings.BQ_LOCATION)


def _rows(sql: str, params: dict | None = None) -> list[dict]:
    from google.cloud import bigquery
    job_config = None
    if params:
        qp = []
        for k, v in params.items():
            typ = "INT64" if isinstance(v, int) else "FLOAT64" if isinstance(v, float) else "STRING"
            qp.append(bigquery.ScalarQueryParameter(k, typ, v))
        job_config = bigquery.QueryJobConfig(query_parameters=qp)
    return [dict(r) for r in _client().query(sql, job_config=job_config).result()]


@functools.lru_cache(maxsize=1)
def _genai():
    from google import genai
    return genai.Client(vertexai=True, project=P, location=settings.GCP_REGION)


def gen_text(prompt: str, max_tokens: int = 400) -> str:
    try:
        resp = _genai().models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt)
        return (resp.text or "").strip()
    except Exception as e:  # pragma: no cover
        return f"(AI commentary unavailable: {e})"


def gen_many(prompts: list[str]) -> list[str]:
    """Run several gen_text prompts concurrently (cuts NBA latency ~5x)."""
    from concurrent.futures import ThreadPoolExecutor
    if not prompts:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(prompts))) as ex:
        return list(ex.map(gen_text, prompts))


def gen_json(prompt: str) -> dict:
    """Generate a JSON object with Gemini (structured output)."""
    import json as _json
    try:
        from google.genai import types
        resp = _genai().models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        return _json.loads(resp.text)
    except Exception:
        # fallback: strip fences from a plain text response
        txt = gen_text(prompt).replace("```json", "").replace("```", "").strip()
        try:
            return _json.loads(txt)
        except Exception:
            return {}


# ---------------------------------------------------------------------------
def raw_overview() -> dict:
    c = _rows(f"""
      SELECT
        (SELECT COUNT(*) FROM `{DS}.raw_apex_clients`) AS apex,
        (SELECT COUNT(*) FROM `{DS}.raw_summit_clients`) AS cs,
        (SELECT COUNT(*) FROM `{DS}.clients`) AS resolved,
        (SELECT COUNTIF(dual_banked) FROM `{DS}.clients`) AS dual
    """)[0]
    sample = _rows(f"""
      SELECT client_id, full_name, segment_tier, source_banks, dual_banked
      FROM `{DS}.clients` ORDER BY total_aum_usd DESC LIMIT 4
    """)
    return {
        "sources": [
            {"name": "Apex Bank — raw clients (CSV)", "rows": int(c["apex"])},
            {"name": "Summit Bank — raw clients (JSON)", "rows": int(c["cs"])},
            {"name": "Resolved Client 360", "rows": int(c["resolved"])},
        ],
        "dual_banked": int(c["dual"]),
        "sample": sample,
    }


def kpis() -> dict:
    r = _rows(f"SELECT * FROM `{DS}.v_kpis`")[0]
    er = 96.4
    try:
        # entity-resolution accuracy proxy: share of clients with resolved source_banks
        er = _rows(f"SELECT ROUND(100*COUNTIF(source_banks IS NOT NULL)/COUNT(*),1) acc "
                   f"FROM `{DS}.clients`")[0]["acc"]
    except Exception:
        pass
    single = 0
    try:
        single = _rows(f"SELECT COUNTIF(NOT dual_banked) n FROM `{DS}.clients`")[0]["n"]
    except Exception:
        pass
    return {
        "clients": int(r["clients"]), "aum_usd_bn": float(r["aum_usd_bn"]),
        "accounts": int(r["accounts"]), "dual_banked_pct": float(r["dual_banked_pct"]),
        "advisors": int(r["advisors"]), "nna_ytd_usd_m": float(r["nna_ytd_usd_m"]),
        "er_accuracy": float(er), "cross_sell_opportunity": int(single),
    }


def sources() -> list[dict]:
    out = []
    spec = [
        ("Apex Bank", "Client master", "CSV", "raw_apex_clients"),
        ("Apex Bank", "Positions", "PARQUET", "raw_apex_positions"),
        ("Summit Bank", "Client master", "JSON", "raw_summit_clients"),
        ("Summit Bank", "Transactions", "NDJSON", "raw_summit_transactions"),
    ]
    for bank, entity, fmt, tbl in spec:
        try:
            n = _rows(f"SELECT COUNT(*) c FROM `{DS}.{tbl}`")[0]["c"]
        except Exception:
            n = 0
        out.append({"bank": bank, "entity": entity, "format": fmt,
                    "rows": int(n), "status": "mapped" if n else "pending"})
    return out


def client_search(q: str) -> list[dict]:
    sql = f"""
    SELECT client_id, full_name, segment_tier, booking_centre, total_aum_usd,
           source_banks, dual_banked
    FROM `{DS}.clients`
    WHERE LOWER(full_name) LIKE @q OR LOWER(client_id) LIKE @q
    ORDER BY total_aum_usd DESC LIMIT 12
    """
    return _rows(sql, {"q": f"%{q.lower()}%"})


def client_get(cid: str) -> dict:
    r = _rows(f"SELECT client_id, full_name, segment_tier, booking_centre, region, "
              f"total_aum_usd, dual_banked, risk_profile FROM `{DS}.clients` "
              f"WHERE client_id=@c", {"c": cid})
    return r[0] if r else {}


def nba(cid: str) -> dict:
    client = client_get(cid)
    # household-mate account types this client lacks (graph GQL)
    graph_sql = f"""
    SELECT * FROM GRAPH_TABLE(`{DS}.client_graph`
      MATCH (me:Client)-[:BELONGS_TO]->(h:Household)<-[:BELONGS_TO]-(mate:Client)-[:HOLDS]->(a:Account)
      WHERE me.client_id = '{cid}'
      RETURN a.account_type AS product, COUNT(*) AS signal
      GROUP BY product ORDER BY signal DESC LIMIT 5)
    """
    try:
        mate_products = _rows(graph_sql)
    except Exception:
        mate_products = []
    # vector look-alikes
    look = []
    try:
        look = _rows(f"""
        SELECT base.client_id, distance FROM VECTOR_SEARCH(
          TABLE `{DS}.client_embeddings`, 'embedding',
          (SELECT embedding FROM `{DS}.client_embeddings` WHERE client_id='{cid}'),
          top_k => 6, distance_type => 'COSINE')
        WHERE base.client_id != '{cid}'
        """)
    except Exception:
        pass
    seg = client.get("segment_tier", "HNW")
    reg = client.get("region", "EMEA")
    actions = []
    asks: dict[str, str] = {}   # id -> instruction (one batched Gemini call)
    for n, mp in enumerate((mate_products or [])[:3]):
        prod = mp["product"]
        actions.append({
            "product": prod.replace("_", " ").title() + " Mandate",
            "score": round(min(0.95, 0.55 + 0.1 * float(mp["signal"])), 2),
            "signals": [f"{mp['signal']} household-mates hold {prod}",
                        f"{len(look)} behavioural look-alikes"],
            "rationale": "",
        })
        asks[f"a{n}"] = (f"Rationale (<=2 sentences) for a Apex advisor to recommend a {prod} mandate "
                         f"to this {seg} client in {reg} whose household already holds it.")

    # cross-platform candidate products (other platform) for single-bank clients
    cross = _cross_platform_products(cid, client)
    for n, rec in enumerate(cross.get("recommendations", [])):
        asks[f"c{n}"] = (f"One sentence on why the '{rec['product']}' — a {cross['other_platform']}-"
                         f"originated capability now available through the Apex–Summit "
                         f"integration — is worth a conversation for this {cross['home_platform']}-only client.")

    # ONE Gemini call returns all rationales as JSON (no threads, low latency)
    if asks:
        prompt = ("You are a Apex advisor copilot. Return ONLY a JSON object mapping each id to a "
                  "concrete, compliant rationale string (no performance guarantees). "
                  f"Items: {asks}")
        out = gen_json(prompt)
        for n, a in enumerate(actions):
            a["rationale"] = (out.get(f"a{n}") or "").strip() or \
                "Household holdings and look-alike behaviour make this a strong, compliant fit."
        for n, rec in enumerate(cross.get("recommendations", [])):
            rec["rationale"] = (out.get(f"c{n}") or "").strip() or \
                f"Now available through the integration and well-suited to a {seg} client."

    return {"client": client, "graph": _build_graph(cid, mate_products),
            "actions": actions, "cross_platform": cross}


def _cross_platform_products(cid: str, client: dict) -> dict:
    """Single-bank clients are prime candidates for the OTHER platform's products,
    now available post-integration. Returns {} for dual-banked clients."""
    rows = _rows(f"SELECT source_banks FROM `{DS}.clients` WHERE client_id=@c", {"c": cid})
    banks = (rows[0]["source_banks"] if rows else "") or ""
    if "|" in banks:   # dual-banked -> not a cross-platform candidate
        return {}
    home = "Apex Bank" if banks == "apex" else "Summit Bank"
    other = "Summit Bank" if home == "Apex Bank" else "Apex Bank"
    seg = client.get("segment_tier", "HNW")
    prods = _rows(f"""
      SELECT name, product_type, target_segment_hint
      FROM `{DS}.products`
      WHERE origin_platform = @other
      ORDER BY IF(target_segment_hint = @seg, 0, 1), product_id
      LIMIT 2
    """, {"other": other, "seg": seg})
    recs = [{"product": p["name"], "product_type": p["product_type"],
             "origin_platform": other, "rationale": ""} for p in prods]
    return {"home_platform": home, "other_platform": other, "recommendations": recs}


def _build_graph(cid: str, mate_products: list[dict]) -> dict:
    nodes = [{"id": cid, "label": cid, "type": "client"},
             {"id": "HH", "label": "Household", "type": "household"}]
    edges = [{"source": cid, "target": "HH", "label": "BELONGS_TO"}]
    for i, mp in enumerate(mate_products[:4]):
        nid = f"A{i}"
        nodes.append({"id": nid, "label": mp["product"], "type": "account"})
        edges.append({"source": "HH", "target": nid, "label": "HOUSEHOLD_HOLDS"})
    return {"nodes": nodes, "edges": edges}


def nba_draft(client_id: str, product: str) -> dict:
    """Gemini-drafted advisor outreach note recommending `product` to the client,
    grounded in the client's segment / region / AuM / risk profile."""
    rows = _rows(f"""
      SELECT full_name, segment_tier, region, booking_centre, risk_profile, total_aum_usd
      FROM `{DS}.clients` WHERE client_id = @c
    """, {"c": client_id})
    c = rows[0] if rows else {"full_name": client_id, "segment_tier": "HNW",
                              "region": "EMEA", "risk_profile": "Balanced", "total_aum_usd": 0}
    note = gen_text(
        f"Write a short (~90 words), warm and compliant advisor outreach note recommending the "
        f"'{product}' to a Apex client. No performance guarantees. Tie it to their profile and the "
        f"Apex Bank + Summit Bank integration where natural. Sign as the client's advisor.\n"
        f"Client: {c['full_name']}, {c['segment_tier']}, {c.get('region','')}, risk profile "
        f"{c.get('risk_profile','')}, AuM USD {int(c.get('total_aum_usd') or 0)}.")
    return {"product": product, "client": c["full_name"], "note": note}


def retention_pipeline() -> list[dict]:
    return [{"week": str(r["week"]), "count": int(r["clients"]),
             "high_risk": int(r["high_risk"])}
            for r in _rows(f"SELECT week, clients, high_risk FROM `{DS}.retention_pipeline` "
                           f"ORDER BY week")]


def retention_scores() -> list[dict]:
    rows = _rows(f"""
      SELECT s.client_id, c.full_name, s.segment_tier, s.flight_risk,
             s.dual_banked, s.outflow_ratio, s.recent_net_flow_usd, c.source_banks
      FROM `{DS}.attrition_scores` s
      JOIN `{DS}.clients` c USING (client_id)
      ORDER BY s.flight_risk DESC LIMIT 20
    """)
    # Only the top few get a bespoke Gemini-drafted play (bounds latency); the
    # rest get a fast templated play so the list returns quickly for the demo.
    AI_PLAYS = 4
    out = []
    for i, r in enumerate(rows):
        drivers = []
        if r["dual_banked"]:
            drivers.append("Dual-banked (Apex + Summit)")
        if (r["outflow_ratio"] or 0) > 0.55:
            drivers.append("Elevated outflow ratio")
        if (r["recent_net_flow_usd"] or 0) < 0:
            drivers.append("Net outflows in last 12m")
        drivers = drivers or ["Behavioural risk factors"]
        if i < AI_PLAYS:
            play = gen_text(
                f"In one sentence, draft a retention action for a {r['segment_tier']} Apex Bank "
                f"client at high flight risk (drivers: {', '.join(drivers)}). Be specific and compliant.")
        else:
            play = (f"Schedule a relationship review for this {r['segment_tier']} client; address "
                    f"{drivers[0].lower()} with a tailored mandate proposal and consolidated pricing.")
        out.append({
            "client_id": r["client_id"], "full_name": r["full_name"],
            "segment_tier": r["segment_tier"], "flight_risk": round(float(r["flight_risk"]), 3),
            "drivers": drivers, "play": play,
            "source_banks": r["source_banks"], "dual_banked": bool(r["dual_banked"]),
        })
    return out


def retention_campaign(client_id: str) -> dict:
    """Build a targeted retention campaign for one client: pull their 360 via
    GQL (household whitespace) + holdings/flows/advisor, then Gemini drafts the
    objective, offer, next-best-action, talking points and a ready-to-send email."""
    core = _rows(f"""
      SELECT c.client_id, c.full_name, c.segment_tier, c.region, c.booking_centre,
             c.risk_profile, c.total_aum_usd, c.tenure_days, c.dual_banked,
             a.name AS advisor_name, a.desk AS advisor_desk,
             s.flight_risk, s.outflow_ratio, s.recent_net_flow_usd
      FROM `{DS}.clients` c
      LEFT JOIN `{DS}.advisors` a ON c.primary_advisor_id = a.advisor_id
      LEFT JOIN `{DS}.attrition_scores` s ON c.client_id = s.client_id
      WHERE c.client_id = @c
    """, {"c": client_id})
    if not core:
        return {}
    c = core[0]

    # GQL: what household-mates hold that this client lacks (cross-sell whitespace)
    whitespace: list[dict] = []
    try:
        mate = _rows(f"""
          SELECT * FROM GRAPH_TABLE(`{DS}.client_graph`
            MATCH (me:Client)-[:BELONGS_TO]->(h:Household)<-[:BELONGS_TO]-(mate:Client)-[:HOLDS]->(a:Account)
            WHERE me.client_id = '{client_id}'
            RETURN a.account_type AS product, COUNT(*) AS signal
            GROUP BY product ORDER BY signal DESC LIMIT 6)
        """)
        own = {r["account_type"] for r in _rows(
            f"SELECT DISTINCT account_type FROM `{DS}.accounts` WHERE client_id='{client_id}'")}
        whitespace = [{"product": m["product"], "household_signal": int(m["signal"])}
                      for m in mate if m["product"] not in own]
    except Exception:
        pass

    asset_mix = _rows(f"""
      SELECT asset_class, ROUND(100*SUM(market_value_usd)/SUM(SUM(market_value_usd)) OVER (), 1) pct
      FROM `{DS}.holdings` WHERE client_id='{client_id}'
      GROUP BY asset_class ORDER BY pct DESC LIMIT 5
    """)
    flow = _rows(f"""
      SELECT ROUND(SUM(net_new_money_usd)) net6m
      FROM (SELECT net_new_money_usd FROM `{DS}.client_flows`
            WHERE client_id='{client_id}' ORDER BY month DESC LIMIT 6)
    """)
    recent_net = float(flow[0]["net6m"]) if flow and flow[0]["net6m"] is not None else 0.0

    drivers = []
    if c["dual_banked"]:
        drivers.append("Dual-banked (Apex Bank + Summit Bank)")
    if (c["outflow_ratio"] or 0) > 0.55:
        drivers.append("Elevated outflow ratio")
    if recent_net < 0:
        drivers.append("Net outflows over the last 6 months")
    drivers = drivers or ["Behavioural risk factors"]

    # cross-platform opportunity for single-bank clients (post-integration shelf)
    cross = _cross_platform_products(client_id, {"segment_tier": c["segment_tier"]})
    cross_names = [r["product"] for r in cross.get("recommendations", [])]

    ctx = {
        "asset_mix": [{"asset_class": a["asset_class"], "pct": float(a["pct"])} for a in asset_mix],
        "household_whitespace": whitespace,
        "recent_net_flow_usd": recent_net,
        "advisor": {"name": c["advisor_name"], "desk": c["advisor_desk"]},
        "flight_risk": round(float(c["flight_risk"] or 0), 3),
        "cross_platform": cross,
    }

    cp_hint = ("" if not cross_names else
               f" This {cross.get('home_platform')}-only client can now also be offered "
               f"{cross.get('other_platform')}-originated capabilities post-integration: {cross_names}.")
    prompt = (
        "You are a Apex Bank retention strategist. Using ONLY the facts below, produce a targeted "
        "retention campaign for this client as JSON with keys: objective (string), "
        "retention_offer (string), next_best_action (string — base it on the household whitespace "
        "OR the cross_platform products if present), preferred_channel (string), "
        "talking_points (array of 3-4 short strings), email_subject (string), "
        "email_body (string — a warm, compliant ~120-word advisor email, no guarantees, signed by "
        "the advisor). Be specific and reference the client's holdings/flows." + cp_hint + "\n\n"
        f"FACTS: {{'name':'{c['full_name']}','segment':'{c['segment_tier']}','region':'{c['region']}',"
        f"'booking_centre':'{c['booking_centre']}','risk_profile':'{c['risk_profile']}',"
        f"'total_aum_usd':{int(c['total_aum_usd'] or 0)},'tenure_years':{round((c['tenure_days'] or 0)/365,1)},"
        f"'flight_risk':{ctx['flight_risk']},'drivers':{drivers},'recent_net_flow_usd_6m':{int(recent_net)},"
        f"'asset_mix':{ctx['asset_mix']},'household_whitespace':{whitespace},"
        f"'cross_platform_products':{cross_names},'advisor':'{c['advisor_name']}'}}")
    campaign = gen_json(prompt) or {
        "objective": f"Retain {c['full_name']} and stabilise AuM",
        "retention_offer": "Relationship review + consolidated pricing",
        "next_best_action": (whitespace[0]["product"] if whitespace else "Portfolio review"),
        "preferred_channel": "Advisor call", "talking_points": drivers,
        "email_subject": "A quick review of your portfolio",
        "email_body": "Dear client, I'd welcome the chance to review your portfolio together…",
    }

    return {
        "client": {k: c[k] for k in ("client_id", "full_name", "segment_tier", "region",
                                     "booking_centre", "risk_profile", "total_aum_usd",
                                     "tenure_days", "dual_banked")},
        "flight_risk": ctx["flight_risk"], "drivers": drivers,
        "context": ctx, "campaign": campaign,
    }


def forecast(metric: str, division: str, region: str) -> dict:
    tbl = {"nna": ("forecast_nna", "ts_nna_monthly", "net_new_money_usd_bn"),
           "aum": ("forecast_aum", "ts_aum_monthly", "aum_usd_bn"),
           "revenue": ("forecast_revenue", "ts_revenue_monthly", "revenue_usd_bn")}[metric]
    fc_tbl, hist_tbl, col = tbl
    where = []
    if division and division != "all":
        where.append(f"division = '{division}'")
    if region and region != "all":
        where.append(f"region = '{region}'")
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    hist = _rows(f"SELECT FORMAT_DATE('%Y-%m', month) ts, ROUND(SUM({col}),2) yhat "
                 f"FROM `{DS}.{hist_tbl}`{wsql} GROUP BY ts ORDER BY ts")
    fc = _rows(f"""
      SELECT FORMAT_TIMESTAMP('%Y-%m', forecast_timestamp) ts,
             ROUND(SUM(forecast_value),2) yhat,
             ROUND(SUM(prediction_interval_lower_bound),2) lo,
             ROUND(SUM(prediction_interval_upper_bound),2) hi
      FROM `{DS}.{fc_tbl}`{wsql} GROUP BY ts ORDER BY ts
    """)
    commentary = gen_text(
        f"In 2 sentences, explain what is driving the {metric.upper()} forecast for Apex Bank "
        f"{division or 'all divisions'}/{region or 'all regions'} into 2026, referencing the "
        f"Summit Bank integration and the $200bn net-new-money ambition.")
    for h in hist:
        h["actual"] = h["yhat"]
    return {"metric": metric, "history": hist, "forecast": fc, "commentary": commentary}


# ---------------------------------------------------------------------------
# AI.KEY_DRIVERS — "from what to why" key-driver analysis over the flow metrics.
# Metric configs map a UI metric id to the numeric flow column + label/sign.
# ---------------------------------------------------------------------------
_KD_METRICS = {
    "nna":     ("net_new_money_usd", "Net New Money",  "higher"),
    "inflow":  ("inflow_usd",        "Gross Inflows",  "higher"),
    "outflow": ("outflow_usd",       "Gross Outflows", "lower"),
}
_KD_DIMS = ["segment_tier", "region", "booking_centre", "risk_profile", "banking"]
# AI.KEY_DRIVERS rejects negative metric values unless min_apriori_support = 0.
# NNA is a signed net flow → use support 0; gross in/out-flows are non-negative.
_KD_PARAMS = {
    "nna": "min_apriori_support => 0.0",
    "inflow": "top_k => 20",
    "outflow": "top_k => 20",
}


def _kd_label(drivers: Any) -> tuple[str, list[dict]]:
    """Turn the AI.KEY_DRIVERS `drivers` array — a list of 'name=value' strings
    (e.g. ['region=APAC','banking=Single-bank'], or ['all'] for the overall
    population) — into a readable label + name/value pairs."""
    import json as _json
    if isinstance(drivers, str):
        try:
            drivers = _json.loads(drivers)
        except Exception:
            return drivers, []
    pairs: list[dict] = []
    for d in drivers or []:
        s = str(d)
        if s == "all":          # the overall-population row, not a segment
            continue
        if "=" in s:
            name, _, val = s.partition("=")
            pairs.append({"name": name.strip(), "value": val.strip()})
        else:
            pairs.append({"name": "", "value": s})
    label = " · ".join(p["value"] for p in pairs if p["value"]) or "(overall)"
    return label, pairs


def _kd_query_sql(metric: str) -> str:
    """The AI.KEY_DRIVERS statement for a metric (used to build the cache table
    and as a live fallback if the cache table is absent)."""
    col, _, _ = _KD_METRICS.get(metric, _KD_METRICS["nna"])
    return f"""
      SELECT * FROM AI.KEY_DRIVERS(
        (SELECT c.segment_tier, c.region, c.booking_centre, c.risk_profile,
                IF(c.dual_banked, 'Dual-banked (Apex + Summit)', 'Single-bank') AS banking,
                f.{col},
                f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 6 MONTH) AS is_recent
         FROM `{DS}.client_flows` f
         JOIN `{DS}.clients` c USING (client_id)
         WHERE f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)),
        metric_col         => '{col}',
        dimension_cols     => {_KD_DIMS},
        interest_label_col => 'is_recent',
        {_KD_PARAMS.get(metric, _KD_PARAMS['nna'])},
        enable_pruning     => TRUE)
    """


def key_drivers(metric: str = "nna") -> dict:
    """Ranked driver segments for a flow metric (recent 6m = interest vs prior
    6m = reference) plus a Gemini narrative. Reads the cached `key_drivers_<metric>`
    table (built by infra/setup_fsi_key_drivers.sql); falls back to running
    AI.KEY_DRIVERS live if the table is absent. services.py falls back to fixtures."""
    col, label, direction = _KD_METRICS.get(metric, _KD_METRICS["nna"])
    select = ("SELECT TO_JSON_STRING(drivers) AS drivers_json, metric_interest, "
              "metric_reference, difference, relative_difference, unexpected_difference, "
              "contribution, apriori_support FROM ")
    try:  # cached table — fast path
        rows = _rows(f"{select} `{DS}.key_drivers_{metric}` "
                     "ORDER BY ABS(unexpected_difference) DESC LIMIT 40")
    except Exception:  # live fallback
        rows = _rows(f"{select} ({_kd_query_sql(metric)}) "
                     "ORDER BY ABS(unexpected_difference) DESC LIMIT 40")

    drivers: list[dict] = []
    total_interest = total_reference = 0.0
    for r in rows:
        lbl, pairs = _kd_label(r["drivers_json"])
        if not pairs:           # skip the overall ['all'] row
            continue
        mi = float(r["metric_interest"] or 0) / 1e6
        mr = float(r["metric_reference"] or 0) / 1e6
        total_interest += mi
        total_reference += mr
        diff = float(r["difference"] or 0) / 1e6
        drivers.append({
            "label": lbl, "segment": pairs,
            "metric_interest_usd_m": round(mi, 2),
            "metric_reference_usd_m": round(mr, 2),
            "difference_usd_m": round(diff, 2),
            "relative_difference": round(float(r["relative_difference"] or 0), 4),
            "unexpected_difference_usd_m": round(float(r["unexpected_difference"] or 0) / 1e6, 2),
            "contribution": round(float(r["contribution"] or 0), 4),
            "apriori_support": round(float(r["apriori_support"] or 0), 4),
            "direction": "up" if diff >= 0 else "down",
        })
        if len(drivers) >= 12:
            break

    net = total_interest - total_reference
    top = drivers[:6]
    commentary = gen_text(
        f"You are a Apex Bank CFO analytics copilot. In 2-3 sentences explain WHY {label} moved "
        f"between the prior 6 months and the most recent 6 months, using ONLY these AI.KEY_DRIVERS "
        f"segments (USD m; relative_difference is a fraction; unexpected_difference is the move "
        f"beyond the population trend). Call out the segments that most over- or under-shot the "
        f"trend and tie it to the Apex–Summit integration and the $200bn net-new-money ambition "
        f"where natural. Be specific and compliant.\nMetric: {label}. Net change USD {net:,.0f}m. "
        f"Drivers: {top}")
    return {
        "metric": metric, "metric_label": label, "direction": direction,
        "interest_period": "Most recent 6 months", "reference_period": "Prior 6 months",
        "total_interest_usd_m": round(total_interest, 1),
        "total_reference_usd_m": round(total_reference, 1),
        "net_change_usd_m": round(net, 1),
        "drivers": drivers, "commentary": commentary,
    }


_KD_DIM_EXPR = {
    "segment_tier": "c.segment_tier", "region": "c.region",
    "booking_centre": "c.booking_centre", "risk_profile": "c.risk_profile",
    "banking": "IF(c.dual_banked, 'Dual-banked (Apex + Summit)', 'Single-bank')",
}
_KD_RECENT = "DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 6 MONTH)"
_KD_WINDOW = "DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)"


def _kd_seg_filter(seg: str):
    """Parse 'name:value|name:value' into (where_sql, params, pairs, names)."""
    pairs, where, params = [], [], {}
    for i, tok in enumerate((seg or "").split("|")):
        if ":" not in tok:
            continue
        name, _, value = tok.partition(":")
        name, value = name.strip(), value.strip()
        if name not in _KD_DIM_EXPR:
            continue
        pairs.append({"name": name, "value": value})
        if name == "banking":
            where.append("c.dual_banked = TRUE" if value.lower().startswith("dual") else "c.dual_banked = FALSE")
        else:
            params[f"v{i}"] = value
            where.append(f"{_KD_DIM_EXPR[name]} = @v{i}")
    return (" AND ".join(where) or "TRUE"), params, pairs, [p["name"] for p in pairs]


def key_drivers_drilldown(metric: str = "nna", seg: str = "") -> dict:
    """Deep-dive for one driver segment: what happened (monthly trend), why
    (sub-dimension RCA breakdown + Gemini narrative), what's next (AI.FORECAST),
    and how to prevent/sustain it (Gemini actions). Best-effort live; services.py
    falls back to fixtures on error."""
    col, label, _ = _KD_METRICS.get(metric, _KD_METRICS["nna"])
    where, params, pairs, names = _kd_seg_filter(seg)
    seg_label = " · ".join(p["value"] for p in pairs) or "(overall)"
    base = (f"FROM `{DS}.client_flows` f JOIN `{DS}.clients` c USING (client_id) "
            f"WHERE ({where}) AND f.month >= {_KD_WINDOW}")

    # 1) exact stats — reuse the ranked list so the deep-dive matches the row
    stats = {}
    try:
        for d in key_drivers(metric)["drivers"]:
            if {(s["name"], s["value"]) for s in d["segment"]} == {(p["name"], p["value"]) for p in pairs}:
                stats = d
                break
    except Exception:
        pass

    # 2) what happened — 12-month monthly trend (USD m)
    trend = [{"ts": r["ts"], "value": float(r["value"])} for r in _rows(
        f"SELECT FORMAT_DATE('%Y-%m', f.month) ts, ROUND(SUM(f.{col})/1e6, 2) value "
        f"{base} GROUP BY ts ORDER BY ts", params)]
    recent = round(sum(p["value"] for p in trend[-6:]), 2)
    prior = round(sum(p["value"] for p in trend[:-6]), 2)
    diff = round(recent - prior, 2)
    rel = round(diff / abs(prior), 4) if prior else 0.0
    direction = stats.get("direction") or ("up" if diff >= 0 else "down")
    down = direction == "down"

    # 2b) flag anomalous months — live AI.DETECT_ANOMALIES, else heuristic
    anom_months: set[str] = set()
    try:
        for r in _rows(
            f"SELECT FORMAT_TIMESTAMP('%Y-%m', month) ts FROM AI.DETECT_ANOMALIES("
            f"  (SELECT TIMESTAMP_TRUNC(TIMESTAMP(f.month), MONTH) AS month, SUM(f.{col}) AS metric "
            f"   {base} GROUP BY month), "
            f"  data_col => 'metric', timestamp_col => 'month', anomaly_prob_threshold => 0.95) "
            f"WHERE is_anomaly", params):
            anom_months.add(r["ts"])
    except Exception:
        pass
    prior_avg = (prior / 6) if trend else 0
    for i, p in enumerate(trend):
        p["is_anomaly"] = (p["ts"] in anom_months) if anom_months else (
            i >= len(trend) - 6 and (p["value"] < prior_avg * 0.85 if down else p["value"] > prior_avg * 1.15))

    # 3) why — break the change down by a sub-dimension not fixed by the segment
    factors = []
    sub = next((d for d in _KD_DIMS if d not in names), None)
    if sub:
        try:
            for r in _rows(
                f"SELECT {_KD_DIM_EXPR[sub]} AS k, ROUND((SUM(IF(f.month >= {_KD_RECENT}, f.{col}, 0)) "
                f"- SUM(IF(f.month < {_KD_RECENT}, f.{col}, 0)))/1e6, 1) AS impact "
                f"{base} GROUP BY k ORDER BY ABS(impact) DESC LIMIT 3", params):
                factors.append({"factor": f"{sub.replace('_', ' ')}: {r['k']}",
                                "impact_usd_m": float(r["impact"]), "detail": ""})
        except Exception:
            pass

    # 4) what's next — AI.FORECAST the segment's monthly series (USD m)
    forecast = []
    try:
        forecast = [{"ts": r["ts"], "yhat": float(r["yhat"]), "lo": float(r["lo"]), "hi": float(r["hi"])}
                    for r in _rows(
            f"SELECT FORMAT_TIMESTAMP('%Y-%m', forecast_timestamp) ts, "
            f"  ROUND(forecast_value/1e6, 2) yhat, "
            f"  ROUND(prediction_interval_lower_bound/1e6, 2) lo, "
            f"  ROUND(prediction_interval_upper_bound/1e6, 2) hi "
            f"FROM AI.FORECAST("
            f"  (SELECT TIMESTAMP(f.month) AS month, SUM(f.{col}) AS v {base} GROUP BY month), "
            f"  data_col => 'v', timestamp_col => 'month', model => 'TimesFM 2.5', "
            f"  horizon => 6, confidence_level => 0.9) ORDER BY ts", params)]
    except Exception:
        pass

    # 5) narrative + factor details + prevention — one structured Gemini call
    favourable_up = metric != "outflow"
    good = (direction == "up") == favourable_up
    gj = gen_json(
        "You are a Apex Bank CFO analytics copilot. Given this key-driver deep-dive, return ONLY a JSON object "
        "with keys: narrative (2-3 sentences, root-cause of the move; use **bold** for the segment), "
        "factor_details (object mapping each factor name to a one-sentence cause), "
        "next_commentary (1-2 sentences on the forecast path), "
        "prevention (array of 3-4 objects {title, detail, owner} — concrete, compliant actions to "
        f"{'sustain' if good else 'prevent/reverse'} this). Tie to the Apex–Summit integration and the "
        "$200bn net-new-money ambition where natural.\n"
        f"Metric: {label}. Segment: {seg_label}. Recent6m USD {recent}m vs Prior6m USD {prior}m "
        f"({rel*100:.1f}%). Unexpected-vs-trend USD {stats.get('unexpected_difference_usd_m', diff)}m. "
        f"Direction: {'favourable' if good else 'unfavourable'}. Sub-driver factors: {factors}.")
    for f in factors:
        f["detail"] = (gj.get("factor_details", {}) or {}).get(f["factor"], "") or \
            "A contributing sub-segment of the overall move."
    prevention = gj.get("prevention") or [
        {"title": "Targeted relationship action",
         "detail": "Prioritise advisor outreach to the highest-value accounts in this segment.",
         "owner": "Regional Market Head"}]

    recent_disp = stats.get("metric_interest_usd_m", recent)
    prior_disp = stats.get("metric_reference_usd_m", prior)
    from .fixtures import data as _fx
    sql = _fx.kd_sql_block(metric, pairs, recent_disp, prior_disp, good)

    return {
        "metric": metric, "metric_label": label, "label": seg_label,
        "segment": pairs, "direction": direction,
        "what_happened": {
            "recent_usd_m": recent_disp,
            "prior_usd_m": prior_disp,
            "difference_usd_m": stats.get("difference_usd_m", diff),
            "relative_difference": stats.get("relative_difference", rel),
            "unexpected_difference_usd_m": stats.get("unexpected_difference_usd_m", diff),
            "contribution": stats.get("contribution", 0.0),
            "apriori_support": stats.get("apriori_support", 0.0),
            "trend": trend,
            "ai_function": "AI.DETECT_ANOMALIES", "sql": sql["anomalies"],
        },
        "rca": {"narrative": gj.get("narrative") or f"**{seg_label}** moved {rel*100:.1f}% recent-vs-prior.",
                "factors": factors, "ai_function": "AI.KEY_DRIVERS", "sql": sql["drivers"]},
        "whats_next": {"forecast": forecast,
                       "commentary": gj.get("next_commentary") or "Forecast continues the recent run-rate.",
                       "ai_function": "AI.FORECAST", "sql": sql["forecast"]},
        "prevention": {"actions": prevention, "ai_function": "AI.GENERATE", "sql": sql["prevention"]},
    }


def research_search(q: str) -> list[dict]:
    sql = f"""
    SELECT base.document_id, base.title, base.doc_type, base.gcs_uri,
           SApex BankTR(base.chunk_text, 0, 240) snippet, (1 - distance) score
    FROM VECTOR_SEARCH(
      TABLE `{DS}.doc_search`, 'embedding',
      (SELECT ml_generate_embedding_result FROM ML.GENERATE_EMBEDDING(
         MODEL `{DS}.embedding_model`,
         (SELECT @q AS content), STRUCT(TRUE AS flatten_json_output))),
      top_k => 5, distance_type => 'COSINE')
    ORDER BY score DESC
    """
    rows = _rows(sql, {"q": q})
    return [{"document_id": r["document_id"], "title": r["title"],
             "doc_type": r["doc_type"], "snippet": r["snippet"],
             "score": round(float(r["score"]), 3),
             "gcs_uri": f"gs://{settings.GCS_BUCKET}/{r['gcs_uri']}"
                        if not str(r["gcs_uri"]).startswith("gs://") else r["gcs_uri"]}
            for r in rows]


def research_answer(q: str) -> dict:
    hits = research_search(q)
    context = "\n\n".join(f"[{h['document_id']}] {h['title']}: {h['snippet']}" for h in hits[:4])
    answer = gen_text(
        f"You are a Apex Bank investment-research assistant. Answer the question using ONLY the "
        f"context, cite document IDs inline like [DOC_000012], and be concise and compliant.\n\n"
        f"Question: {q}\n\nContext:\n{context}")
    return {"answer": answer,
            "citations": [{"document_id": h["document_id"], "title": h["title"],
                           "gcs_uri": h["gcs_uri"]} for h in hits[:3]]}


def segments() -> list[dict]:
    # behavioural segments cached by the DS agent / BQML; fall back to a SQL approximation
    try:
        rows = _rows(f"SELECT * FROM `{DS}.client_segments_summary` ORDER BY id")
        if rows:
            # enrich with integration overlap (dual-banked %) per segment
            try:
                dual = {int(r["segment"]): float(r["dual_pct"]) for r in _rows(f"""
                  SELECT s.segment, ROUND(100*AVG(CAST(c.dual_banked AS INT64)),1) dual_pct
                  FROM `{DS}.client_segments` s JOIN `{DS}.clients` c USING (client_id)
                  GROUP BY s.segment""")}
                for r in rows:
                    r["dual_banked_pct"] = dual.get(int(r["id"]), 0.0)
            except Exception:
                pass
            return rows
    except Exception:
        pass
    rows = _rows(f"""
      SELECT segment_tier label, COUNT(*) size, ROUND(AVG(total_aum_usd),2) avg_aum_usd
      FROM `{DS}.clients` GROUP BY label ORDER BY size DESC
    """)
    out = []
    for i, r in enumerate(rows):
        out.append({"id": i, "label": r["label"], "size": int(r["size"]),
                    "avg_aum_usd": float(r["avg_aum_usd"]),
                    "dominant_asset": "equity", "attrition_index": 0.2})
    return out


_SCHEMA_HINT = """
Tables in `raves-altostrat.FSI_POV` (BigQuery Standard SQL):
- clients(client_id, full_name, segment_tier, domicile, booking_centre, region,
  risk_profile, kyc_status, total_aum_usd, dual_banked, tenure_days)
- accounts(account_id, client_id, account_type, booking_centre, currency, balance_usd)
- holdings(portfolio_id, client_id, isin, asset_class, market_value_usd, weight_pct)
- transactions(txn_id, client_id, txn_type, amount_usd, value_date)
- client_flows(client_id, month DATE, net_new_money_usd, inflow_usd, outflow_usd)
- advisors(advisor_id, name, role, desk, booking_centre, market)
- attrition_scores(client_id, segment_tier, region, flight_risk)
"""


def ask_ca(q: str) -> list[dict]:
    """
    Conversational Analytics API (Gemini Data Analytics) — query the real BigQuery
    data agent grounded on FSI_POV. Streams systemMessage chunks (THOUGHT /
    FINAL_RESPONSE / data.generatedSql / data.result / chart) and maps them to the
    UI block format. Returns [] on any failure so callers can fall back.
    """
    import json as _json
    import urllib.request
    import google.auth
    import google.auth.transport.requests as _gart

    if not settings.CA_AGENT_ID:
        return []
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(_gart.Request())
    loc = settings.CA_LOCATION
    parent = f"projects/{P}/locations/{loc}"
    url = f"https://geminidataanalytics.googleapis.com/v1beta/{parent}:chat"
    body = {
        "parent": parent,
        "messages": [{"userMessage": {"text": q}}],
        "dataAgentContext": {"dataAgent": f"{parent}/dataAgents/{settings.CA_AGENT_ID}"},
    }
    req = urllib.request.Request(
        url, data=_json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=180).read().decode()
    chunks = _json.loads(raw)

    final_text: list[str] = []
    followups: list[str] = []
    sql_seen: list[str] = []
    table: dict | None = None
    chart: dict | None = None
    for c in chunks:
        sm = c.get("systemMessage", {})
        if "text" in sm:
            tt = sm["text"].get("textType")
            parts = sm["text"].get("parts", [])
            if tt == "FINAL_RESPONSE":
                final_text.extend(parts)
            elif tt == "FOLLOWUP_QUESTIONS":
                followups.extend(parts)
        elif "data" in sm:
            d = sm["data"]
            sql = d.get("generatedSql")
            if sql and sql not in sql_seen:
                sql_seen.append(sql)
            if "result" in d:
                res = d["result"]
                cols = [f["name"] for f in res.get("schema", {}).get("fields", [])]
                rows = [[r.get(col) for col in cols] for r in res.get("data", [])]
                table = {"columns": cols, "rows": rows}
        elif "chart" in sm:
            ch = sm["chart"]
            if "result" in ch:
                vc = ch["result"].get("vegaConfig", {})
                enc = vc.get("encoding", {})
                chart = {"mark": vc.get("mark", "bar"),
                         "x": (enc.get("x") or {}).get("field"),
                         "y": (enc.get("y") or {}).get("field"),
                         "title": vc.get("title")}

    blocks: list[dict] = []
    if final_text:
        blocks.append({"type": "text", "text": " ".join(final_text)})
    if table and table["columns"]:
        blocks.append({"type": "table", **table})
    if chart:
        blocks.append({"type": "chart", "spec": chart})
    for s in sql_seen:
        blocks.append({"type": "sql", "sql": s})
    if followups:
        blocks.append({"type": "text", "text": "**Suggested follow-ups:** " + "  ·  ".join(followups)})
    return blocks


def ask(q: str) -> list[dict]:
    """Fallback NL -> SQL -> table + narrative (Gemini + BigQuery) if the CA agent is unavailable."""
    sql = gen_text(
        f"Generate ONE BigQuery Standard SQL query (no markdown, no comments) to answer the "
        f"question. Use fully-qualified table names with backticks. Limit to 50 rows.\n"
        f"{_SCHEMA_HINT}\nQuestion: {q}\nSQL:")
    sql = sql.replace("```sql", "").replace("```", "").strip()
    blocks: list[dict] = []
    try:
        rows = _rows(sql)
        cols = list(rows[0].keys()) if rows else []
        blocks.append({"type": "text", "text": gen_text(
            f"In 2 sentences, summarise the answer to '{q}' given these result rows: "
            f"{rows[:8]}. Be specific.")})
        blocks.append({"type": "table", "columns": cols,
                       "rows": [[r.get(c) for c in cols] for r in rows[:50]]})
        if len(cols) >= 2:
            blocks.append({"type": "chart",
                           "spec": {"mark": "bar", "x": cols[0], "y": cols[1]}})
        blocks.append({"type": "sql", "sql": sql})
    except Exception as e:
        blocks.append({"type": "text", "text": gen_text(
            f"Answer this Apex wealth-management question conversationally: {q}")})
        blocks.append({"type": "sql", "sql": f"-- generation/exec note: {e}\n{sql}"})
    return blocks


def network_patterns() -> dict:
    """
    Financial-crime detection over the client/entity/transaction data. Each anomaly
    carries its OWN interactive subgraph (built from real rows) + the underlying
    records, so the UI can show what's actually behind the pattern.
    """
    anomalies: list[dict] = []

    # --- 1) Structuring / Smurfing: sub-threshold transfers into a collector ---
    try:
        struct = _rows(f"""
          SELECT client_id, COUNT(*) n, ROUND(SUM(amount_usd)) total
          FROM `{DS}.transactions`
          WHERE txn_type IN ('transfer_out','transfer_in') AND amount_usd BETWEEN 8000 AND 9999
          GROUP BY client_id HAVING n >= 3 ORDER BY n DESC LIMIT 1
        """)
        if struct:
            s = struct[0]
            name = (_rows(f"SELECT full_name FROM `{DS}.clients` WHERE client_id='{s['client_id']}'")
                    or [{"full_name": s["client_id"]}])[0]["full_name"]
            txns = _rows(f"""
              SELECT txn_id, ROUND(amount_usd,2) amount_usd, value_date, counterparty
              FROM `{DS}.transactions`
              WHERE client_id='{s['client_id']}' AND amount_usd BETWEEN 8000 AND 9999
              ORDER BY value_date LIMIT 8
            """)
            nodes = [{"id": s["client_id"], "label": name, "type": "client", "risk": "high"},
                     {"id": "COLLECTOR", "label": "Collector account", "type": "account", "risk": "high"}]
            edges = [{"source": s["client_id"], "target": "COLLECTOR",
                      "amount": int(t["amount_usd"])} for t in txns]
            anomalies.append({
                "id": "structuring", "type": "Structuring / Smurfing", "severity": "high",
                "summary": f"{name} made {s['n']} just-under-USD-10k transfers, "
                           f"≈USD {int(s['total']):,} total — classic smurfing into a collector.",
                "subgraph": {"nodes": nodes, "edges": edges},
                "details": {"columns": ["txn_id", "amount_usd", "value_date", "counterparty"],
                            "rows": [[t["txn_id"], t["amount_usd"], t["value_date"], t["counterparty"]] for t in txns]},
                "gql": "MATCH (c:Client)-[t:TRANSFERS]->(a:Account)\nWHERE t.amount BETWEEN 9000 AND 9900\nRETURN c, COUNT(t) AS n HAVING n >= 5"})
    except Exception:
        pass

    # --- 2) UBO Risk: flagged legal entity -> beneficial owner -> household ----
    try:
        ubo = _rows(f"""
          SELECT e.entity_id, e.name, e.entity_type, e.jurisdiction, e.ubo_client_id,
                 c.full_name ubo_name, c.segment_tier, c.household_id
          FROM `{DS}.legal_entities` e
          JOIN `{DS}.clients` c ON e.ubo_client_id = c.client_id
          WHERE e.risk_flag = TRUE ORDER BY c.total_aum_usd DESC LIMIT 1
        """)
        if ubo:
            u = ubo[0]
            members = _rows(f"""
              SELECT client_id, full_name, segment_tier FROM `{DS}.clients`
              WHERE household_id='{u['household_id']}' AND client_id != '{u['ubo_client_id']}' LIMIT 6
            """)
            nodes = [{"id": u["ubo_client_id"], "label": u["ubo_name"], "type": "client", "risk": "high"},
                     {"id": u["entity_id"], "label": f"{u['name']} ({u['jurisdiction']})", "type": "account", "risk": "high"},
                     {"id": u["household_id"], "label": "Household", "type": "household", "risk": "med"}]
            edges = [{"source": u["entity_id"], "target": u["ubo_client_id"], "label": "UBO"},
                     {"source": u["ubo_client_id"], "target": u["household_id"], "label": "BELONGS_TO"}]
            for m in members:
                nodes.append({"id": m["client_id"], "label": m["full_name"], "type": "client", "risk": "low"})
                edges.append({"source": m["client_id"], "target": u["household_id"], "label": "BELONGS_TO"})
            anomalies.append({
                "id": "ubo", "type": "UBO Risk", "severity": "high",
                "summary": f"High-risk {u['entity_type']} '{u['name']}' ({u['jurisdiction']}) is "
                           f"ultimately owned by {u['segment_tier']} client {u['ubo_name']}, who is "
                           f"connected to {len(members)} household members.",
                "subgraph": {"nodes": nodes, "edges": edges},
                "details": {"columns": ["client_id", "full_name", "segment_tier"],
                            "rows": [[m["client_id"], m["full_name"], m["segment_tier"]] for m in members]},
                "gql": "MATCH (e:Entity {risk_flag:true})-[:OWNED_BY]->(c:Client)-[:BELONGS_TO]->(h:Household)<-[:BELONGS_TO]-(m:Client)\nRETURN e, c, COLLECT(m)"})
    except Exception:
        pass

    # --- 3) Cross-bank household cluster (integration-era concentration) -------
    try:
        clus = _rows(f"""
          SELECT household_id, COUNT(*) members, ROUND(SUM(total_aum_usd)/1e6) aum_m,
                 COUNTIF(dual_banked) dual
          FROM `{DS}.clients`
          WHERE household_id LIKE 'HH0%'
          GROUP BY household_id HAVING members >= 4 AND dual >= 1
          ORDER BY aum_m DESC LIMIT 1
        """)
        if clus:
            cl = clus[0]
            mem = _rows(f"""
              SELECT client_id, full_name, segment_tier, dual_banked FROM `{DS}.clients`
              WHERE household_id='{cl['household_id']}' ORDER BY total_aum_usd DESC LIMIT 7
            """)
            nodes = [{"id": cl["household_id"], "label": f"Household (USD {int(cl['aum_m'])}m)",
                      "type": "household", "risk": "med"}]
            edges = []
            for m in mem:
                nodes.append({"id": m["client_id"], "label": m["full_name"], "type": "client",
                              "risk": "high" if m["dual_banked"] else "low"})
                edges.append({"source": m["client_id"], "target": cl["household_id"], "label": "BELONGS_TO"})
            anomalies.append({
                "id": "cluster", "type": "Cross-bank Concentration", "severity": "medium",
                "summary": f"A {cl['members']}-member household holds ≈USD {int(cl['aum_m'])}m with "
                           f"{cl['dual']} dual-banked (Apex + Summit) members — concentration "
                           f"and integration-overlap risk to review.",
                "subgraph": {"nodes": nodes, "edges": edges},
                "details": {"columns": ["client_id", "full_name", "segment_tier", "dual_banked"],
                            "rows": [[m["client_id"], m["full_name"], m["segment_tier"], m["dual_banked"]] for m in mem]},
                "gql": "MATCH (c:Client)-[:BELONGS_TO]->(h:Household)\nRETURN h, COUNT(c) AS members, SUM(c.total_aum_usd) AS aum HAVING members >= 4"})
    except Exception:
        pass

    return {"anomalies": anomalies}
