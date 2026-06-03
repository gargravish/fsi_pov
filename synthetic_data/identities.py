"""
identities.py — Hidden master client / household / legal-entity / advisor pool.

This is the "ground truth" for the post-merger entity-resolution game. Each
source bank (UBS, Credit Suisse) sees a *mutated projection* of a client
(different name order, domicile spelling, email domain, client number). The
master_client_id is NEVER written to source files; it lives only in
ground_truth_identity_map.csv for offline accuracy scoring.

~DUAL_BANK_FRACTION of clients are projected into BOTH banks (dual-banked) —
the unification opportunity the platform must rediscover.
"""
from __future__ import annotations

import csv
import os
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from faker import Faker

from config import (
    MASTER_SEED, N_CLIENTS, N_ADVISORS, DUAL_BANK_FRACTION,
    BOOKING_CENTRES, BOOKING_CENTRE_REGION, SEGMENT_TIERS, SEGMENT_WEIGHTS,
    SEGMENT_AUM_BAND, RISK_PROFILES, KYC_STATUSES, KYC_WEIGHTS, LANGUAGES,
    LEGAL_ENTITY_TYPES, truth_output_dir,
)

_rng = np.random.default_rng(MASTER_SEED)

# Locale faker pool keyed by domicile flavour
_FAKERS = {
    "ch_de": Faker("de_CH"), "ch_fr": Faker("fr_CH"), "uk": Faker("en_GB"),
    "us": Faker("en_US"), "apac": Faker("zh_TW"),
}
for _f in _FAKERS.values():
    _f.seed_instance(MASTER_SEED)

_DOMICILES = {
    "Zurich": ("Switzerland", "ch_de"), "Basel": ("Switzerland", "ch_de"),
    "Geneva": ("Switzerland", "ch_fr"), "Lugano": ("Switzerland", "ch_fr"),
    "London": ("United Kingdom", "uk"), "New York": ("United States", "us"),
    "Hong Kong": ("Hong Kong", "apac"), "Singapore": ("Singapore", "apac"),
}

_UBS_EMAIL = ["bluewin.ch", "gmail.com", "outlook.com", "icloud.com", "swissonline.ch"]
_CS_EMAIL = ["gmx.ch", "yahoo.com", "hotmail.com", "protonmail.com", "sunrise.ch"]


# ---------------------------------------------------------------------------
@dataclass
class MasterClient:
    master_client_id: str
    is_entity: bool                 # True => legal entity (family office / institutional)
    full_name: str
    first_name: str
    last_name: str
    dob: str                        # ISO; for entities = incorporation date
    domicile_country: str
    booking_centre: str
    region: str
    segment_tier: str
    risk_profile: str
    kyc_status: str
    languages: list[str]
    email: str
    phone: str
    address_line: str
    city: str
    base_aum_usd: float
    household_id: str
    advisor_seed: int               # used to assign advisor per bank
    in_banks: list[str] = field(default_factory=list)


@dataclass
class Household:
    household_id: str
    address_line: str
    city: str
    member_ids: list[str] = field(default_factory=list)


@dataclass
class Advisor:
    advisor_id: str
    name: str
    role: str                       # CA / RM
    desk: str
    booking_centre: str
    market: str
    languages: list[str]
    bank: str


@dataclass
class LegalEntity:
    entity_id: str
    entity_type: str
    name: str
    jurisdiction: str
    ubo_master_client_id: str
    risk_flag: bool


_MASTER: Optional[list[MasterClient]] = None
_HOUSEHOLDS: Optional[dict[str, Household]] = None
_ADVISORS: Optional[list[Advisor]] = None
_ENTITIES: Optional[list[LegalEntity]] = None


# ---------------------------------------------------------------------------
def _phone() -> str:
    return "+%d %d %03d %02d %02d" % (
        _rng.choice([41, 44, 1, 852, 65]), _rng.integers(10, 99),
        _rng.integers(100, 999), _rng.integers(10, 99), _rng.integers(10, 99),
    )


