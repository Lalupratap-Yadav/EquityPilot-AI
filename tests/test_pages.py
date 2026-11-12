"""Smoke tests: every page renders without exceptions (offline, sample data)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["views/dashboard.py", "views/company.py", "views/financials.py", "views/valuation.py",
         "views/compare.py", "views/technicals.py", "views/risk.py", "views/screener.py",
         "views/news.py", "views/data_manager.py",
         "views/assistant.py", "views/report.py",
         "views/portfolio.py", "views/learning.py", "views/guide.py"]


def run_page(page: str, symbol: str | None = "SAMPLE-BETA") -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    if symbol:
        at.query_params["symbol"] = symbol
    at.run()
    at.switch_page(page)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = run_page(page)
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("page", PAGES[1:])
@pytest.mark.parametrize("symbol", ["SAMPLE-ALPHA", "SAMPLE-GAMMA", "SAMPLE-DELTA", "SAMPLE-EPSILON"])
def test_company_pages_for_each_sample(page, symbol):
    at = run_page(page, symbol)
    assert not at.exception, [e.value for e in at.exception]


def test_company_page_without_selection_shows_empty_state():
    at = run_page("views/company.py", symbol=None)
    assert not at.exception


def test_valuation_dcf_produces_value():
    at = run_page("views/valuation.py", "SAMPLE-ALPHA")
    assert not at.exception
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Estimated value / share (model)" in html and "EV → equity bridge" in html


def test_financials_tables_present():
    at = run_page("views/financials.py", "SAMPLE-BETA")
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Revenue from operations" in html and "Return on equity" in html


def test_portfolio_with_sample_holdings():
    from equitypilot.data import repository as repo, sample
    if repo.get_holdings().empty:
        sample.load_sample_portfolio()
    at = run_page("views/portfolio.py")
    assert not at.exception, [e.value for e in at.exception]
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "XIRR" in html and "Effective no. of stocks" in html


def test_assistant_answers_suggested_question():
    at = run_page("views/assistant.py", "SAMPLE-GAMMA")
    at.chat_input[0].set_value("What are the key risks?").run()
    assert not at.exception, [e.value for e in at.exception]
    md = " ".join(m.value for m in at.markdown)
    assert "Facts from sources" in md and "[S" in md


def test_learning_quiz_submission():
    at = run_page("views/learning.py")
    for r in at.radio:
        r.set_value(0)
    at.button[0].click().run() if at.button else None
    assert not at.exception


def test_bank_metrics_tab_and_quarterly_results():
    at = run_page("views/company.py", "SAMPLE-EPSILON")
    assert not at.exception
    assert "Bank metrics" in [t.label for t in at.tabs]
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Gross NPA" in html and "Capital adequacy" in html
    at = run_page("views/financials.py", "SAMPLE-BETA")
    html = " ".join(h.proto.body for h in at.get("html"))
    md = " ".join(m.value for m in at.markdown)
    assert "Latest quarter: Q2 FY27" in md and "Revenue growth YoY" in html and "Revenue QoQ" in html


def test_bank_valuation_page_disables_dcf():
    at = run_page("views/valuation.py", "SAMPLE-EPSILON")
    assert not at.exception
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "not appropriate for banks" in html and "Justified P/B" in html
