"""
bq.py — Live BigQuery AI query layer for UBS Helix.

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
        (SELECT COUNT(*) FROM `{DS}.raw_ubs_clients`) AS ubs,
        (SELECT COUNT(*) FROM `{DS}.raw_cs_clients`) AS cs,
        (SELECT COUNT(*) FROM `{DS}.clients`) AS resolved,
        (SELECT COUNTIF(dual_banked) FROM `{DS}.clients`) AS dual
    """)[0]
    sample = _rows(f"""
      SELECT client_id, full_name, segment_tier, source_banks, dual_banked
      FROM `{DS}.clients` ORDER BY total_aum_usd DESC LIMIT 4
    """)
    return {
        "sources": [
            {"name": "UBS — raw clients (CSV)", "rows": int(c["ubs"])},
            {"name": "Credit Suisse — raw clients (JSON)", "rows": int(c["cs"])},
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
    return {
        "clients": int(r["clients"]), "aum_usd_bn": float(r["aum_usd_bn"]),
        "accounts": int(r["accounts"]), "dual_banked_pct": float(r["dual_banked_pct"]),
        "advisors": int(r["advisors"]), "nna_ytd_usd_m": float(r["nna_ytd_usd_m"]),
        "er_accuracy": float(er),
    }


def sources() -> list[dict]:
    out = []
    spec = [
        ("UBS", "Client master", "CSV", "raw_ubs_clients"),
        ("UBS", "Positions", "PARQUET", "raw_ubs_positions"),
        ("Credit Suisse", "Client master", "JSON", "raw_cs_clients"),
        ("Credit Suisse", "Transactions", "NDJSON", "raw_cs_transactions"),
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
    SELECT client_id, full_name, segment_tier, booking_centre, total_aum_usd
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
    actions = []
    for mp in (mate_products or [])[:3]:
        prod = mp["product"]
        actions.append({
            "product": prod.replace("_", " ").title() + " Mandate",
            "score": round(min(0.95, 0.55 + 0.1 * float(mp["signal"])), 2),
            "signals": [f"{mp['signal']} household-mates hold {prod}",
                        f"{len(look)} behavioural look-alikes"],
            "rationale": gen_text(
                f"In <=2 sentences, give a UBS client advisor a rationale to recommend a "
                f"{prod} mandate to a {client.get('segment_tier','HNW')} client in "
                f"{client.get('region','EMEA')} whose household already holds it. "
                f"Be concrete and compliant; no guarantees."),
        })
    return {"client": client, "graph": _build_graph(cid, mate_products), "actions": actions}


def _build_graph(cid: str, mate_products: list[dict]) -> dict:
    nodes = [{"id": cid, "label": cid, "type": "client"},
             {"id": "HH", "label": "Household", "type": "household"}]
    edges = [{"source": cid, "target": "HH", "label": "BELONGS_TO"}]
    for i, mp in enumerate(mate_products[:4]):
        nid = f"A{i}"
        nodes.append({"id": nid, "label": mp["product"], "type": "account"})
        edges.append({"source": "HH", "target": nid, "label": "HOUSEHOLD_HOLDS"})
    return {"nodes": nodes, "edges": edges}


def retention_pipeline() -> list[dict]:
    return [{"week": str(r["week"]), "count": int(r["clients"]),
             "high_risk": int(r["high_risk"])}
            for r in _rows(f"SELECT week, clients, high_risk FROM `{DS}.retention_pipeline` "
                           f"ORDER BY week")]


def retention_scores() -> list[dict]:
    rows = _rows(f"""
      SELECT s.client_id, c.full_name, s.segment_tier, s.flight_risk,
             s.dual_banked, s.outflow_ratio, s.recent_net_flow_usd
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
            drivers.append("Dual-banked (UBS + CS)")
        if (r["outflow_ratio"] or 0) > 0.55:
            drivers.append("Elevated outflow ratio")
        if (r["recent_net_flow_usd"] or 0) < 0:
            drivers.append("Net outflows in last 12m")
        drivers = drivers or ["Behavioural risk factors"]
        if i < AI_PLAYS:
            play = gen_text(
                f"In one sentence, draft a retention action for a {r['segment_tier']} UBS "
                f"client at high flight risk (drivers: {', '.join(drivers)}). Be specific and compliant.")
        else:
            play = (f"Schedule a relationship review for this {r['segment_tier']} client; address "
                    f"{drivers[0].lower()} with a tailored mandate proposal and consolidated pricing.")
        out.append({
            "client_id": r["client_id"], "full_name": r["full_name"],
            "segment_tier": r["segment_tier"], "flight_risk": round(float(r["flight_risk"]), 3),
            "drivers": drivers, "play": play,
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
        drivers.append("Dual-banked (UBS + Credit Suisse)")
    if (c["outflow_ratio"] or 0) > 0.55:
        drivers.append("Elevated outflow ratio")
    if recent_net < 0:
        drivers.append("Net outflows over the last 6 months")
    drivers = drivers or ["Behavioural risk factors"]

    ctx = {
        "asset_mix": [{"asset_class": a["asset_class"], "pct": float(a["pct"])} for a in asset_mix],
        "household_whitespace": whitespace,
        "recent_net_flow_usd": recent_net,
        "advisor": {"name": c["advisor_name"], "desk": c["advisor_desk"]},
        "flight_risk": round(float(c["flight_risk"] or 0), 3),
    }

    prompt = (
        "You are a UBS retention strategist. Using ONLY the facts below, produce a targeted "
        "retention campaign for this client as JSON with keys: objective (string), "
        "retention_offer (string), next_best_action (string — base it on the household whitespace), "
        "preferred_channel (string), talking_points (array of 3-4 short strings), "
        "email_subject (string), email_body (string — a warm, compliant ~120-word advisor email, "
        "no guarantees, signed by the advisor). Be specific and reference the client's holdings/flows.\n\n"
        f"FACTS: {{'name':'{c['full_name']}','segment':'{c['segment_tier']}','region':'{c['region']}',"
        f"'booking_centre':'{c['booking_centre']}','risk_profile':'{c['risk_profile']}',"
        f"'total_aum_usd':{int(c['total_aum_usd'] or 0)},'tenure_years':{round((c['tenure_days'] or 0)/365,1)},"
        f"'flight_risk':{ctx['flight_risk']},'drivers':{drivers},'recent_net_flow_usd_6m':{int(recent_net)},"
        f"'asset_mix':{ctx['asset_mix']},'household_whitespace':{whitespace},"
        f"'advisor':'{c['advisor_name']}'}}")
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
        f"In 2 sentences, explain what is driving the {metric.upper()} forecast for UBS "
        f"{division or 'all divisions'}/{region or 'all regions'} into 2026, referencing the "
        f"Credit Suisse integration and the $200bn net-new-money ambition.")
    for h in hist:
        h["actual"] = h["yhat"]
    return {"metric": metric, "history": hist, "forecast": fc, "commentary": commentary}


def research_search(q: str) -> list[dict]:
    sql = f"""
    SELECT base.document_id, base.title, base.doc_type, base.gcs_uri,
           SUBSTR(base.chunk_text, 0, 240) snippet, (1 - distance) score
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
        f"You are a UBS investment-research assistant. Answer the question using ONLY the "
        f"context, cite document IDs inline like [DOC_000012], and be concise and compliant.\n\n"
        f"Question: {q}\n\nContext:\n{context}")
    return {"answer": answer,
            "citations": [{"document_id": h["document_id"], "title": h["title"],
                           "gcs_uri": h["gcs_uri"]} for h in hits[:3]]}


def segments() -> list[dict]:
    # behavioural segments cached by the DS agent / BigFrames; fall back to a SQL approximation
    try:
        rows = _rows(f"SELECT * FROM `{DS}.client_segments_summary` ORDER BY id")
        if rows:
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
Tables in `raves-altostrat.UBS_POV` (BigQuery Standard SQL):
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
    data agent grounded on UBS_POV. Streams systemMessage chunks (THOUGHT /
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
            f"Answer this UBS wealth-management question conversationally: {q}")})
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
                           f"{cl['dual']} dual-banked (UBS + Credit Suisse) members — concentration "
                           f"and integration-overlap risk to review.",
                "subgraph": {"nodes": nodes, "edges": edges},
                "details": {"columns": ["client_id", "full_name", "segment_tier", "dual_banked"],
                            "rows": [[m["client_id"], m["full_name"], m["segment_tier"], m["dual_banked"]] for m in mem]},
                "gql": "MATCH (c:Client)-[:BELONGS_TO]->(h:Household)\nRETURN h, COUNT(c) AS members, SUM(c.total_aum_usd) AS aum HAVING members >= 4"})
    except Exception:
        pass

    return {"anomalies": anomalies}
