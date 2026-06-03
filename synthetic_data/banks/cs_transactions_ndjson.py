"""
Credit Suisse legacy transaction event stream — NDJSON, value date as epoch ms,
FX legs, code-based transaction types. Feeds the AML / financial-crime graph.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone

import numpy as np

from config import MASTER_SEED
from identities import project_client

_TXN_CODES = {"buy": "BUY", "sell": "SEL", "transfer_in": "TIN",
              "transfer_out": "TOU", "fee": "FEE", "fx": "FXS"}


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "cs_transactions.ndjson")
    rng = random.Random(MASTER_SEED ^ 0x7AC)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(clients_m):
            if "credit_suisse" not in c.in_banks:
                continue
            p = project_client(c, "credit_suisse")
            for _ in range(rng.randint(3, 20)):
                code = rng.choice(list(_TXN_CODES.values()))
                amt = round(abs(np.random.lognormal(10.4, 1.5)), 2)
                days_ago = rng.randint(0, 730)
                ts = datetime.now(timezone.utc).timestamp() - days_ago * 86400
                rec = {
                    "cif": f"CS{i:09d}",
                    "txCode": code,
                    "amount": amt,
                    "ccy": rng.choice(["EUR", "USD", "CHF"]),
                    "valueDateMs": int(ts * 1000),
                    "counterparty": rng.choice(
                        ["INTERNAL", "EXT_BANK", "BROKER", "CUSTODIAN", "SELF"]),
                    "fxLeg": (rng.choice(["EURUSD", "USDCHF", "GBPUSD"])
                              if code == "FXS" else None),
                }
                f.write(json.dumps(rec) + "\n")
                n += 1
    return {"file": path, "rows": n, "format": "NEWLINE_DELIMITED_JSON"}
