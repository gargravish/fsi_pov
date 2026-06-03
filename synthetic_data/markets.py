"""
markets.py — Clean analytic time-series marts for AI.FORECAST / TimesFM:
ts_aum_monthly, ts_nna_monthly, ts_revenue_monthly by division x region, with
trend + seasonality + realistic shocks (2022 drawdown, 2023 CS-deal NNA dip,
2024-26 recovery & NNA ramp). >=48 monthly points per series.
"""
from __future__ import annotations

import math
import random
from datetime import date

import numpy as np

from config import MASTER_SEED, DIVISIONS, REGIONS, TS_MONTHS

_rng = random.Random(MASTER_SEED ^ 0x7E5)


def _months(n: int) -> list[str]:
    out = []
    y, m = 2022, 1
    for _ in range(n):
        out.append(date(y, m, 1).isoformat())
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _shock(t: int) -> float:
    """Multiplicative shock by month index from 2022-01."""
    # 2022 market drawdown (months 0-11), trough ~ month 9
    drop = -0.10 * math.exp(-((t - 9) ** 2) / 30.0) if t < 14 else 0.0
    # 2023 CS-acquisition NNA wobble (months 14-22)
    wobble = -0.06 * math.exp(-((t - 17) ** 2) / 20.0) if 12 <= t <= 26 else 0.0
    # 2024-26 recovery ramp
    recovery = 0.08 * (1 / (1 + math.exp(-(t - 30) / 6.0)))
    return 1.0 + drop + wobble + recovery


def _seasonal(month_idx: int, amp: float) -> float:
    m = (month_idx % 12) + 1
    return 1.0 + amp * math.sin(2 * math.pi * (m - 3) / 12.0)


# Base levels (USD bn) per division x region — GWM dominates
_DIV_BASE = {"GWM": 1.0, "P&C": 0.35, "Asset Management": 0.55, "Investment Bank": 0.45}
_REGION_BASE = {"Switzerland": 1.0, "EMEA": 0.7, "Americas": 0.8, "APAC": 0.6}


def build_marts() -> dict[str, list[dict]]:
    months = _months(TS_MONTHS)
    aum, nna, rev = [], [], []
    for div in DIVISIONS:
        for reg in REGIONS:
            base_aum_bn = 800 * _DIV_BASE[div] * _REGION_BASE[reg]
            trend = 0.006 + 0.004 * _DIV_BASE[div]
            seed = _rng.random()
            for t, mth in enumerate(months):
                shock = _shock(t)
                seas = _seasonal(t, 0.04)
                noise = np.random.normal(1.0, 0.02)
                aum_v = base_aum_bn * (1 + trend) ** t * shock * seas * noise
                aum.append({"month": mth, "division": div, "region": reg,
                            "aum_usd_bn": round(aum_v, 2)})

                # NNA: ramps toward the $200bn/yr group ambition; dips in 2023
                # (~0.2%/month of AuM per series → ~$200bn/yr group run-rate)
                nna_base = base_aum_bn * 0.002
                nna_v = nna_base * _seasonal(t, 0.18) * (0.4 + 0.9 * (t / TS_MONTHS)) \
                    * (1 + (shock - 1) * 2.0) * np.random.normal(1.0, 0.08)
                nna.append({"month": mth, "division": div, "region": reg,
                            "net_new_money_usd_bn": round(nna_v, 3)})

                # revenue: ~ fee on AuM + seasonal IB swing
                rev_v = aum_v * (0.0028 + 0.0006 * math.sin(seed + t / 8.0)) \
                    * np.random.normal(1.0, 0.03)
                rev.append({"month": mth, "division": div, "region": reg,
                            "revenue_usd_bn": round(rev_v, 3)})

    return {"ts_aum_monthly": aum, "ts_nna_monthly": nna, "ts_revenue_monthly": rev}
