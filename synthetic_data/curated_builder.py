"""
curated_builder.py — Build the clean, resolved CURATED canonical objects from the
hidden master pool. These are the tables the app reads (clients, accounts,
portfolios, holdings, transactions, advisors, households, legal_entities,
products, client_flows) plus the attrition feature/scoring tables.

The RAW per-bank fragmented files (banks/*) are projections of these same
canonical objects — so the /unify demo is consistent with everything else.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import numpy as np

import reference
from config import (
    MASTER_SEED, AVG_ACCOUNTS_PER_CLIENT, AVG_HOLDINGS_PER_PORTFOLIO,
    AVG_TXNS_PER_CLIENT, ACCOUNT_TYPES, ACCOUNT_TYPE_WEIGHTS,
    ASSET_CLASSES, ASSET_CLASS_WEIGHTS, TXN_TYPES, TXN_TYPE_WEIGHTS,
)
from identities import (
    get_master_pool, get_households, get_advisors, get_legal_entities,
    assign_banks,
)

TODAY = date(2026, 6, 1)

# Risk profile -> rough target asset-class weights (drives holdings + cross-sell logic)
_RISK_MIX = {
    "Conservative": {"fixed_income": 0.5, "cash": 0.2, "fund": 0.15, "equity": 0.1, "structured": 0.05},
    "Balanced":     {"equity": 0.35, "fixed_income": 0.3, "fund": 0.15, "alternative": 0.1, "cash": 0.1},
    "Growth":       {"equity": 0.5, "fund": 0.2, "alternative": 0.15, "fixed_income": 0.1, "cash": 0.05},
    "Aggressive":   {"equity": 0.55, "alternative": 0.25, "structured": 0.1, "fund": 0.07, "cash": 0.03},
}


def _weighted_assets(risk: str, rng: random.Random, k: int) -> list[str]:
    mix = _RISK_MIX.get(risk, _RISK_MIX["Balanced"])
    classes = list(mix.keys())
    weights = list(mix.values())
    return rng.choices(classes, weights=weights, k=k)


def build_all() -> dict[str, list[dict]]:
    rng = random.Random(MASTER_SEED ^ 0xC0FFEE)
    clients_m = get_master_pool()
    assign_banks(clients_m)
    households = get_households()
    advisors = get_advisors()
    entities = get_legal_entities()
    products = reference.products()
    inst_by_class = reference.instruments_by_class()

    advisor_ids = [a.advisor_id for a in advisors]

    clients: list[dict] = []
    accounts: list[dict] = []
    portfolios: list[dict] = []
    holdings: list[dict] = []
    transactions: list[dict] = []
    client_flows: list[dict] = []
    attrition_rows: list[dict] = []

    for c in clients_m:
        # tenure: older for entities, varied otherwise
        tenure_days = rng.randint(120, 365 * 22)
        first_seen = TODAY - timedelta(days=tenure_days)
        primary_advisor = advisor_ids[c.advisor_seed % len(advisor_ids)]

        # ---- accounts ----
        n_acc = max(1, int(np.random.poisson(AVG_ACCOUNTS_PER_CLIENT)))
        client_aum = 0.0
        acc_ids_for_client: list[tuple[str, str]] = []  # (account_id, type)
        # allocate AuM across investment accounts
        for _ in range(n_acc):
            atype = rng.choices(ACCOUNT_TYPES, weights=ACCOUNT_TYPE_WEIGHTS, k=1)[0]
            aid = f"ACC_{len(accounts):08d}"
            ccy = rng.choice(["CHF", "USD", "EUR", "GBP", "HKD", "SGD"])
            # split base AuM into account balances
            share = rng.uniform(0.2, 1.0)
            bal = round(c.base_aum_usd * share / n_acc, 2)
            if atype in ("lombard", "mortgage"):
                bal = -round(bal * rng.uniform(0.1, 0.5), 2)  # liability
            else:
                client_aum += max(bal, 0)
            accounts.append({
                "account_id": aid, "client_id": c.master_client_id,
                "account_type": atype, "booking_centre": c.booking_centre,
                "currency": ccy, "status": rng.choices(
                    ["active", "dormant", "closing"], weights=[0.88, 0.08, 0.04], k=1)[0],
                "open_date": (first_seen + timedelta(days=rng.randint(0, max(1, tenure_days // 2)))
                              ).isoformat(),
                "balance_usd": bal,
            })
            acc_ids_for_client.append((aid, atype))

            # ---- portfolio + holdings for investment accounts ----
            if atype in ("discretionary", "advisory", "execution_only") and bal > 0:
                pid = f"PF_{len(portfolios):08d}"
                portfolios.append({
                    "portfolio_id": pid, "account_id": aid,
                    "client_id": c.master_client_id,
                    "mandate_type": atype,
                    "benchmark": rng.choice(["MSCI World", "SMI", "60/40 Global",
                                             "Bloomberg Global Agg", "Custom UHNW"]),
                    "currency": ccy,
                    "market_value_usd": bal,
                    "inception_date": accounts[-1]["open_date"],
                })
                n_hold = max(3, int(np.random.poisson(AVG_HOLDINGS_PER_PORTFOLIO)))
                classes = _weighted_assets(c.risk_profile, rng, n_hold)
                # normalise weights
                raw_w = [rng.uniform(0.3, 1.0) for _ in range(n_hold)]
                tot_w = sum(raw_w)
                for j in range(n_hold):
                    ac = classes[j]
                    pool = inst_by_class.get(ac) or inst_by_class["equity"]
                    ins = rng.choice(pool)
                    w = raw_w[j] / tot_w
                    mv = round(bal * w, 2)
                    holdings.append({
                        "holding_id": f"H_{len(holdings):09d}",
                        "portfolio_id": pid, "client_id": c.master_client_id,
                        "isin": ins.isin, "instrument_name": ins.name,
                        "asset_class": ac,
                        "quantity": round(mv / rng.uniform(10, 500), 2),
                        "market_value_usd": mv, "weight_pct": round(w * 100, 2),
                        "currency": ins.currency,
                    })

        # ---- transactions ----
        n_txn = max(1, int(np.random.poisson(AVG_TXNS_PER_CLIENT)))
        for _ in range(n_txn):
            if not acc_ids_for_client:
                break
            aid, _t = rng.choice(acc_ids_for_client)
            ttype = rng.choices(TXN_TYPES, weights=TXN_TYPE_WEIGHTS, k=1)[0]
            amt = round(abs(np.random.lognormal(mean=10.5, sigma=1.4)), 2)
            transactions.append({
                "txn_id": f"TXN_{len(transactions):09d}",
                "account_id": aid, "client_id": c.master_client_id,
                "txn_type": ttype, "amount_usd": amt,
                "currency": rng.choice(["CHF", "USD", "EUR"]),
                "value_date": (TODAY - timedelta(days=rng.randint(0, 730))).isoformat(),
                "counterparty": rng.choice(
                    ["internal", "external_bank", "broker", "custodian", "self"]),
            })

        # ---- per-client monthly NNA flows (last 12 months) + attrition signal ----
        # flight-risk drivers: dual-banked + recent net outflows + advisor churn
        dual = len(c.in_banks) == 2
        base_risk = 0.10
        base_risk += 0.18 if dual else 0.0
        base_risk += {"Conservative": 0.0, "Balanced": 0.02, "Growth": 0.04,
                      "Aggressive": 0.06}[c.risk_profile]
        if c.kyc_status in ("expired", "review_required"):
            base_risk += 0.08
        outflow_bias = rng.uniform(-0.4, 0.6) + (0.5 if dual else 0.0)
        recent_net = 0.0
        recent_outflow = 0.0
        recent_inflow = 0.0
        for m in range(12):
            mdate = (TODAY.replace(day=1) - timedelta(days=30 * (11 - m)))
            month_str = mdate.replace(day=1).isoformat()
            inflow = max(0.0, np.random.normal(client_aum * 0.01, client_aum * 0.01))
            outflow = max(0.0, np.random.normal(
                client_aum * 0.01 * (1 + outflow_bias), client_aum * 0.012))
            net = inflow - outflow
            recent_net += net
            recent_inflow += inflow
            recent_outflow += outflow
            client_flows.append({
                "client_id": c.master_client_id, "month": month_str,
                "net_new_money_usd": round(net, 2),
                "inflow_usd": round(inflow, 2), "outflow_usd": round(outflow, 2),
            })
        outflow_ratio = recent_outflow / (recent_inflow + recent_outflow + 1.0)
        # label: attrited if strongly net-negative + risk factors
        risk_score = base_risk + 0.4 * outflow_ratio
        attrited = int(rng.random() < min(0.9, risk_score))

        clients.append({
            "client_id": c.master_client_id, "full_name": c.full_name,
            "is_entity": c.is_entity, "dob": c.dob,
            "segment_tier": c.segment_tier, "domicile": c.domicile_country,
            "booking_centre": c.booking_centre, "region": c.region,
            "risk_profile": c.risk_profile, "kyc_status": c.kyc_status,
            "languages": "|".join(c.languages),
            "email": c.email, "phone": c.phone,
            "address_line": c.address_line, "city": c.city,
            "primary_advisor_id": primary_advisor,
            "source_banks": "|".join(sorted(c.in_banks)),
            "dual_banked": dual,
            "total_aum_usd": round(client_aum, 2),
            "first_seen_date": first_seen.isoformat(),
            "tenure_days": tenure_days,
            "household_id": c.household_id,
            "marketing_consent": rng.random() < 0.7,
        })

        # attrition feature row
        feat = {
            "client_id": c.master_client_id, "segment_tier": c.segment_tier,
            "region": c.region, "risk_profile": c.risk_profile,
            "tenure_days": tenure_days, "total_aum_usd": round(client_aum, 2),
            "n_accounts": n_acc, "n_txns": n_txn,
            "dual_banked": int(dual),
            "kyc_flag": int(c.kyc_status in ("expired", "review_required")),
            "recent_net_flow_usd": round(recent_net, 2),
            "outflow_ratio": round(outflow_ratio, 4),
        }
        attrition_rows.append({**feat, "attrited": attrited})

    # advisors / households / entities / products as dict lists
    advisors_out = [{
        "advisor_id": a.advisor_id, "name": a.name, "role": a.role, "desk": a.desk,
        "booking_centre": a.booking_centre, "market": a.market,
        "languages": "|".join(a.languages), "source_bank": a.bank,
    } for a in advisors]

    households_out = []
    for hid, h in households.items():
        if not h.member_ids:
            continue
        members = [cl for cl in clients if cl["household_id"] == hid]
        households_out.append({
            "household_id": hid, "address_key": f"{h.address_line}, {h.city}",
            "member_count": len(h.member_ids),
            "total_aum_usd": round(sum(m["total_aum_usd"] for m in members), 2),
            "lines_held": "|".join(sorted({
                a["account_type"] for a in accounts
                if a["client_id"] in {m["client_id"] for m in members}})),
        })

    entities_out = [{
        "entity_id": e.entity_id, "entity_type": e.entity_type, "name": e.name,
        "jurisdiction": e.jurisdiction, "ubo_client_id": e.ubo_master_client_id,
        "risk_flag": e.risk_flag,
    } for e in entities]

    products_out = [{
        "product_id": p.product_id, "product_type": p.product_type, "name": p.name,
        "description": p.description, "target_segment_hint": p.target_segment_hint,
    } for p in products]

    # split attrition into training (80%) / scoring (all, without label)
    rng.shuffle(attrition_rows)
    n_train = int(len(attrition_rows) * 0.8)
    attrition_training = attrition_rows[:n_train]
    attrition_scoring = [{k: v for k, v in r.items() if k != "attrited"}
                         for r in attrition_rows]

    return {
        "clients": clients, "accounts": accounts, "portfolios": portfolios,
        "holdings": holdings, "transactions": transactions,
        "advisors": advisors_out, "households": households_out,
        "legal_entities": entities_out, "products": products_out,
        "client_flows": client_flows,
        "attrition_training": attrition_training,
        "attrition_scoring": attrition_scoring,
    }
