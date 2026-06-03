"""
Deterministic demo fixtures — power Demo mode (USE_BQ=false) with zero cloud
calls. Numbers are realistic and stable across runs (fixed seed).
"""
from __future__ import annotations

import random

_R = random.Random(7)

SEGMENTS = ["Affluent", "HNW", "UHNW", "Family Office", "Institutional"]
REGIONS = ["Switzerland", "EMEA", "Americas", "APAC"]
DIVISIONS = ["GWM", "P&C", "Asset Management", "Investment Bank"]
CENTRES = ["Zurich", "Geneva", "Basel", "Lugano", "London", "New York",
           "Hong Kong", "Singapore"]
PRODUCTS = [
    "UBS Manage Advanced Discretionary Mandate",
    "Private Markets Access Programme",
    "Lombard Credit Facility",
    "Sustainable Investing Discretionary Mandate",
    "Wealth Planning & Succession Advisory",
    "Capital Protection Structured Solutions",
    "Family Office Co-Investment Platform",
]

_FIRST = ["Hans", "Marie", "Luca", "Sophie", "Wei", "Anya", "Pierre", "Elena",
          "Maximilian", "Chiara", "Johan", "Priya", "Antoine", "Lena"]
_LAST = ["Müller", "Dubois", "Rossi", "Schmid", "Chen", "Keller", "Moreau",
         "Bernasconi", "Weber", "Tan", "Favre", "Brunner", "Lim", "Roth"]


def _name() -> str:
    return f"{_R.choice(_FIRST)} {_R.choice(_LAST)}"


_CLIENTS = []
for i in range(60):
    seg = _R.choices(SEGMENTS, weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]
    aum = {"Affluent": 1.2e6, "HNW": 1.4e7, "UHNW": 1.2e8,
           "Family Office": 8e8, "Institutional": 1.5e9}[seg] * _R.uniform(0.4, 2.2)
    _CLIENTS.append({
        "client_id": f"CLI_{i:07d}",
        "full_name": _name(),
        "segment_tier": seg,
        "booking_centre": _R.choice(CENTRES),
        "region": _R.choice(REGIONS),
        "total_aum_usd": round(aum, 2),
        "dual_banked": _R.random() < 0.22,
        "risk_profile": _R.choice(["Conservative", "Balanced", "Growth", "Aggressive"]),
    })


def kpis() -> dict:
    return {
        "clients": 40_217, "aum_usd_bn": 6843.2, "accounts": 88_940,
        "dual_banked_pct": 22.1, "advisors": 902, "nna_ytd_usd_m": 18420.0,
        "er_accuracy": 96.4,
    }


def raw_overview() -> dict:
    return {
        "sources": [
            {"name": "UBS — raw clients (CSV)", "rows": 24321},
            {"name": "Credit Suisse — raw clients (JSON)", "rows": 24375},
            {"name": "Resolved Client 360", "rows": 40000},
        ],
        "dual_banked": 8696,
        "sample": [
            {"client_id": "CLI_0001288", "full_name": "Hans Müller", "segment_tier": "UHNW", "source_banks": "credit_suisse|ubs", "dual_banked": True},
            {"client_id": "CLI_0004102", "full_name": "Sophie Favre", "segment_tier": "Family Office", "source_banks": "ubs", "dual_banked": False},
            {"client_id": "CLI_0009934", "full_name": "Wei Chen", "segment_tier": "UHNW", "source_banks": "credit_suisse|ubs", "dual_banked": True},
            {"client_id": "CLI_0002281", "full_name": "Elena Bernasconi", "segment_tier": "HNW", "source_banks": "ubs", "dual_banked": False},
        ],
    }


def sources() -> list[dict]:
    return [
        {"bank": "UBS", "entity": "Client master", "format": "CSV", "rows": 24890, "status": "mapped"},
        {"bank": "UBS", "entity": "Portfolios", "format": "FIXED_WIDTH", "rows": 37120, "status": "mapped"},
        {"bank": "UBS", "entity": "Positions", "format": "PARQUET", "rows": 248300, "status": "mapped"},
        {"bank": "UBS", "entity": "Advisors", "format": "XLSX", "rows": 451, "status": "mapped"},
        {"bank": "Credit Suisse", "entity": "Client master", "format": "JSON", "rows": 24510, "status": "mapped"},
        {"bank": "Credit Suisse", "entity": "Accounts", "format": "XML", "rows": 47900, "status": "mapped"},
        {"bank": "Credit Suisse", "entity": "Transactions", "format": "NDJSON", "rows": 263400, "status": "mapped"},
    ]


