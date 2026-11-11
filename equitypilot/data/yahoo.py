"""Yahoo Finance provider (via the open-source `yfinance` library).

Yahoo Finance is a SECONDARY, third-party source. It is not an official NSE/BSE feed, quotes
may be delayed, and statement figures should be verified against company filings. Usage is
subject to Yahoo's terms; we cache results locally and pause between bulk requests.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .. import config
from .schema import LINE_ITEMS
from .universe import exchange_of


class ProviderError(RuntimeError):
    """Raised when the provider cannot return data (offline, symbol unknown, rate-limited...)."""


def _yf():
    if config.OFFLINE:
        raise ProviderError("Offline mode is enabled (EQUITYPILOT_OFFLINE=1).")
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("yfinance is not installed.") from exc
    return yf


def _num(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(v) else v


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def source_url(symbol: str) -> str:
    return config.YAHOO_URL.format(symbol=symbol)


def fetch_profile_and_quote(symbol: str) -> tuple[dict, dict]:
    yf = _yf()
    t = yf.Ticker(symbol)
    try:
        info = t.info or {}
    except Exception as exc:  # network / HTTP / JSON errors from the provider
        raise ProviderError(f"Could not fetch profile for {symbol}: {exc}") from exc
    name = info.get("longName") or info.get("shortName")
    if not name:
        raise ProviderError(f"No data returned for '{symbol}'. Check the symbol (NSE symbols end in .NS).")
    now = _now()
    url = source_url(symbol)
    company = {
        "symbol": symbol, "name": name, "exchange": exchange_of(symbol),
        "isin": info.get("isin") if info.get("isin") not in (None, "-") else None,
        "sector": info.get("sector"), "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"), "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"), "is_sample": False,
        "source": config.YAHOO_SOURCE, "source_url": url + "/profile", "data_type": "third_party",
        "fetched_at": now,
    }
    mkt_time = info.get("regularMarketTime")
    as_of = datetime.fromtimestamp(mkt_time, tz=timezone.utc).replace(tzinfo=None) if isinstance(mkt_time, (int, float)) else None
    quote = {
        "symbol": symbol,
        "price": _num(info.get("currentPrice") or info.get("regularMarketPrice")),
        "prev_close": _num(info.get("regularMarketPreviousClose") or info.get("previousClose")),
        "market_cap": _num(info.get("marketCap")),
        "shares_outstanding": _num(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")),
        "beta": _num(info.get("beta")),
        "week52_high": _num(info.get("fiftyTwoWeekHigh")),
        "week52_low": _num(info.get("fiftyTwoWeekLow")),
        "dividend_rate": _num(info.get("dividendRate")),
        "currency": info.get("currency") or "INR",
        "as_of": as_of, "source": config.YAHOO_SOURCE, "source_url": url,
        "data_type": "delayed", "fetched_at": now,
    }
    return company, quote


def _statement_rows(df: pd.DataFrame, statement: str, period_type: str, symbol: str,
                    currency: str = "INR") -> list[dict]:
    rows: list[dict] = []
    if df is None or df.empty:
        return rows
    now = _now()
    keys = [k for k, (st, _, _) in LINE_ITEMS.items() if st == statement]
    for col in df.columns:
        period_end = pd.Timestamp(col).date()
        for key in keys:
            value = None
            for yahoo_name in LINE_ITEMS[key][2]:
                if yahoo_name in df.index:
                    value = _num(df.at[yahoo_name, col])
                    if value is not None:
                        break
            if value is None:
                continue  # missing stays missing - never filled in
            rows.append({
                "symbol": symbol, "statement": statement, "period_end": period_end,
                "period_type": period_type,
                # Yahoo does not state the basis per figure; for Indian listings it generally
                # shows consolidated numbers, but we do not assert that.
                "basis": "unspecified", "line_item": key, "value": value, "currency": currency,
                "source": config.YAHOO_SOURCE, "source_url": source_url(symbol) + "/financials",
                "data_type": "third_party", "fetched_at": now,
            })
    return rows


def fetch_financials(symbol: str, quarterly: bool = False) -> list[dict]:
    yf = _yf()
    t = yf.Ticker(symbol)
    ptype = "quarterly" if quarterly else "annual"
    rows: list[dict] = []
    try:
        # Some Indian companies (e.g. ADR issuers) are reported by the provider in USD.
        currency = (t.info or {}).get("financialCurrency") or "INR"
        frames = {
            "income": t.quarterly_income_stmt if quarterly else t.income_stmt,
            "balance": t.quarterly_balance_sheet if quarterly else t.balance_sheet,
            "cashflow": t.quarterly_cashflow if quarterly else t.cashflow,
        }
    except Exception as exc:
        raise ProviderError(f"Could not fetch financial statements for {symbol}: {exc}") from exc
    for statement, df in frames.items():
        rows.extend(_statement_rows(df, statement, ptype, symbol, currency))
    # Yahoo reports capex as a negative number; FCF is reported directly when available.
    return rows


def fetch_prices(symbol: str, period: str = "5y") -> pd.DataFrame:
    yf = _yf()
    try:
        h = yf.Ticker(symbol).history(period=period, auto_adjust=False)
    except Exception as exc:
        raise ProviderError(f"Could not fetch prices for {symbol}: {exc}") from exc
    if h is None or h.empty:
        raise ProviderError(f"No price history returned for {symbol}.")
    h = h.reset_index()
    h["date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.date
    out = h.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    return out[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])


def fetch_index_snapshot(symbols: dict[str, str]) -> pd.DataFrame:
    """Last close / previous close for indices. Returns one row per index (missing ones skipped)."""
    yf = _yf()
    rows = []
    for sym, name in symbols.items():
        try:
            h = yf.Ticker(sym).history(period="1mo")
        except Exception:
            continue
        if h is None or len(h) < 2:
            continue
        last, prev = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
        rows.append({"symbol": sym, "name": name, "last": last, "prev": prev,
                     "change": last - prev, "change_pct": last / prev - 1,
                     "as_of": pd.Timestamp(h.index[-1]).tz_localize(None).to_pydatetime(),
                     "spark": h["Close"].tolist()})
        time.sleep(0.2)
    return pd.DataFrame(rows)


def fetch_news(symbol: str) -> list[dict]:
    """Headlines aggregated by Yahoo Finance (third-party publishers). Links point to the original article."""
    yf = _yf()
    try:
        items = yf.Ticker(symbol).news or []
    except Exception as exc:
        raise ProviderError(f"Could not fetch news for {symbol}: {exc}") from exc
    now = _now()
    out = []
    for it in items:
        c = it.get("content", it)  # newer yfinance nests fields under 'content'
        title = c.get("title")
        if not title:
            continue
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or c.get("link")
        pub = c.get("pubDate") or c.get("providerPublishTime")
        if isinstance(pub, (int, float)):
            pub_dt = datetime.fromtimestamp(pub, tz=timezone.utc).replace(tzinfo=None)
        else:
            try:
                pub_dt = pd.Timestamp(pub).tz_localize(None).to_pydatetime() if pub else None
            except (TypeError, ValueError):
                pub_dt = pd.Timestamp(pub).tz_convert(None).to_pydatetime() if pub else None
        publisher = (c.get("provider") or {}).get("displayName") or c.get("publisher")
        out.append({"symbol": symbol, "date": pub_dt, "title": title, "category": "News",
                    "publisher": publisher, "url": url,
                    "source": f"{config.YAHOO_SOURCE} news aggregator", "data_type": "third_party",
                    "fetched_at": now})
    return out
