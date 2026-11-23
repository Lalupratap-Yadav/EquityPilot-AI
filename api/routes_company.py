"""Search, company profile, financials, valuation (incl. DCF lab), technicals, risk, peers, bank metrics, notes."""
from __future__ import annotations

from dataclasses import asdict

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from equitypilot import config, db, users
from equitypilot import formatting as F
from equitypilot.analytics import bank as B
from equitypilot.analytics import ratios as R
from equitypilot.analytics import risk as K
from equitypilot.analytics import technicals as T
from equitypilot.analytics import valuation as V
from equitypilot.analytics.screener import company_metrics
from equitypilot.content import metrics_guide as MG
from equitypilot.content.industries import BY_ID, industry_of
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo
from equitypilot.data import securities as S
from equitypilot.data.official import official_links
from equitypilot.data.schema import STATEMENTS, items_for, label
from equitypilot.data.universe import is_valid_symbol, normalise_symbol

from .core import LIMITER, clean, current_user, not_found

router = APIRouter(prefix="/api", tags=["company"])


def _company_or_404(symbol: str) -> dict:
    c = repo.get_company(symbol)
    if not c:
        raise not_found(f"Company {symbol}")
    return c


# ------------------------------------------------------------------ search
@router.post("/companies/{symbol}/track")
def track(symbol: str, request: Request):
    """Fetch an untracked company from the data provider (profile, quote, statements, prices)."""
    LIMITER.check(request, "track", 10, 60)
    if not is_valid_symbol(symbol):
        raise HTTPException(400, "Invalid symbol.")
    sym = normalise_symbol(symbol)
    if repo.get_company(sym):
        return {"symbol": sym, "message": "Already tracked."}
    if config.OFFLINE:
        raise HTTPException(503, "Offline mode - cannot fetch new companies.")
    ok, msg, sym = repo.add_company(sym)
    if not ok:
        raise HTTPException(404 if msg.startswith("No data returned") else 502, msg)
    M.refresh_actions(sym)
    from .routes_explore import invalidate_metrics
    invalidate_metrics()
    return {"symbol": sym, "message": msg}


# ------------------------------------------------------------------ profile
@router.get("/companies/{symbol}")
def company(symbol: str, request: Request):
    uid = current_user(request)
    c = _company_or_404(symbol)
    db.upsert(db.recent_views, [{"user_id": uid, "symbol": symbol, "ts": db.utcnow()}], ["user_id", "symbol"])
    quote = repo.get_quote(symbol) or {}
    live = M.QUOTES.get_nowait([symbol])[symbol]     # never wait for the provider; the quote stream pushes a fresher value
    m = company_metrics(symbol)
    iid = industry_of(symbol, c.get("sector"), c.get("industry"))
    fd = repo.get_financials(symbol, auto_refresh=False)
    return clean({
        "company": {k: c.get(k) for k in ("symbol", "name", "exchange", "isin", "sector", "industry", "description",
                                          "website", "employees", "is_sample", "source", "source_url", "fetched_at")},
        "industry": {"id": iid, "name": BY_ID[iid]["name"]} if iid in BY_ID else None,
        "category": S.category_for(symbol), "is_financial": R.is_financial(c),
        "quote": live, "fundamentals_quote": {k: quote.get(k) for k in ("market_cap", "shares_outstanding", "beta",
                                                                         "week52_high", "week52_low", "dividend_rate", "fetched_at")},
        "metrics": m, "statement_basis": fd.basis, "statement_currency": fd.currency,
        "official_links": official_links(symbol),
        "notes": users.get_pref(uid, f"notes:{symbol}", {}),
        "in_watchlists": db.read_df(db.select(db.watchlist_items.c.watchlist_id).join(
            db.watchlists, db.watchlists.c.id == db.watchlist_items.c.watchlist_id)
            .where(db.watchlists.c.user_id == uid).where(db.watchlist_items.c.symbol == symbol))["watchlist_id"].tolist(),
    })


