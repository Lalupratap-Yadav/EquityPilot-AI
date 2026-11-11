"""Official sources: deep links only.

NSE India does not offer a public, documented data API for retail developers and blocks
automated requests to its website; BSE India likewise publishes data through its website
rather than a documented open API. EquityPilot therefore does NOT scrape these sites.
Instead it links the user to the official page, and offers uploads (CSV/Excel/PDF) so that
figures taken from official filings can be stored with their source reference.
"""
from __future__ import annotations

from urllib.parse import quote

from .universe import base_ticker

OFFICIAL_SOURCES = [
    {"name": "NSE India", "url": "https://www.nseindia.com/",
     "use": "Quotes, corporate announcements, financial results, shareholding patterns (NSE-listed)",
     "access": "Website only - no public developer API; automated access is blocked. Use manual download + upload."},
    {"name": "BSE India", "url": "https://www.bseindia.com/",
     "use": "Corporate announcements, results, shareholding patterns, annual reports (BSE-listed)",
     "access": "Website only - no documented open API. Use manual download + upload."},
    {"name": "SEBI", "url": "https://www.sebi.gov.in/",
     "use": "Regulations (incl. Research Analyst Regulations), circulars, investor education",
     "access": "Website (reference links)."},
    {"name": "RBI", "url": "https://www.rbi.org.in/",
     "use": "Policy repo rate, G-sec yields, macro data (also data.rbi.org.in - DBIE)",
     "access": "Website / DBIE portal. Enter rates used in valuation as assumptions with the date."},
    {"name": "MOSPI", "url": "https://mospi.gov.in/",
     "use": "GDP, CPI inflation, IIP - macro context for research reports",
     "access": "Website / releases. Used for context only."},
    {"name": "Company investor relations", "url": None,
     "use": "Annual reports, investor presentations, quarterly results (primary source)",
     "access": "Download PDFs from the company's website and upload them in the Data Manager."},
    {"name": "Yahoo Finance (via yfinance)", "url": "https://finance.yahoo.com/",
     "use": "Delayed quotes, price history, summarised statements, news headlines",
     "access": "Secondary third-party source accessed through the open-source yfinance library; "
               "verify important figures against official filings."},
]


def nse_links(symbol: str) -> dict[str, str]:
    t = quote(base_ticker(symbol))
    return {
        "NSE quote page": f"https://www.nseindia.com/get-quotes/equity?symbol={t}",
        "NSE corporate announcements": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "NSE financial results": "https://www.nseindia.com/companies-listing/corporate-filings-financial-results",
        "NSE shareholding patterns": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
        "NSE annual reports": "https://www.nseindia.com/companies-listing/corporate-filings-annual-reports",
    }


def bse_links(symbol: str) -> dict[str, str]:
    return {
        "BSE corporate announcements": "https://www.bseindia.com/corporates/ann.html",
        "BSE results": "https://www.bseindia.com/corporates/Comp_Resultsnew.aspx",
        "BSE shareholding pattern": "https://www.bseindia.com/corporates/Sharehold_Searchnew.aspx",
    }


def official_links(symbol: str) -> dict[str, str]:
    if symbol.startswith("SAMPLE-"):
        return {}
    links = nse_links(symbol)
    links.update(bse_links(symbol))
    links["SEBI investor portal"] = "https://investor.sebi.gov.in/"
    return links
