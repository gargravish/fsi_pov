"""
Credit Suisse legacy account extract — XML <Account> elements, product code lists,
EUR/USD amounts. BigQuery cannot read XML natively: the loader parses it to JSON;
the original XML stays in GCS for the AI-unification story.
"""
from __future__ import annotations

import os
import random
from xml.sax.saxutils import escape

from config import MASTER_SEED
from identities import project_client

_PROD_CODES = {"discretionary": "CS-DIM", "advisory": "CS-AVM",
               "execution_only": "CS-EXO", "lombard": "CS-LOM",
               "mortgage": "CS-MTG", "deposit": "CS-DEP"}


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "cs_accounts.xml")
    rng = random.Random(MASTER_SEED ^ 0xC50)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<Accounts>\n')
        for i, c in enumerate(clients_m):
            if "credit_suisse" not in c.in_banks:
                continue
            p = project_client(c, "credit_suisse")
            for _ in range(rng.randint(1, 3)):
                code = rng.choice(list(_PROD_CODES.values()))
                bal = round(max(0.0, p["base_aum_usd"]) * rng.uniform(0.1, 0.7), 2)
                ccy = rng.choice(["EUR", "USD", "CHF"])
                opened = f"{rng.randint(2005,2025)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
                f.write(
                    f'  <Account cif="CS{i:09d}">\n'
                    f'    <ProductCode>{code}</ProductCode>\n'
                    f'    <BookingCenter>{escape(p["booking_centre"])}</BookingCenter>\n'
                    f'    <Currency>{ccy}</Currency>\n'
                    f'    <Balance>{bal}</Balance>\n'
                    f'    <Status>{rng.choice(["ACTIVE","DORMANT","CLOSING"])}</Status>\n'
                    f'    <OpenedDate>{opened}</OpenedDate>\n'
                    f'  </Account>\n'
                )
                n += 1
        f.write('</Accounts>\n')
    return {"file": path, "rows": n, "format": "XML"}
