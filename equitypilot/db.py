"""SQLite database (SQLAlchemy Core).

Every data table carries provenance columns (source, source_url, data_type, fetched_at)
so the UI can always show where a number came from and how fresh it is.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
    UniqueConstraint, create_engine, delete, event, insert, select, update,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from . import config

metadata = MetaData()

companies = Table(
    "companies", metadata,
    Column("symbol", String, primary_key=True),          # e.g. RELIANCE.NS or SAMPLE-ALPHA
    Column("name", String, nullable=False),
    Column("exchange", String),                          # NSE / BSE
    Column("isin", String),
    Column("sector", String),
    Column("industry", String),
    Column("description", Text),
    Column("website", String),
    Column("employees", Integer),
    Column("is_sample", Boolean, default=False),
    Column("in_universe", Boolean, default=True),
    Column("source", String),
    Column("source_url", String),
    Column("data_type", String),
    Column("fetched_at", DateTime),
)

quotes = Table(
    "quotes", metadata,
    Column("symbol", String, primary_key=True),
    Column("price", Float),
    Column("prev_close", Float),
    Column("market_cap", Float),
    Column("shares_outstanding", Float),
    Column("beta", Float),
    Column("week52_high", Float),
    Column("week52_low", Float),
    Column("dividend_rate", Float),
    Column("currency", String),
    Column("as_of", DateTime),                            # market timestamp from provider
    Column("source", String),
    Column("source_url", String),
    Column("data_type", String),
    Column("fetched_at", DateTime),
)

financials = Table(
    "financials", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, nullable=False, index=True),
    Column("statement", String, nullable=False),          # income / balance / cashflow
    Column("period_end", Date, nullable=False),
    Column("period_type", String, nullable=False),        # annual / quarterly
    Column("basis", String, nullable=False),              # consolidated / standalone / unspecified
    Column("line_item", String, nullable=False),          # canonical key, see data/schema in repository
    Column("value", Float),
    Column("currency", String, default="INR"),
    Column("source", String),
    Column("source_url", String),
    Column("data_type", String),
    Column("fetched_at", DateTime),
    UniqueConstraint("symbol", "statement", "period_end", "period_type", "basis", "line_item",
                     name="uq_fin"),
)

prices = Table(
    "prices", metadata,
    Column("symbol", String, primary_key=True),
    Column("date", Date, primary_key=True),
    Column("open", Float), Column("high", Float), Column("low", Float),
    Column("close", Float), Column("volume", Float),
    Column("source", String),
    Column("data_type", String),
    Column("fetched_at", DateTime),
)

segments = Table(
    "segments", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, nullable=False, index=True),
    Column("period", String, nullable=False),             # e.g. FY2025
    Column("segment", String, nullable=False),
    Column("revenue", Float),                              # INR
    Column("ebit", Float),
    Column("basis", String),
    Column("source", String), Column("source_url", String),
    Column("data_type", String), Column("fetched_at", DateTime),
)

shareholding = Table(
    "shareholding", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, nullable=False, index=True),
    Column("period", String, nullable=False),             # quarter end e.g. 2025-09-30
    Column("category", String, nullable=False),           # Promoter & Promoter Group, FII/FPI, DII, Public, Others
    Column("pct", Float),
    Column("pledged_pct", Float),
    Column("source", String), Column("source_url", String),
    Column("data_type", String), Column("fetched_at", DateTime),
)

competitors = Table(
    "competitors", metadata,
    Column("symbol", String, primary_key=True),
    Column("peer_symbol", String, primary_key=True),
    Column("note", String),
)

disclosures = Table(
    "disclosures", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, index=True),
    Column("date", DateTime),
    Column("title", Text, nullable=False),
    Column("category", String),                            # Results / Board Meeting / News / ...
    Column("publisher", String),
    Column("url", Text),
    Column("source", String),
    Column("data_type", String),
    Column("fetched_at", DateTime),
    UniqueConstraint("symbol", "title", "url", name="uq_disc"),
)

documents = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, index=True),
    Column("filename", String, nullable=False),
    Column("doc_type", String),                            # Annual Report / Quarterly Results / ...
    Column("period", String),
    Column("source_url", Text),
    Column("pages", Integer),
    Column("text", Text),
    Column("uploaded_at", DateTime),
)

watchlist = Table(
    "watchlist", metadata,
    Column("symbol", String, primary_key=True),
    Column("added_at", DateTime),
)

holdings = Table(
    "holdings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, nullable=False),
    Column("quantity", Float, nullable=False),
    Column("avg_cost", Float, nullable=False),
    Column("buy_date", Date),
    Column("notes", String),
)

activity = Table(
    "activity", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", DateTime),
    Column("action", String),
    Column("detail", String),
)

settings = Table(
    "settings", metadata,
    Column("key", String, primary_key=True),
    Column("value", Text),
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@lru_cache(maxsize=4)
def _engine_for(path: str) -> Engine:
    eng = create_engine(f"sqlite:///{path}", future=True)

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    metadata.create_all(eng)
    return eng


def get_engine() -> Engine:
    config.ensure_dirs()
    return _engine_for(str(config.DB_PATH))


# ---------------------------------------------------------------- generic helpers
def read_df(stmt) -> pd.DataFrame:
    with get_engine().connect() as conn:
        res = conn.execute(stmt)
        return pd.DataFrame(res.fetchall(), columns=list(res.keys()))


def upsert(table: Table, rows: Iterable[dict], conflict_cols: list[str]) -> int:
    rows = [r for r in rows]
    if not rows:
        return 0
    stmt = sqlite_insert(table)
    update_cols = {c.name: stmt.excluded[c.name] for c in table.columns
                   if c.name not in conflict_cols and c.name != "id"}
    stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    with get_engine().begin() as conn:
        # chunk to stay below SQLite's variable limit
        for i in range(0, len(rows), 200):
            conn.execute(stmt, rows[i:i + 200])
    return len(rows)


def execute(stmt, params: Any = None) -> Any:
    with get_engine().begin() as conn:
        return conn.execute(stmt, params) if params is not None else conn.execute(stmt)


# ---------------------------------------------------------------- settings & activity
def get_setting(key: str, default: Any = None) -> Any:
    with get_engine().connect() as conn:
        row = conn.execute(select(settings.c.value).where(settings.c.key == key)).first()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except (TypeError, ValueError):
        return row[0]


def set_setting(key: str, value: Any) -> None:
    upsert(settings, [{"key": key, "value": json.dumps(value)}], ["key"])


def log_activity(action: str, detail: str = "") -> None:
    execute(insert(activity).values(ts=utcnow(), action=action, detail=detail[:300]))


def recent_activity(limit: int = 10) -> pd.DataFrame:
    return read_df(select(activity).order_by(activity.c.id.desc()).limit(limit))


__all__ = [
    "metadata", "companies", "quotes", "financials", "prices", "segments", "shareholding",
    "competitors", "disclosures", "documents", "watchlist", "holdings", "activity", "settings",
    "get_engine", "read_df", "upsert", "execute", "get_setting", "set_setting", "log_activity",
    "recent_activity", "utcnow", "select", "insert", "update", "delete",
]