def unify_result() -> dict:
    return {
        "mapped_fields": 142,
        "dual_banked_clusters": 8894,
        "accuracy": 96.4,
        "before": {
            "_source": "credit_suisse / cs_clients.json",
            "cifNumber": "CS000128844",
            "client": {"displayName": "MÜLLER, H.", "clientSegment": "UHNW",
                       "dateOfBirth": "1968-04-12"},
            "address": {"country": "CH"}, "booking": {"baseCcy": "CHF"},
        },
        "after": {
            "client_id": "CLI_0001288",
            "full_name": "Hans Müller",
            "segment_tier": "UHNW", "domicile": "Switzerland",
            "source_banks": ["credit_suisse", "ubs"], "dual_banked": True,
            "total_aum_usd": 134_200_000.0,
        },
    }


def client_search(q: str) -> list[dict]:
    q = (q or "").lower()
    hits = [c for c in _CLIENTS if q in c["full_name"].lower() or q in c["client_id"].lower()]
    return (hits or _CLIENTS)[:12]


def client_by_id(cid: str) -> dict:
    for c in _CLIENTS:
        if c["client_id"] == cid:
            return c
    return _CLIENTS[0]


def nba(cid: str) -> dict:
    c = client_by_id(cid)
    mate1, mate2 = _R.sample(_CLIENTS, 2)
    graph = {
        "nodes": [
            {"id": c["client_id"], "label": c["full_name"], "type": "client"},
            {"id": "HH", "label": "Household", "type": "household"},
            {"id": mate1["client_id"], "label": mate1["full_name"], "type": "client"},
            {"id": mate2["client_id"], "label": mate2["full_name"], "type": "client"},
            {"id": "A1", "label": "Discretionary", "type": "account"},
            {"id": "A2", "label": "Lombard", "type": "account"},
            {"id": "ADV", "label": "R. Brunner (CA)", "type": "advisor"},
        ],
        "edges": [
            {"source": c["client_id"], "target": "HH", "label": "BELONGS_TO"},
            {"source": mate1["client_id"], "target": "HH", "label": "BELONGS_TO"},
            {"source": mate2["client_id"], "target": "HH", "label": "BELONGS_TO"},
            {"source": c["client_id"], "target": "A1", "label": "HOLDS"},
            {"source": c["client_id"], "target": "A2", "label": "HOLDS"},
            {"source": c["client_id"], "target": "ADV", "label": "ADVISED_BY"},
        ],
    }
    actions = [
        {"product": "Private Markets Access Programme", "score": 0.91,
         "signals": ["2 household members hold private markets", "UHNW look-alike cohort"],
         "rationale": f"{c['full_name']}'s household holds significant private-markets exposure "
                      "while this client does not — a private-markets sleeve aligns with their "
                      "risk profile and the household's allocation pattern."},
        {"product": "Wealth Planning & Succession Advisory", "score": 0.78,
         "signals": ["Family Office linkage", "Multi-generational household"],
         "rationale": "Household structure suggests succession-planning needs not yet served."},
        {"product": "Sustainable Investing Discretionary Mandate", "score": 0.66,
         "signals": ["Look-alike clients adopting ESG mandates"],
         "rationale": "Behaviourally similar clients increasingly hold sustainable mandates."},
    ]
    return {"client": c, "graph": graph, "actions": actions}


def retention_pipeline() -> list[dict]:
    out = []
    for w in range(12):
        cnt = _R.randint(40, 120)
        out.append({"week": f"2026-W{24+w:02d}", "count": cnt,
                    "high_risk": int(cnt * _R.uniform(0.15, 0.4))})
    return out


def retention_scores() -> list[dict]:
    out = []
    hi = sorted(_CLIENTS, key=lambda c: (not c["dual_banked"], -c["total_aum_usd"]))
    for c in hi[:20]:
        risk = _R.uniform(0.55, 0.93) if c["dual_banked"] else _R.uniform(0.2, 0.6)
        drivers = []
        if c["dual_banked"]:
            drivers.append("Dual-banked (UBS + CS)")
        drivers += _R.sample(["Recent net outflows", "Advisor change", "Fee sensitivity",
                              "KYC review pending", "Reduced txn velocity"], 2)
        out.append({
            "client_id": c["client_id"], "full_name": c["full_name"],
            "segment_tier": c["segment_tier"], "flight_risk": round(risk, 3),
            "drivers": drivers,
            "play": f"Relationship review + tailored mandate proposal for {c['full_name']}; "
                    "offer CIO portfolio health-check and discuss consolidated pricing.",
        })
    return sorted(out, key=lambda x: -x["flight_risk"])


