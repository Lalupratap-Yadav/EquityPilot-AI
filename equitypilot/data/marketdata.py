"""Market-data provider layer.

A provider returns quotes and price bars. The default is Yahoo Finance (via yfinance), which is
DELAYED (typically ~15 minutes for NSE) - it is never presented as live. A licensed/broker
real-time feed can be added by implementing `MarketDataProvider` (see docs/MARKET_DATA.md);
the API and WebSocket layer label every quote with its provider status.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from .. import config, db

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

# chart ranges -> (yfinance period, interval, label of the data)
RANGES = {
    "1D": ("1d", "5m"), "5D": ("5d", "15m"), "1M": ("1mo", "1h"), "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"), "5Y": ("5y", "1wk"), "MAX": ("max", "1mo"),
}


@dataclass
class Quote:
    symbol: str
    price: float | None
    prev_close: float | None
    change: float | None
    change_pct: float | None
    volume: float | None
    time: str | None                 # ISO UTC timestamp of the last trade/bar used
    status: str                      # live | delayed | close | sample | unavailable
    source: str

    def dict(self) -> dict:
        return asdict(self)


def market_status(now: datetime | None = None) -> dict:
    """NSE regular session 09:15-15:30 IST, Monday-Friday. Exchange holidays are not modelled."""
    now = (now or datetime.now(timezone.utc)).astimezone(IST)
    open_t, close_t = now.replace(hour=9, minute=15, second=0, microsecond=0), now.replace(hour=15, minute=30, second=0, microsecond=0)
    is_open = now.weekday() < 5 and open_t <= now <= close_t
    return {"open": is_open, "now_ist": now.strftime("%d %b %Y, %H:%M IST"),
            "note": "Regular session 09:15-15:30 IST, Mon-Fri. Exchange holidays are not checked."}


class MarketDataProvider:
    name = "base"
    realtime = False

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        raise NotImplementedError

    def bars(self, symbol: str, rng: str) -> pd.DataFrame:
        raise NotImplementedError


class YahooDelayedProvider(MarketDataProvider):
    name = "Yahoo Finance (via yfinance)"
    realtime = False

    def _yf(self):
        import yfinance as yf
        return yf

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        syms = [s for s in symbols if not s.startswith("SAMPLE-")]
        if not syms or config.OFFLINE:
            return {}
        yf = self._yf()
        out: dict[str, Quote] = {}
        try:
            daily = yf.download(syms, period="5d", interval="1d", group_by="ticker", progress=False,
                                threads=True, auto_adjust=False, timeout=20)
            intraday = yf.download(syms, period="1d", interval="1m", group_by="ticker", progress=False,
                                   threads=True, auto_adjust=False, timeout=20)
        except Exception as exc:  # network / provider failure -> caller falls back to cache
            log.warning("yahoo batch quote failed: %s", exc)
            return {}
        status_open = market_status()["open"]
        for s in syms:
            try:
                d = daily[s].dropna(subset=["Close"]) if len(syms) > 1 else daily.dropna(subset=["Close"])
                i = intraday[s].dropna(subset=["Close"]) if len(syms) > 1 else intraday.dropna(subset=["Close"])
            except KeyError:
                continue
            if d.empty:
                continue
            last_day = pd.Timestamp(d.index[-1]).date()
            if not i.empty and pd.Timestamp(i.index[-1]).date() >= last_day:
                price, ts = float(i["Close"].iloc[-1]), pd.Timestamp(i.index[-1])
            else:
                price, ts = float(d["Close"].iloc[-1]), pd.Timestamp(d.index[-1])
            # previous close = close of the last completed session before the latest bar's session
            prev_rows = d[[pd.Timestamp(x).date() < ts.date() for x in d.index]]
            prev = float(prev_rows["Close"].iloc[-1]) if len(prev_rows) else None
            ts_utc = (ts.tz_convert("UTC").tz_localize(None) if ts.tzinfo else ts).to_pydatetime()
            fresh = datetime.utcnow() - ts_utc < timedelta(minutes=40)
            out[s] = Quote(s, price, prev, price - prev if prev else None, price / prev - 1 if prev else None,
                           float(d["Volume"].iloc[-1]) if "Volume" in d else None, ts_utc.isoformat(),
                           "delayed" if (status_open and fresh) else "close", self.name)
        return out

    def bars(self, symbol: str, rng: str) -> pd.DataFrame:
        period, interval = RANGES.get(rng, RANGES["1Y"])
        h = self._yf().Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, timeout=20)
        if h is None or h.empty:
            return pd.DataFrame()
        h = h.reset_index()
        tcol = "Datetime" if "Datetime" in h.columns else "Date"
        t = pd.to_datetime(h[tcol])
        t = t.dt.tz_convert("UTC").dt.tz_localize(None) if t.dt.tz is not None else t
        return pd.DataFrame({"time": t, "open": h["Open"], "high": h["High"], "low": h["Low"], "close": h["Close"],
                             "volume": h["Volume"]}).dropna(subset=["close"])

    def actions(self, symbol: str) -> list[dict]:
        acts = self._yf().Ticker(symbol).actions
        out = []
        if acts is None or acts.empty:
            return out
        for ts, r in acts.iterrows():
            d = pd.Timestamp(ts).tz_localize(None).date() if pd.Timestamp(ts).tzinfo else pd.Timestamp(ts).date()
            if r.get("Dividends", 0):
                out.append({"symbol": symbol, "date": d, "type": "dividend", "value": float(r["Dividends"]),
                            "source": "Yahoo Finance (via yfinance)"})
            if r.get("Stock Splits", 0):
                out.append({"symbol": symbol, "date": d, "type": "split", "value": float(r["Stock Splits"]),
                            "source": "Yahoo Finance (via yfinance)"})
        return out


_PROVIDER: MarketDataProvider = YahooDelayedProvider()


def provider() -> MarketDataProvider:
    return _PROVIDER


# ------------------------------------------------------------------ cached quotes
class QuoteCache:
    """Process-wide cache so many users/widgets share one provider request per symbol per TTL."""

    def __init__(self, ttl: float = 60.0):
        self.ttl, self._data, self._lock = ttl, {}, threading.Lock()

    def get(self, symbols: list[str]) -> dict[str, dict]:
        now = time.time()
        with self._lock:
            stale = [s for s in symbols if s not in self._data or now - self._data[s][0] > self.ttl]
        fetched = provider().quotes(stale) if stale else {}
        with self._lock:
            for s, q in fetched.items():
                self._data[s] = (now, q.dict())
        if fetched:
            _persist(fetched)
        out = {}
        for s in symbols:
            if s in self._data:
                out[s] = self._data[s][1]
            else:
                out[s] = _from_db(s)
        return out


def _persist(quotes: dict[str, Quote]) -> None:
    rows = []
    for s, q in quotes.items():
        if q.price is None:
            continue
        rows.append({"symbol": s, "price": q.price, "prev_close": q.prev_close, "as_of": datetime.fromisoformat(q.time),
                     "data_type": "delayed", "source": q.source, "fetched_at": db.utcnow()})
    if not rows:
        return
    from sqlalchemy import update
    with db.get_engine().begin() as conn:   # update only price fields; keep fundamentals (market cap etc.)
        for r in rows:
            conn.execute(update(db.quotes).where(db.quotes.c.symbol == r["symbol"]).values(
                price=r["price"], prev_close=r["prev_close"], as_of=r["as_of"], data_type="delayed", fetched_at=r["fetched_at"]))


def _from_db(symbol: str) -> dict:
    df = db.read_df(db.select(db.quotes).where(db.quotes.c.symbol == symbol))
    if df.empty:
        return Quote(symbol, None, None, None, None, None, None, "unavailable", "—").dict()
    r = df.iloc[0]
    price, prev = r["price"], r["prev_close"]
    sample = symbol.startswith("SAMPLE-")
    t = r["as_of"] if pd.notna(r["as_of"]) else r["fetched_at"]
    return Quote(symbol, float(price) if pd.notna(price) else None, float(prev) if pd.notna(prev) else None,
                 float(price - prev) if pd.notna(price) and pd.notna(prev) else None,
                 float(price / prev - 1) if pd.notna(price) and pd.notna(prev) and prev else None, None,
                 pd.Timestamp(t).isoformat() if pd.notna(t) else None,
                 "sample" if sample else "close", "EquityPilot sample dataset (fictional)" if sample else (r["source"] or "cache")).dict()


QUOTES = QuoteCache(ttl=60)


def refresh_actions(symbol: str) -> int:
    if symbol.startswith("SAMPLE-") or config.OFFLINE:
        return 0
    try:
        rows = YahooDelayedProvider().actions(symbol)
    except Exception as exc:
        log.warning("corporate actions failed for %s: %s", symbol, exc)
        return 0
    db.upsert(db.corporate_actions, rows, ["symbol", "date", "type"])
    db.set_setting(f"actions_refreshed:{symbol}", db.utcnow().isoformat())
    return len(rows)


def get_actions(symbol: str, since=None) -> pd.DataFrame:
    stmt = db.select(db.corporate_actions).where(db.corporate_actions.c.symbol == symbol)
    if since is not None:
        stmt = stmt.where(db.corporate_actions.c.date > since)
    return db.read_df(stmt.order_by(db.corporate_actions.c.date))


# ------------------------------------------------------------------ indices
BROAD_INDICES = {"^NSEI": "NIFTY 50", "^BSESN": "SENSEX", "^NSEBANK": "NIFTY BANK", "^CNX100": "NIFTY 100",
                 "^NSEMDCP50": "NIFTY MIDCAP 50", "^INDIAVIX": "INDIA VIX"}
SECTOR_INDICES = {"^CNXIT": ("NIFTY IT", "it"), "^CNXAUTO": ("NIFTY AUTO", "automobiles"),
                  "^CNXPHARMA": ("NIFTY PHARMA", "pharma"), "^CNXFMCG": ("NIFTY FMCG", "fmcg"),
                  "^CNXMETAL": ("NIFTY METAL", "metals"), "^CNXREALTY": ("NIFTY REALTY", "real-estate"),
                  "^CNXENERGY": ("NIFTY ENERGY", "energy"), "^CNXINFRA": ("NIFTY INFRA", "infrastructure"),
                  "^CNXPSUBANK": ("NIFTY PSU BANK", "banking"), "NIFTY_FIN_SERVICE.NS": ("NIFTY FIN SERVICE", "financial-services"),
                  "^CNXCONSUM": ("NIFTY CONSUMPTION", "consumer-durables")}

_IDX_CACHE: dict = {"t": 0.0, "data": []}


def index_overview(ttl: float = 120) -> list[dict]:
    """Last value, change and 1-month sparkline for broad and sectoral indices (DELAYED, Yahoo)."""
    if time.time() - _IDX_CACHE["t"] < ttl and _IDX_CACHE["data"]:
        return _IDX_CACHE["data"]
    if config.OFFLINE:
        return []
    import yfinance as yf
    syms = list(BROAD_INDICES) + list(SECTOR_INDICES)
    try:
        d = yf.download(syms, period="1mo", interval="1d", group_by="ticker", progress=False, auto_adjust=False, timeout=20)
    except Exception as exc:
        log.warning("index download failed: %s", exc)
        return _IDX_CACHE["data"]
    out = []
    for s in syms:
        try:
            c = d[s]["Close"].dropna()
        except KeyError:
            continue
        if len(c) < 2:
            continue
        last, prev = float(c.iloc[-1]), float(c.iloc[-2])
        name, industry = (BROAD_INDICES[s], None) if s in BROAD_INDICES else SECTOR_INDICES[s]
        out.append({"symbol": s, "name": name, "kind": "broad" if s in BROAD_INDICES else "sector", "industry": industry,
                    "last": last, "prev": prev, "change": last - prev, "change_pct": last / prev - 1,
                    "month_change_pct": last / float(c.iloc[0]) - 1, "as_of": pd.Timestamp(c.index[-1]).date().isoformat(),
                    "spark": [float(x) for x in c.tolist()], "status": "delayed", "source": "Yahoo Finance (via yfinance)"})
    _IDX_CACHE.update(t=time.time(), data=out)
    return out
