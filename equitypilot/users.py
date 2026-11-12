"""Users: automatic guest profiles (no registration needed) and optional username/password accounts.

Passwords are hashed with scrypt (Python standard library) and a per-user random salt; plain
passwords are never stored or logged. All personal data (watchlists, alerts, portfolio, virtual
trades, saved screens, preferences) is keyed by user id.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from typing import Any

from . import db

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")


class AuthError(ValueError):
    pass


def _hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def _verify(password: str, stored: str) -> bool:
    try:
        _, salt_hex, hash_hex = stored.split("$")
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt_hex)).split("$")[2], hash_hex)


def create_guest() -> int:
    res = db.execute(db.insert(db.users).values(display_name=f"Guest {secrets.randbelow(9000) + 1000}", is_guest=True,
                                                created_at=db.utcnow(), last_seen=db.utcnow()))
    uid = int(res.inserted_primary_key[0])
    ensure_defaults(uid)
    return uid


def ensure_defaults(uid: int) -> None:
    """Every user starts with one watchlist."""
    wl = db.read_df(db.select(db.watchlists.c.id).where(db.watchlists.c.user_id == uid).limit(1))
    if wl.empty:
        db.execute(db.insert(db.watchlists).values(user_id=uid, name="My watchlist", created_at=db.utcnow()))


def get_user(uid: int) -> dict | None:
    df = db.read_df(db.select(db.users).where(db.users.c.id == uid))
    if df.empty:
        return None
    u = df.iloc[0].to_dict()
    u.pop("password_hash", None)
    return u


def touch(uid: int) -> None:
    db.execute(db.update(db.users).where(db.users.c.id == uid).values(last_seen=db.utcnow()))


def register(uid: int, username: str, password: str, display_name: str | None = None) -> dict:
    """Turn the current guest profile into an account (keeps all its data)."""
    if not USERNAME_RE.match(username or ""):
        raise AuthError("Username must be 3-30 characters: letters, digits, dot, dash or underscore.")
    if len(password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")
    taken = db.read_df(db.select(db.users.c.id).where(db.users.c.username == username.lower()))
    if not taken.empty:
        raise AuthError("That username is already taken.")
    db.execute(db.update(db.users).where(db.users.c.id == uid).values(
        username=username.lower(), password_hash=_hash(password), is_guest=False,
        display_name=(display_name or username).strip()[:40]))
    return get_user(uid)


def login(username: str, password: str) -> int:
    df = db.read_df(db.select(db.users.c.id, db.users.c.password_hash).where(db.users.c.username == (username or "").lower()))
    if df.empty or not _verify(password or "", df.iloc[0]["password_hash"]):
        raise AuthError("Incorrect username or password.")
    uid = int(df.iloc[0]["id"])
    touch(uid)
    return uid


def update_profile(uid: int, display_name: str | None = None, show_on_leaderboard: bool | None = None) -> dict:
    vals = {}
    if display_name is not None:
        name = display_name.strip()[:40]
        if not name:
            raise AuthError("Display name cannot be empty.")
        vals["display_name"] = name
    if show_on_leaderboard is not None:
        vals["show_on_leaderboard"] = bool(show_on_leaderboard)
    if vals:
        db.execute(db.update(db.users).where(db.users.c.id == uid).values(**vals))
    return get_user(uid)


# ------------------------------------------------------------------ per-user settings
def get_pref(uid: int, key: str, default: Any = None) -> Any:
    df = db.read_df(db.select(db.user_settings.c.value).where(db.user_settings.c.user_id == uid)
                    .where(db.user_settings.c.key == key))
    if df.empty:
        return default
    try:
        return json.loads(df.iloc[0]["value"])
    except (TypeError, ValueError):
        return df.iloc[0]["value"]


def set_pref(uid: int, key: str, value: Any) -> None:
    db.upsert(db.user_settings, [{"user_id": uid, "key": key, "value": json.dumps(value)}], ["user_id", "key"])


def all_prefs(uid: int) -> dict:
    df = db.read_df(db.select(db.user_settings).where(db.user_settings.c.user_id == uid))
    out = {}
    for _, r in df.iterrows():
        try:
            out[r["key"]] = json.loads(r["value"])
        except (TypeError, ValueError):
            out[r["key"]] = r["value"]
    return out


def export_user_data(uid: int) -> dict:
    """Everything stored for a user (backup / data portability)."""
    def rows(table, col="user_id"):
        return db.read_df(db.select(table).where(table.c[col] == uid)).astype(object).where(lambda d: d.notna(), None) \
            .to_dict("records")
    wls = rows(db.watchlists)
    items = db.read_df(db.select(db.watchlist_items).where(db.watchlist_items.c.watchlist_id.in_([w["id"] for w in wls] or [-1])))
    return {"user": get_user(uid), "watchlists": wls, "watchlist_items": items.astype(object).where(items.notna(), None).to_dict("records"),
            "alerts": rows(db.alerts), "holdings": rows(db.holdings), "paper_account": rows(db.paper_accounts),
            "paper_trades": rows(db.paper_trades), "saved_screens": rows(db.saved_screens),
            "preferences": all_prefs(uid)}
