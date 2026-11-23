"""Learning Centre modules in the classic format (summary, sections, formulas, MCQ quiz), used by the Streamlit page and
the Explore topics. The content itself lives in equitypilot/content/curriculum (three levels, lessons, quizzes);
this module adapts it so older callers keep working. Regulatory content is a simplified educational overview, checked
against the official sources cited in each lesson - always refer to the current SEBI regulations and NISM workbooks.
"""
from .curriculum import legacy_modules

MODULES = legacy_modules()


def module(mid: str) -> dict | None:
    from .curriculum import MODULE_ALIASES
    mid = MODULE_ALIASES.get(mid, mid)
    return next((m for m in MODULES if m["id"] == mid), None)


def total_questions() -> int:
    return sum(len(m["quiz"]) for m in MODULES)
