"""
config.py — Shared constants and environment configuration for FSI Helix
synthetic data generator.

The estate models TWO legacy banks — "Apex Bank" and "Summit Bank" — whose data
must be unified into one governed BigQuery Client 360. All values can be
overridden via environment variables.
"""
from __future__ import annotations

import os
import random

import numpy as np

# ---------------------------------------------------------------------------
# GCP / BigQuery
# ---------------------------------------------------------------------------
GOOGLE_CLOUD_PROJECT: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "raves-altostrat")
GCP_REGION: str = os.environ.get("GCP_REGION", "us-central1")
BQ_LOCATION: str = os.environ.get("BQ_LOCATION", "us-central1")
# Single consolidated dataset (logical zones via table prefixes).
BQ_DATASET: str = os.environ.get("BQ_DATASET", "FSI_POV")
GCS_BUCKET: str = os.environ.get("GCS_BUCKET", "fsi_pov")
BQ_CONNECTION: str = os.environ.get("BQ_CONNECTION", "us-central1.vertex_conn")

# Optional Gemini for rich text generation in documents
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Scale knob
# 1 → ~40k clients, ~90k accounts, ~1.2m holdings, ~600k txns, ~1.5k docs
# Values scale linearly.
# ---------------------------------------------------------------------------
DATA_SCALE: float = float(os.environ.get("DATA_SCALE", "1"))

N_CLIENTS: int = int(40_000 * DATA_SCALE)
N_ADVISORS: int = int(900 * DATA_SCALE)
N_DOCUMENTS: int = int(1_500 * DATA_SCALE)
# Derived volumes (per-client multipliers applied in generators)
AVG_ACCOUNTS_PER_CLIENT: float = 2.2
AVG_HOLDINGS_PER_PORTFOLIO: float = 14.0
AVG_TXNS_PER_CLIENT: float = 15.0

# Fraction of clients that exist in BOTH banks (dual-banked) — the entity-res game
DUAL_BANK_FRACTION: float = 0.22

# ---------------------------------------------------------------------------
# RNG seeds — deterministic everywhere
# ---------------------------------------------------------------------------
MASTER_SEED: int = 42


def seed_all() -> None:
    random.seed(MASTER_SEED)
    np.random.seed(MASTER_SEED)


seed_all()

# ---------------------------------------------------------------------------
# Source banks
# ---------------------------------------------------------------------------
SOURCE_BANKS = ["apex", "summit"]

# ---------------------------------------------------------------------------
# Reference enums (kept here so generators + loaders agree)
# ---------------------------------------------------------------------------
BOOKING_CENTRES = [
    "Zurich", "Geneva", "Basel", "Lugano",        # CH
    "London",                                       # EMEA
    "New York",                                     # Americas
    "Hong Kong", "Singapore",                       # APAC
]

BOOKING_CENTRE_REGION = {
    "Zurich": "Switzerland", "Geneva": "Switzerland", "Basel": "Switzerland",
    "Lugano": "Switzerland", "London": "EMEA", "New York": "Americas",
    "Hong Kong": "APAC", "Singapore": "APAC",
}

# Division each booking centre primarily rolls into (for forecasting marts)
REGIONS = ["Switzerland", "EMEA", "Americas", "APAC"]
DIVISIONS = ["GWM", "P&C", "Asset Management", "Investment Bank"]

SEGMENT_TIERS = ["Affluent", "HNW", "UHNW", "Family Office", "Institutional"]
SEGMENT_WEIGHTS = [0.46, 0.34, 0.12, 0.05, 0.03]

# Approx AuM band (USD) per segment tier — drives realistic portfolio sizing
SEGMENT_AUM_BAND = {
    "Affluent":      (250_000, 2_000_000),
    "HNW":           (2_000_000, 30_000_000),
    "UHNW":          (30_000_000, 500_000_000),
    "Family Office": (100_000_000, 3_000_000_000),
    "Institutional": (200_000_000, 5_000_000_000),
}

RISK_PROFILES = ["Conservative", "Balanced", "Growth", "Aggressive"]
KYC_STATUSES = ["verified", "review_required", "expired", "pending"]
KYC_WEIGHTS = [0.78, 0.10, 0.06, 0.06]

CURRENCIES = ["CHF", "USD", "EUR", "GBP", "HKD", "SGD"]

ACCOUNT_TYPES = [
    "discretionary", "advisory", "execution_only",
    "lombard", "mortgage", "deposit",
]
ACCOUNT_TYPE_WEIGHTS = [0.24, 0.30, 0.18, 0.10, 0.08, 0.10]

ASSET_CLASSES = [
    "equity", "fixed_income", "fund", "structured", "alternative", "cash", "fx",
]
ASSET_CLASS_WEIGHTS = [0.34, 0.24, 0.14, 0.08, 0.10, 0.08, 0.02]

TXN_TYPES = ["buy", "sell", "transfer_in", "transfer_out", "fee", "fx"]
TXN_TYPE_WEIGHTS = [0.34, 0.26, 0.12, 0.12, 0.10, 0.06]

LANGUAGES = ["German", "French", "Italian", "English", "Mandarin", "Spanish", "Portuguese"]

DOC_TYPES = ["cio_research", "kyc", "suitability", "advice_note"]
DOC_TYPE_WEIGHTS = [0.30, 0.30, 0.20, 0.20]

LEGAL_ENTITY_TYPES = ["trust", "holdco", "foundation", "spv"]

# Time-series window
TS_START = "2022-01-01"   # 48+ months of history feeding TimesFM
TS_MONTHS = 54            # through ~mid-2026 demo window


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
OUTPUT_ROOT: str = os.environ.get(
    "OUTPUT_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"),
)


def bank_output_dir(bank: str) -> str:
    d = os.path.join(OUTPUT_ROOT, bank)
    os.makedirs(d, exist_ok=True)
    return d


def curated_output_dir() -> str:
    d = os.path.join(OUTPUT_ROOT, "curated")
    os.makedirs(d, exist_ok=True)
    return d


def ts_output_dir() -> str:
    d = os.path.join(OUTPUT_ROOT, "timeseries")
    os.makedirs(d, exist_ok=True)
    return d


def docs_output_dir() -> str:
    d = os.path.join(OUTPUT_ROOT, "documents")
    os.makedirs(d, exist_ok=True)
    return d


def truth_output_dir() -> str:
    d = os.path.join(OUTPUT_ROOT, "_truth")
    os.makedirs(d, exist_ok=True)
    return d
