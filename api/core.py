"""Shared API plumbing: user resolution, JSON cleaning, rate limiting, TTL cache."""
from __future__ import annotations

import math
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime
from functools import wraps
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import HTTPException, Request

from equitypilot import config, users


def secret_key() -> str:
    """EQUITYPILOT_SECRET env var, else a random key generated once and kept in the data folder."""
    import os
    if os.environ.get("EQUITYPILOT_SECRET"):
        return os.environ["EQUITYPILOT_SECRET"]
    config.ensure_dirs()
    f = Path(config.DATA_DIR) / "secret.key"
    if not f.exists():
        f.write_text(secrets.token_urlsafe(48))
    return f.read_text().strip()


def current_user(request: Request) -> int:
    """Resolve the user from the signed session cookie; create a guest profile on first visit."""
    uid = request.session.get("uid")
    if uid and users.get_user(int(uid)):
        return int(uid)
    uid = users.create_guest()
    request.session["uid"] = uid
    return uid


def clean(obj):
    """Make pandas / numpy / datetime values JSON-safe (NaN and inf become null)."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return clean(obj.to_dict("records"))
    if isinstance(obj, pd.Series):
        return clean(obj.to_dict())
    if isinstance(obj, (pd.Timestamp, datetime)):
        return None if pd.isna(obj) else obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    if obj is pd.NaT:
        return None
    try:
        if pd.isna(obj) is True:
            return None
    except (TypeError, ValueError):
        pass
    return obj


class RateLimiter:
    """Sliding-window limit per client and bucket (protects the provider and paid AI calls)."""

    def __init__(self):
        self.hits: dict[tuple, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, request: Request, bucket: str, limit: int, window: float) -> None:
        key = (request.client.host if request.client else "?", bucket)
        now = time.time()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(429, f"Too many requests - please wait a little (limit {limit} per {int(window)}s).")
            q.append(now)


LIMITER = RateLimiter()


def ttl_cache(seconds: float):
    """Memoise a function's result for `seconds` (per argument tuple)."""
    def deco(fn):
        store: dict = {}
        lock = threading.Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            with lock:
                if key in store and now - store[key][0] < seconds:
                    return store[key][1]
            val = fn(*args, **kwargs)
            with lock:
                store[key] = (now, val)
            return val

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper
    return deco


def not_found(what: str) -> HTTPException:
    return HTTPException(404, f"{what} not found")
