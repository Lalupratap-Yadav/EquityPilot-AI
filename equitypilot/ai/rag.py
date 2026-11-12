"""Retrieval over uploaded documents (RAG).

Documents are split into overlapping passages that keep their page number. Retrieval uses
Okapi BM25 - a transparent, offline ranking method (no external embedding service), so every
answer can show exactly which passages (document + page) it relies on.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import pandas as pd

from .. import db
from ..data import uploads as U

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were will with
which their they our we not but been than into also any all can may such these those its per over under""".split())
TOKEN = re.compile(r"[a-z0-9][a-z0-9.%-]*")


def tokens(text: str) -> list[str]:
    return [t.strip(".-") for t in TOKEN.findall((text or "").lower()) if t not in STOP and len(t) > 1]


def chunk_pages(pages: list[dict], size: int = 900, overlap: int = 150) -> list[dict]:
    out = []
    for p in pages:
        text = re.sub(r"\s+", " ", p["text"] or "").strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):                       # end on a sentence/word boundary when possible
                cut = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
                end = cut + 1 if cut > start + size // 2 else end
            out.append({"page": p["page"], "text": text[start:end].strip()})
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return out


def index_document(doc_id: int) -> int:
    doc = U.get_document(doc_id)
    if not doc:
        return 0
    chunks = chunk_pages(U.text_to_pages(doc["text"]))
    db.execute(db.delete(db.doc_chunks).where(db.doc_chunks.c.doc_id == doc_id))
    if chunks:
        db.execute(db.insert(db.doc_chunks), [{"doc_id": doc_id, "chunk_no": i, "page": c["page"], "text": c["text"]}
                                             for i, c in enumerate(chunks)])
    return len(chunks)


def _chunks(doc_ids: list[int]) -> pd.DataFrame:
    df = db.read_df(db.select(db.doc_chunks).where(db.doc_chunks.c.doc_id.in_(doc_ids)))
    missing = set(doc_ids) - set(df["doc_id"]) if not df.empty else set(doc_ids)
    for d in missing:
        index_document(d)
    if missing:
        df = db.read_df(db.select(db.doc_chunks).where(db.doc_chunks.c.doc_id.in_(doc_ids)))
    return df


def retrieve(question: str, doc_ids: list[int], k: int = 6, k1: float = 1.5, b: float = 0.75) -> list[dict]:
    """Top-k passages by BM25. Each: doc_id, filename, page, text, score."""
    if not doc_ids:
        return []
    df = _chunks(doc_ids)
    if df.empty:
        return []
    q = tokens(question)
    if not q:
        return []
    docs = [tokens(t) for t in df["text"]]
    n, avgdl = len(docs), sum(len(d) for d in docs) / max(1, len(docs))
    dfreq = Counter(t for d in docs for t in set(d))
    scores = []
    for i, d in enumerate(docs):
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (n - dfreq[t] + 0.5) / (dfreq[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    df = df.assign(score=scores)
    top = df[df["score"] > 0].sort_values("score", ascending=False).head(k)
    names = {int(r["id"]): r["filename"] for _, r in U.list_documents().iterrows()}
    return [{"doc_id": int(r["doc_id"]), "filename": names.get(int(r["doc_id"]), f"document {r['doc_id']}"),
             "page": int(r["page"]), "text": r["text"], "score": round(float(r["score"]), 3)} for _, r in top.iterrows()]


def best_sentences(passages: list[dict], question: str, n: int = 5) -> list[dict]:
    """Extractive answer: the sentences with the highest overlap with the question (quoted verbatim)."""
    q = set(tokens(question))
    out = []
    for p in passages:
        for s in re.split(r"(?<=[.!?])\s+", p["text"]):
            if len(s) < 40:
                continue
            overlap = len(q & set(tokens(s)))
            if overlap:
                out.append({"sentence": s.strip(), "filename": p["filename"], "page": p["page"],
                            "score": overlap + (0.5 if re.search(r"\d", s) else 0)})
    seen, uniq = set(), []
    for x in sorted(out, key=lambda x: -x["score"]):
        if x["sentence"][:80] not in seen:
            seen.add(x["sentence"][:80])
            uniq.append(x)
    return uniq[:n]
