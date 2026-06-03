"""
UBS legacy client master — CSV, Swiss-German field names, DD.MM.YYYY dates, CHF.
"""
from __future__ import annotations

import csv
import os
from datetime import date

from identities import project_client

FIELDS = ["kunde_nr", "name", "geburtsdatum", "domizil", "buchungszentrum",
          "segment", "risiko_profil", "kyc_status", "sprachen", "email",
          "telefon", "adresse", "ort", "waehrung"]


def _ch_date(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso


def write(clients_m, out_dir: str) -> dict:
    path = os.path.join(out_dir, "ubs_clients.csv")
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, c in enumerate(clients_m):
            if "ubs" not in c.in_banks:
                continue
            p = project_client(c, "ubs")
            w.writerow({
                "kunde_nr": f"U{i:08d}",
                "name": p["name"], "geburtsdatum": _ch_date(p["dob"]),
                "domizil": p["domicile"], "buchungszentrum": p["booking_centre"],
                "segment": p["segment_tier"], "risiko_profil": p["risk_profile"],
                "kyc_status": p["kyc_status"], "sprachen": ";".join(p["languages"]),
                "email": p["email"], "telefon": p["phone"],
                "adresse": p["address_line"], "ort": p["city"],
                "waehrung": p["primary_ccy"],
            })
            n += 1
    return {"file": path, "rows": n, "format": "CSV"}
