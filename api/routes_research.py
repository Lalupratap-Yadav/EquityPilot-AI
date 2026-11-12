"""News intelligence, documents (upload + RAG), AI assistant, PDF reports, learning, data sources."""
from __future__ import annotations

import io
import os
import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from equitypilot import config, db, users
from equitypilot import formatting as F
from equitypilot.ai import offline, rag
from equitypilot.ai import providers as P
from equitypilot.ai.context import build_context, grounding_check
from equitypilot.content.glossary import GLOSSARY
from equitypilot.content.industries import BY_ID
from equitypilot.content.learning import MODULES
from equitypilot.data import feeds as N
from equitypilot.data import repository as repo
from equitypilot.data import source_tiers as ST
from equitypilot.data import uploads as U
from equitypilot.data.official import OFFICIAL_SOURCES
from equitypilot.reports.pdf_report import ReportOptions, build_report

from .core import LIMITER, clean, current_user, not_found

router = APIRouter(prefix="/api", tags=["research"])

NEWS_SECTIONS = {
    "disclosures": {"title": "Exchange disclosures", "feeds": ["nse_announcements"]},
    "results": {"title": "Quarterly results", "feeds": ["nse_announcements", "nse_results"], "category": "Quarterly results"},
    "corporate": {"title": "Corporate announcements", "feeds": ["nse_announcements"], "category": "Dividend & corporate action"},
    "economy": {"title": "Economy & RBI", "feeds": ["rbi_press", "rbi_notifications"]},
    "regulation": {"title": "Regulation & SEBI", "feeds": ["sebi"]},
    "global": {"title": "Markets & global", "feeds": ["yahoo_market"]},
}


def _filter_tiers(items: list[dict], include_unrated: bool) -> tuple[list[dict], int]:
    if include_unrated:
        return items, 0
    kept = [i for i in items if i.get("tier") != "unrated"]
    return kept, len(items) - len(kept)


@router.get("/news")
def news(request: Request, section: str = "disclosures", symbol: str | None = None, industry: str | None = None,
         q: str | None = None, tracked_only: bool = False, limit: int = 60, include_unrated: bool = False):
    current_user(request)
    limit = max(1, min(limit, 200))
    N.refresh_all()                          # TTL-cached per feed
    if section == "company":
        if industry in BY_ID:
            syms = BY_ID[industry]["symbols"]
        elif symbol:
            syms = [symbol]
        else:
            syms = repo.list_companies()["symbol"].tolist()            # all tracked companies
        if symbol and not symbol.startswith("SAMPLE-"):
            have = repo.get_disclosures(symbol, limit=50)
            if have.empty or not (have["category"] == "News").any():    # never fetched for this company
                repo.refresh_news(symbol)
        nse = N.query(feeds=["nse_announcements", "nse_results"], symbols=syms, q=q, limit=limit)
        ynews = repo.get_disclosures(None, limit=500)
        if not ynews.empty:
            ynews = ynews[ynews["symbol"].isin(syms)]
            if q:
                ynews = ynews[ynews["title"].str.contains(q, case=False, regex=False)]
        items = [{"title": r["title"], "url": r["url"], "published": r["published"], "source": r["source"], "category": r["category"],
                  "symbol": r["symbol"], "summary": r["summary"], "tier": "primary"} for r in nse.to_dict("records")]
        if not ynews.empty:
            items += [{"title": r["title"], "url": r["url"], "published": r["date"], "category": r["category"],
                       "source": (r["publisher"] or "") + (" via Yahoo Finance" if r["data_type"] == "third_party" else f" ({r['source']})"),
                       "symbol": r["symbol"], "summary": None, "tier": ST.tier(r["publisher"], r["data_type"])} for r in ynews.to_dict("records")]
        items, hidden = _filter_tiers(items, include_unrated)
        items.sort(key=lambda x: str(x["published"] or ""), reverse=True)
        return clean({"items": items[:limit], "section": "Company & sector news", "hidden_unrated": hidden,
                      "unrated_note": ST.UNRATED_NOTE})
    cfg = NEWS_SECTIONS.get(section)
    if not cfg:
        raise not_found("News section")
    tracked = repo.list_companies()["symbol"].tolist() if tracked_only else None
    df = N.query(feeds=cfg["feeds"], category=cfg.get("category"), symbols=tracked, q=q, limit=limit * 2)
    items = [{**r, "tier": "primary" if r.get("feed") != "yahoo_market" else ST.tier(r.get("source"))} for r in df.to_dict("records")]
    items, hidden = _filter_tiers(items, include_unrated)
    return clean({"items": items[:limit], "section": cfg["title"], "hidden_unrated": hidden, "unrated_note": ST.UNRATED_NOTE,
                  "sources": sorted({N.FEEDS[f]["source"] if f in N.FEEDS else "Yahoo Finance headlines (third-party publishers)" for f in cfg["feeds"]})})


