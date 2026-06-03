"""
UBS legacy portfolio extract — fixed-width mainframe format (no headers),
YYYYMMDD dates, mandate codes (not labels), CHF amounts. BigQuery cannot read
fixed-width natively: the loader parses this into JSON; the original stays in GCS
for the "AI parses the messy mainframe extract" story.

Layout (column positions):
  [0:9]   kunde_nr
  [9:13]  mandat_code   (DSC=discretionary, ADV=advisory, EXE=execution)
  [13:23] benchmark_cd
  [23:26] waehrung
  [26:41] marktwert_chf (right-justified, 2dp, no separator)
  [41:49] eroeffnung    (YYYYMMDD)
"""
from __future__ import annotations

import os
import random

from config import MASTER_SEED
from identities import project_client

_MANDATE_CODES = {"discretionary": "DSC", "advisory": "ADV", "execution_only": "EXE"}
_BENCH = ["MSCIWORLD", "SMI_______", "G60_40____", "BBGAGG____", "UHNWCUST__"]


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "ubs_portfolios.txt")
    rng = random.Random(MASTER_SEED ^ 0x501)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(clients_m):
            if "ubs" not in c.in_banks:
                continue
            p = project_client(c, "ubs")
            for _ in range(rng.randint(1, 2)):
                code = rng.choice(list(_MANDATE_CODES.values()))
                bench = rng.choice(_BENCH)
                mv = int(max(0.0, p["base_aum_usd"] * rng.uniform(0.2, 0.9)) * 100)
                year = rng.randint(2002, 2025)
                eroeff = f"{year}{rng.randint(1,12):02d}{rng.randint(1,28):02d}"
                line = (
                    f"U{i:08d}"
                    f"{code:<4}"
                    f"{bench:<10}"
                    f"{p['primary_ccy']:<3}"
                    f"{mv:015d}"
                    f"{eroeff:<8}"
                )
                f.write(line + "\n")
                n += 1
    return {"file": path, "rows": n, "format": "FIXED_WIDTH"}
