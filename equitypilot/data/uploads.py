"""Upload parsing: financial statements (CSV/Excel), daily prices (CSV/Excel), PDF documents.

Workflow: parse -> show to user for review/correction -> save with source reference.
Nothing is saved without the user's review.
"""
from __future__ import annotations

import io
import re
from datetime import date

import pandas as pd

from .. import db
from .schema import LINE_ITEMS, label

UNITS = {"₹ crore": 1e7, "₹ lakh": 1e5, "₹ million": 1e6, "₹ (absolute)": 1.0}

# Common names used in Indian financial statements -> canonical key
ALIASES = {
    "revenue from operations": "revenue", "total revenue from operations": "revenue", "net sales": "revenue",
    "sales": "revenue", "revenue": "revenue", "total income from operations": "revenue",
    "cost of materials consumed": "cogs", "cost of goods sold": "cogs", "cost of revenue": "cogs",
    "ebitda": "ebitda", "operating profit": "ebit", "ebit": "ebit", "depreciation and amortisation expense": "depreciation",
    "depreciation and amortization": "depreciation", "depreciation": "depreciation", "finance costs": "interest_expense",
    "finance cost": "interest_expense", "interest": "interest_expense", "profit before tax": "pretax_income", "pbt": "pretax_income",
    "tax expense": "tax", "total tax expense": "tax", "profit after tax": "net_income", "pat": "net_income",
    "net profit": "net_income", "profit for the year": "net_income", "profit for the period": "net_income",
    "profit attributable to owners": "net_income", "basic eps": "eps_basic", "diluted eps": "eps_diluted",
    "total assets": "total_assets", "total current assets": "current_assets", "current assets": "current_assets",
    "cash and cash equivalents": "cash", "trade receivables": "receivables", "inventories": "inventory",
    "property, plant and equipment": "net_ppe", "total liabilities": "total_liabilities",
    "total current liabilities": "current_liabilities", "current liabilities": "current_liabilities",
    "borrowings": "total_debt", "total borrowings": "total_debt", "total debt": "total_debt",
    "total equity": "total_equity", "equity attributable to owners": "total_equity", "net worth": "total_equity",
    "shareholders' funds": "total_equity", "other equity": "retained_earnings", "reserves and surplus": "retained_earnings",
    "non-controlling interest": "minority_interest", "non controlling interests": "minority_interest",
    "net cash from operating activities": "cfo", "net cash generated from operating activities": "cfo",
    "cash flow from operations": "cfo", "purchase of property, plant and equipment": "capex", "capital expenditure": "capex",
    "net cash used in investing activities": "cfi", "net cash used in financing activities": "cff",
    "dividends paid": "dividends_paid", "free cash flow": "fcf",
}
COUNT_ITEMS = {"shares_outstanding", "shares_diluted"}
PER_SHARE = {"eps_basic", "eps_diluted"}
OUTFLOWS = {"capex", "dividends_paid"}


def match_line_item(text: str) -> str | None:
    t = re.sub(r"\s+", " ", str(text).strip().lower())
    t = re.sub(r"[\(\)\[\]]", "", t).strip(" :-")
    if t in LINE_ITEMS:
        return t
    for key, (_, lbl, _) in LINE_ITEMS.items():
        if t == lbl.lower():
            return key
    return ALIASES.get(t)


def parse_period(header: str) -> date | None:
    """'FY2025', 'FY25', 'Mar-25', 'Mar 2025', '2025-03-31', '31-03-2025', 'Q2FY26'."""
    h = str(header).strip()
    m = re.fullmatch(r"(?i)fy\s*'?(\d{2}|\d{4})", h)
    if m:
        y = int(m.group(1))
        y = 2000 + y if y < 100 else y
        return date(y, 3, 31)
    m = re.fullmatch(r"(?i)q([1-4])\s*fy\s*'?(\d{2}|\d{4})", h)
    if m:
        q, y = int(m.group(1)), int(m.group(2))
        y = 2000 + y if y < 100 else y
        return {1: date(y - 1, 6, 30), 2: date(y - 1, 9, 30), 3: date(y - 1, 12, 31), 4: date(y, 3, 31)}[q]
    try:
        iso = re.fullmatch(r"\d{4}-\d{2}-\d{2}", h) is not None
        ts = pd.to_datetime(h, dayfirst=not iso)
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    if re.fullmatch(r"(?i)[a-z]{3}[- ]?'?\d{2,4}", h):     # month-year -> month end
        ts = ts + pd.offsets.MonthEnd(0)
    return ts.date()