# ------------------------------------------------------------------ documents
MAX_PDF = 50 * 1024 * 1024


def visible_doc_ids(uid: int) -> set[int]:
    """Documents this user may read: their own uploads plus shared (unowned) ones such as v1 uploads."""
    owner = db.read_df(db.select(db.documents.c.id, db.documents.c.user_id))
    if owner.empty:
        return set()
    return {int(i) for i in owner[(owner["user_id"] == uid) | owner["user_id"].isna()]["id"]}


@router.get("/documents")
def documents(request: Request, symbol: str | None = None):
    uid = current_user(request)
    df = U.list_documents(symbol)
    mine = visible_doc_ids(uid)
    df = df[df["id"].isin(mine)] if not df.empty else df
    return clean(df.to_dict("records"))


@router.post("/documents")
async def upload(request: Request, file: UploadFile = File(...), symbol: str | None = Form(None),
                 doc_type: str = Form("Annual Report"), period: str = Form(""), source_url: str | None = Form(None)):
    LIMITER.check(request, "upload", 10, 600)
    uid = current_user(request)
    name = re.sub(r"[^A-Za-z0-9 ._()-]", "_", file.filename or "document.pdf")[:120]
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    data = await file.read(MAX_PDF + 1)
    if len(data) > MAX_PDF:
        raise HTTPException(413, "File larger than 50 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "The file is not a valid PDF.")
    if symbol and not repo.get_company(symbol):
        raise HTTPException(400, "Unknown company.")
    try:
        ext = U.extract_pdf(data)
    except Exception as exc:
        raise HTTPException(400, f"Could not read this PDF: {exc}")
    doc_id = U.save_document(symbol, name, doc_type[:60], period[:30], source_url, ext, user_id=uid)
    return clean({"id": doc_id, "pages": ext["n_pages"], "tables": len(ext["tables"]), "scanned": ext["scanned"],
                  "truncated": ext["truncated"],
                  "warning": "Little or no text found - this looks like a scanned PDF (OCR not included)." if ext["scanned"] else None})


@router.delete("/documents/{doc_id}")
def delete_doc(doc_id: int, request: Request):
    uid = current_user(request)
    d = U.get_document(doc_id)
    owner = d.get("user_id") if d else None
    if not d or (owner is not None and owner == owner and int(owner) != uid):   # owner == owner filters NaN
        raise not_found("Document")
    U.delete_document(doc_id)
    return {"ok": True}


@router.get("/documents/{doc_id}/search")
def doc_search(doc_id: int, q: str, request: Request):
    if doc_id not in visible_doc_ids(current_user(request)):
        raise not_found("Document")
    return clean({"passages": rag.retrieve(q, [doc_id], k=8)})


# ------------------------------------------------------------------ AI assistant
class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    symbol: str | None = None
    doc_ids: list[int] = []
    history: list[dict] = []


@router.post("/assistant/ask")
def ask(body: Ask, request: Request):
    uid = current_user(request)
    LIMITER.check(request, "assistant", 20, 60)
    settings = users.get_pref(uid, "ai_settings", {}) or {}
    engine = settings.get("provider", "offline")
    doc_ids = [d for d in body.doc_ids if d in visible_doc_ids(uid)] if body.doc_ids else []
    passages = rag.retrieve(body.question, doc_ids, k=6) if doc_ids else []
    ctx = build_context(body.symbol, body.question) if body.symbol and repo.get_company(body.symbol) else None
    if ctx and passages:
        for p in passages:
            ctx.add(f"Document passage: {p['filename']}, page {p['page']}", p["text"], f"Uploaded document {p['filename']}",
                    "official_upload")
    ctx_text = ctx.render() if ctx else "\n\n".join(f"[D{i + 1}] {p['filename']} p.{p['page']}: {p['text']}" for i, p in enumerate(passages))
    meta = {"engine": "offline analyst (rule-based)", "grounding": None}
    if engine == "offline" or (not ctx and not passages):
        answer = offline.answer(ctx, body.question) if (ctx or not passages) else ""
        if passages:
            sents = rag.best_sentences(passages, body.question)
            if sents:
                answer = (answer + "\n\n" if answer else "") + "**From your documents (quoted verbatim)**\n" + \
                         "\n".join(f"- \"{s['sentence']}\" — *{s['filename']}, p. {s['page']}*" for s in sents)
            else:
                answer += "\n\nNo passage in the selected documents answers this question."
    else:
        LIMITER.check(request, "llm", 10, 60)
        try:
            hist = [{"role": h.get("role"), "content": str(h.get("content", ""))[:4000]} for h in body.history[-6:]
                    if h.get("role") in ("user", "assistant")]
            if engine == "anthropic":
                key = api_key_for(request)
                if not key or not settings.get("consent"):
                    raise P.ProviderError("Claude API is not configured (key + billing acknowledgement in Settings).")
                res = P.ask_anthropic(ctx_text, hist, body.question, settings.get("model", "claude-opus-5-5"), key)
                cost = P.estimate_cost_usd(res.model, res.input_tokens or 0, res.output_tokens or 0)
            else:
                res = P.ask_ollama(ctx_text, hist, body.question, settings.get("ollama_model", "llama3.1:8b"),
                                   settings.get("ollama_host", "http://localhost:11434"))
                cost = None
            answer = res.text
            total, untraced = grounding_check(answer, ctx_text)
            meta = {"engine": res.model, "tokens": [res.input_tokens, res.output_tokens], "cost_usd": cost,
                    "grounding": {"figures": total, "untraced": untraced[:10]}, "note": res.note}
        except P.ProviderError as exc:
            answer = offline.answer(ctx, body.question) if ctx else "\n".join(
                f"- \"{s['sentence']}\" — *{s['filename']}, p. {s['page']}*" for s in rag.best_sentences(passages, body.question))
            meta = {"engine": "offline analyst (fallback)", "warning": str(exc)}
    sources = ctx.source_list().to_dict("records") if ctx else []
    sources += [{"ID": f"D{i + 1}", "Content": f"{p['filename']} - page {p['page']}", "Source": "Uploaded document",
                 "Type": "OFFICIAL (UPLOADED)", "Retrieved": "—", "Link": None, "excerpt": p["text"][:400]}
                for i, p in enumerate(passages)]
    db.log_activity("Asked assistant", f"user {uid}: {body.question[:60]}")
    return clean({"answer": answer, "meta": meta, "sources": sources})


def api_key_for(request: Request) -> str | None:
    """The user's own key (this session only). A server-wide ANTHROPIC_API_KEY is used only when the owner opts in with
    EQUITYPILOT_SHARED_AI_KEY=1 - otherwise any visitor of a public deployment could spend the owner's API credit."""
    own = request.session.get("anthropic_key")
    if own:
        return own
    return P.find_api_key() if os.environ.get("EQUITYPILOT_SHARED_AI_KEY") == "1" else None


class AISettings(BaseModel):
    provider: str = Field(pattern="^(offline|anthropic|ollama)$")
    model: str | None = None
    consent: bool = False
    api_key: str | None = Field(None, max_length=300)
    ollama_host: str | None = Field(None, max_length=200)
    ollama_model: str | None = Field(None, max_length=80)


@router.get("/assistant/settings")
def get_ai_settings(request: Request):
    uid = current_user(request)
    s = users.get_pref(uid, "ai_settings", {}) or {}
    return clean({**s, "provider": s.get("provider", "offline"), "key_configured": bool(api_key_for(request)),
                  "models": P.ANTHROPIC_MODELS, "pricing_note": P.PRICING_NOTE,
                  "estimates": {m: {"company": P.estimate_cost_usd(m, 6000, 900), "document": P.estimate_cost_usd(m, 30000, 1500)}
                                for m in P.ANTHROPIC_MODELS}})


@router.put("/assistant/settings")
def put_ai_settings(body: AISettings, request: Request):
    uid = current_user(request)
    if body.model and body.model not in P.ANTHROPIC_MODELS:
        raise HTTPException(400, "Unknown model.")
    if body.api_key:
        request.session["anthropic_key"] = body.api_key.strip()   # signed session cookie only; never stored in the DB
    data = body.model_dump(exclude={"api_key"})
    users.set_pref(uid, "ai_settings", data)
    return {"ok": True}


# ------------------------------------------------------------------ reports
class ReportBody(BaseModel):
    analyst: str = Field("EquityPilot user", max_length=80)
    title: str | None = Field(None, max_length=140)
    thesis: str = Field("", max_length=5000)
    own_view: str = Field("", max_length=2000)
    sections: list[str] = ["overview", "financials", "ratios", "valuation", "technicals", "risk", "news", "sources"]


@router.post("/reports/{symbol}")
def report(symbol: str, body: ReportBody, request: Request):
    LIMITER.check(request, "report", 6, 60)
    uid = current_user(request)
    if not repo.get_company(symbol):
        raise not_found("Company")
    # the PDF builder reads saved valuation / notes from global settings: copy this user's for the build
    for key in (f"valuation:{symbol}", f"notes:{symbol}", f"risk_notes:{symbol}"):
        val = users.get_pref(uid, key)
        if val:
            db.set_setting(key, val)
        else:
            db.execute(db.delete(db.settings).where(db.settings.c.key == key))
    pdf = build_report(symbol, ReportOptions(**body.model_dump()))
    fname = f"{F.safe_filename(symbol)}_research_{db.utcnow():%Y%m%d_%H%M}.pdf"
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ------------------------------------------------------------------ learning, glossary, data sources
@router.get("/learn")
def learn(request: Request):
    uid = current_user(request)
    return clean({"modules": MODULES, "progress": users.get_pref(uid, "learning_progress", {}),
                  "glossary": [{"term": k, **v} for k, v in GLOSSARY.items()]})


@router.get("/learn/metrics")
def metrics_guide():
    """Plain-English metric explanations used by tooltips and 'Explain' panels across the app."""
    from equitypilot.content import metrics_guide as MG
    return {"guide": MG.GUIDE, "benchmark_note": MG.BENCHMARK_NOTE}


class QuizResult(BaseModel):
    module: str
    score: int = Field(ge=0, le=20)


@router.post("/learn/progress")
def learn_progress(body: QuizResult, request: Request):
    uid = current_user(request)
    if body.module not in {m["id"] for m in MODULES}:
        raise not_found("Module")
    prog = users.get_pref(uid, "learning_progress", {}) or {}
    prev = prog.get(body.module, {})
    prog[body.module] = {"best": max(body.score, prev.get("best", 0)), "last": body.score,
                         "attempts": prev.get("attempts", 0) + 1, "updated": F.ist(db.utcnow())}
    users.set_pref(uid, "learning_progress", prog)
    return prog


@router.get("/data/sources")
def data_sources(request: Request):
    current_user(request)
    status = repo.data_status()
    real = status[~status["is_sample"].astype(bool)] if not status.empty else status
    feeds = {k: {"source": v["source"], "last_refreshed": db.get_setting(f"feed_refreshed:{k}")} for k, v in N.FEEDS.items()}
    return clean({"sources": OFFICIAL_SOURCES + [
        {"name": "NSE RSS feeds", "url": "https://www.nseindia.com/rss-feed", "use": "Corporate announcements and results with filing links",
         "access": "Public RSS feeds published by NSE"},
        {"name": "AMFI market-cap categorisation", "url": "https://www.amfiindia.com", "use": "Large/Mid/Small-cap classification",
         "access": f"Official half-yearly list ({db.get_setting('securities_as_of') or 'not downloaded'})"}],
        "feeds": feeds, "companies_tracked": len(real), "securities_listed": int(db.read_df(db.select(db.securities.c.isin)).shape[0]),
        "offline": config.OFFLINE, "data_types": config.DATA_TYPES,
        "realtime_note": "Real-time NSE/BSE prices require a licensed vendor or a broker API linked to your own trading account. "
                         "EquityPilot currently uses delayed Yahoo Finance data and labels every price accordingly."})