def _build() -> tuple[list[MasterClient], dict[str, Household]]:
    rng = random.Random(MASTER_SEED)
    households: dict[str, Household] = {}
    clients: list[MasterClient] = []

    n_households = N_CLIENTS // 3
    for h in range(n_households):
        hid = f"HH{h:07d}"
        bc = rng.choice(BOOKING_CENTRES)
        _, flavour = _DOMICILES.get(bc, ("Switzerland", "ch_de"))
        fk = _FAKERS[flavour]
        households[hid] = Household(hid, fk.street_address(), fk.city())
    household_ids = list(households.keys())

    for i in range(N_CLIENTS):
        cid = f"CLI_{i:07d}"
        bc = rng.choice(BOOKING_CENTRES)
        country, flavour = _DOMICILES[bc]
        fk = _FAKERS[flavour]
        region = BOOKING_CENTRE_REGION[bc]

        tier = rng.choices(SEGMENT_TIERS, weights=SEGMENT_WEIGHTS, k=1)[0]
        is_entity = tier in ("Family Office", "Institutional") and rng.random() < 0.7

        if is_entity:
            suffix = rng.choice(["Holdings AG", "Family Office SA", "Foundation",
                                 "Capital Partners", "Trust", "Investments Ltd"])
            last = fk.last_name()
            full = f"{last} {suffix}"
            first = ""
            dob = f"{rng.randint(1975, 2018)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        else:
            first = fk.first_name()
            last = fk.last_name()
            full = f"{first} {last}"
            dob = fk.date_of_birth(minimum_age=25, maximum_age=88).strftime("%Y-%m-%d")

        lo, hi = SEGMENT_AUM_BAND[tier]
        base_aum = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))

        if rng.random() < 0.62:
            hid = rng.choice(household_ids)
            addr = households[hid].address_line
            city = households[hid].city
            households[hid].member_ids.append(cid)
        else:
            hid = f"HH_SOLO_{i:07d}"
            addr = fk.street_address()
            city = fk.city()

        n_lang = rng.randint(1, 3)
        langs = rng.sample(LANGUAGES, k=n_lang)

        clients.append(MasterClient(
            master_client_id=cid, is_entity=is_entity, full_name=full,
            first_name=first, last_name=last, dob=dob, domicile_country=country,
            booking_centre=bc, region=region, segment_tier=tier,
            risk_profile=rng.choice(RISK_PROFILES),
            kyc_status=rng.choices(KYC_STATUSES, weights=KYC_WEIGHTS, k=1)[0],
            languages=langs,
            email=f"{(first or last).lower()}.{last.lower()}@{rng.choice(_UBS_EMAIL)}".replace(" ", ""),
            phone=_phone(), address_line=addr, city=city, base_aum_usd=base_aum,
            household_id=hid, advisor_seed=rng.randint(0, N_ADVISORS - 1),
        ))

    return clients, households


def get_master_pool() -> list[MasterClient]:
    global _MASTER, _HOUSEHOLDS
    if _MASTER is None:
        _MASTER, _HOUSEHOLDS = _build()
    return _MASTER


def get_households() -> dict[str, Household]:
    global _MASTER, _HOUSEHOLDS
    if _HOUSEHOLDS is None:
        _MASTER, _HOUSEHOLDS = _build()
    return _HOUSEHOLDS


# ---------------------------------------------------------------------------
# Advisors
# ---------------------------------------------------------------------------
def get_advisors() -> list[Advisor]:
    global _ADVISORS
    if _ADVISORS is not None:
        return _ADVISORS
    rng = random.Random(MASTER_SEED ^ 0x1234)
    out: list[Advisor] = []
    for i in range(N_ADVISORS):
        bc = rng.choice(BOOKING_CENTRES)
        _, flavour = _DOMICILES.get(bc, ("Switzerland", "ch_de"))
        fk = _FAKERS[flavour]
        bank = rng.choice(["ubs", "credit_suisse"])
        out.append(Advisor(
            advisor_id=f"ADV_{i:05d}", name=fk.name(),
            role=rng.choice(["CA", "RM"]),
            desk=rng.choice(["Private Wealth", "UHNW & Family Office",
                             "Affluent", "Institutional Clients"]),
            booking_centre=bc, market=BOOKING_CENTRE_REGION[bc],
            languages=rng.sample(LANGUAGES, k=rng.randint(1, 3)), bank=bank,
        ))
    _ADVISORS = out
    return out


