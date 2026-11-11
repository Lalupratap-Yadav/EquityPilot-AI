"""Canonical financial line items.

All providers (Yahoo, uploads, sample data) map into these keys so analytics code never
depends on a provider's naming. All values are stored in absolute INR (not crore).
"""
from __future__ import annotations

# key -> (statement, display label, list of Yahoo Finance row names in priority order)
LINE_ITEMS: dict[str, tuple[str, str, list[str]]] = {
    # ---------------- income statement
    "revenue": ("income", "Revenue from operations", ["Total Revenue", "Operating Revenue"]),
    "cogs": ("income", "Cost of revenue", ["Cost Of Revenue", "Reconciled Cost Of Revenue"]),
    "gross_profit": ("income", "Gross profit", ["Gross Profit"]),
    "opex": ("income", "Operating expenses", ["Operating Expense"]),
    "ebitda": ("income", "EBITDA", ["EBITDA", "Normalized EBITDA"]),
    "depreciation": ("income", "Depreciation & amortisation", ["Reconciled Depreciation", "Depreciation And Amortization In Income Statement"]),
    "ebit": ("income", "EBIT (operating profit)", ["Operating Income", "EBIT"]),
    "interest_expense": ("income", "Finance costs", ["Interest Expense", "Interest Expense Non Operating"]),
    "pretax_income": ("income", "Profit before tax", ["Pretax Income"]),
    "tax": ("income", "Tax expense", ["Tax Provision"]),
    "net_income": ("income", "Net profit (to shareholders)", ["Net Income Common Stockholders", "Net Income", "Net Income From Continuing Operation Net Minority Interest"]),
    "eps_basic": ("income", "EPS - basic (₹)", ["Basic EPS"]),
    "eps_diluted": ("income", "EPS - diluted (₹)", ["Diluted EPS"]),
    "shares_diluted": ("income", "Diluted weighted shares", ["Diluted Average Shares", "Basic Average Shares"]),
    # ---------------- balance sheet
    "total_assets": ("balance", "Total assets", ["Total Assets"]),
    "current_assets": ("balance", "Current assets", ["Current Assets"]),
    "cash": ("balance", "Cash & short-term investments", ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
    "receivables": ("balance", "Trade receivables", ["Accounts Receivable", "Receivables"]),
    "inventory": ("balance", "Inventories", ["Inventory"]),
    "net_ppe": ("balance", "Net fixed assets (PP&E)", ["Net PPE"]),
    "total_liabilities": ("balance", "Total liabilities", ["Total Liabilities Net Minority Interest"]),
    "current_liabilities": ("balance", "Current liabilities", ["Current Liabilities"]),
    "total_debt": ("balance", "Total borrowings", ["Total Debt"]),
    "total_equity": ("balance", "Shareholders' equity", ["Stockholders Equity", "Common Stock Equity"]),
    "retained_earnings": ("balance", "Retained earnings / reserves", ["Retained Earnings"]),
    "minority_interest": ("balance", "Non-controlling interest", ["Minority Interest"]),
    "shares_outstanding": ("balance", "Shares outstanding", ["Ordinary Shares Number", "Share Issued"]),
    # ---------------- cash flow
    "cfo": ("cashflow", "Cash flow from operations", ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]),
    "capex": ("cashflow", "Capital expenditure", ["Capital Expenditure"]),
    "fcf": ("cashflow", "Free cash flow", ["Free Cash Flow"]),
    "cfi": ("cashflow", "Cash flow from investing", ["Investing Cash Flow"]),
    "cff": ("cashflow", "Cash flow from financing", ["Financing Cash Flow"]),
    "dividends_paid": ("cashflow", "Dividends paid", ["Cash Dividends Paid", "Common Stock Dividend Paid"]),
}

STATEMENTS = {"income": "Income statement", "balance": "Balance sheet", "cashflow": "Cash flow statement"}

# Line items that are per-share or counts (not converted to crore when displayed)
NON_MONETARY = {"eps_basic", "eps_diluted", "shares_diluted", "shares_outstanding"}


def items_for(statement: str) -> list[str]:
    return [k for k, (st, _, _) in LINE_ITEMS.items() if st == statement]


def label(key: str) -> str:
    return LINE_ITEMS[key][1] if key in LINE_ITEMS else key


def statement_of(key: str) -> str | None:
    return LINE_ITEMS[key][0] if key in LINE_ITEMS else None
