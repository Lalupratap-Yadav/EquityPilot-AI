"""Unified data access layer used by every page.

Pattern: read from the local SQLite cache; if data is missing or stale and we are online,
fetch from the provider, store it with provenance, then read again. Provider failures never
crash a page - they are returned as messages and the cached data (if any) is still shown.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Iterable

import pandas as pd

from .. import config, db
from . import yahoo
from .schema import LINE_ITEMS
from .universe import DEFAULT_UNIVERSE, normalise_symbol

BASIS_PREFERENCE = ["consolidated", "unspecified", "standalone"]


@dataclass
class FinancialData:
    """Wide table of statement data plus provenance metadata."""
    wide: pd.DataFrame                      # index: line_item key; columns: period_end (ascending)
    period_type: str
    basis: str
    sources: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    data_types: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None

    @property
    def empty(self) -> bool:
        return self.wide.empty

    def get(self, key: str) -> pd.Series:
        """Series of a line item across periods (NaN where missing)."""
        if key in self.wide.index:
            return self.wide.loc[key].astype(float)
        return pd.Series(float("nan"), index=self.wide.columns, dtype=float)

    def latest(self, key: str) -> float | None:
        s = self.get(key).dropna()
        return float(s.iloc[-1]) if len(s) else None

    @property
    def periods(self) -> list:
        return list(self.wide.columns)


def _is_stale(ts, kind: str) -> bool:
    if ts is None or pd.isna(ts):
        return True
    return db.utcnow() - pd.Timestamp(ts).to_pydatetime() > timedelta(hours=config.FRESHNESS_HOURS[kind])


# ------------------------------------------------------------------ companies & quotes
def get_company(symbol: str) -> dict | None:
    df = db.read_df(db.select(db.companies).where(db.companies.c.symbol == symbol))
    return df.iloc[0].to_dict() if len(df) else None


def get_quote(symbol: str) -> dict | None:
    df = db.read_df(db.select(db.quotes).where(db.quotes.c.symbol == symbol))
    return df.iloc[0].to_dict() if len(df) else None


def list_companies(universe_only: bool = False) -> pd.DataFrame:
    stmt = db.select(db.companies.c.symbol, db.companies.c.name, db.companies.c.sector,
                     db.companies.c.industry, db.companies.c.is_sample, db.companies.c.in_universe,
                     db.companies.c.data_type, db.companies.c.fetched_at)
    if universe_only:
        stmt = stmt.where(db.companies.c.in_universe == True)  # noqa: E712
    return db.read_df(stmt.order_by(db.companies.c.is_sample, db.companies.c.name))


def search_companies(query: str, limit: int = 20) -> pd.DataFrame:
    df = list_companies()
    if not query:
        return df.head(limit)
    q = query.strip().lower()
    mask = df["symbol"].str.lower().str.contains(q, regex=False) | df["name"].str.lower().str.contains(q, regex=False)
    return df[mask].head(limit)


def refresh_company(symbol: str) -> tuple[bool, str]:
    """Fetch profile + quote from Yahoo. Returns (ok, message)."""
    if symbol.startswith("SAMPLE-"):
        return True, "Sample company - nothing to refresh."
    try:
        company, quote = yahoo.fetch_profile_and_quote(symbol)
    except yahoo.ProviderError as exc:
        return False, str(exc)
    existing = get_company(symbol)
    company["in_universe"] = bool(existing["in_universe"]) if existing else True
    db.upsert(db.companies, [company], ["symbol"])
    db.upsert(db.quotes, [quote], ["symbol"])
    return True, f"Profile and quote updated for {company['name']}."


def refresh_quote_if_stale(symbol: str) -> tuple[bool, str] | None:
    q = get_quote(symbol)
    if symbol.startswith("SAMPLE-") or config.OFFLINE:
        return None
    if q is None or _is_stale(q.get("fetched_at"), "quote"):
        return refresh_company(symbol)
    return None


def add_company(raw_symbol: str) -> tuple[bool, str, str]:
    """Add a company by symbol (fetches profile, quote, statements, prices). Returns (ok, msg, symbol)."""
    symbol = normalise_symbol(raw_symbol)
    ok, msg = refresh_company(symbol)
    if not ok:
        return False, msg, symbol
    msgs = [msg]
    for fn in (refresh_financials, refresh_prices):
        ok2, m2 = fn(symbol)
        msgs.append(m2)
    db.log_activity("Added company", symbol)
    return True, " ".join(msgs), symbol


def set_in_universe(symbol: str, value: bool) -> None:
    db.execute(db.update(db.companies).where(db.companies.c.symbol == symbol).values(in_universe=value))


# ------------------------------------------------------------------ financial statements
def refresh_financials(symbol: str) -> tuple[bool, str]:
    if symbol.startswith("SAMPLE-"):
        return True, "Sample company - statements are fictional and fixed."
    total = 0
    try:
        for quarterly in (False, True):
            rows = yahoo.fetch_financials(symbol, quarterly=quarterly)
            total += db.upsert(db.financials, rows, ["symbol", "statement", "period_end", "period_type", "basis", "line_item"])
    except yahoo.ProviderError as exc:
        return False, str(exc)
    if total == 0:
        return False, f"The provider returned no statement data for {symbol}."
    return True, f"{total} statement values stored for {symbol}."


def available_bases(symbol: str, period_type: str = "annual") -> list[str]:
    df = db.read_df(db.select(db.financials.c.basis).distinct()
                    .where(db.financials.c.symbol == symbol).where(db.financials.c.period_type == period_type))
    found = set(df["basis"]) if len(df) else set()
    return [b for b in BASIS_PREFERENCE if b in found]


def get_financials(symbol: str, period_type: str = "annual", basis: str | None = None,
                   auto_refresh: bool = True) -> FinancialData:
    bases = available_bases(symbol, period_type)
    if not bases and auto_refresh and not config.OFFLINE and not symbol.startswith("SAMPLE-"):
        refresh_financials(symbol)
        bases = available_bases(symbol, period_type)
    if not bases:
        return FinancialData(pd.DataFrame(), period_type, basis or "—")
    basis = basis if basis in bases else bases[0]
    df = db.read_df(db.select(db.financials).where(db.financials.c.symbol == symbol)
                    .where(db.financials.c.period_type == period_type).where(db.financials.c.basis == basis))
    if df.empty:
        return FinancialData(pd.DataFrame(), period_type, basis)
    df["period_end"] = pd.to_datetime(df["period_end"])
    wide = df.pivot_table(index="line_item", columns="period_end", values="value", aggfunc="last")
    wide = wide.reindex(columns=sorted(wide.columns))
    order = [k for k in LINE_ITEMS if k in wide.index]
    wide = wide.loc[order]
    # Drop periods that are almost empty (Yahoo sometimes returns a stub column)
    keep = [c for c in wide.columns if wide[c].notna().sum() >= 3]
    wide = wide[keep]
    return FinancialData(
        wide=wide, period_type=period_type, basis=basis,
        sources=sorted(df["source"].dropna().unique().tolist()),
        source_urls=sorted(df["source_url"].dropna().unique().tolist()),
        data_types=sorted(df["data_type"].dropna().unique().tolist()),
        fetched_at=pd.to_datetime(df["fetched_at"]).max(),
    )


def save_financial_rows(rows: list[dict]) -> int:
    return db.upsert(db.financials, rows, ["symbol", "statement", "period_end", "period_type", "basis", "line_item"])


# ------------------------------------------------------------------ prices
def refresh_prices(symbol: str, period: str = "5y") -> tuple[bool, str]:
    if symbol.startswith("SAMPLE-"):
        return True, "Sample company - prices are simulated."
    try:
        df = yahoo.fetch_prices(symbol, period)
    except yahoo.ProviderError as exc:
        return False, str(exc)
    now = db.utcnow()
    src = "Yahoo Finance (via yfinance) - end-of-day history"
    db.upsert(db.prices, [{"symbol": symbol, **r, "source": src, "data_type": "historical", "fetched_at": now}
                          for r in df.to_dict("records")], ["symbol", "date"])
    return True, f"{len(df)} daily prices stored for {symbol}."


def get_prices(symbol: str, auto_refresh: bool = True) -> pd.DataFrame:
    df = db.read_df(db.select(db.prices).where(db.prices.c.symbol == symbol).order_by(db.prices.c.date))
    stale = df.empty or _is_stale(pd.to_datetime(df["fetched_at"]).max(), "prices")
    if stale and auto_refresh and not config.OFFLINE and not symbol.startswith("SAMPLE-"):
        ok, _ = refresh_prices(symbol)
        if ok:
            df = db.read_df(db.select(db.prices).where(db.prices.c.symbol == symbol).order_by(db.prices.c.date))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def save_prices(symbol: str, df: pd.DataFrame, source: str, data_type: str = "official_upload") -> int:
    now = db.utcnow()
    recs = []
    for r in df.to_dict("records"):
        recs.append({"symbol": symbol, "date": pd.Timestamp(r["date"]).date(),
                     "open": r.get("open"), "high": r.get("high"), "low": r.get("low"),
                     "close": r["close"], "volume": r.get("volume"), "source": source,
                     "data_type": data_type, "fetched_at": now})
    return db.upsert(db.prices, recs, ["symbol", "date"])


# ------------------------------------------------------------------ peers, segments, shareholding
def get_peers(symbol: str, limit: int = 6) -> list[str]:
    df = db.read_df(db.select(db.competitors.c.peer_symbol).where(db.competitors.c.symbol == symbol))
    peers = df["peer_symbol"].tolist() if len(df) else []
    comp = get_company(symbol)
    if comp and len(peers) < limit:
        allc = list_companies()
        allc = allc[(allc["symbol"] != symbol) & (allc["is_sample"] == bool(comp["is_sample"]))]
        same_ind = allc[allc["industry"] == comp.get("industry")]["symbol"].tolist()
        same_sec = allc[allc["sector"] == comp.get("sector")]["symbol"].tolist()
        for s in same_ind + same_sec:
            if s not in peers:
                peers.append(s)
    return peers[:limit]


def set_peers(symbol: str, peer_symbols: Iterable[str]) -> None:
    db.execute(db.delete(db.competitors).where(db.competitors.c.symbol == symbol))
    rows = [{"symbol": symbol, "peer_symbol": p, "note": "User-selected"} for p in peer_symbols if p != symbol]
    if rows:
        db.execute(db.insert(db.competitors), rows)


def get_segments(symbol: str) -> pd.DataFrame:
    return db.read_df(db.select(db.segments).where(db.segments.c.symbol == symbol).order_by(db.segments.c.period))


def get_shareholding(symbol: str) -> pd.DataFrame:
    return db.read_df(db.select(db.shareholding).where(db.shareholding.c.symbol == symbol)
                      .order_by(db.shareholding.c.period))


# ------------------------------------------------------------------ news & disclosures
def refresh_news(symbol: str) -> tuple[bool, str]:
    if symbol.startswith("SAMPLE-"):
        return True, "Sample company - no real news exists."
    try:
        rows = yahoo.fetch_news(symbol)
    except yahoo.ProviderError as exc:
        return False, str(exc)
    if not rows:
        return True, "The provider returned no recent headlines."
    db.upsert(db.disclosures, rows, ["symbol", "title", "url"])
    return True, f"{len(rows)} headlines fetched."


def get_disclosures(symbol: str | None = None, limit: int = 200) -> pd.DataFrame:
    stmt = db.select(db.disclosures)
    if symbol:
        stmt = stmt.where(db.disclosures.c.symbol == symbol)
    df = db.read_df(stmt.order_by(db.disclosures.c.date.desc()).limit(limit))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def add_disclosure(symbol: str, date, title: str, category: str, url: str | None, publisher: str) -> None:
    db.upsert(db.disclosures, [{
        "symbol": symbol, "date": pd.Timestamp(date).to_pydatetime(), "title": title.strip(),
        "category": category, "publisher": publisher or "User entry", "url": url or None,
        "source": "Entered by user from official source" if url else "Entered by user",
        "data_type": "user_entered", "fetched_at": db.utcnow()}], ["symbol", "title", "url"])


# ------------------------------------------------------------------ watchlist & holdings
def get_watchlist() -> list[str]:
    return db.read_df(db.select(db.watchlist).order_by(db.watchlist.c.added_at))["symbol"].tolist()


def add_to_watchlist(symbol: str) -> None:
    db.upsert(db.watchlist, [{"symbol": symbol, "added_at": db.utcnow()}], ["symbol"])


def remove_from_watchlist(symbol: str) -> None:
    db.execute(db.delete(db.watchlist).where(db.watchlist.c.symbol == symbol))


def get_holdings() -> pd.DataFrame:
    return db.read_df(db.select(db.holdings).order_by(db.holdings.c.id))


def replace_holdings(df: pd.DataFrame) -> int:
    db.execute(db.delete(db.holdings))
    recs = []
    for r in df.to_dict("records"):
        if not r.get("symbol") or pd.isna(r.get("quantity")) or pd.isna(r.get("avg_cost")):
            continue
        bd = r.get("buy_date")
        recs.append({"symbol": str(r["symbol"]).strip().upper(), "quantity": float(r["quantity"]),
                     "avg_cost": float(r["avg_cost"]),
                     "buy_date": pd.Timestamp(bd).date() if bd is not None and not pd.isna(bd) else None,
                     "notes": r.get("notes") or None})
    if recs:
        db.execute(db.insert(db.holdings), recs)
    return len(recs)


# ------------------------------------------------------------------ bulk refresh
def refresh_universe(symbols: list[str] | None = None,
                     progress: Callable[[float, str], None] | None = None,
                     pause: float = 0.6) -> list[dict]:
    """Fetch profile, quote, statements and prices for many companies, politely (paused)."""
    symbols = symbols or DEFAULT_UNIVERSE
    results = []
    for i, sym in enumerate(symbols):
        if progress:
            progress(i / len(symbols), f"Fetching {sym} ({i + 1}/{len(symbols)})")
        ok, msg = refresh_company(sym)
        row = {"symbol": sym, "profile": "OK" if ok else msg}
        if ok:
            okf, mf = refresh_financials(sym)
            okp, mp = refresh_prices(sym)
            row.update(financials="OK" if okf else mf, prices="OK" if okp else mp)
        results.append(row)
        time.sleep(pause)
    if progress:
        progress(1.0, "Done")
    db.log_activity("Refreshed universe", f"{len(symbols)} companies")
    return results


def data_status() -> pd.DataFrame:
    """One row per company: what is cached and when it was fetched."""
    comp = list_companies()
    if comp.empty:
        return comp
    fin = db.read_df(db.select(db.financials.c.symbol, db.financials.c.period_end, db.financials.c.fetched_at,
                               db.financials.c.period_type))
    px = db.read_df(db.select(db.prices.c.symbol, db.prices.c.date))
    q = db.read_df(db.select(db.quotes.c.symbol, db.quotes.c.fetched_at))
    out = comp[["symbol", "name", "is_sample", "in_universe", "data_type"]].copy()
    if not fin.empty:
        ann = fin[fin["period_type"] == "annual"].groupby("symbol").agg(
            years=("period_end", "nunique"), latest_fy=("period_end", "max"), fin_fetched=("fetched_at", "max"))
        out = out.merge(ann, left_on="symbol", right_index=True, how="left")
    if not px.empty:
        p = px.groupby("symbol").agg(price_days=("date", "count"), last_price_date=("date", "max"))
        out = out.merge(p, left_on="symbol", right_index=True, how="left")
    if not q.empty:
        out = out.merge(q.rename(columns={"fetched_at": "quote_fetched"}), on="symbol", how="left")
    return out
