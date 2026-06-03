"""
UBS legacy advisor (Client Advisor / RM) book — Excel .xlsx.
"""
from __future__ import annotations

import os

import pandas as pd

from identities import get_advisors


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "ubs_advisors.xlsx")
    advisors = [a for a in get_advisors() if a.bank == "ubs"]
    rows = [{
        "Advisor ID": a.advisor_id, "Name": a.name, "Role": a.role,
        "Desk": a.desk, "Booking Centre": a.booking_centre, "Market": a.market,
        "Languages": ", ".join(a.languages),
    } for a in advisors]
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False, sheet_name="Advisors")
    return {"file": path, "rows": len(rows), "format": "XLSX"}