# ---------------------------------------------------------------------------
# Legal entities (family offices / UBO chains, also feeds AML graph)
# ---------------------------------------------------------------------------
def get_legal_entities() -> list[LegalEntity]:
    global _ENTITIES
    if _ENTITIES is not None:
        return _ENTITIES
    rng = random.Random(MASTER_SEED ^ 0x9999)
    clients = get_master_pool()
    fo_clients = [c for c in clients if c.segment_tier in ("Family Office", "Institutional")]
    out: list[LegalEntity] = []
    for i, c in enumerate(fo_clients):
        n_layers = rng.randint(1, 3)
        for layer in range(n_layers):
            etype = rng.choice(LEGAL_ENTITY_TYPES)
            out.append(LegalEntity(
                entity_id=f"LE_{i:05d}_{layer}", entity_type=etype,
                name=f"{c.last_name} {etype.upper()} {rng.choice(['SA','AG','Ltd','LP'])}",
                jurisdiction=rng.choice(["CH", "LU", "KY", "JE", "SG", "BVI", "US"]),
                ubo_master_client_id=c.master_client_id,
                risk_flag=rng.random() < 0.18,
            ))
    _ENTITIES = out
    return out


# ---------------------------------------------------------------------------
# Bank assignment + projection (the entity-resolution game)
# ---------------------------------------------------------------------------
def assign_banks(clients: list[MasterClient]) -> None:
    """Decide which bank(s) each client appears in. ~DUAL_BANK_FRACTION in both."""
    rng = random.Random(MASTER_SEED ^ 0xBEEF)
    for c in clients:
        r = rng.random()
        if r < DUAL_BANK_FRACTION:
            c.in_banks = ["ubs", "credit_suisse"]
        elif r < DUAL_BANK_FRACTION + (1 - DUAL_BANK_FRACTION) / 2:
            c.in_banks = ["ubs"]
        else:
            c.in_banks = ["credit_suisse"]


def _mutate_name(c: MasterClient, bank: str, rng: random.Random) -> str:
    """Slightly mutate the displayed name per bank (order, abbreviation, casing)."""
    if c.is_entity:
        nm = c.full_name
        if bank == "credit_suisse" and rng.random() < 0.4:
            nm = nm.replace("Holdings", "Hldg").replace("Foundation", "Fdn")
        return nm.upper() if rng.random() < 0.2 else nm
    first, last = c.first_name, c.last_name
    if bank == "credit_suisse" and rng.random() < 0.45:
        # CS stores "Last, First"
        if rng.random() < 0.3:
            first = first[0] + "."
        return f"{last}, {first}"
    if rng.random() < 0.25:
        first = first[0] + "."
    nm = f"{first} {last}"
    return nm.upper() if rng.random() < 0.15 else nm


def project_client(c: MasterClient, bank: str) -> dict:
    """Bank-specific representation. NEVER includes master_client_id."""
    seed_val = (hash((c.master_client_id, bank)) & 0xFFFFFFFF)
    rng = random.Random(seed_val)
    name = _mutate_name(c, bank, rng)
    domains = _UBS_EMAIL if bank == "ubs" else _CS_EMAIL
    local = c.email.split("@")[0]
    if rng.random() < 0.4:
        local = local + str(rng.randint(1, 99))
    email = f"{local}@{rng.choice(domains)}"
    # vary domicile spelling between banks
    dom = c.domicile_country
    if bank == "credit_suisse":
        dom = {"Switzerland": "CH", "United Kingdom": "UK", "United States": "USA",
               "Hong Kong": "HK"}.get(dom, dom)
    ccy = {"Switzerland": "CHF", "CH": "CHF", "United Kingdom": "GBP", "UK": "GBP",
           "United States": "USD", "USA": "USD", "Hong Kong": "HKD", "HK": "HKD",
           "Singapore": "SGD"}.get(dom, "USD")
    return {
        "_master_client_id": c.master_client_id,
        "name": name, "first_name": c.first_name, "last_name": c.last_name,
        "dob": c.dob, "is_entity": c.is_entity,
        "domicile": dom, "booking_centre": c.booking_centre, "region": c.region,
        "segment_tier": c.segment_tier, "risk_profile": c.risk_profile,
        "kyc_status": c.kyc_status, "languages": c.languages,
        "email": email, "phone": c.phone, "address_line": c.address_line,
        "city": c.city, "primary_ccy": ccy, "base_aum_usd": c.base_aum_usd,
        "household_id": c.household_id, "advisor_seed": c.advisor_seed,
    }


# ---------------------------------------------------------------------------
def write_ground_truth(rows: list[dict]) -> str:
    out_dir = truth_output_dir()
    path = os.path.join(out_dir, "ground_truth_identity_map.csv")
    if not rows:
        return path
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path
