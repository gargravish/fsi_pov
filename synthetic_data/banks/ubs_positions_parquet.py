"""
UBS legacy positions extract — Parquet, ISIN + asset-class codes, CHF valuation.
"""
from __future__ import annotations

import os
import random

import pandas as pd

import reference
from config import MASTER_SEED
from identities import project_client

_AC_CODE = {"equity": "EQ", "fixed_income": "FI", "fund": "FD",
            "structured": "ST", "alternative": "ALT", "cash": "CSH", "fx": "FX"}


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "ubs_positions.parquet")
    rng = random.Random(MASTER_SEED ^ 0x9A1)
    inst_by_class = reference.instruments_by_class()
    rows = []
    for i, c in enumerate(clients_m):
        if "ubs" not in c.in_banks:
            continue
        p = project_client(c, "ubs")
        n_pos = rng.randint(4, 16)
        for _ in range(n_pos):
            ac = rng.choice(list(inst_by_class.keys()))
            ins = rng.choice(inst_by_class[ac])
            rows.append({
                "KUNDE_NR": f"U{i:08d}",
                "ISIN": ins.isin,
                "ASSET_CLASS_CD": _AC_CODE[ac],
                "MARKTWERT_CHF": round(max(0.0, p["base_aum_usd"]) * rng.uniform(0.01, 0.2), 2),
                "WAEHRUNG": ins.currency,
            })
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    return {"file": path, "rows": len(rows), "format": "PARQUET"}
