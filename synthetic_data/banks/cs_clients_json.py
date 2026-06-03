"""
Credit Suisse legacy client master — nested JSON (NDJSON), cifNumber, ISO dates,
"Last, First" name order, mixed currency. The platform must reconcile these
against the UBS CSV records (entity resolution).
"""
from __future__ import annotations

import json
import os

from identities import project_client


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "cs_clients.json")
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(clients_m):
            if "credit_suisse" not in c.in_banks:
                continue
            p = project_client(c, "credit_suisse")
            rec = {
                "cifNumber": f"CS{i:09d}",
                "client": {
                    "displayName": p["name"],
                    "isLegalEntity": p["is_entity"],
                    "dateOfBirth": p["dob"],
                    "clientSegment": p["segment_tier"],
                    "riskProfile": p["risk_profile"],
                    "languages": p["languages"],
                },
                "kyc": {"status": p["kyc_status"]},
                "address": {
                    "line1": p["address_line"], "city": p["city"],
                    "country": p["domicile"],
                },
                "contact": {"email": p["email"], "phone": p["phone"]},
                "booking": {"center": p["booking_centre"], "baseCcy": p["primary_ccy"]},
            }
            f.write(json.dumps(rec) + "\n")
            n += 1
    return {"file": path, "rows": n, "format": "NEWLINE_DELIMITED_JSON"}
