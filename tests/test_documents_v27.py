"""v2.7 documents: fast text extraction, table rows that question answering can find (with page numbers), scanned-PDF
detection and document summaries that quote the report verbatim."""
from __future__ import annotations

import io
import json
import os

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from equitypilot.ai import rag  # noqa: E402
from equitypilot.data import uploads as U  # noqa: E402


def _report_pdf() -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    st = getSampleStyleSheet()["Normal"]
    doc = SimpleDocTemplate(buf, pagesize=A4)
    story = [Paragraph("Directors' report. Revenue from operations grew 12% to Rs 1,000 crore while EBITDA margin improved "
                       "to 21% on better pricing and cost control across the business.", st), Spacer(1, 400),
             Paragraph("Management expects capex of Rs 300 crore next year to expand capacity; debt remains low and the "
                       "board recommended a dividend of Rs 8 per share for the year.", st), Spacer(1, 400),
             Table([["Particulars", "FY2025", "FY2024"], ["Revenue from operations", "1,000", "893"], ["Net profit", "150", "120"]],
                   style=[("GRID", (0, 0), (-1, -1), 0.5, colors.black)])]          # ruled, like annual-report tables
    doc.build(story)
    return buf.getvalue()


def _scanned_pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for _ in range(3):
        c.rect(72, 72, 400, 600, fill=1)          # an image-like page: shapes, no text layer
        c.showPage()
    c.save()
    return buf.getvalue()


def test_tables_are_searchable_with_their_page():
    ext = U.extract_pdf(_report_pdf())
    assert not ext["scanned"] and ext["tables"]
    page = ext["tables"][0]["page"]
    assert "Net profit | 150 | 120" in ext["pages"][page - 1]["text"]
    doc_id = U.save_document("SAMPLE-BETA", "table.pdf", "Annual Report", "FY2025", None, ext)
    try:
        hits = rag.retrieve("net profit FY2025", [doc_id], k=3)
        assert hits and hits[0]["page"] == page and "150" in hits[0]["text"]
    finally:
        U.delete_document(doc_id)


def test_scanned_pdf_is_reported_not_summarised():
    ext = U.extract_pdf(_scanned_pdf())
    assert ext["scanned"] and ext["n_pages"] == 3
    with TestClient(app) as c:
        r = c.post("/api/documents", files={"file": ("scan.pdf", _scanned_pdf(), "application/pdf")}, data={"doc_type": "Annual Report"})
        assert r.status_code == 200 and "scanned PDF" in r.json()["warning"]
        doc_id = r.json()["id"]
        try:
            r = c.post("/api/assistant/stream", json={"question": "Summarise this document", "doc_ids": [doc_id]})
            final = [json.loads(x[6:]) for x in r.text.split("\n") if x.startswith("data: ")][-1]
            assert "no readable text layer" in final["text"] and "OCR is not available" in final["text"]
        finally:
            c.delete(f"/api/documents/{doc_id}")


@pytest.mark.parametrize("question", ["Summarise this document", "What are the key points of the report?"])
def test_document_summary_quotes_with_page_numbers(question):
    with TestClient(app) as c:
        r = c.post("/api/documents", files={"file": ("report.pdf", _report_pdf(), "application/pdf")}, data={"doc_type": "Annual Report"})
        doc_id = r.json()["id"]
        try:
            r = c.post("/api/assistant/stream", json={"question": question, "doc_ids": [doc_id]})
            final = [json.loads(x[6:]) for x in r.text.split("\n") if x.startswith("data: ")][-1]
            assert "Key passages from report.pdf" in final["text"] and "— *p. " in final["text"]
            assert "Revenue from operations grew 12%" in final["text"]
            assert any(s["Type"] == "OFFICIAL (UPLOADED)" for s in final["sources"])
        finally:
            c.delete(f"/api/documents/{doc_id}")