@router.get("/companies/{symbol}/financials")
def financials(symbol: str, period: str = "annual", basis: str | None = None):
    c = _company_or_404(symbol)
    fin = R.is_financial(c)
    if period not in ("annual", "quarterly"):
        raise HTTPException(400, "period must be annual or quarterly")
    fd = repo.get_financials(symbol, period, basis, auto_refresh=False)
    if fd.empty:
        return {"empty": True, "bases": repo.available_bases(symbol, period)}
    labels = [F.fiscal_label(p) if period == "annual" else F.quarter_label(p) for p in fd.periods]
    statements = {}
    for st, title in STATEMENTS.items():
        rows = []
        for k in items_for(st):
            if k in fd.wide.index:
                rows.append({"key": k, "label": label(k), "values": clean(fd.wide.loc[k].tolist())})
        statements[st] = {"title": title, "rows": rows}
    rt = R.compute_ratios(fd)
    ratios = []
    for k, d in R.RATIOS.items():
        if k not in rt.index:
            continue
        vals = rt.loc[k]
        latest = vals.dropna()
        ratios.append({"key": k, "label": d.label, "category": d.category, "formula": d.formula, "kind": d.kind, "help": d.help,
                       "values": clean(vals.tolist()), "guide": MG.GUIDE.get(k),
                       # benchmark ratings only for annual data - quarterly flows against balances are not comparable
                       "assessment": MG.assess(k, float(latest.iloc[-1]), fin) if period == "annual" and len(latest) else None})
    dp = R.dupont(fd)
    fscore, tests = R.piotroski_f_score(fd) if period == "annual" else (None, [])
    return clean({
        "periods": [str(pd.Timestamp(p).date()) for p in fd.periods], "labels": labels, "basis": fd.basis,
        "bases": repo.available_bases(symbol, period), "currency": fd.currency, "unit": F.amount_unit(fd.currency)[1],
        "divisor": F.amount_unit(fd.currency)[0], "statements": statements, "ratios": ratios,
        "dupont": dp.to_dict("index") if not dp.empty else {}, "piotroski": {"score": fscore, "tests": tests},
        "cagr": {k: {"3y": R.cagr(fd.get(k), 3), "all": R.cagr(fd.get(k))} for k in ("revenue", "ebitda", "net_income", "eps_diluted")},
        "benchmark_note": MG.BENCHMARK_NOTE, "is_financial": fin,
        "quality": R.quality_checks(fd), "sources": fd.sources, "source_urls": fd.source_urls, "data_types": fd.data_types,
        "fetched_at": fd.fetched_at,
    })


@router.get("/companies/{symbol}/health")
def health(symbol: str, request: Request):
    """Financial Health dashboard: seven areas, each with its metrics, formulas and documented rating rules."""
    current_user(request)
    _company_or_404(symbol)
    from equitypilot.analytics import health as H
    return clean(H.health(symbol))


@router.get("/companies/{symbol}/coverage")
def coverage(symbol: str, request: Request):
    """Which datasets EquityPilot holds for this company, their source label, period, freshness and gaps."""
    uid = current_user(request)
    _company_or_404(symbol)
    from equitypilot.data import quality as Q
    return clean(Q.company_coverage(symbol, uid))


@router.get("/companies/{symbol}/quarterly")
def quarterly(symbol: str):
    _company_or_404(symbol)
    fq = repo.get_financials(symbol, "quarterly", auto_refresh=False)
    if fq.empty:
        return {"empty": True}
    qs = R.quarterly_summary(fq)
    expected = pd.date_range(qs.index.min(), qs.index.max(), freq="QE")
    have = {pd.Timestamp(p).normalize() for p in qs.index}
    return clean({"quarters": [{"period": str(pd.Timestamp(p).date()), "label": F.quarter_label(p), **r.to_dict()}
                               for p, r in qs.iterrows()],
                  "missing": [F.quarter_label(d) for d in expected if d.normalize() not in have],
                  "currency": fq.currency, "basis": fq.basis, "sources": fq.sources, "fetched_at": fq.fetched_at})


