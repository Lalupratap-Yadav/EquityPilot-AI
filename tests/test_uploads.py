"""Upload parsing: statements, prices, PDFs."""
import io
from datetime import date

import pandas as pd
import pytest

from equitypilot.data import repository as repo
from equitypilot.data import uploads as U


def test_parse_period_formats():
    assert U.parse_period("FY2025") == date(2025, 3, 31)
    assert U.parse_period("FY25") == date(2025, 3, 31)
    assert U.parse_period("Mar-2025") == date(2025, 3, 31)
    assert U.parse_period("2024-03-31") == date(2024, 3, 31)
    assert U.parse_period("31-03-2023") == date(2023, 3, 31)
    assert U.parse_period("Q2FY26") == date(2025, 9, 30)
    assert U.parse_period("Notes") is None


def test_parse_statements_aliases_and_numbers():
    df = pd.DataFrame({"Particulars": ["Revenue from operations", "Profit after tax", "Finance costs", "Some note"],
                       "FY2025": ["1,234.5", "(10)", "5", "x"], "FY2024": [1000, 50, None, None]})
    wide, warns = U.parse_statements(df)
    assert wide.loc["revenue", date(2025, 3, 31)] == pytest.approx(1234.5)
    assert wide.loc["net_income", date(2025, 3, 31)] == pytest.approx(-10)
    assert "interest_expense" in wide.index
    assert any("not recognised" in w for w in warns)


def test_to_rows_units_and_outflows_then_saved():
    wide = pd.DataFrame({date(2025, 3, 31): {"revenue": 100.0, "capex": 20.0, "eps_diluted": 12.5}})
    rows = U.to_rows(wide, "SAMPLE-ALPHA", "standalone", "annual", 1e7, "Test AR FY25", "https://example.com/ar.pdf")
    by = {r["line_item"]: r for r in rows}
    assert by["revenue"]["value"] == pytest.approx(100e7)
    assert by["capex"]["value"] == pytest.approx(-20e7)          # stored as outflow
    assert by["eps_diluted"]["value"] == pytest.approx(12.5)     # per-share not scaled
    assert by["revenue"]["data_type"] == "official_upload"
    repo.save_financial_rows(rows)
    assert "standalone" in repo.available_bases("SAMPLE-ALPHA")
    fd = repo.get_financials("SAMPLE-ALPHA", basis="consolidated")
    assert fd.basis == "consolidated"   # uploads do not overwrite another basis


def test_parse_prices_nse_style():
    csv = 'Date ,OPEN ,HIGH ,LOW ,PREV. CLOSE ,close ,VOLUME \n"02-Jan-2025","1,200.0","1,250.5","1,190","1,195","1,240.25","1,23,456"\n' \
          '"01-Jan-2025","1,180","1,205","1,170","1,175","1,195","98,765"\n'
    df, warns = U.parse_prices(U.read_table(csv.encode(), "nse.csv"))
    assert list(df["close"]) == [1195.0, 1240.25]                 # sorted ascending by date
    assert df["volume"].iloc[-1] == 123456


def test_pdf_extract_and_search():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 750, "Annual Report - Management Discussion")
    c.showPage()
    c.drawString(72, 750, "Revenue from operations grew 12% to Rs 1,000 crore.")
    c.save()
    ext = U.extract_pdf(buf.getvalue())
    assert ext["n_pages"] == 2 and not ext["scanned"]
    pages = U.text_to_pages(U.pages_to_text(ext["pages"]))
    hits = U.search_pages(pages, "revenue from operations")
    assert hits and hits[0]["page"] == 2
    doc_id = U.save_document("SAMPLE-BETA", "test.pdf", "Annual Report", "FY2025", None, ext)
    assert U.get_document(doc_id)["pages"] == 2
    U.delete_document(doc_id)
    assert U.get_document(doc_id) is None
