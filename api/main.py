"""EquityPilot AI - FastAPI application.

Run (development):   uvicorn api.main:app --reload --port 8000     (frontend: cd web && npm run dev)
Run (production):    cd web && npm run build ; uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from equitypilot import config, db
from equitypilot.data import feeds, marketdata, sample, securities

from . import routes_company, routes_explore, routes_invest, routes_market, routes_research, routes_user
from .core import secret_key

logging.basicConfig(level=os.environ.get("EQUITYPILOT_LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("equitypilot.api")
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


async def warmer() -> None:
    """Background refresh so pages read from cache: universe quotes, feeds, securities list."""
    await asyncio.sleep(3)
    while True:
        try:
            if not config.OFFLINE:
                syms = routes_market.tracked_real()
                await asyncio.to_thread(marketdata.QUOTES.get, syms)
                routes_market.universe_snapshot.cache_clear()
                await asyncio.to_thread(marketdata.index_overview)
                await asyncio.to_thread(routes_explore.metrics_frame, True)  # screener / explore / industries
                await asyncio.to_thread(feeds.refresh_all)
                await asyncio.to_thread(securities.refresh_securities)
        except Exception as exc:  # keep the loop alive whatever happens
            log.warning("warmer: %s", exc)
        await asyncio.sleep(90 if marketdata.market_status()["open"] else 900)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.get_engine()
    sample.load_sample_data()
    task = asyncio.create_task(warmer()) if os.environ.get("EQUITYPILOT_NO_WARMER") != "1" else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="EquityPilot AI API", version="2.0.0", lifespan=lifespan,
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


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Something went wrong on the server. The error has been logged."}, status_code=500)


for r in (routes_market, routes_company, routes_explore, routes_user, routes_invest, routes_research):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version, "offline": config.OFFLINE}


# ------------------------------------------------------------------ built frontend (single-page app)
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = WEB_DIST / path
        if path and target.is_file() and WEB_DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
