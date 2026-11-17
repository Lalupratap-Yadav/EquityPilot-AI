"""Earnings & Results calendar and Corporate Actions centre (official exchange filings; see data/events.py)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request

from equitypilot.content.industries import BY_ID
from equitypilot.data import events as EV
from equitypilot.data import repository as repo

from .core import LIMITER, clean, current_user

router = APIRouter(prefix="/api/events", tags=["events"])


def _date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, "Dates must be YYYY-MM-DD.") from None


def _industry(industry: str | None) -> str | None:
    if industry and industry not in BY_ID:
        raise HTTPException(400, "Unknown industry.")
    return industry


@router.get("/results")
def results(request: Request, view: str = Query("upcoming", pattern="^(upcoming|recent|past|all)$"),
            q: str | None = Query(None, max_length=80), industry: str | None = Query(None, max_length=60),
            start: str | None = Query(None, max_length=10), end: str | None = Query(None, max_length=10),
            tracked_only: bool = False, limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
    current_user(request)
    LIMITER.check(request, "events", 120, 60)
    out = EV.results_calendar(view, q, _industry(industry), tracked_only, _date(start), _date(end))
    out["items"] = out["items"][offset: offset + limit]
    out["industries"] = {k: v["name"] for k, v in BY_ID.items()}
    return clean(out)


@router.get("/company/{symbol}")
def company(symbol: str, request: Request):
    current_user(request)
    if not repo.get_company(symbol):
        raise HTTPException(404, f"Company {symbol} not found.")
    return clean(EV.company_events(symbol))


@router.get("/actions")
def actions(request: Request, when: str = Query("upcoming", pattern="^(upcoming|past)$"),
            type: str | None = Query(None, max_length=20), q: str | None = Query(None, max_length=80),
            industry: str | None = Query(None, max_length=60), tracked_only: bool = False,
            limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
    current_user(request)
    LIMITER.check(request, "events", 120, 60)
    if type and type not in EV.ACTION_TYPES:
        raise HTTPException(400, "Unknown action type.")
    out = EV.actions_centre(when, type, q, _industry(industry), tracked_only)
    out["items"] = out["items"][offset: offset + limit]
    out["industries"] = {k: v["name"] for k, v in BY_ID.items()}
    return clean(out)
