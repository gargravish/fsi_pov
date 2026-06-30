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
    "Apex Manage Advanced Discretionary Mandate",
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
    _dual = _R.random() < 0.22
    _CLIENTS.append({
        "client_id": f"CLI_{i:07d}",
        "full_name": _name(),
        "segment_tier": seg,
        "booking_centre": _R.choice(CENTRES),
        "region": _R.choice(REGIONS),
        "total_aum_usd": round(aum, 2),
        "dual_banked": _dual,
        "source_banks": "summit|apex" if _dual else _R.choice(["apex", "summit"]),
        "risk_profile": _R.choice(["Conservative", "Balanced", "Growth", "Aggressive"]),
    })


def kpis() -> dict:
    return {
        "clients": 40_000, "aum_usd_bn": 2114.5, "accounts": 92_626,
        "dual_banked_pct": 21.7, "advisors": 900, "nna_ytd_usd_m": 18420.0,
        "er_accuracy": 96.4, "cross_sell_opportunity": 31_304,
    }


def raw_overview() -> dict:
    return {
        "sources": [
            {"name": "Apex Bank — raw clients (CSV)", "rows": 24321},
            {"name": "Summit Bank — raw clients (JSON)", "rows": 24375},
            {"name": "Resolved Client 360", "rows": 40000},
        ],
        "dual_banked": 8696,
        "sample": [
            {"client_id": "CLI_0001288", "full_name": "Hans Müller", "segment_tier": "UHNW", "source_banks": "summit|apex", "dual_banked": True},
            {"client_id": "CLI_0004102", "full_name": "Sophie Favre", "segment_tier": "Family Office", "source_banks": "apex", "dual_banked": False},
            {"client_id": "CLI_0009934", "full_name": "Wei Chen", "segment_tier": "UHNW", "source_banks": "summit|apex", "dual_banked": True},
            {"client_id": "CLI_0002281", "full_name": "Elena Bernasconi", "segment_tier": "HNW", "source_banks": "apex", "dual_banked": False},
        ],
    }


def sources() -> list[dict]:
    return [
        {"bank": "Apex Bank", "entity": "Client master", "format": "CSV", "rows": 24890, "status": "mapped"},
        {"bank": "Apex Bank", "entity": "Portfolios", "format": "FIXED_WIDTH", "rows": 37120, "status": "mapped"},
        {"bank": "Apex Bank", "entity": "Positions", "format": "PARQUET", "rows": 248300, "status": "mapped"},
        {"bank": "Apex Bank", "entity": "Advisors", "format": "XLSX", "rows": 451, "status": "mapped"},
        {"bank": "Summit Bank", "entity": "Client master", "format": "JSON", "rows": 24510, "status": "mapped"},
        {"bank": "Summit Bank", "entity": "Accounts", "format": "XML", "rows": 47900, "status": "mapped"},
        {"bank": "Summit Bank", "entity": "Transactions", "format": "NDJSON", "rows": 263400, "status": "mapped"},
    ]


