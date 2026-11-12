"""Securities master: every listed company we can search, with official market-cap categories.

Sources (official published files, downloaded at most once a week and cached in the DB):
* AMFI "Average Market Capitalization of listed companies" (half-yearly) - SEBI categorisation
  (Large Cap = top 100, Mid Cap = 101-250, Small Cap = 251+), ISIN, NSE & BSE symbols.
* NSE "EQUITY_L.csv" - securities available for trading on NSE (symbol, name, ISIN, listing date).
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime

import pandas as pd
import requests

from .. import config, db

log = logging.getLogger(__name__)
USER_AGENT = "EquityPilotAI/2.0 (educational research tool)"
AMFI_URL = "https://www.amfiindia.com/Themes/Theme1/downloads/AverageMarketCapitalization{}.xlsx"
NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


def _amfi_candidates(today: date | None = None) -> list[tuple[str, str]]:
    """Most recent half-year ends first: ('31Dec2025', '6 months ended 31 Dec 2025'), ..."""
    today = today or date.today()
    out = []
    for y in range(today.year, today.year - 3, -1):
        for m, d in ((12, 31), (6, 30)):
            if date(y, m, d) < today:
                stamp = date(y, m, d).strftime("%d%b%Y")
                out.append((stamp, f"6 months ended {date(y, m, d).strftime('%d %b %Y')}"))
    return out


def _get(url: str, timeout: int = 30) -> bytes | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    except requests.RequestException as exc:
        log.warning("download failed %s: %s", url, exc)
        return None
    if r.status_code != 200 or len(r.content) < 1000:
        return None
    return r.content


def parse_amfi(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content), header=1)
    cols = {c: str(c).strip().lower() for c in df.columns}
    df = df.rename(columns=cols)

    def col(*names):
        for n in names:
            for c in df.columns:
                if c.startswith(n):
                    return c
        return None

    name_c, isin_c = col("company name"), col("isin")
    bse_c, nse_c = col("bse symbol"), col("nse symbol")
    avg_c, cat_c = col("average of all"), col("categorization", "categorisation")
    out = pd.DataFrame({
        "isin": df[isin_c].astype(str).str.strip(), "name": df[name_c].astype(str).str.strip(),
        "bse_symbol": df[bse_c].astype(str).str.strip() if bse_c else None,
        "nse_symbol": df[nse_c].astype(str).str.strip() if nse_c else None,
        "avg_mcap_cr": pd.to_numeric(df[avg_c], errors="coerce"), "category": df[cat_c].astype(str).str.strip(),
    })
    out = out[out["isin"].str.match(r"^IN[A-Z0-9]{10}$")]
    for c in ("bse_symbol", "nse_symbol"):
        out.loc[out[c].isin(["-", "nan", "None", ""]), c] = None
    out["mcap_rank"] = out["avg_mcap_cr"].rank(ascending=False, method="first").astype("Int64")
    return out.drop_duplicates("isin")


def parse_nse_equity(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [c.strip().upper() for c in df.columns]
    return pd.DataFrame({
        "isin": df["ISIN NUMBER"].str.strip(), "name": df["NAME OF COMPANY"].str.strip(),
        "nse_symbol": df["SYMBOL"].str.strip(), "series": df["SERIES"].str.strip(),
        "listing_date": pd.to_datetime(df["DATE OF LISTING"], format="%d-%b-%Y", errors="coerce").dt.date,
    })


def refresh_securities(force: bool = False) -> tuple[bool, str]:
    """Download AMFI + NSE lists and merge into the securities table (weekly cache)."""
    last = db.get_setting("securities_refreshed")
    if not force and last and (db.utcnow() - datetime.fromisoformat(last)).days < 7:
        return True, "Securities list is up to date."
    if config.OFFLINE:
        return False, "Offline mode - securities list not refreshed."
    amfi, as_of = None, None
    for stamp, label in _amfi_candidates():
        content = _get(AMFI_URL.format(stamp))
        if content:
            try:
                amfi, as_of = parse_amfi(content), label
                break
            except Exception as exc:  # unexpected file layout - try the previous half-year
                log.warning("AMFI parse failed for %s: %s", stamp, exc)
    nse_content = _get(NSE_EQUITY_URL)
    nse = parse_nse_equity(nse_content) if nse_content else None
    if amfi is None and nse is None:
        return False, "Could not download the AMFI or NSE securities lists."
    rows: dict[str, dict] = {}
    if amfi is not None:
        for r in amfi.to_dict("records"):
            rows[r["isin"]] = {**r, "series": None, "listing_date": None,
                               "source": "AMFI average market capitalisation list", "as_of": as_of}
    if nse is not None:
        for r in nse.to_dict("records"):
            if r["isin"] in rows:
                rows[r["isin"]].update(series=r["series"], listing_date=r["listing_date"],
                                       nse_symbol=rows[r["isin"]]["nse_symbol"] or r["nse_symbol"])
            else:
                rows[r["isin"]] = {**r, "bse_symbol": None, "avg_mcap_cr": None, "mcap_rank": None,
                                   "category": None, "source": "NSE securities available for trading", "as_of": None}
    clean = []
    for r in rows.values():
        r["mcap_rank"] = int(r["mcap_rank"]) if r.get("mcap_rank") is not None and not pd.isna(r["mcap_rank"]) else None
        r["avg_mcap_cr"] = None if r.get("avg_mcap_cr") is None or pd.isna(r["avg_mcap_cr"]) else float(r["avg_mcap_cr"])
        ld = r.get("listing_date")
        r["listing_date"] = None if ld is None or pd.isna(ld) else ld
        clean.append(r)
    n = db.upsert(db.securities, clean, ["isin"])
    db.set_setting("securities_refreshed", db.utcnow().isoformat())
    db.set_setting("securities_as_of", as_of)
    return True, f"{n} securities stored (AMFI list: {as_of or 'unavailable'}; NSE list: {'yes' if nse is not None else 'unavailable'})."


def category_map() -> dict[str, tuple[str, int | None]]:
    """NSE symbol -> (category, rank)."""
    df = db.read_df(db.select(db.securities.c.nse_symbol, db.securities.c.category, db.securities.c.mcap_rank)
                    .where(db.securities.c.nse_symbol.isnot(None)))
    return {r["nse_symbol"]: (r["category"], r["mcap_rank"]) for _, r in df.iterrows()}


def category_for(symbol: str) -> str | None:
    base = symbol.rsplit(".", 1)[0]
    df = db.read_df(db.select(db.securities.c.category).where(db.securities.c.nse_symbol == base).limit(1))
    return df["category"].iloc[0] if len(df) else None


# ------------------------------------------------------------------ name resolver (typo-tolerant), shared by search and the AI
import difflib  # noqa: E402
import re  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

_LEGAL = re.compile(r"\b(limited|ltd|the|company|co|corporation|corp|inc|plc|pvt|private)\b")
# everyday names for companies whose official name or symbol people don't type
ALIASES = {"sbi": "SBIN", "state bank": "SBIN", "l and t": "LT", "larsen": "LT", "m and m": "M&M", "mahindra": "M&M",
           "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR", "ril": "RELIANCE", "airtel": "BHARTIARTL",
           "bharti airtel": "BHARTIARTL", "maruti": "MARUTI", "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK",
           "icici": "ICICIBANK", "axis": "AXISBANK", "indusind": "INDUSINDBK", "bajaj finance": "BAJFINANCE",
           "bajaj finserv": "BAJAJFINSV", "hero": "HEROMOTOCO", "hero motocorp": "HEROMOTOCO", "dr reddy": "DRREDDY",
           "dr reddys": "DRREDDY", "sun pharma": "SUNPHARMA", "ongc": "ONGC", "ntpc": "NTPC", "zomato": "ETERNAL",
           "paytm": "PAYTM", "nykaa": "NYKAA", "irctc": "IRCTC", "lic": "LICI", "hdfc life": "HDFCLIFE", "hcl": "HCLTECH",
           "tech mahindra": "TECHM", "asian paints": "ASIANPAINT", "ultratech": "ULTRACEMCO", "jsw steel": "JSWSTEEL",
           "tata steel": "TATASTEEL", "tata power": "TATAPOWER", "tcs": "TCS", "infosys": "INFY", "wipro": "WIPRO",
           "adani": "ADANIENT", "hdfc": "HDFCBANK", "jsw": "JSWSTEEL", "godrej": "GODREJCP", "vedanta": "VEDL"}


def norm(text: str) -> str:
    s = (text or "").lower().replace("&", " and ").replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def core_name(name: str) -> str:
    """'The Tata Power Company Limited' -> 'tata power'."""
    return " ".join(_LEGAL.sub(" ", norm(name)).split())


_IDX: dict = {"t": 0.0, "rows": [], "vocab": [], "by_base": {}}
_IDX_LOCK = threading.Lock()


def name_index(ttl: float = 600) -> dict:
    """In-memory index of tracked companies + the securities master (about 5,500 names)."""
    if time.time() - _IDX["t"] < ttl and _IDX["rows"]:
        return _IDX
    with _IDX_LOCK:
        if time.time() - _IDX["t"] < ttl and _IDX["rows"]:
            return _IDX
        comps = db.read_df(db.select(db.companies.c.symbol, db.companies.c.name, db.companies.c.is_sample))
        s = db.securities.c
        sec = db.read_df(db.select(s.name, s.nse_symbol, s.bse_symbol, s.mcap_rank, s.category))
        rows: dict[str, dict] = {}
        for _, r in sec.iterrows():
            sym = f"{r['nse_symbol']}.NS" if r["nse_symbol"] else (f"{r['bse_symbol']}.BO" if r["bse_symbol"] else None)
            if not sym:
                continue
            rank = int(r["mcap_rank"]) if pd.notna(r["mcap_rank"]) else None
            rows[sym] = {"symbol": sym, "name": r["name"], "rank": rank, "category": r["category"], "tracked": False}
        for _, r in comps.iterrows():
            e = rows.setdefault(r["symbol"], {"symbol": r["symbol"], "name": r["name"], "rank": None, "category": None})
            e.update(tracked=True, name=r["name"] or e["name"], sample=bool(r["is_sample"]))
        _IDX.update(build_index(list(rows.values())), t=time.time())
    return _IDX


def build_index(rows: list[dict]) -> dict:
    """rows: {symbol, name, rank, category, tracked} -> searchable index (also used by tests)."""
    vocab: set[str] = set()
    by_base: dict[str, list[dict]] = {}
    for e in rows:
        e["core"] = core_name(e["name"] or "")
        e["tokens"] = e["core"].split()
        e["base"] = norm(e["symbol"].rsplit(".", 1)[0]).replace(" ", "")
        by_base.setdefault(e["base"], []).append(e)
        vocab.update(t for t in e["tokens"] if len(t) >= 3)
        if len(e["base"]) >= 3:
            vocab.add(e["base"])
    return {"rows": rows, "vocab": sorted(vocab), "by_base": by_base}


def correct_spelling(text: str) -> str:
    """Fix typos word by word against the company-name vocabulary ('enterprwses' -> 'enterprises')."""
    idx = name_index()
    vocab = idx["vocab"]
    vs = set(vocab)
    out = []
    for t in norm(text).split():
        if len(t) >= 4 and not t.isdigit() and t not in vs:
            m = difflib.get_close_matches(t, vocab, n=1, cutoff=0.78)
            out.append(m[0] if m else t)
        else:
            out.append(t)
    return " ".join(out)


def _rank_key(score: int, e: dict):
    return (-score, not e.get("tracked"), e.get("rank") or 99999)


def resolve(phrase: str, limit: int = 6, fuzzy: bool = True) -> list[dict]:
    """Best company matches for a phrase, highest score first. Scores: 100 symbol, 99 alias, 98 exact name,
    90 name starts with the phrase, 80 every word is a prefix of the name's words, 75 symbol prefix.
    Typo-corrected matches score 5 lower and carry corrected=<text>."""
    idx = name_index()
    raw = (phrase or "").strip()
    if re.fullmatch(r"[A-Za-z0-9&-]+\.(NS|BO)", raw, re.I):
        e = next((x for x in idx["rows"] if x["symbol"].upper() == raw.upper()), None)
        return [{**e, "score": 100}] if e else []
    p = core_name(raw)
    if not p:
        return []
    pc = p.replace(" ", "")
    hits: list[tuple[int, dict]] = []
    alias = ALIASES.get(p)
    if alias:
        hits += [(99, e) for e in idx["by_base"].get(norm(alias).replace(" ", ""), [])]
    ptoks = p.split()
    for e in idx["rows"]:
        if e["base"] == pc:
            s = 100
        elif e["core"] == p:
            s = 98
        elif e["core"].startswith(p + " "):
            s = 90
        elif len(p) >= 3 and e["tokens"] and e["tokens"][0].startswith(ptoks[0]) and \
                all(any(t.startswith(pt) for t in e["tokens"]) for pt in ptoks):
            s = 80
        elif len(pc) >= 3 and e["base"].startswith(pc):
            s = 75
        else:
            continue
        hits.append((s, e))
    if not hits and fuzzy:
        fixed = correct_spelling(p)
        if fixed != p:
            return [{**h, "score": h["score"] - 5, "corrected": fixed} for h in resolve(fixed, limit, fuzzy=False)]
    best: dict[str, tuple[int, dict]] = {}
    for s, e in hits:
        if e["symbol"] not in best or best[e["symbol"]][0] < s:
            best[e["symbol"]] = (s, e)
    ordered = sorted(best.values(), key=lambda x: _rank_key(*x))
    return [{**e, "score": s} for s, e in ordered[:limit]]


def search(query: str, limit: int = 12) -> list[dict]:
    """Search tracked companies and the full securities master by name, NSE/BSE symbol or ISIN.
    Falls back to typo-tolerant matching when the plain search finds little."""
    res = _search_plain(query, limit)
    if len(res) < min(3, limit) and len((query or "").strip()) >= 3:
        have = {r["symbol"] for r in res}
        for h in resolve(query, limit):
            if h["symbol"] in have:
                continue
            res.append({"symbol": h["symbol"], "name": h["name"], "sector": None, "industry": None, "tracked": h.get("tracked", False),
                        "is_sample": bool(h.get("sample")), "category": h.get("category"), "score": h["score"] - 50,
                        **({"did_you_mean": h["corrected"]} if h.get("corrected") else {})})
    return res[:limit]


def _search_plain(query: str, limit: int = 12) -> list[dict]:
    """Search tracked companies and the full securities master by name, NSE/BSE symbol or ISIN."""
    q = (query or "").strip()
    if not q:
        return []
    ql = q.lower()
    out: dict[str, dict] = {}
    comps = db.read_df(db.select(db.companies.c.symbol, db.companies.c.name, db.companies.c.sector,
                                 db.companies.c.industry, db.companies.c.is_sample))
    comps = comps.astype(object).where(comps.notna(), None)
    tracked = set(comps["symbol"])
    for _, r in comps.iterrows():
        base = r["symbol"].rsplit(".", 1)[0].lower()
        name = (r["name"] or "").lower()
        score = 100 if base == ql else 80 if base.startswith(ql) else 70 if name.startswith(ql) else \
            50 if ql in name or ql in base else 40 if ql in (r["industry"] or "").lower() or ql in (r["sector"] or "").lower() else 0
        if score:
            out[r["symbol"]] = {"symbol": r["symbol"], "name": r["name"], "sector": r["sector"], "industry": r["industry"],
                                "tracked": True, "is_sample": bool(r["is_sample"]), "score": score + 5}
    like = f"%{q}%"
    s = db.securities.c
    rows = db.read_df(db.select(s.isin, s.name, s.nse_symbol, s.bse_symbol, s.category, s.mcap_rank)
                      .where((s.name.ilike(like)) | (s.nse_symbol.ilike(like)) | (s.bse_symbol.ilike(like)) | (s.isin == q.upper()))
                      .order_by(s.mcap_rank.is_(None), s.mcap_rank).limit(60))
    rows = rows.astype(object).where(rows.notna(), None)
    for _, r in rows.iterrows():
        sym = f"{r['nse_symbol']}.NS" if r["nse_symbol"] else (f"{r['bse_symbol']}.BO" if r["bse_symbol"] else None)
        if not sym or sym in out:
            if sym in out:
                out[sym].update(category=r["category"], isin=r["isin"])
            continue
        base = (r["nse_symbol"] or r["bse_symbol"] or "").lower()
        name = (r["name"] or "").lower()
        score = 90 if base == ql else 60 if base.startswith(ql) else 55 if name.startswith(ql) else 30
        score += max(0, 10 - (r["mcap_rank"] or 5000) // 500)   # nudge larger companies up
        out[sym] = {"symbol": sym, "name": r["name"], "sector": None, "industry": None, "tracked": sym in tracked,
                    "is_sample": False, "category": r["category"], "isin": r["isin"], "score": score}
    return sorted(out.values(), key=lambda x: -x["score"])[:limit]