def forecast(metric: str, division: str, region: str) -> dict:
    base = {"nna": 22.0, "aum": 780.0, "revenue": 2.3}.get(metric, 50.0)
    hist, fc = [], []
    val = base
    for t in range(36):
        val *= (1 + _R.uniform(-0.01, 0.025))
        hist.append({"ts": f"2023-{(t % 12)+1:02d}", "yhat": round(val, 2),
                     "actual": round(val, 2)})
    last = val
    for t in range(12):
        last *= (1 + _R.uniform(0.0, 0.03))
        spread = last * 0.06
        fc.append({"ts": f"2026-{(t % 12)+1:02d}", "yhat": round(last, 2),
                   "lo": round(last - spread, 2), "hi": round(last + spread, 2)})
    comm = (f"{metric.upper()} for {division}/{region} is projected to grow steadily over the "
            "next 12 months, with momentum strongest in APAC and GWM — consistent with the "
            "$200bn net-new-money ambition. Confidence bands widen beyond month 6.")
    return {"metric": metric, "history": hist, "forecast": fc, "commentary": comm}


def research_search(q: str) -> list[dict]:
    docs = [
        ("DOC_000012", "UBS CIO Research — Private credit allocation for UHNW portfolios",
         "cio_research", "Our CIO view favours a structural allocation to private credit for "
         "qualified UHNW and family-office clients, citing attractive risk-adjusted yields..."),
        ("DOC_000044", "UBS CIO Research — Global asset allocation: balanced positioning into 2026",
         "cio_research", "Our balanced multi-asset stance holds a modest overweight to global "
         "equities funded from cash, neutral duration in high-grade bonds..."),
        ("DOC_000091", "Suitability Assessment — CLI_0002281",
         "suitability", "Investment objective: balanced growth and income. Structured products "
         "limited to 15% of the portfolio..."),
        ("DOC_000133", "UBS CIO Research — APAC wealth: capturing the next decade of growth",
         "cio_research", "Asia-Pacific remains the fastest-growing wealth pool. We highlight "
         "onshore and offshore booking considerations and currency hedging..."),
    ]
    out = []
    for i, (did, title, dt, txt) in enumerate(docs):
        out.append({"document_id": did, "title": title, "doc_type": dt,
                    "snippet": txt, "score": round(0.92 - i * 0.07, 3),
                    "gcs_uri": f"gs://ubs_pov/raw/documents/{did}.pdf"})
    return out


def research_answer(q: str) -> dict:
    hits = research_search(q)
    return {
        "answer": "Per the latest CIO research, a 5–12% allocation to private credit is "
                  "recommended for qualified UHNW and family-office clients, funded from public "
                  "high yield and phased over 12–18 months via diversified direct-lending and "
                  "secondaries vehicles. Liquidity terms and J-curve management are key.",
        "citations": [{"document_id": h["document_id"], "title": h["title"],
                       "gcs_uri": h["gcs_uri"]} for h in hits[:2]],
    }


def segments() -> list[dict]:
    labels = [
        ("Globally-Mobile UHNW Entrepreneurs", "equity", 0.31),
        ("Conservative Swiss Retirees", "fixed_income", 0.12),
        ("Multi-Generational Family Offices", "alternative", 0.18),
        ("APAC Growth Seekers", "equity", 0.27),
        ("Sustainable-Focused Affluent", "fund", 0.15),
        ("Structured-Yield Income Clients", "structured", 0.22),
        ("Institutional Mandates", "fixed_income", 0.09),
        ("Lombard-Active Liquidity Users", "cash", 0.34),
    ]
    out = []
    for i, (lab, dom, attr) in enumerate(labels):
        out.append({"id": i, "label": lab, "size": _R.randint(1800, 9200),
                    "avg_aum_usd": round(_R.uniform(2e6, 4e8), 2),
                    "dominant_asset": dom, "attrition_index": attr})
    return out


def ask(q: str) -> list[dict]:
    return [
        {"type": "text",
         "text": "Across booking centres, **Hong Kong** and **Singapore** posted the fastest "
                 "net-new-money growth last quarter, with APAC GWM leading the bank. Switzerland "
                 "remains the largest AuM base. Below are the top centres by NNA."},
        {"type": "table",
         "columns": ["booking_centre", "nna_usd_m", "qoq_growth_pct"],
         "rows": [["Hong Kong", 2140.0, 11.4], ["Singapore", 1890.0, 9.8],
                  ["Zurich", 3120.0, 4.1], ["Geneva", 1640.0, 3.7],
                  ["New York", 1430.0, 5.2], ["London", 1210.0, 2.9]]},
        {"type": "chart",
         "spec": {"mark": "bar", "x": "booking_centre", "y": "nna_usd_m"}},
        {"type": "sql",
         "sql": "SELECT booking_centre, ROUND(SUM(net_new_money_usd)/1e6,1) AS nna_usd_m\n"
                "FROM `raves-altostrat.UBS_POV.client_flows` f\n"
                "JOIN `raves-altostrat.UBS_POV.clients` c USING (client_id)\n"
                "WHERE f.month >= '2026-01-01'\nGROUP BY booking_centre\nORDER BY nna_usd_m DESC"},
    ]


