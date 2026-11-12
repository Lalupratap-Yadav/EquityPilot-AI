"""Source reliability tiers for news and disclosures.

  primary      - official sources: stock exchanges, regulators, government, company filings
  established  - secondary reporting by established news organisations and professional newswires
  unrated      - anything else (blogs, stock-tip sites, content aggregators, trade newsletters).
                 Hidden by default in the UI and never given to the AI assistant as evidence.

The established list is deliberately conservative: a publisher is added only if it is a
recognised newsroom or wire service with editorial standards. Being "established" does not make
a headline a verified fact - the UI still labels it SECONDARY and links to the original.
"""
from __future__ import annotations

import re

# official source labels start with one of these (feed labels such as "NSE India - corporate announcements (RSS)")
PRIMARY_PREFIXES = ("nse india", "nse ", "bse ", "bse india", "sebi", "reserve bank of india", "rbi ", "mospi",
                    "ministry of statistics", "press information bureau")

ESTABLISHED = {
    # wires
    "reuters", "associated press", "ap", "afp", "bloomberg", "dow jones", "mt newswires", "press trust of india", "pti",
    "ani", "ians",
    # Indian business press
    "the economic times", "economic times", "mint", "livemint", "business standard", "the hindu businessline",
    "hindu businessline", "the hindu", "financial express", "the financial express", "moneycontrol", "cnbc-tv18",
    "cnbctv18", "ndtv profit", "business today", "the times of india", "hindustan times", "the indian express",
    # international business press
    "financial times", "the wall street journal", "wall street journal", "barrons.com", "barron's", "marketwatch",
    "cnbc", "cnn business", "bbc", "the economist", "nikkei asia", "fortune", "forbes", "investor's business daily",
    "the new york times", "the guardian", "euronews", "morningstar", "s&p global", "fitch", "moody's",
    # market-data portals with newsrooms
    "investing.com", "yahoo finance",
}

UNRATED_NOTE = ("Headlines from publishers EquityPilot does not classify as established news organisations "
                "(for example stock-tip sites, blogs and content aggregators) are hidden by default.")


def _norm(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\s+via yahoo finance$", "", n)
    n = re.sub(r"\s*\(.*\)$", "", n)
    return n.strip()


def tier(source: str | None, data_type: str | None = None) -> str:
    """Classify a publisher / source label. `data_type` from the database can force primary
    (exchange feeds, official uploads) or sample."""
    if data_type in ("official_feed", "official", "official_upload"):
        return "primary"
    if data_type == "sample":
        return "sample"
    if data_type == "user_entered":
        return "user"
    if not source:
        return "unrated"
    raw = source.lower().strip()
    n = _norm(source)
    if " via yahoo finance" not in raw and raw.startswith(PRIMARY_PREFIXES):
        return "primary"
    if n in ESTABLISHED or n.startswith("yahoo finance"):
        return "established"
    return "unrated"


TIER_LABELS = {"primary": "Official source", "established": "Secondary - established publisher",
               "unrated": "Unrated publisher", "sample": "Sample data", "user": "Entered by you"}