def unify_result() -> dict:
    return {
        "mapped_fields": 142,
        "dual_banked_clusters": 8894,
        "accuracy": 96.4,
        "before": {
            "_source": "summit / summit_clients.json",
            "cifNumber": "Summit000128844",
            "client": {"displayName": "MÜLLER, H.", "clientSegment": "UHNW",
                       "dateOfBirth": "1968-04-12"},
            "address": {"country": "CH"}, "booking": {"baseCcy": "CHF"},
        },
        "after": {
            "client_id": "CLI_0001288",
            "full_name": "Hans Müller",
            "segment_tier": "UHNW", "domicile": "Switzerland",
            "source_banks": ["summit", "apex"], "dual_banked": True,
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
    cross = {} if c["dual_banked"] else {
        "home_platform": "Apex Bank", "other_platform": "Summit Bank",
        "recommendations": [
            {"product": "Capital Protection Structured Solutions", "product_type": "structured", "origin_platform": "Summit Bank",
             "rationale": "A Summit Bank-originated structured solution, now available post-integration, that offers defined downside protection suited to this client's risk profile."},
            {"product": "Lombard Credit Facility", "product_type": "lombard", "origin_platform": "Summit Bank",
             "rationale": "Securities-backed lending — a Summit Bank strength now on the unified shelf — can unlock liquidity without liquidating the portfolio."},
        ]}
    return {"client": c, "graph": graph, "actions": actions, "cross_platform": cross}


def nba_draft(client_id: str, product: str) -> dict:
    c = client_by_id(client_id)
    first = c["full_name"].split()[0]
    note = (f"Dear {first},\n\nAs we bring your Apex Bank and Summit Bank relationships together, I've "
            f"been reviewing your portfolio and believe the {product} could be a strong fit for your "
            f"objectives and {c.get('risk_profile','balanced')} risk profile. Several clients in your "
            f"household already benefit from it. I'd welcome a brief call to walk through how it works "
            f"and our latest CIO views — no obligation. Warm regards,\nYour Apex advisor")
    return {"product": product, "client": c["full_name"], "note": note}


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
            drivers.append("Dual-banked (Apex + Summit)")
        drivers += _R.sample(["Recent net outflows", "Advisor change", "Fee sensitivity",
                              "KYC review pending", "Reduced txn velocity"], 2)
        out.append({
            "client_id": c["client_id"], "full_name": c["full_name"],
            "segment_tier": c["segment_tier"], "flight_risk": round(risk, 3),
            "drivers": drivers,
            "play": f"Relationship review + tailored mandate proposal for {c['full_name']}; "
                    "offer CIO portfolio health-check and discuss consolidated pricing.",
            "source_banks": c.get("source_banks"), "dual_banked": c["dual_banked"],
        })
    return sorted(out, key=lambda x: -x["flight_risk"])


def retention_campaign(client_id: str) -> dict:
    c = client_by_id(client_id)
    drivers = ["Dual-banked (Apex Bank + Summit Bank)", "Net outflows over the last 6 months"] if c["dual_banked"] \
        else ["Fee sensitivity", "Reduced transaction velocity"]
    whitespace = [{"product": "discretionary", "household_signal": 3},
                  {"product": "alternative", "household_signal": 2}]
    return {
        "client": {"client_id": c["client_id"], "full_name": c["full_name"], "segment_tier": c["segment_tier"],
                   "region": c["region"], "booking_centre": c["booking_centre"], "risk_profile": c["risk_profile"],
                   "total_aum_usd": c["total_aum_usd"], "tenure_days": 3650, "dual_banked": c["dual_banked"]},
        "flight_risk": 0.82,
        "drivers": drivers,
        "context": {
            "asset_mix": [{"asset_class": "equity", "pct": 48.0}, {"asset_class": "fixed_income", "pct": 22.0},
                          {"asset_class": "cash", "pct": 18.0}, {"asset_class": "alternative", "pct": 12.0}],
            "household_whitespace": whitespace,
            "recent_net_flow_usd": -2400000,
            "advisor": {"name": "R. Brunner", "desk": "UHNW & Family Office"},
            "flight_risk": 0.82,
        },
        "campaign": {
            "objective": f"Retain {c['full_name']} and reverse recent outflows by deepening the relationship.",
            "retention_offer": "Complimentary CIO portfolio health-check + consolidated cross-bank pricing review.",
            "next_best_action": "Introduce a discretionary mandate (held by household members) to capture idle cash.",
            "preferred_channel": "Senior advisor call, followed by an in-person review",
            "talking_points": [
                "Acknowledge the Summit Bank integration and reassure on continuity of service",
                "18% idle cash could be deployed into a discretionary mandate",
                "Household members already hold discretionary & alternatives — offer parity",
                "Consolidated pricing to address fee sensitivity",
            ],
            "email_subject": "Bringing your Apex Bank & Summit Bank relationships together — a portfolio review",
            "email_body": (f"Dear {c['full_name'].split()[0]},\n\nAs we complete the integration of Apex Bank and "
                           "Summit Bank, I wanted to reach out personally to ensure your portfolio is working "
                           "as hard as it can for you. I've noticed a meaningful cash balance that we could put to "
                           "work, and several solutions your wider household already benefits from that may suit "
                           "your objectives. I'd welcome a short call to share our latest CIO views and a "
                           "consolidated view of your relationships.\n\nWarm regards,\nR. Brunner, Apex Bank"),
        },
    }


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


def _kd_row(seg: list[tuple[str, str]], interest: float, reference: float,
            unexpected: float, contribution: float, support: float) -> dict:
    pairs = [{"name": n, "value": v} for n, v in seg]
    diff = round(interest - reference, 2)
    rel = round((interest - reference) / abs(reference), 4) if reference else 0.0
    return {
        "label": " · ".join(v for _, v in seg),
        "segment": pairs,
        "metric_interest_usd_m": round(interest, 2),
        "metric_reference_usd_m": round(reference, 2),
        "difference_usd_m": diff,
        "relative_difference": rel,
        "unexpected_difference_usd_m": round(unexpected, 2),
        "contribution": contribution,
        "apriori_support": support,
        "direction": "up" if diff >= 0 else "down",
    }


# Hand-tuned, deterministic AI.KEY_DRIVERS output that tells the integration
# story: APAC growth pulls NNA up; dual-banked Swiss clients (integration
# overlap) drag it down by more than the population trend explains.
_KD_NNA = [
    _kd_row([("region", "APAC"), ("segment_tier", "UHNW")],            812.0, 540.0,  198.0, 0.214, 0.121),
    _kd_row([("booking_centre", "Geneva"), ("banking", "Dual-banked (Apex + Summit)")], 96.0, 318.0, -171.0, 0.165, 0.094),
    _kd_row([("booking_centre", "Hong Kong")],                          604.0, 470.0,  121.0, 0.142, 0.158),
    _kd_row([("segment_tier", "Family Office"), ("region", "EMEA")],    288.0, 196.0,   88.0, 0.118, 0.067),
    _kd_row([("booking_centre", "Zurich"), ("banking", "Dual-banked (Apex + Summit)")], 142.0, 286.0, -109.0, 0.108, 0.102),
    _kd_row([("segment_tier", "Affluent"), ("risk_profile", "Conservative")], 174.0, 252.0, -64.0, 0.082, 0.144),
    _kd_row([("region", "Americas"), ("segment_tier", "HNW")],          356.0, 300.0,   47.0, 0.071, 0.116),
    _kd_row([("risk_profile", "Aggressive"), ("region", "APAC")],       228.0, 168.0,   54.0, 0.069, 0.058),
    _kd_row([("segment_tier", "Institutional")],                        410.0, 372.0,   31.0, 0.044, 0.071),
]
_KD_INFLOW = [
    _kd_row([("region", "APAC"), ("segment_tier", "UHNW")],           1240.0, 980.0,  176.0, 0.198, 0.121),
    _kd_row([("booking_centre", "Hong Kong")],                        1010.0, 860.0,  118.0, 0.151, 0.158),
    _kd_row([("segment_tier", "Family Office"), ("region", "EMEA")],   520.0, 410.0,   84.0, 0.122, 0.067),
    _kd_row([("region", "Americas"), ("segment_tier", "HNW")],         690.0, 600.0,   58.0, 0.094, 0.116),
    _kd_row([("booking_centre", "Singapore")],                         470.0, 408.0,   46.0, 0.077, 0.083),
    _kd_row([("segment_tier", "Affluent"), ("risk_profile", "Growth")],380.0, 352.0,   24.0, 0.051, 0.139),
]
_KD_OUTFLOW = [
    _kd_row([("booking_centre", "Geneva"), ("banking", "Dual-banked (Apex + Summit)")], 402.0, 214.0, 158.0, 0.231, 0.094),
    _kd_row([("booking_centre", "Zurich"), ("banking", "Dual-banked (Apex + Summit)")], 318.0, 198.0, 101.0, 0.164, 0.102),
    _kd_row([("segment_tier", "Affluent"), ("risk_profile", "Conservative")], 246.0, 188.0, 49.0, 0.097, 0.144),
    _kd_row([("region", "EMEA"), ("segment_tier", "HNW")],             290.0, 244.0,   38.0, 0.082, 0.131),
    _kd_row([("booking_centre", "London")],                            210.0, 180.0,   27.0, 0.061, 0.088),
]
_KD = {
    "nna":     ("Net New Money",  "higher", _KD_NNA),
    "inflow":  ("Gross Inflows",  "higher", _KD_INFLOW),
    "outflow": ("Gross Outflows", "lower",  _KD_OUTFLOW),
}
_KD_COMMENTARY = {
    "nna": ("Net New Money rose overall, but the gain is uneven: **APAC UHNW** and **Hong Kong** "
            "booking centres pulled NNA well above the bankwide trend (+USD 198m / +USD 121m "
            "unexpected), while **dual-banked clients in Geneva and Zurich** dragged it down by far "
            "more than the trend explains (−USD 171m / −USD 109m unexpected) — the integration-overlap "
            "cohort to defend first. Sustaining the APAC momentum while stemming Swiss dual-banked "
            "outflows is the clearest path to the $200bn net-new-money ambition."),
    "inflow": ("Gross inflows are being driven by **APAC UHNW** and **Hong Kong**, which together "
               "contribute the bulk of the recent uplift and over-shoot the population trend — "
               "consistent with the post-integration push into Asia-Pacific wealth."),
    "outflow": ("The recent rise in outflows is concentrated in **dual-banked (Apex + Summit) "
                "clients booked in Geneva and Zurich** — the integration-overlap cohort — which "
                "exceed the bankwide outflow trend by the widest margin and warrant immediate "
                "retention attention."),
}


def key_drivers(metric: str = "nna") -> dict:
    label, direction, drivers = _KD.get(metric, _KD["nna"])
    drivers = sorted(drivers, key=lambda d: -abs(d["unexpected_difference_usd_m"]))
    ti = round(sum(d["metric_interest_usd_m"] for d in drivers), 1)
    tr = round(sum(d["metric_reference_usd_m"] for d in drivers), 1)
    return {
        "metric": metric, "metric_label": label, "direction": direction,
        "interest_period": "Most recent 6 months", "reference_period": "Prior 6 months",
        "total_interest_usd_m": ti, "total_reference_usd_m": tr,
        "net_change_usd_m": round(ti - tr, 1),
        "drivers": drivers,
        "commentary": _KD_COMMENTARY.get(metric, _KD_COMMENTARY["nna"]),
    }


_KD_HIST_MONTHS = ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
                   "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
_KD_FC_MONTHS = ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]


_KD_DS = "raves-altostrat.FSI_POV"
_KD_COL = {"nna": ("net_new_money_usd", "Net New Money"),
           "inflow": ("inflow_usd", "Gross Inflows"),
           "outflow": ("outflow_usd", "Gross Outflows")}
_KD_ALL_DIMS = ["segment_tier", "region", "booking_centre", "risk_profile", "banking"]


def _kd_dim_expr(n: str) -> str:
    return ("IF(c.dual_banked, 'Dual-banked (Apex + Summit)', 'Single-bank')"
            if n == "banking" else f"c.{n}")


def _kd_where(pairs: list[dict]) -> str:
    parts = []
    for p in pairs:
        if p["name"] == "banking":
            parts.append("c.dual_banked = TRUE" if p["value"].lower().startswith("dual") else "c.dual_banked = FALSE")
        else:
            parts.append(f"{_kd_dim_expr(p['name'])} = '{p['value']}'")
    return "\n     AND ".join(parts) or "TRUE"


def kd_sql_block(metric: str, pairs: list[dict], recent: float, prior: float, good: bool) -> dict:
    """The real AI-function SQL behind each deep-dive stage, scoped to this segment.
    Shared by the live BigQuery layer and the fixtures so the UI shows identical SQL."""
    col, label = _KD_COL.get(metric, _KD_COL["nna"])
    where = _kd_where(pairs)
    subs = [d for d in _KD_ALL_DIMS if d not in {p["name"] for p in pairs}]
    sub_select = ",\n            ".join(f"{_kd_dim_expr(d)} AS {d}" for d in subs) or "c.segment_tier"
    sub_list = "[" + ", ".join(f"'{d}'" for d in subs) + "]" if subs else "['segment_tier']"
    seg_text = " · ".join(p["value"] for p in pairs)
    return {
        "anomalies": f"""-- WHAT HAPPENED · AI.DETECT_ANOMALIES — flag the anomalous months in this
-- segment's monthly {label} series (recent dip/spike vs its own history).
SELECT month, metric AS {col}, is_anomaly, anomaly_probability
FROM AI.DETECT_ANOMALIES(
  (SELECT TIMESTAMP_TRUNC(TIMESTAMP(f.month), MONTH) AS month,
          SUM(f.{col}) AS metric
   FROM `{_KD_DS}.client_flows` f
   JOIN `{_KD_DS}.clients`  c USING (client_id)
   WHERE {where}
     AND f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)
   GROUP BY month),
  data_col              => 'metric',
  timestamp_col         => 'month',
  anomaly_prob_threshold => 0.95)
ORDER BY month;""",
        "drivers": f"""-- WHY IT HAPPENED · AI.KEY_DRIVERS — within this segment, rank the sub-segments
-- driving the change (recent 6m = interest vs prior 6m = reference).
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT {sub_select},
          f.{col} AS metric,
          f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 6 MONTH) AS is_recent
   FROM `{_KD_DS}.client_flows` f
   JOIN `{_KD_DS}.clients`  c USING (client_id)
   WHERE {where}
     AND f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)),
  metric_col         => 'metric',
  dimension_cols     => {sub_list},
  interest_label_col => 'is_recent',
  top_k              => 10)
ORDER BY ABS(unexpected_difference) DESC;""",
        "forecast": f"""-- WHAT'S NEXT · AI.FORECAST (TimesFM 2.5) — 6-month forward path of this
-- segment's monthly {label}, with a 90% prediction interval.
SELECT forecast_timestamp, forecast_value,
       prediction_interval_lower_bound, prediction_interval_upper_bound
FROM AI.FORECAST(
  (SELECT TIMESTAMP(f.month) AS month, SUM(f.{col}) AS v
   FROM `{_KD_DS}.client_flows` f
   JOIN `{_KD_DS}.clients`  c USING (client_id)
   WHERE {where}
   GROUP BY month),
  data_col         => 'v',
  timestamp_col    => 'month',
  model            => 'TimesFM 2.5',
  horizon          => 6,
  confidence_level => 0.9)
ORDER BY forecast_timestamp;""",
        "prevention": f"""-- HOW TO {'SUSTAIN' if good else 'PREVENT'} IT · AI.GENERATE — compliant actions grounded in the numbers.
SELECT AI.GENERATE(
  CONCAT('Recommend 3-4 concrete, compliant actions for a Apex Bank market head to ',
         '{'sustain' if good else 'prevent and reverse'} the recent {label} move for the ',
         '"{seg_text}" segment. Recent 6m USD {recent}m vs prior 6m USD {prior}m. ',
         'Tie to the Apex-Summit integration and the $200bn net-new-money ambition.'),
  connection_id => 'us-central1.vertex_conn',
  endpoint      => 'gemini-2.5-flash').result AS recommended_actions;""",
    }


def _parse_seg(seg: str) -> list[dict]:
    pairs = []
    for tok in (seg or "").split("|"):
        if ":" in tok:
            n, _, v = tok.partition(":")
            pairs.append({"name": n.strip(), "value": v.strip()})
    return pairs


def key_drivers_drilldown(metric: str = "nna", seg: str = "") -> dict:
    label, direction, rows = _KD.get(metric, _KD["nna"])
    pairs = _parse_seg(seg)
    want = {(p["name"], p["value"]) for p in pairs}
    drv = next((d for d in rows if {(s["name"], s["value"]) for s in d["segment"]} == want), None) \
        or next((d for d in rows if pairs and d["label"] == " · ".join(p["value"] for p in pairs)), None) \
        or rows[0]

    seg_lower = drv["label"].lower()
    is_dual = "dual-banked" in seg_lower
    is_apac = any(k in seg_lower for k in ("apac", "hong kong", "singapore"))
    down = drv["direction"] == "down"

    prior_avg = drv["metric_reference_usd_m"] / 6
    recent_avg = drv["metric_interest_usd_m"] / 6
    trend = []
    for i, ts in enumerate(_KD_HIST_MONTHS):
        value = round((prior_avg if i < 6 else recent_avg) * (1 + (((i * 37) % 7) - 3) / 100), 2)
        is_anom = i >= 6 and (value < prior_avg * 0.85 if down else value > prior_avg * 1.15)
        trend.append({"ts": ts, "value": value, "is_anomaly": bool(is_anom)})
    slope = (recent_avg - prior_avg) / 6
    forecast = []
    for i, ts in enumerate(_KD_FC_MONTHS):
        yhat = round(recent_avg + slope * (i + 1) * 0.6, 2)
        spread = abs(yhat) * (0.07 + i * 0.015)
        forecast.append({"ts": ts, "yhat": yhat, "lo": round(yhat - spread, 2), "hi": round(yhat + spread, 2)})

    diff = drv["difference_usd_m"]
    if is_dual:
        factors = [
            {"factor": "Integration-overlap attrition", "impact_usd_m": round(diff * 0.52, 1),
             "detail": "Dual-banked clients consolidating away from the former Summit relationship as the platforms merge — duplicated mandates and fee-schedule overlap."},
            {"factor": "Fee & pricing harmonisation", "impact_usd_m": round(diff * 0.28, 1),
             "detail": "Repricing to the unified Apex schedule triggered partial withdrawals among price-sensitive Swiss-booked clients."},
            {"factor": "Advisor reassignment", "impact_usd_m": round(diff * 0.20, 1),
             "detail": "Relationship-manager changes during migration reduced engagement and prompted balance transfers."},
        ]
    elif is_apac:
        factors = [
            {"factor": "New-client acquisition", "impact_usd_m": round(diff * 0.49, 1),
             "detail": "Onboarding of UHNW entrepreneurs in Hong Kong & Singapore following the integrated APAC platform launch."},
            {"factor": "Mandate up-tiering", "impact_usd_m": round(diff * 0.31, 1),
             "detail": "Existing clients moving from advisory into discretionary and private-markets mandates."},
            {"factor": "FX / market tailwind", "impact_usd_m": round(diff * 0.20, 1),
             "detail": "Favourable currency moves and equity performance lifted reported flows for the cohort."},
        ]
    else:
        factors = [
            {"factor": "Allocation shift", "impact_usd_m": round(diff * 0.46, 1),
             "detail": "Net reallocation between cash and invested mandates within the segment."},
            {"factor": "Seasonality", "impact_usd_m": round(diff * 0.30, 1),
             "detail": "Recurring half-year funding/liquidity pattern typical for this cohort."},
            {"factor": "Pricing & engagement", "impact_usd_m": round(diff * 0.24, 1),
             "detail": "Changes in fee sensitivity and advisor contact frequency over the period."},
        ]

    if down:
        narrative = (f"**{drv['label']}** {'outflows rose' if metric == 'outflow' else 'flows fell'} from "
                     f"${abs(drv['metric_reference_usd_m'])}m to ${abs(drv['metric_interest_usd_m'])}m over the recent "
                     f"six months ({drv['relative_difference'] * 100:.1f}%), about ${abs(drv['unexpected_difference_usd_m'])}m "
                     f"worse than the bankwide trend would predict. The move is driven mainly by {factors[0]['factor'].lower()}"
                     f"{' — the classic post-merger consolidation risk where clients who held both Apex and Summit relationships rationalise down to one provider' if is_dual else ''}. "
                     f"This is a controllable, relationship-led decline rather than a market effect, which is why it warrants direct intervention.")
        prevention = [
            {"title": "Launch a dual-banked retention sprint" if is_dual else "Targeted retention outreach",
             "detail": ("Auto-enrol every dual-banked client in this segment into the Flight-Risk Sentinel save-play queue; "
                        "senior-advisor calls within 10 business days, consolidated cross-bank pricing on the table." if is_dual
                        else "Prioritise advisor outreach to the highest-balance accounts in this segment with a portfolio health-check offer."),
             "owner": "Regional Market Head"},
            {"title": "Pre-empt fee-driven attrition",
             "detail": "Apply grandfathered or blended pricing for migrating clients for 12 months; flag any repricing >15bps for relationship-manager review before it lands.",
             "owner": "Pricing & Revenue Mgmt"},
            {"title": "Stabilise relationship continuity",
             "detail": "Freeze advisor reassignments for at-risk dual-banked clients during migration; assign a named transition contact per household.",
             "owner": "COO / Integration Office"},
            {"title": "Add an early-warning monitor",
             "detail": "Stand up a weekly AI.KEY_DRIVERS + attrition watch on this segment so an unexpected-difference breach pages the desk before the quarter closes.",
             "owner": "Data & Analytics"},
        ]
        nxt = (f"Left unmanaged, {drv['label']} stays below trend through H2 — an estimated "
               f"${abs(sum(f['yhat'] for f in forecast)):.0f}m over the next six months, widening confidence bands as "
               f"attrition compounds. The retention actions below are modelled to arrest and reverse the slide.")
    else:
        narrative = (f"**{drv['label']}** {'outflows' if metric == 'outflow' else 'flows'} grew from "
                     f"${drv['metric_reference_usd_m']}m to ${drv['metric_interest_usd_m']}m ({drv['relative_difference'] * 100:.1f}%), "
                     f"roughly ${drv['unexpected_difference_usd_m']}m above the bankwide trend. The uplift is led by "
                     f"{factors[0]['factor'].lower()}{', reflecting the integrated APAC platform gaining share in the fastest-growing wealth pool' if is_apac else ''}. "
                     f"Protecting and replicating this momentum is the priority.")
        prevention = [
            {"title": "Codify and scale the winning play",
             "detail": "Document the acquisition + up-tiering motion behind this cohort and roll it out to comparable segments in adjacent booking centres.",
             "owner": "Regional Market Head"},
            {"title": "Protect the gains",
             "detail": "Lock in newly onboarded UHNW clients with onboarding-plus journeys and private-markets access before competitors respond.",
             "owner": "Product & Advisory"},
            {"title": "Reinforce capacity",
             "detail": "Ensure advisor and booking-centre capacity keeps pace with the inflow so service quality does not dilute the momentum.",
             "owner": "COO"},
        ]
        nxt = (f"On current trajectory {drv['label']} continues above trend into H2, contributing an estimated "
               f"${sum(f['yhat'] for f in forecast):.0f}m over the next six months — a meaningful step toward the "
               f"$200bn NNA ambition if capacity keeps pace.")

    good = (drv["direction"] == "up") == (metric != "outflow")
    sql = kd_sql_block(metric, drv["segment"], drv["metric_interest_usd_m"], drv["metric_reference_usd_m"], good)

    return {
        "metric": metric, "metric_label": label, "label": drv["label"],
        "segment": drv["segment"], "direction": drv["direction"],
        "what_happened": {
            "recent_usd_m": drv["metric_interest_usd_m"], "prior_usd_m": drv["metric_reference_usd_m"],
            "difference_usd_m": drv["difference_usd_m"], "relative_difference": drv["relative_difference"],
            "unexpected_difference_usd_m": drv["unexpected_difference_usd_m"],
            "contribution": drv["contribution"], "apriori_support": drv["apriori_support"], "trend": trend,
            "ai_function": "AI.DETECT_ANOMALIES", "sql": sql["anomalies"],
        },
        "rca": {"narrative": narrative, "factors": factors, "ai_function": "AI.KEY_DRIVERS", "sql": sql["drivers"]},
        "whats_next": {"forecast": forecast, "commentary": nxt, "ai_function": "AI.FORECAST", "sql": sql["forecast"]},
        "prevention": {"actions": prevention, "ai_function": "AI.GENERATE", "sql": sql["prevention"]},
    }


def research_search(q: str) -> list[dict]:
    docs = [
        ("DOC_000012", "Apex CIO Research — Private credit allocation for UHNW portfolios",
         "cio_research", "Our CIO view favours a structural allocation to private credit for "
         "qualified UHNW and family-office clients, citing attractive risk-adjusted yields..."),
        ("DOC_000044", "Apex CIO Research — Global asset allocation: balanced positioning into 2026",
         "cio_research", "Our balanced multi-asset stance holds a modest overweight to global "
         "equities funded from cash, neutral duration in high-grade bonds..."),
        ("DOC_000091", "Suitability Assessment — CLI_0002281",
         "suitability", "Investment objective: balanced growth and income. Structured products "
         "limited to 15% of the portfolio..."),
        ("DOC_000133", "Apex CIO Research — APAC wealth: capturing the next decade of growth",
         "cio_research", "Asia-Pacific remains the fastest-growing wealth pool. We highlight "
         "onshore and offshore booking considerations and currency hedging..."),
    ]
    out = []
    for i, (did, title, dt, txt) in enumerate(docs):
        out.append({"document_id": did, "title": title, "doc_type": dt,
                    "snippet": txt, "score": round(0.92 - i * 0.07, 3),
                    "gcs_uri": f"gs://fsi_pov/raw/documents/{did}.pdf"})
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
    dual = [38, 12, 41, 27, 15, 22, 9, 34]
    out = []
    for i, (lab, dom, attr) in enumerate(labels):
        out.append({"id": i, "label": lab, "size": _R.randint(1800, 9200),
                    "avg_aum_usd": round(_R.uniform(2e6, 4e8), 2),
                    "dominant_asset": dom, "attrition_index": attr,
                    "dual_banked_pct": dual[i % 8]})
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
                "FROM `raves-altostrat.FSI_POV.client_flows` f\n"
                "JOIN `raves-altostrat.FSI_POV.clients` c USING (client_id)\n"
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
         "summary": "A 6-member household holds ≈USD 420m with 3 dual-banked (Apex + Summit) "
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
