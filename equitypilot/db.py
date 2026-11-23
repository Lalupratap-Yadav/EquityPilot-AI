"""SQLite database (SQLAlchemy Core).

Every data table carries provenance columns (source, source_url, data_type, fetched_at)
so the UI can always show where a number came from and how fresh it is.
"""
from __future__ import annotations

import json
import os
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
    Column("user_id", Integer, index=True),               # NULL = legacy/shared document
)

bank_metrics = Table(
    # Bank / NBFC metrics entered from quarterly disclosures (not available from the market-data provider)
    "bank_metrics", metadata,
    Column("symbol", String, primary_key=True),
    Column("period", String, primary_key=True),           # quarter end, e.g. 2025-09-30
    Column("metric", String, primary_key=True),           # key from analytics.bank.BANK_METRICS
    Column("value", Float),                               # percent value, e.g. 1.35 for 1.35%
    Column("source", String), Column("source_url", String),
    Column("data_type", String), Column("fetched_at", DateTime),
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
    Column("user_id", Integer, index=True),               # NULL = legacy single-user (Streamlit) data
)

# ================================================================ v2 platform tables
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, unique=True),               # NULL for guests
    Column("display_name", String),
    Column("password_hash", String),                       # scrypt$salt$hash; NULL for guests
    Column("is_guest", Boolean, default=True),
    Column("show_on_leaderboard", Boolean, default=False),
    Column("created_at", DateTime),
    Column("last_seen", DateTime),
)

user_settings = Table(
    "user_settings", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("key", String, primary_key=True),
    Column("value", Text),
)

watchlists = Table(
    "watchlists", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("created_at", DateTime),
)

watchlist_items = Table(
    "watchlist_items", metadata,
    Column("watchlist_id", Integer, primary_key=True),
    Column("symbol", String, primary_key=True),
    Column("note", Text),
    Column("added_at", DateTime),
)

alerts = Table(
    "alerts", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("symbol", String, nullable=False),
    Column("direction", String, nullable=False),          # above / below
    Column("price", Float, nullable=False),
    Column("note", String),
    Column("active", Boolean, default=True),
    Column("created_at", DateTime),
    Column("triggered_at", DateTime),
    Column("triggered_price", Float),
)

notifications = Table(
    "notifications", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("ts", DateTime),
    Column("kind", String),
    Column("title", String),
    Column("body", Text),
    Column("link", String),
    Column("read", Boolean, default=False),
)

recent_views = Table(
    "recent_views", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("symbol", String, primary_key=True),
    Column("ts", DateTime),
)

recent_searches = Table(
    "recent_searches", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("query", String, primary_key=True),
    Column("ts", DateTime),
)

saved_news = Table(
    "saved_news", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("url", String, primary_key=True),
    Column("title", Text, nullable=False),
    Column("source", String),
    Column("published", DateTime),
    Column("symbol", String),
    Column("saved_at", DateTime),
)

saved_screens = Table(
    "saved_screens", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("filters", Text),                               # JSON
    Column("created_at", DateTime),
)

fav_industries = Table(
    "fav_industries", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("industry", String, primary_key=True),
)

paper_accounts = Table(
    "paper_accounts", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("cash", Float, nullable=False),
    Column("initial", Float, nullable=False),
    Column("started_at", DateTime),
    Column("resets", Integer, default=0),
)

paper_trades = Table(
    "paper_trades", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("ts", DateTime, nullable=False),
    Column("kind", String, nullable=False),                # BUY / SELL / DIVIDEND / SPLIT
    Column("symbol", String, nullable=False),
    Column("qty", Float, nullable=False),
    Column("price", Float),
    Column("amount", Float),                               # cash impact (+ in, - out)
    Column("cash_after", Float),
    Column("price_time", DateTime),                        # timestamp of the quote used
    Column("price_type", String),                          # delayed / live / sample
    Column("note", String),
)

corporate_actions = Table(
    "corporate_actions", metadata,
    Column("symbol", String, primary_key=True),
    Column("date", Date, primary_key=True),
    Column("type", String, primary_key=True),              # dividend / split
    Column("value", Float),                                # ₹ per share / split ratio (new shares per old)
    Column("source", String),
)

