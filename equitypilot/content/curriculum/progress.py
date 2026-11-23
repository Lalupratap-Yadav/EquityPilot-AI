"""Learning progress: which lessons are complete, quiz scores, recently viewed lessons, and a per-module summary.

Stored per user (users.set_pref 'learning_progress'), so it is private to the account. Only learning activity is kept:
no opinions, notes or investment decisions. Version 1 (the earlier eight-module centre) stored
{module: {best, last, attempts, updated}}; normalise() converts it to version 2 without losing scores.
"""
from __future__ import annotations

from . import LEGACY_TOTALS, LESSONS, MODULE_ALIASES, MODULES, ORDER, PASS_MARK, QUESTIONS, resolve_module

RECENT_MAX = 8


def empty() -> dict:
    return {"v": 2, "lessons": {}, "quizzes": {}, "recent": []}


def normalise(raw) -> dict:
    """Any stored value (missing, version 1 or version 2) as a clean version-2 record."""
    if not isinstance(raw, dict):
        return empty()
    if raw.get("v") == 2:
        out = empty()
        out["lessons"] = {k: v for k, v in (raw.get("lessons") or {}).items() if k in LESSONS and isinstance(v, dict)}
        out["quizzes"] = {k: v for k, v in (raw.get("quizzes") or {}).items() if valid_quiz(k) and isinstance(v, dict)}
        out["recent"] = [x for x in (raw.get("recent") or []) if x in LESSONS][:RECENT_MAX]
        return out
    out = empty()
    for mid, rec in raw.items():                    # version 1: one quiz record per old module
        m = resolve_module(mid)
        if not m or not isinstance(rec, dict):
            continue
        out["quizzes"][m["id"]] = {"best": int(rec.get("best", 0)), "last": int(rec.get("last", 0)),
                                   "total": LEGACY_TOTALS.get(mid, int(rec.get("best", 0)) or 1),
                                   "attempts": int(rec.get("attempts", 1)), "updated": rec.get("updated"), "legacy": True}
    return out


def valid_quiz(qid: str) -> bool:
    return qid == "revision" or qid in LESSONS or resolve_module(qid) is not None


def quiz_size(qid: str) -> int:
    if qid in LESSONS:
        return len(LESSONS[qid]["check"])
    m = resolve_module(qid)
    if m:
        return len(m["test"])
    return 20                                       # revision quizzes are capped at 20 questions


def mark_lesson(prog: dict, lid: str, done: bool, now: str) -> dict:
    if done:
        prog["lessons"][lid] = {"done": now}
    else:
        prog["lessons"].pop(lid, None)
    return prog


def mark_viewed(prog: dict, lid: str) -> dict:
    prog["recent"] = [lid] + [x for x in prog["recent"] if x != lid][:RECENT_MAX - 1]
    return prog


def record_quiz(prog: dict, qid: str, score: int, total: int, now: str) -> dict:
    key = MODULE_ALIASES.get(qid, qid)
    prev = prog["quizzes"].get(key, {})
    if prev.get("legacy") or prev.get("total") != total:   # a different question set: start the best score afresh
        prev = {"attempts": prev.get("attempts", 0)}
    prog["quizzes"][key] = {"best": max(score, prev.get("best", 0)), "last": score, "total": total,
                            "attempts": prev.get("attempts", 0) + 1, "updated": now}
    return prog


def summary(prog: dict) -> dict:
    """What the Learning Centre home shows: per-module completion and test status, overall counts, where to continue."""
    done = prog["lessons"]
    modules = {}
    for m in MODULES:
        ids = [les["id"] for les in m["lessons"]]
        n_done = sum(1 for i in ids if i in done)
        test = prog["quizzes"].get(m["id"])
        passed = bool(test and not test.get("legacy") and test["best"] >= PASS_MARK * test["total"])
        modules[m["id"]] = {"lessons_done": n_done, "lessons_total": len(ids), "test": test, "passed": passed,
                            "complete": n_done == len(ids) and passed}
    nxt = next((lid for lid in prog["recent"] if lid not in done), None) or next((lid for lid in ORDER if lid not in done), None)
    return {"modules": modules, "lessons_done": sum(1 for lid in done if lid in LESSONS), "lessons_total": len(LESSONS),
            "modules_complete": sum(1 for v in modules.values() if v["complete"]), "modules_total": len(MODULES),
            "continue": nxt, "recent": prog["recent"], "lessons": done, "quizzes": prog["quizzes"],
            "questions_total": len(QUESTIONS)}
