"""
reference.py — Reference/master data pools shared across the estate:
instruments (ISINs by asset class), the product catalogue, and small helpers.
Deterministic given the master seed.
"""
from __future__ import annotations

import random
import string
from dataclasses import dataclass

from config import MASTER_SEED

_rng = random.Random(MASTER_SEED ^ 0xA5A5)

# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------
_ISIN_COUNTRIES = ["CH", "US", "DE", "GB", "FR", "LU", "JP", "HK", "SG"]

_EQUITY_NAMES = [
    "Nestle SA", "Novartis AG", "Roche Holding", "Apple Inc", "Microsoft Corp",
    "Alphabet Inc", "ASML Holding", "LVMH", "Nvidia Corp", "TSMC ADR",
    "Tencent Holdings", "Samsung Electronics", "Zurich Insurance", "UBS Group AG",
    "Richemont", "Siemens AG", "Shell plc", "AstraZeneca", "HSBC Holdings",
]
_FUND_NAMES = [
    "Global Equity Income Fund", "Sustainable Bond Fund", "EM Opportunities Fund",
    "Swiss Equity Fund", "Multi-Asset Balanced Fund", "Tech Innovation Fund",
    "Gold & Precious Metals Fund", "Short Duration Credit Fund",
]
_STRUCTURED_NAMES = [
    "Capital Protection Note (SMI)", "Barrier Reverse Convertible (Tech basket)",
    "Autocallable Note (EuroStoxx)", "Yield Enhancement Certificate (FX)",
]
_ALT_NAMES = [
    "Private Equity Secondary Fund IV", "Global Macro Hedge Fund",
    "Real Estate Income Fund (CH)", "Infrastructure Debt Fund",
    "Private Credit Direct Lending II", "Venture Growth Fund III",
]
_BOND_NAMES = [
    "Swiss Confederation 1.5% 2031", "US Treasury 4.25% 2034",
    "Bund 2.4% 2033", "Nestle 0.9% 2029", "Apple 3.85% 2043",
    "EIB Green Bond 2.7% 2030", "Zurich Ins 3.5% 2032",
]


@dataclass
class Instrument:
    isin: str
    name: str
    asset_class: str
    currency: str


def _make_isin() -> str:
    country = _rng.choice(_ISIN_COUNTRIES)
    body = "".join(_rng.choices(string.ascii_uppercase + string.digits, k=9))
    check = _rng.randint(0, 9)
    return f"{country}{body}{check}"


def _build_instruments() -> list[Instrument]:
    out: list[Instrument] = []
    for nm in _EQUITY_NAMES:
        out.append(Instrument(_make_isin(), nm, "equity", _rng.choice(["CHF", "USD", "EUR"])))
    for nm in _BOND_NAMES:
        out.append(Instrument(_make_isin(), nm, "fixed_income", _rng.choice(["CHF", "USD", "EUR"])))
    for nm in _FUND_NAMES:
        out.append(Instrument(_make_isin(), nm, "fund", _rng.choice(["CHF", "USD", "EUR"])))
    for nm in _STRUCTURED_NAMES:
        out.append(Instrument(_make_isin(), nm, "structured", _rng.choice(["CHF", "USD"])))
    for nm in _ALT_NAMES:
        out.append(Instrument(_make_isin(), nm, "alternative", "USD"))
    # cash + fx pseudo-instruments
    out.append(Instrument("CASH_USD", "USD Cash", "cash", "USD"))
    out.append(Instrument("CASH_CHF", "CHF Cash", "cash", "CHF"))
    out.append(Instrument("FX_EURUSD", "EUR/USD FX", "fx", "USD"))
    return out


_INSTRUMENTS: list[Instrument] | None = None


def instruments() -> list[Instrument]:
    global _INSTRUMENTS
    if _INSTRUMENTS is None:
        _INSTRUMENTS = _build_instruments()
    return _INSTRUMENTS


def instruments_by_class() -> dict[str, list[Instrument]]:
    out: dict[str, list[Instrument]] = {}
    for ins in instruments():
        out.setdefault(ins.asset_class, []).append(ins)
    return out


# ---------------------------------------------------------------------------
# Product catalogue (with rich descriptions for autonomous embeddings)
# ---------------------------------------------------------------------------
@dataclass
class Product:
    product_id: str
    product_type: str
    name: str
    description: str
    target_segment_hint: str


_PRODUCTS_RAW = [
    ("discretionary", "UBS Manage Advanced Discretionary Mandate",
     "Fully delegated discretionary portfolio management where UBS investment "
     "professionals implement CIO house views across global equities, fixed income "
     "and alternatives, with active risk management and tax-aware rebalancing.",
     "HNW"),
    ("discretionary", "Sustainable Investing Discretionary Mandate",
     "Discretionary mandate built around ESG and impact objectives, screening and "
     "tilting toward sustainable leaders while tracking a global multi-asset benchmark.",
     "HNW"),
    ("advisory", "UBS Advice Premium Advisory Mandate",
     "Advisory mandate giving clients proactive, CIO-led investment ideas and "
     "portfolio health checks while retaining full decision control over each trade.",
     "Affluent"),
    ("lombard", "Lombard Credit Facility",
     "Flexible securities-backed lending against a pledged portfolio, providing "
     "liquidity for investment, real estate or business needs without liquidating assets.",
     "UHNW"),
    ("mortgage", "Swiss Residential Mortgage",
     "Mortgage financing for primary and secondary Swiss residential property with "
     "fixed and SARON-linked options and integrated wealth planning.",
     "Affluent"),
    ("alternative", "Private Markets Access Programme",
     "Curated access to institutional-quality private equity, private credit, real "
     "estate and infrastructure funds for qualified UHNW and family-office clients.",
     "UHNW"),
    ("alternative", "Family Office Co-Investment Platform",
     "Direct and co-investment opportunities alongside UBS and partner family offices "
     "across late-stage venture, buyout and real assets.",
     "Family Office"),
    ("structured", "Capital Protection Structured Solutions",
     "Tailored structured products offering defined downside protection and equity "
     "or rate-linked upside, customised to client market views and tenor.",
     "HNW"),
    ("fund", "Global Multi-Asset Fund Range",
     "Open-architecture fund selection spanning UBS and third-party active and index "
     "strategies across equities, bonds, commodities and thematic baskets.",
     "Affluent"),
    ("advisory", "Wealth Planning & Succession Advisory",
     "Holistic wealth structuring, trust and foundation advice, and cross-border "
     "succession planning for complex multi-generational families.",
     "Family Office"),
]


def products() -> list[Product]:
    out = []
    for i, (ptype, name, desc, hint) in enumerate(_PRODUCTS_RAW):
        out.append(Product(f"PRD_{i:03d}", ptype, name, desc, hint))
    return out