# ------------------------------------------------------------------ valuation lab
@router.get("/companies/{symbol}/valuation")
def valuation(symbol: str, request: Request):
    uid = current_user(request)
    c = _company_or_404(symbol)
    quote = repo.get_quote(symbol)
    fd = repo.get_financials(symbol, auto_refresh=False)
    fq = repo.get_financials(symbol, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
    snap = V.market_snapshot(quote, fd, fq)
    base, notes = V.default_dcf_inputs(fd, quote)
    hist = V.multiple_history(fd, repo.get_prices(symbol, auto_refresh=False))
    peers = repo.get_peers(symbol)
    pc, pq = repo.get_companies(peers), repo.get_quotes(peers)
    pm = pd.DataFrame([company_metrics(p, company=pc.get(p), quote=pq.get(p)) for p in peers]) if peers else pd.DataFrame()
    rel = V.peer_relative(snap, pm) if not pm.empty else pd.DataFrame()
    kd = None
    if not fd.empty and fd.latest("interest_expense") and fd.latest("total_debt"):
        kd = abs(fd.latest("interest_expense")) / fd.latest("total_debt")
    rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
    fcfe_extra, fcfe_notes = V.default_fcfe_extras(fd)
    bands = V.multiple_bands(hist, snap)
    eps_now = snap["net_income"] / snap["shares"] if snap.get("net_income") and snap.get("shares") else None
    bvps_now = snap["equity"] / snap["shares"] if snap.get("equity") and snap.get("shares") else None
    implied_hist = {
        "pe": bands["pe"]["median"] * eps_now if bands["pe"]["median"] and eps_now and eps_now > 0 else None,
        "pb": bands["pb"]["median"] * bvps_now if bands["pb"]["median"] and bvps_now and bvps_now > 0 else None,
    }
    return clean({
        "snapshot": snap, "bands": bands, "implied_from_history": implied_hist,
        "fcfe_defaults": fcfe_extra or None, "fcfe_notes": fcfe_notes, "formulas": V.MULTIPLE_FORMULAS, "is_financial": R.is_financial(c), "history": hist,
        "dcf_defaults": asdict(base) if base else None, "dcf_notes": notes, "provider_beta": (quote or {}).get("beta"),
        "kd_hint": kd, "peers": pm[["symbol", "name", "pe", "pb", "ev_ebitda", "roe"]].to_dict("records") if not pm.empty else [],
        "relative": rel.to_dict("records") if not rel.empty else [],
        "roe_3y": float(rt.loc["roe"].dropna().iloc[-3:].mean()) if not rt.empty and rt.loc["roe"].notna().any() else None,
        "bvps": (fd.latest("total_equity") / (snap.get("shares") or fd.latest("shares_outstanding")))
        if not fd.empty and fd.latest("total_equity") and (snap.get("shares") or fd.latest("shares_outstanding")) else None,
        "saved": users.get_pref(uid, f"valuation:{symbol}"),
        "hist_cagr_3y": R.cagr(fd.get("revenue"), 3) if not fd.empty else None,
    })


class FCFEExtras(BaseModel):
    net_margin: float = Field(ge=-1, le=1)
    debt_ratio: float = Field(ge=0, lt=1)
    cost_of_equity: float = Field(gt=0, le=0.5)


class DCFRequest(BaseModel):
    base_revenue: float = Field(gt=0)
    growth_start: float = Field(ge=-0.5, le=1.0)
    growth_end: float = Field(ge=-0.5, le=1.0)
    ebit_margin: float = Field(ge=-1, le=1)
    tax_rate: float = Field(ge=0, le=0.6)
    da_pct: float = Field(ge=0, le=1)
    capex_pct: float = Field(ge=0, le=1)
    nwc_pct: float = Field(ge=-1, le=2)
    wacc: float = Field(gt=0, le=0.5)
    terminal_growth: float = Field(ge=-0.05, le=0.15)
    net_debt: float
    shares: float = Field(gt=0)
    years: int = Field(5, ge=1, le=15)
    minority_interest: float = 0.0
    scenario_shifts: dict[str, list[float]] | None = None
    fcfe: FCFEExtras | None = None
    save: bool = False


@router.post("/companies/{symbol}/dcf")
def dcf(symbol: str, body: DCFRequest, request: Request):
    uid = current_user(request)
    _company_or_404(symbol)
    data = body.model_dump()
    shifts, save, fx = data.pop("scenario_shifts"), data.pop("save"), data.pop("fcfe")
    inp = V.DCFInputs(**data)
    try:
        res = V.run_dcf(inp)
    except V.DCFError as exc:
        raise HTTPException(400, str(exc))
    price = (repo.get_quote(symbol) or {}).get("price")
    scn = V.scenarios(inp, {k: tuple(v) for k, v in shifts.items()} if shifts else None)
    waccs = [round(inp.wacc + d, 4) for d in (-0.02, -0.01, 0, 0.01, 0.02)]
    gs = [round(inp.terminal_growth + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    grid = V.sensitivity(inp, waccs, gs)
    implied = V.reverse_dcf(inp, price) if price else None
    out = {"per_share": res.per_share, "enterprise_value": res.enterprise_value, "equity_value": res.equity_value,
           "pv_fcff": res.pv_fcff, "terminal_value": res.terminal_value, "pv_terminal": res.pv_terminal,
           "terminal_share": res.terminal_share, "price": price,
           "projection": res.projection.reset_index().to_dict("records"),
           "scenarios": {k: ({"per_share": v.per_share, "terminal_share": v.terminal_share} if isinstance(v, V.DCFResult) else {"error": v})
                         for k, v in scn.items()},
           "sensitivity": {"waccs": waccs, "growths": gs, "values": grid.values.tolist()},
           "implied_growth": implied, "margin_of_safety": V.margin_of_safety(res.per_share, price)}
    if fx:
        try:
            fr = V.run_fcfe(V.FCFEInputs(
                base_revenue=inp.base_revenue, growth_start=inp.growth_start, growth_end=inp.growth_end,
                net_margin=fx["net_margin"], da_pct=inp.da_pct, capex_pct=inp.capex_pct, nwc_pct=inp.nwc_pct,
                debt_ratio=fx["debt_ratio"], cost_of_equity=fx["cost_of_equity"], terminal_growth=inp.terminal_growth,
                shares=inp.shares, years=inp.years))
            out["fcfe"] = {"per_share": fr.per_share, "equity_value": fr.equity_value, "pv_fcfe": fr.pv_fcfe,
                           "terminal_value": fr.terminal_value, "pv_terminal": fr.pv_terminal, "terminal_share": fr.terminal_share,
                           "projection": fr.projection.reset_index().to_dict("records"),
                           "margin_of_safety": V.margin_of_safety(fr.per_share, price)}
        except V.DCFError as exc:
            out["fcfe"] = {"error": str(exc)}
    if save:
        users.set_pref(uid, f"valuation:{symbol}", {"inputs": asdict(inp), "per_share": res.per_share, "price": price,
                                                    "saved": F.ist(db.utcnow())})
    return clean(out)


# ------------------------------------------------------------------ technicals & risk
@router.get("/companies/{symbol}/technicals")
def technicals(symbol: str):
    _company_or_404(symbol)
    px = repo.get_prices(symbol, auto_refresh=False)
    if px.empty or len(px) < 30:
        return {"empty": True}
    ind = T.indicator_frame(px)
    c, d = px["close"], px["date"]
    ly = px[px["date"] >= d.max() - pd.Timedelta(days=365)]
    beta = corr = None
    if not symbol.startswith("SAMPLE-"):
        bench = repo.get_prices(config.BENCHMARK, auto_refresh=False)
        if not bench.empty:
            beta, corr, _ = T.beta(ly.set_index("date")["close"], bench.set_index("date")["close"])
    return clean({"readings": T.readings(ind), "stats": {
        "r1m": T.period_return(c, d, 30), "r3m": T.period_return(c, d, 91), "r1y": T.period_return(c, d, 365),
        "r3y": T.period_return(c, d, 1095), "vol1y": T.annualised_volatility(ly["close"]), "mdd1y": T.max_drawdown(ly["close"]),
        "beta": beta, "corr": corr, "atr": float(ind["ATR 14"].iloc[-1])}, "source": px["source"].dropna().iloc[-1],
        "period": [str(d.min().date()), str(d.max().date())]})


@router.get("/companies/{symbol}/risk")
def risk(symbol: str, request: Request):
    uid = current_user(request)
    c = _company_or_404(symbol)
    fd = repo.get_financials(symbol, auto_refresh=False)
    flags = K.assess(c, fd, repo.get_prices(symbol, auto_refresh=False), repo.get_shareholding(symbol),
                     repo.get_segments(symbol), repo.get_bank_metrics(symbol))
    z, zone, xs = K.altman_z_double_prime(fd) if not R.is_financial(c) else (None, None, {})
    return clean({"flags": flags, "summary": K.summarise(flags).to_dict("records"), "score": K.overall_score(flags),
                  "altman": {"z": z, "zone": zone, "components": xs}, "sector_considerations": K.SECTOR_CONSIDERATIONS.get(c.get("sector"), []),
                  "regulatory": K.GENERAL_REGULATORY, "notes": users.get_pref(uid, f"risk_notes:{symbol}", {})})


@router.get("/companies/{symbol}/peers")
def peers(symbol: str):
    _company_or_404(symbol)
    syms = [symbol] + repo.get_peers(symbol)
    comps, quotes = repo.get_companies(syms), repo.get_quotes(syms)
    return clean({"rows": [company_metrics(s, company=comps.get(s), quote=quotes.get(s)) for s in syms]})


@router.get("/companies/{symbol}/ownership")
def ownership(symbol: str):
    _company_or_404(symbol)
    return clean({"shareholding": repo.get_shareholding(symbol).to_dict("records"),
                  "segments": repo.get_segments(symbol).to_dict("records")})


@router.get("/companies/{symbol}/bank")
def bank_metrics(symbol: str):
    _company_or_404(symbol)
    bm = repo.get_bank_metrics(symbol)
    w = B.wide(bm)
    return clean({"definitions": {k: {"label": v[0], "help": v[1], "higher_better": v[2]} for k, v in B.BANK_METRICS.items()},
                  "periods": list(w.columns), "values": {k: w.loc[k].tolist() for k in w.index} if not w.empty else {},
                  "flags": B.assess(bm), "sources": bm["source"].dropna().unique().tolist() if not bm.empty else []})


class BankEntry(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    values: dict[str, float | None]
    source: str = Field(min_length=3, max_length=300)
    source_url: str | None = None


@router.post("/companies/{symbol}/bank")
def save_bank(symbol: str, body: BankEntry, request: Request):
    current_user(request)
    c = _company_or_404(symbol)
    if c.get("is_sample"):
        raise HTTPException(400, "Sample companies are read-only.")
    vals = {k: v for k, v in body.values.items() if k in B.BANK_METRICS and v is not None and 0 <= v <= 100}
    if not vals:
        raise HTTPException(400, "Enter at least one metric between 0 and 100.")
    n = repo.save_bank_metrics(symbol, body.period, vals, body.source, body.source_url)
    return {"saved": n}


class ShareholdingRow(BaseModel):
    category: str = Field(min_length=2, max_length=60)
    pct: float = Field(ge=0, le=100)
    pledged_pct: float | None = Field(None, ge=0, le=100)


class ShareholdingEntry(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    rows: list[ShareholdingRow] = Field(min_length=1, max_length=12)
    source_url: str | None = Field(None, max_length=500)


@router.post("/companies/{symbol}/shareholding")
def save_shareholding(symbol: str, body: ShareholdingEntry, request: Request):
    """User-entered shareholding pattern from an exchange filing (SEBI LODR Reg. 31). Replaces that quarter."""
    current_user(request)
    c = _company_or_404(symbol)
    if c.get("is_sample"):
        raise HTTPException(400, "Sample companies are read-only.")
    total = sum(r.pct for r in body.rows)
    if not 99.0 <= total <= 101.0:
        raise HTTPException(400, f"Holdings add up to {total:.2f}% - they should total 100%.")
    sh = db.shareholding
    db.execute(db.delete(sh).where(sh.c.symbol == symbol).where(sh.c.period == body.period))
    db.execute(db.insert(sh), [{
        "symbol": symbol, "period": body.period, "category": r.category.strip(), "pct": r.pct, "pledged_pct": r.pledged_pct,
        "source": "User-entered from exchange filing", "source_url": F.safe_url(body.source_url),
        "data_type": "user_entered", "fetched_at": db.utcnow()} for r in body.rows])
    db.log_activity("Saved shareholding", f"{symbol} {body.period}")
    return {"saved": len(body.rows)}


class Notes(BaseModel):
    business_model: str = ""
    products: str = ""
    moat: str = ""
    management: str = ""
    risks: str = ""
    source: str = ""


@router.put("/companies/{symbol}/notes")
def save_notes(symbol: str, body: Notes, request: Request):
    uid = current_user(request)
    _company_or_404(symbol)
    data = {k: v[:4000] for k, v in body.model_dump().items()}
    data["updated"] = F.ist(db.utcnow())
    users.set_pref(uid, f"notes:{symbol}", data)
    if data.get("risks"):
        users.set_pref(uid, f"risk_notes:{symbol}", {"text": data["risks"], "source": data["source"], "updated": data["updated"]})
    return data


@router.post("/companies/{symbol}/refresh")
def refresh(symbol: str, request: Request):
    LIMITER.check(request, "refresh", 6, 60)
    c = _company_or_404(symbol)
    if c.get("is_sample"):
        return {"messages": ["Sample company - nothing to refresh."]}
    msgs = [repo.refresh_company(symbol)[1], repo.refresh_financials(symbol)[1], repo.refresh_prices(symbol)[1],
            repo.refresh_news(symbol)[1]]
    M.refresh_actions(symbol)
    from .routes_explore import invalidate_metrics
    invalidate_metrics()
    return {"messages": msgs}
