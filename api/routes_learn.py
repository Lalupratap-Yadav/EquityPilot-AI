"""Learning Centre: curriculum overview, modules with lessons and tests, quizzes, glossary, ratio guide, case studies
and per-user progress. All content is served from memory; case studies read stored statements only (no provider calls)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator

from equitypilot import db, users
from equitypilot import formatting as F
from equitypilot.content import curriculum as C
from equitypilot.content.curriculum import progress as PR

from .core import LIMITER, clean, current_user, not_found

router = APIRouter(prefix="/api", tags=["learn"])


def _progress(uid: int) -> dict:
    return PR.normalise(users.get_pref(uid, "learning_progress", None))


@router.get("/learn")
def learn(request: Request):
    """Levels and module cards, the user's progress summary, the glossary and the official sources."""
    uid = current_user(request)
    return clean({**C.overview(), "progress": PR.summary(_progress(uid)), "glossary": C.glossary(),
                  "sources": C.SOURCES, "case_companies": _case_companies()})


@router.get("/learn/modules/{mid}")
def learn_module(mid: str, request: Request):
    current_user(request)
    m = C.resolve_module(mid)
    if not m:
        raise not_found("Module")
    return C.module_payload(m)


@router.get("/learn/lessons/{lid}")
def learn_lesson(lid: str, request: Request):
    current_user(request)
    les = C.LESSONS.get(lid)
    if not les:
        raise not_found("Lesson")
    m = C.MODULE_BY_ID[les["module"]]
    return {"lesson": C.lesson_payload(les), "module": C.module_card(m)}


@router.get("/learn/quiz/{qid}")
def learn_quiz(qid: str, request: Request, modules: str = Query("", max_length=300), n: int = Query(10, ge=3, le=20),
               seed: int | None = None):
    """A lesson's knowledge check (topic quiz), a module completion test, or a revision quiz across modules."""
    current_user(request)
    if qid == "revision":
        ids = [x for x in modules.split(",") if x.strip()]
        return {"id": "revision", "title": "Revision quiz", "questions": C.revision_quiz(ids, n, seed)}
    if qid in C.LESSONS:
        les = C.LESSONS[qid]
        return {"id": qid, "title": f"Topic quiz: {les['title']}", "questions": [C.public_question(q) for q in les["check"]]}
    m = C.resolve_module(qid)
    if not m:
        raise not_found("Quiz")
    return {"id": m["id"], "title": f"Module test: {m['title']}", "questions": [C.public_question(q) for q in m["test"]]}


@router.get("/learn/glossary")
def learn_glossary(request: Request):
    current_user(request)
    return {"terms": C.glossary(), "reviewed": C.REVIEWED}


@router.get("/learn/metrics")
def metrics_guide():
    """Plain-English metric explanations used by tooltips and 'Explain' panels across the app."""
    from equitypilot.content import metrics_guide as MG
    return {"guide": MG.GUIDE, "benchmark_note": MG.BENCHMARK_NOTE}


def _case_companies() -> list[dict]:
    from equitypilot.content.curriculum.cases import CASE_COMPANIES
    from equitypilot.data import repository as repo
    names = repo.company_names(CASE_COMPANIES)
    return [{"symbol": s, "name": names.get(s) or s} for s in CASE_COMPANIES]


@router.get("/learn/case/{symbol}")
def learn_case(symbol: str, request: Request):
    current_user(request)
    LIMITER.check(request, "learn_case", 60, 60)
    from equitypilot.content.curriculum.cases import case_study
    from equitypilot.data.universe import normalise_symbol
    out = case_study(normalise_symbol(symbol))
    if out is None:
        raise not_found("Company")
    return clean(out)


class ProgressIn(BaseModel):
    """One learning event. `module` + `score` is the earlier eight-module format and is still accepted."""
    lesson: str | None = Field(None, max_length=60)
    done: bool | None = None
    viewed: str | None = Field(None, max_length=60)
    quiz: str | None = Field(None, max_length=60)
    score: int | None = Field(None, ge=0, le=50)
    total: int | None = Field(None, ge=1, le=50)
    module: str | None = Field(None, max_length=60)

    @model_validator(mode="after")
    def one_event(self):
        if not (self.lesson or self.viewed or self.quiz or self.module):
            raise ValueError("Send a lesson, viewed, quiz or module event.")
        return self


@router.post("/learn/progress")
def learn_progress(body: ProgressIn, request: Request):
    uid = current_user(request)
    prog = _progress(uid)
    now = F.ist(db.utcnow())
    if body.lesson:
        if body.lesson not in C.LESSONS:
            raise not_found("Lesson")
        PR.mark_lesson(prog, body.lesson, body.done is not False, now)
    if body.viewed:
        if body.viewed not in C.LESSONS:
            raise not_found("Lesson")
        PR.mark_viewed(prog, body.viewed)
    quiz = body.quiz or body.module
    if quiz:
        if not PR.valid_quiz(quiz):
            raise not_found("Quiz")
        if body.score is None:
            raise HTTPException(422, "A quiz result needs a score.")
        total = body.total or PR.quiz_size(quiz)
        if total > PR.quiz_size(quiz) or body.score > total:
            raise HTTPException(422, "The score does not fit this quiz.")
        PR.record_quiz(prog, quiz, body.score, total, now)
    users.set_pref(uid, "learning_progress", prog)
    return clean(PR.summary(prog))


@router.delete("/learn/progress")
def learn_progress_reset(request: Request):
    """Clear this user's learning progress (lessons, quiz scores and recently viewed)."""
    uid = current_user(request)
    users.set_pref(uid, "learning_progress", PR.empty())
    return clean(PR.summary(PR.empty()))
