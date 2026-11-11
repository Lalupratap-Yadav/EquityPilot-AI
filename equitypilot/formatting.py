"""Consistent number formatting (Indian conventions). Missing values always render as an em dash."""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from .config import CRORE

MISSING = "—"


def is_missing(x: Any) -> bool:
    if x is None:
        return True
    try:
        return math.isnan(float(x)) or math.isinf(float(x))
    except (TypeError, ValueError):
        return True


def indian_group(n: float, decimals: int = 2) -> str:
    """1234567.891 -> '12,34,567.89' (Indian digit grouping)."""
    neg = n < 0
    s = f"{abs(n):.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    out = whole + (f".{frac}" if frac else "")
    return f"-{out}" if neg else out


def inr(x: Any, decimals: int = 2) -> str:
    """Rupee amount with Indian grouping, e.g. a share price."""
    return MISSING if is_missing(x) else f"₹{indian_group(float(x), decimals)}"


def crore(x: Any, decimals: int = 0, unit: bool = True) -> str:
    """Rupee amount (in absolute INR) expressed in crore."""
    if is_missing(x):
        return MISSING
    v = float(x) / CRORE
    s = indian_group(v, decimals)
    return f"₹{s} Cr" if unit else s


def big_inr(x: Any) -> str:
    """Compact rupee figure: lakh crore for very large numbers, else crore."""
    if is_missing(x):
        return MISSING
    v = float(x)
    if abs(v) >= 1e12:  # 1 lakh crore
        return f"₹{v / 1e12:,.2f} L Cr"
    return crore(v, 0)


def pct(x: Any, decimals: int = 1, signed: bool = False) -> str:
    """x is a fraction (0.153 -> 15.3%)."""
    if is_missing(x):
        return MISSING
    v = float(x) * 100
    return f"{v:+.{decimals}f}%" if signed else f"{v:.{decimals}f}%"


def mult(x: Any, decimals: int = 1) -> str:
    return MISSING if is_missing(x) else f"{float(x):.{decimals}f}x"


def num(x: Any, decimals: int = 2) -> str:
    return MISSING if is_missing(x) else indian_group(float(x), decimals)


def fdate(d: Any, with_time: bool = False) -> str:
    if d is None or (isinstance(d, float) and math.isnan(d)):
        return MISSING
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return d
    if hasattr(d, "to_pydatetime"):
        d = d.to_pydatetime()
    if isinstance(d, datetime):
        return d.strftime("%d %b %Y, %H:%M") if with_time else d.strftime("%d %b %Y")
    if isinstance(d, date):
        return d.strftime("%d %b %Y")
    return str(d)


def ist(ts: Any) -> str:
    """Timestamps are stored in UTC; display them in Indian Standard Time."""
    if ts is None:
        return MISSING
    try:
        import pandas as pd
        t = pd.Timestamp(ts)
    except (TypeError, ValueError):
        return str(ts)
    if pd.isna(t):
        return MISSING
    t = t.tz_convert(None) if t.tzinfo else t
    return (t + pd.Timedelta(hours=5, minutes=30)).strftime("%d %b %Y, %H:%M IST")


def fiscal_label(d: Any) -> str:
    """Indian fiscal-year label for a period end date: 2025-03-31 -> FY2025."""
    if d is None:
        return MISSING
    if hasattr(d, "to_pydatetime"):
        d = d.to_pydatetime()
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    year = d.year if d.month <= 3 else d.year + 1
    if d.month == 3:
        return f"FY{year}"
    return f"FY{year} ({d.strftime('%b %Y')})"


def by_kind(x: Any, kind: str) -> str:
    """Format a value according to its metric kind (pct | x | inr | cr | days | num)."""
    if kind == "pct":
        return pct(x)
    if kind == "x":
        return mult(x)
    if kind == "inr":
        return inr(x)
    if kind == "cr":
        return crore(x)
    if kind == "days":
        return MISSING if is_missing(x) else f"{float(x):.0f} days"
    if kind == "num":
        return MISSING if is_missing(x) else (f"{float(x):.0f}" if float(x).is_integer() else f"{float(x):,.2f}")
    return MISSING if is_missing(x) else str(x)
