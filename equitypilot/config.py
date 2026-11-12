"""Central configuration: paths, constants, freshness rules and data-type labels."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "EquityPilot AI"
APP_TAGLINE = "Indian Equity Research & Financial Intelligence Platform"
APP_VERSION = "1.0.0"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("EQUITYPILOT_DATA_DIR", ROOT_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = Path(os.environ.get("EQUITYPILOT_DB", DATA_DIR / "equitypilot.db"))

# When set (tests, offline demos) no network call is attempted.
OFFLINE = os.environ.get("EQUITYPILOT_OFFLINE", "0") == "1"

CRORE = 1e7  # 1 crore = 10 million

# How long cached data is considered fresh before the app offers a refresh.
FRESHNESS_HOURS = {
    "quote": 0.25,      # Yahoo quotes are delayed anyway; refresh every 15 min at most
    "prices": 12,
    "financials": 24 * 7,
    "profile": 24 * 30,
    "news": 3,
}

# Every number shown in the app carries one of these data-type labels.
DATA_TYPES = {
    "sample": ("SAMPLE", "Fictional demonstration data - not a real company"),
    "live": ("LIVE", "Real-time price from a licensed broker feed"),
    "delayed": ("DELAYED", "Third-party market data; may be delayed by 15+ minutes"),
    "official": ("OFFICIAL", "Primary source: exchange, regulator or government publication"),
    "historical": ("HISTORICAL", "Historical data as reported by the stated source"),
    "third_party": ("THIRD-PARTY", "Secondary data provider (e.g. Yahoo Finance) - verify with official filings"),
    "official_upload": ("OFFICIAL (UPLOADED)", "Entered from an official filing uploaded by the user"),
    "user_entered": ("USER-ENTERED", "Entered manually by the user"),
    "calculated": ("CALCULATED", "Computed by EquityPilot from the data shown"),
    "assumption": ("ASSUMPTION", "User-editable assumption, not a reported figure"),
}

YAHOO_SOURCE = "Yahoo Finance (via yfinance)"
YAHOO_URL = "https://finance.yahoo.com/quote/{symbol}"
SAMPLE_SOURCE = "EquityPilot sample dataset (fictional)"

# Indices shown on the dashboard (Yahoo Finance symbols).
INDICES = {
    "^NSEI": "NIFTY 50",
    "^BSESN": "S&P BSE SENSEX",
    "^NSEBANK": "NIFTY BANK",
    "^CNXIT": "NIFTY IT",
    "^INDIAVIX": "India VIX",
}
BENCHMARK = "^NSEI"


def ensure_dirs() -> None:
    for d in (DATA_DIR, UPLOAD_DIR, REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