def _clean_number(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("₹", "")
    if s in ("", "-", "—", "NA", "N/A", "nil", "Nil"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def read_table(data: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data), header=0)
    text = data.decode("utf-8-sig", errors="replace")
    return pd.read_csv(io.StringIO(text), sep=None, engine="python")


def statement_template(periods: list[str] | None = None) -> pd.DataFrame:
    periods = periods or ["FY2026", "FY2025", "FY2024", "FY2023", "FY2022"]
    df = pd.DataFrame({"line_item": list(LINE_ITEMS), "label": [label(k) for k in LINE_ITEMS]})
    for p in periods:
        df[p] = None
    return df


def parse_statements(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (wide table index=line_item key, columns=period_end dates, values as entered) + warnings."""
    warnings: list[str] = []
    if df.empty:
        return pd.DataFrame(), ["The file is empty."]
    label_col = "line_item" if "line_item" in df.columns else df.columns[0]
    period_cols = {}
    for c in df.columns:
        if c in (label_col, "label"):
            continue
        p = parse_period(c)
        if p:
            period_cols[c] = p
        else:
            warnings.append(f"Column '{c}' ignored - could not read it as a period (use FY2025, Mar-2025 or 2025-03-31).")
    if not period_cols:
        return pd.DataFrame(), warnings + ["No period columns found."]
    rows, unmatched = {}, []
    for _, r in df.iterrows():
        key = match_line_item(r[label_col])
        if key is None and "label" in df.columns:
            key = match_line_item(r["label"])
        if key is None:
            if str(r[label_col]).strip() and str(r[label_col]) != "nan":
                unmatched.append(str(r[label_col]))
            continue
        vals = {p: _clean_number(r[c]) for c, p in period_cols.items()}
        if any(v is not None for v in vals.values()):
            rows[key] = vals
    if unmatched:
        warnings.append(f"{len(unmatched)} row(s) not recognised and skipped: " + ", ".join(unmatched[:8]) +
                        ("…" if len(unmatched) > 8 else "") + ". Rename them to a template line item to include them.")
    wide = pd.DataFrame(rows).T
    if not wide.empty:
        wide = wide.reindex(columns=sorted(wide.columns))
    return wide, warnings


def to_rows(wide: pd.DataFrame, symbol: str, basis: str, period_type: str, unit: float,
            source: str, source_url: str | None) -> list[dict]:
    """Convert a reviewed wide table (values in `unit`) to DB rows in absolute INR."""
    now = db.utcnow()
    out = []
    for key, row in wide.iterrows():
        if key not in LINE_ITEMS:
            continue
        for period, v in row.items():
            if v is None or pd.isna(v):
                continue
            mult = 1.0 if key in PER_SHARE else (1.0 if key in COUNT_ITEMS else unit)
            v = float(v)
            if key in OUTFLOWS:  # cash outflows are stored as negatives regardless of how they were entered
                v = -abs(v)
            out.append({"symbol": symbol, "statement": LINE_ITEMS[key][0], "period_end": pd.Timestamp(period).date(),
                        "period_type": period_type, "basis": basis, "line_item": key, "value": v * mult,
                        "currency": "INR", "source": source, "source_url": source_url or None,
                        "data_type": "official_upload", "fetched_at": now})
    return out


# ------------------------------------------------------------------ prices
PRICE_COLS = {
    "date": ["date", "trade date", "timestamp"],
    "open": ["open", "open price", "open_price"],
    "high": ["high", "high price", "high_price"],
    "low": ["low", "low price", "low_price"],
    "close": ["close", "close price", "close_price", "closing price", "adj close", "last price", "ltp"],
    "volume": ["volume", "total traded quantity", "no.of shares", "no. of shares", "shares traded", "qty"],
}


def parse_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Normalise NSE/BSE/Yahoo style daily price exports."""
    cols = {re.sub(r"\s+", " ", str(c).strip().lower()): c for c in df.columns}
    mapping, warnings = {}, []
    for std, cands in PRICE_COLS.items():
        for cand in cands:
            if cand in cols:
                mapping[std] = cols[cand]
                break
    if "date" not in mapping or "close" not in mapping:
        return pd.DataFrame(), ["Need at least 'Date' and 'Close' columns. Found: " + ", ".join(map(str, df.columns))]
    out = pd.DataFrame({"date": pd.to_datetime(df[mapping["date"]].astype(str).str.strip(), dayfirst=True, errors="coerce")})
    for std in ("open", "high", "low", "close", "volume"):
        out[std] = df[mapping[std]].map(_clean_number) if std in mapping else None
    bad = int(out["date"].isna().sum() + out["close"].isna().sum())
    if bad:
        warnings.append(f"{bad} row(s) with unreadable date or close were dropped.")
    out = out.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date", keep="last")
    for std in ("open", "high", "low"):
        out[std] = out[std].fillna(out["close"])
    return out.reset_index(drop=True), warnings


# ------------------------------------------------------------------ PDF documents
def extract_pdf(data: bytes, max_pages: int = 600) -> dict:
    """Extract text per page and tables (pdfplumber). Scanned (image-only) PDFs yield no text."""
    import pdfplumber
    pages, tables = [], []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages[:max_pages], start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # malformed page - keep going
                text = ""
            pages.append({"page": i, "text": text})
            if len(tables) < 60:
                try:
                    for t in page.extract_tables() or []:
                        if t and len(t) > 1 and len(t[0]) > 1:
                            tables.append({"page": i, "rows": t})
                except Exception:
                    pass
    chars = sum(len(p["text"]) for p in pages)
    return {"n_pages": n, "pages": pages, "tables": tables, "truncated": n > max_pages,
            "scanned": chars < 10 * max(1, min(n, max_pages))}  # ~no text layer


def pages_to_text(pages: list[dict]) -> str:
    return "\n".join(f"[[page {p['page']}]]\n{p['text']}" for p in pages)


def text_to_pages(text: str) -> list[dict]:
    parts = re.split(r"\[\[page (\d+)\]\]\n", text or "")
    return [{"page": int(parts[i]), "text": parts[i + 1]} for i in range(1, len(parts) - 1, 2)]


def search_pages(pages: list[dict], query: str, window: int = 220, limit: int = 30) -> list[dict]:
    q = query.strip().lower()
    hits = []
    if not q:
        return hits
    for p in pages:
        low = p["text"].lower()
        start = 0
        while (i := low.find(q, start)) >= 0 and len(hits) < limit:
            s, e = max(0, i - window), min(len(low), i + len(q) + window)
            hits.append({"page": p["page"], "snippet": ("…" if s else "") + p["text"][s:e].replace("\n", " ") + ("…" if e < len(low) else "")})
            start = i + len(q)
    return hits


def save_document(symbol: str | None, filename: str, doc_type: str, period: str, source_url: str | None,
                  extracted: dict) -> int:
    res = db.execute(db.insert(db.documents).values(
        symbol=symbol, filename=filename, doc_type=doc_type, period=period, source_url=source_url or None,
        pages=extracted["n_pages"], text=pages_to_text(extracted["pages"]), uploaded_at=db.utcnow()))
    db.log_activity("Uploaded document", f"{filename} ({symbol or 'general'})")
    return int(res.inserted_primary_key[0])


def list_documents(symbol: str | None = None) -> pd.DataFrame:
    stmt = db.select(db.documents.c.id, db.documents.c.symbol, db.documents.c.filename, db.documents.c.doc_type,
                     db.documents.c.period, db.documents.c.pages, db.documents.c.source_url, db.documents.c.uploaded_at)
    if symbol:
        stmt = stmt.where(db.documents.c.symbol == symbol)
    return db.read_df(stmt.order_by(db.documents.c.uploaded_at.desc()))


def get_document(doc_id: int) -> dict | None:
    df = db.read_df(db.select(db.documents).where(db.documents.c.id == doc_id))
    return df.iloc[0].to_dict() if len(df) else None


def delete_document(doc_id: int) -> None:
    db.execute(db.delete(db.documents).where(db.documents.c.id == doc_id))