securities = Table(
    "securities", metadata,
    Column("isin", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("nse_symbol", String, index=True),
    Column("bse_symbol", String),
    Column("series", String),
    Column("listing_date", Date),
    Column("avg_mcap_cr", Float),                          # AMFI 6-month average, ₹ crore
    Column("mcap_rank", Integer),
    Column("category", String),                            # Large Cap / Mid Cap / Small Cap (AMFI)
    Column("source", String),
    Column("as_of", String),
)

news_items = Table(
    "news_items", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("feed", String, nullable=False),                # nse_announcements / nse_results / rbi / sebi / yahoo_market ...
    Column("category", String),
    Column("title", Text, nullable=False),
    Column("summary", Text),
    Column("url", Text),
    Column("published", DateTime),
    Column("source", String),
    Column("symbol", String, index=True),
    Column("fetched_at", DateTime),
    UniqueConstraint("feed", "url", "title", name="uq_news"),
)

doc_chunks = Table(
    "doc_chunks", metadata,
    Column("doc_id", Integer, primary_key=True),
    Column("chunk_no", Integer, primary_key=True),
    Column("page", Integer),
    Column("text", Text),
)

# columns added to pre-existing tables (lightweight migration for existing SQLite files)
_ADDED_COLUMNS = {"holdings": [("user_id", "INTEGER")], "documents": [("user_id", "INTEGER")]}

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


def _migrate(eng: Engine) -> None:
    """Add columns introduced after a database file was created (SQLite and PostgreSQL)."""
    from sqlalchemy import inspect, text
    insp = inspect(eng)
    with eng.begin() as conn:
        for table, cols in _ADDED_COLUMNS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, sqltype in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}"))
        # indexes added after a database was created (CREATE INDEX IF NOT EXISTS works on SQLite and PostgreSQL)
        for name, table, cols in _ADDED_INDEXES:
            if insp.has_table(table):
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))


_ADDED_INDEXES = [
    ("ix_news_feed_published", "news_items", "feed, published"),
    ("ix_news_published", "news_items", "published"),
    ("ix_disclosures_date", "disclosures", "date"),
]


@lru_cache(maxsize=4)
def _engine_for(url: str) -> Engine:
    if url.startswith("sqlite"):
        eng = create_engine(url, future=True, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(eng, "connect")
        def _pragmas(dbapi_conn, _):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    else:  # e.g. postgresql+psycopg://user:pass@host/db  (set EQUITYPILOT_DATABASE_URL)
        eng = create_engine(url, future=True, pool_pre_ping=True)
    metadata.create_all(eng)
    _migrate(eng)
    return eng


_DIRS_READY: set[str] = set()


def get_engine() -> Engine:
    url = os.environ.get("EQUITYPILOT_DATABASE_URL") or f"sqlite:///{config.DB_PATH}"
    if url not in _DIRS_READY:        # create the data folders once, not on every query (3 mkdir calls each time,
        config.ensure_dirs()          # which on Windows was the largest single cost in a profile of the server)
        _DIRS_READY.add(url)
    return _engine_for(url)


# ---------------------------------------------------------------- generic helpers
def read_df(stmt) -> pd.DataFrame:
    with get_engine().connect() as conn:
        res = conn.execute(stmt)
        return pd.DataFrame(res.fetchall(), columns=list(res.keys()))


def upsert(table: Table, rows: Iterable[dict], conflict_cols: list[str], update: bool = True) -> int:
    """Insert rows; on conflict update the other columns (or keep the existing row when update=False)."""
    rows = [r for r in rows]
    if not rows:
        return 0
    eng = get_engine()
    if eng.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        dialect_insert = sqlite_insert
    stmt = dialect_insert(table)
    update_cols = {c.name: stmt.excluded[c.name] for c in table.columns
                   if update and c.name not in conflict_cols and c.name != "id"}
    stmt = (stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols) if update_cols
            else stmt.on_conflict_do_nothing(index_elements=conflict_cols))
    with eng.begin() as conn:
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


def get_settings(keys: list[str]) -> dict[str, Any]:
    """Several settings in one query ({key: value}; missing keys map to None)."""
    out: dict[str, Any] = {k: None for k in keys}
    if not keys:
        return out
    with get_engine().connect() as conn:
        rows = conn.execute(select(settings.c.key, settings.c.value).where(settings.c.key.in_(list(keys)))).all()
    for k, v in rows:
        try:
            out[k] = json.loads(v)
        except (TypeError, ValueError):
            out[k] = v
    return out


def set_setting(key: str, value: Any) -> None:
    upsert(settings, [{"key": key, "value": json.dumps(value)}], ["key"])


def log_activity(action: str, detail: str = "") -> None:
    execute(insert(activity).values(ts=utcnow(), action=action, detail=detail[:300]))


def recent_activity(limit: int = 10) -> pd.DataFrame:
    return read_df(select(activity).order_by(activity.c.id.desc()).limit(limit))


__all__ = [
    "metadata", "companies", "quotes", "financials", "prices", "segments", "shareholding",
    "competitors", "disclosures", "documents", "bank_metrics", "watchlist", "holdings", "activity", "settings",
    "get_engine", "read_df", "upsert", "execute", "get_setting", "set_setting", "log_activity",
    "recent_activity", "utcnow", "select", "insert", "update", "delete",
]