def network_patterns() -> dict:
    return {"anomalies": [
        {"id": "structuring", "type": "Structuring / Smurfing", "severity": "high",
         "summary": "Hans Müller made 8 sub-threshold transfers (USD 9.0k–9.9k), ≈USD 74,200 total "
                    "— classic smurfing into a collector account.",
         "subgraph": {
             "nodes": [{"id": "CLI_0001288", "label": "Hans Müller", "type": "client", "risk": "high"},
                       {"id": "COLLECTOR", "label": "Collector account", "type": "account", "risk": "high"}],
             "edges": [{"source": "CLI_0001288", "target": "COLLECTOR", "amount": 9000 + i * 90} for i in range(8)]},
         "details": {"columns": ["txn_id", "amount_usd", "value_date", "counterparty"],
                     "rows": [[f"TXN_{1000+i}", 9000 + i * 90, f"2026-0{1+(i%6)}-1{i%9}", "external_bank"] for i in range(8)]},
         "gql": "MATCH (c:Client)-[t:TRANSFERS]->(a:Account)\nWHERE t.amount BETWEEN 9000 AND 9900\nRETURN c, COUNT(t) AS n HAVING n >= 5"},
        {"id": "ubo", "type": "UBO Risk", "severity": "high",
         "summary": "High-risk SPV 'Favre HOLDCO SA' (KY) is ultimately owned by Family Office client "
                    "Sophie Favre, who is connected to 4 household members.",
         "subgraph": {
             "nodes": [{"id": "CLI_0004102", "label": "Sophie Favre", "type": "client", "risk": "high"},
                       {"id": "LE_1", "label": "Favre HOLDCO SA (KY)", "type": "account", "risk": "high"},
                       {"id": "HH", "label": "Household", "type": "household", "risk": "med"},
                       {"id": "M1", "label": "Pierre Moreau", "type": "client", "risk": "low"},
                       {"id": "M2", "label": "Elena Bernasconi", "type": "client", "risk": "low"},
                       {"id": "M3", "label": "Luca Rossi", "type": "client", "risk": "low"}],
             "edges": [{"source": "LE_1", "target": "CLI_0004102", "label": "UBO"},
                       {"source": "CLI_0004102", "target": "HH", "label": "BELONGS_TO"},
                       {"source": "M1", "target": "HH", "label": "BELONGS_TO"},
                       {"source": "M2", "target": "HH", "label": "BELONGS_TO"},
                       {"source": "M3", "target": "HH", "label": "BELONGS_TO"}]},
         "details": {"columns": ["client_id", "full_name", "segment_tier"],
                     "rows": [["CLI_0007711", "Pierre Moreau", "HNW"], ["CLI_0002281", "Elena Bernasconi", "HNW"],
                              ["CLI_0006654", "Luca Rossi", "UHNW"]]},
         "gql": "MATCH (e:Entity {risk_flag:true})-[:OWNED_BY]->(c:Client)-[:BELONGS_TO]->(h:Household)<-[:BELONGS_TO]-(m:Client)\nRETURN e, c, COLLECT(m)"},
        {"id": "cluster", "type": "Cross-bank Concentration", "severity": "medium",
         "summary": "A 6-member household holds ≈USD 420m with 3 dual-banked (UBS + Credit Suisse) "
                    "members — concentration and integration-overlap risk to review.",
         "subgraph": {
             "nodes": [{"id": "HH", "label": "Household (USD 420m)", "type": "household", "risk": "med"},
                       {"id": "C1", "label": "Wei Chen", "type": "client", "risk": "high"},
                       {"id": "C2", "label": "Chiara Tan", "type": "client", "risk": "high"},
                       {"id": "C3", "label": "Johan Brunner", "type": "client", "risk": "low"},
                       {"id": "C4", "label": "Priya Lim", "type": "client", "risk": "low"}],
             "edges": [{"source": f"C{i}", "target": "HH", "label": "BELONGS_TO"} for i in range(1, 5)]},
         "details": {"columns": ["client_id", "full_name", "segment_tier", "dual_banked"],
                     "rows": [["CLI_0009934", "Wei Chen", "UHNW", True], ["CLI_0003110", "Chiara Tan", "UHNW", True],
                              ["CLI_0005521", "Johan Brunner", "HNW", False]]},
         "gql": "MATCH (c:Client)-[:BELONGS_TO]->(h:Household)\nRETURN h, COUNT(c) AS members HAVING members >= 4"},
    ]}
