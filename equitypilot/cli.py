"""Command-line tools - e.g. for a scheduled (Task Scheduler / cron) data refresh.

    python -m equitypilot status
    python -m equitypilot refresh                 # quotes + statements + prices for the screener universe
    python -m equitypilot refresh --quotes-only   # fast: delayed quotes only
    python -m equitypilot refresh --news          # also fetch headlines
    python -m equitypilot refresh --symbols TCS INFY RELIANCE
"""
from __future__ import annotations

import argparse
import sys
import time

from . import config, db
from .data import repository as repo
from .data import sample
from .data.universe import normalise_symbol


def _universe() -> list[str]:
    syms = [s for s in repo.list_companies(universe_only=True)["symbol"] if not s.startswith("SAMPLE-")]
    return syms


def cmd_status(_: argparse.Namespace) -> int:
    st = repo.data_status()
    real = st[~st["is_sample"].astype(bool)] if not st.empty else st
    print(f"Database: {config.DB_PATH}")
    print(f"Companies: {len(st)} ({len(real)} real, {len(st) - len(real)} fictional samples)")
    if not real.empty:
        q = real["quote_fetched"].dropna() if "quote_fetched" in real else []
        f = real["fin_fetched"].dropna() if "fin_fetched" in real else []
        if len(q):
            print(f"Quotes retrieved:     oldest {min(q)} UTC · newest {max(q)} UTC")
        if len(f):
            print(f"Statements retrieved: oldest {min(f)} UTC · newest {max(f)} UTC")
    return 0


def cmd_refresh(a: argparse.Namespace) -> int:
    if config.OFFLINE:
        print("Offline mode is on (EQUITYPILOT_OFFLINE=1) - nothing to refresh.")
        return 1
    syms = [normalise_symbol(s) for s in a.symbols] if a.symbols else _universe()
    if not syms:
        print("No real companies in the universe yet - running the default universe download.")
        syms = None
    failures = 0
    if a.quotes_only:
        for i, s in enumerate(syms or [], 1):
            ok, msg = repo.refresh_company(s)
            failures += not ok
            print(f"[{i}/{len(syms)}] {s}: {'OK' if ok else msg}", flush=True)
            time.sleep(a.pause)
    else:
        res = repo.refresh_universe(syms, progress=lambda p, m: print(m, flush=True), pause=a.pause)
        bad = [r for r in res if any(v != "OK" for k, v in r.items() if k != "symbol")]
        failures += len(bad)
        for r in bad:
            print("Problem:", r)
    if a.news:
        for s in syms or _universe():
            ok, msg = repo.refresh_news(s)
            print(f"news {s}: {msg}", flush=True)
            time.sleep(a.pause)
    db.log_activity("Scheduled refresh (CLI)", f"{len(syms or [])} companies, {failures} problem(s)")
    print(f"Done with {failures} problem(s).")
    return 0 if failures == 0 else 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m equitypilot", description="EquityPilot AI command-line tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show what is cached").set_defaults(fn=cmd_status)
    r = sub.add_parser("refresh", help="refresh market data from Yahoo Finance")
    r.add_argument("--symbols", nargs="+", help="NSE symbols (default: screener universe)")
    r.add_argument("--quotes-only", action="store_true", help="only refresh delayed quotes (fast)")
    r.add_argument("--news", action="store_true", help="also fetch news headlines")
    r.add_argument("--pause", type=float, default=0.6, help="seconds between companies (be polite to the provider)")
    r.set_defaults(fn=cmd_refresh)
    a = p.parse_args(argv)
    db.get_engine()
    sample.load_sample_data()
    return a.fn(a)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
