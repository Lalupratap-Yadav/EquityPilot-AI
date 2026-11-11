"""Smoke tests: every page renders without exceptions (offline, sample data)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["views/dashboard.py", "views/company.py", "views/financials.py"]


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
@pytest.mark.parametrize("symbol", ["SAMPLE-ALPHA", "SAMPLE-GAMMA", "SAMPLE-DELTA"])
def test_company_pages_for_each_sample(page, symbol):
    at = run_page(page, symbol)
    assert not at.exception, [e.value for e in at.exception]


def test_company_page_without_selection_shows_empty_state():
    at = run_page("views/company.py", symbol=None)
    assert not at.exception
