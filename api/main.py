"""EquityPilot AI - FastAPI application.

Run (development):   uvicorn api.main:app --reload --port 8000     (frontend: cd web && npm run dev)
Run (production):    cd web && npm run build ; uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from equitypilot import config, db, workers
from equitypilot.data import feeds, marketdata, sample, securities

from . import (routes_company, routes_events, routes_explore, routes_invest, routes_market, routes_news, routes_research,
               routes_search, routes_user)
from .core import secret_key

class JsonFormatter(logging.Formatter):
    """One JSON object per line (EQUITYPILOT_LOG_JSON=1) - easy to search and ship to a log service."""
    def format(self, record: logging.LogRecord) -> str:
        import json
        out = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        for k in ("request_id", "method", "path", "status", "ms"):
            if hasattr(record, k):
                out[k] = getattr(record, k)
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


# Windows consoles default to a legacy code page; never let a ₹ or a company name with accents crash a log call
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter() if os.environ.get("EQUITYPILOT_LOG_JSON") == "1"
                      else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=os.environ.get("EQUITYPILOT_LOG_LEVEL", "INFO"), handlers=[_handler])
log = logging.getLogger("equitypilot.api")
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


async def _warm_step(name: str, fn, *args) -> None:
    """One warm-up step in a worker thread: timed, and isolated so a failure never skips the steps after it."""
    import time
    t0 = time.perf_counter()
    try:
        await asyncio.to_thread(fn, *args)
    except Exception as exc:
        log.warning("warmer step %s failed: %s", name, exc)
        return
    secs = time.perf_counter() - t0
    (log.warning if secs > 30 else log.info)("warmer step %s took %.1f s", name, secs)


async def warmer() -> None:
    """Background refresh so pages read from cache: universe quotes, feeds, securities list."""
    await asyncio.sleep(3)
    if not config.OFFLINE:                         # the Market Tracker opens on NIFTY 50 / 1D: have it ready first
        await _warm_step("NIFTY chart", routes_market._bars_cached, "^NSEI", "1D")
    while True:
        if not config.OFFLINE:
            syms = routes_market.tracked_real() + marketdata.HOT.symbols()   # companies + indices + on-screen symbols
            await _warm_step("quotes", marketdata.QUOTES.get, syms)
            routes_market.universe_snapshot.cache_clear()
            await _warm_step("index tiles", marketdata.index_overview)
            await _warm_step("universe metrics", routes_explore.metrics_frame, True)   # screener / explore / industries
            await _warm_step("news feeds", feeds.refresh_all)
            await _warm_step("securities list", securities.refresh_securities)
        await asyncio.sleep(90 if marketdata.market_status()["open"] else 900)


HOT_INTERVAL = int(os.environ.get("EQUITYPILOT_HOT_INTERVAL", "20"))


async def hot_refresher() -> None:
    """While the market is in session (or pre-open), refresh the 'hot set' - every index plus the symbols someone has
    on screen - every HOT_INTERVAL seconds, so tiles, tickers and charts move with the provider's latest values."""
    await asyncio.sleep(5)
    while True:
        phase = "closed"
        try:
            phase = marketdata.market_status()["phase"]
            if not config.OFFLINE and phase in ("open", "pre-open"):
                await asyncio.to_thread(marketdata.QUOTES.refresh, marketdata.HOT.symbols())
        except Exception as exc:
            log.warning("hot refresher: %s", exc)
        await asyncio.sleep(HOT_INTERVAL if phase in ("open", "pre-open") else 300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.get_engine()
    sample.load_sample_data()
    warm = os.environ.get("EQUITYPILOT_NO_WARMER") != "1"
    if warm:
        workers.enable()                    # bulk quote downloads and metrics recomputes in a worker process
    tasks = [asyncio.create_task(warmer()), asyncio.create_task(hot_refresher())] if warm else []
    yield
    for t in tasks:
        t.cancel()
    workers.shutdown()


app = FastAPI(title="EquityPilot AI API", version="2.7.0", lifespan=lifespan,
              description="Indian equity research platform API. Educational use; not investment advice.")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SessionMiddleware, secret_key=secret_key(), session_cookie="ep_session", max_age=60 * 60 * 24 * 365,
                   same_site="lax", https_only=os.environ.get("EQUITYPILOT_SECURE_COOKIES") == "1")


SECURITY_HEADERS = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin")]


class SecurityHeaders:
    """Pure ASGI middleware (no BaseHTTPMiddleware: cancelled browser requests no longer log spurious errors)."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                present = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [h for h in SECURITY_HEADERS if h[0] not in present]
            await send(message)
        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeaders)

SLOW_MS = float(os.environ.get("EQUITYPILOT_SLOW_MS", "2000"))
access_log = logging.getLogger("equitypilot.access")


class RequestLog:
    """Request id + timing for every API call (pure ASGI). Slow requests are logged as warnings; the id is returned
    in the X-Request-ID header so a user-reported error can be found in the logs."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        import time
        import uuid
        rid = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        status = {"code": 0}

        async def send_wrapped(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                message["headers"] = list(message.get("headers", [])) + [(b"x-request-id", rid.encode())]
            await send(message)
        try:
            await self.app(scope, receive, send_wrapped)
        finally:
            ms = round((time.perf_counter() - t0) * 1000, 1)
            extra = {"request_id": rid, "method": scope.get("method"), "path": scope["path"], "status": status["code"], "ms": ms}
            if status["code"] >= 500:
                access_log.error("%s %s -> %s in %s ms [%s]", scope.get("method"), scope["path"], status["code"], ms, rid, extra=extra)
            elif ms > SLOW_MS and not scope["path"].startswith(("/api/assistant/stream", "/api/ws/")):
                access_log.warning("slow request %s %s -> %s in %s ms [%s]", scope.get("method"), scope["path"], status["code"], ms, rid, extra=extra)
            else:
                access_log.debug("%s %s -> %s in %s ms [%s]", scope.get("method"), scope["path"], status["code"], ms, rid, extra=extra)


app.add_middleware(RequestLog)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Something went wrong on the server. The error has been logged."}, status_code=500)


for r in (routes_search, routes_news, routes_events, routes_market, routes_company, routes_explore, routes_user, routes_invest,
          routes_research):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    prov = marketdata.provider()
    return {"status": "ok", "version": app.version, "offline": config.OFFLINE,
            "market_data": {"provider": prov.name, "realtime": prov.realtime, "error": getattr(prov, "last_error", None),
                            "watchers": marketdata.HOT.clients(), "refresh_seconds": HOT_INTERVAL}}


# ------------------------------------------------------------------ built frontend (single-page app)
class ImmutableStatic(StaticFiles):
    """Vite emits content-hashed file names under /assets, so browsers may cache them for a year."""
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            resp.headers["cache-control"] = "public, max-age=31536000, immutable"
        return resp


if WEB_DIST.exists():
    app.mount("/assets", ImmutableStatic(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not found."}, status_code=404)
        target = WEB_DIST / path
        if path and target.is_file() and WEB_DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html", headers={"cache-control": "no-cache"})
else:
    @app.get("/", include_in_schema=False)
    def frontend_missing():
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h2>EquityPilot API is running, but the web app has not been built yet.</h2>"
                            "<p>Run <code>cd web</code>, <code>npm install</code>, <code>npm run build</code>, then restart the server "
                            "(or simply run <code>start.bat</code>). The API documentation is at <a href='/docs'>/docs</a>.</p>")
