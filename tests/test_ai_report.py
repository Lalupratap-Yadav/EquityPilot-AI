"""AI assistant grounding rules and PDF report generation."""
import pytest

from equitypilot.ai import offline
from equitypilot.ai import providers as P
from equitypilot.ai.context import build_context, grounding_check
from equitypilot.reports.pdf_report import ReportOptions, build_report


@pytest.fixture(scope="module")
def ctx():
    return build_context("SAMPLE-BETA", "how is growth")


def test_context_blocks_carry_provenance(ctx):
    titles = [b.title for b in ctx.blocks]
    assert titles[0] == "Company profile"
    assert any(t.startswith("Annual financial statements") for t in titles)
    rendered = ctx.render()
    assert "[S1]" in rendered and "type: SAMPLE" in rendered


def test_offline_answer_is_sectioned_and_cited(ctx):
    a = offline.answer(ctx, "How has revenue grown?")
    assert "**Facts from sources**" in a and "**Calculations**" in a
    assert "[S" in a
    assert "FICTIONAL" in a                       # sample data disclosed


def test_offline_answer_figures_are_grounded(ctx):
    a = offline.answer(ctx, "Is the balance sheet strong?")
    facts = a.split("**Automated interpretation")[0]   # interpretation contains generic thresholds
    total, untraced = grounding_check(facts, ctx.render())
    assert total > 0 and not untraced, untraced


def test_recommendation_requests_are_declined(ctx):
    a = offline.answer(ctx, "Should I buy this stock?")
    assert "can't give buy, sell or hold recommendations" in a
    assert "SEBI" in a


def test_concept_question_without_company():
    a = offline.answer(None, "What is ROCE?")
    assert "Capital employed" in a


def test_shareholding_answer(ctx):
    a = offline.answer(ctx, "What is the shareholding pattern?")
    assert "Shareholding pattern" in a and "Promoter" in a


def test_missing_information_is_admitted(ctx):
    a = offline.answer(ctx, "Summarise the annual report")
    assert "No document selected" in a


def test_grounding_check_flags_invented_numbers():
    total, untraced = grounding_check("Revenue was ₹12,345 Cr and margin 18.4%", "revenue ₹12,345 Cr")
    assert total == 2 and untraced == ["18.4"]


def test_cost_estimate_and_ollama_unreachable():
    assert P.estimate_cost_usd("claude-haiku-5-5", 1_000_000, 0) == pytest.approx(0.10)
    with pytest.raises(P.ProviderError):
        P.ask_ollama("ctx", [], "q", "none", host="http://127.0.0.1:9")


@pytest.mark.parametrize("symbol", ["SAMPLE-ALPHA", "SAMPLE-GAMMA"])
def test_pdf_report_builds(symbol):
    pdf = build_report(symbol, ReportOptions(analyst="Tester", thesis="Thesis", own_view="View"))
    assert pdf[:4] == b"%PDF" and len(pdf) > 30_000
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    text = " ".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    n = len(doc)
    doc.close()
    assert n >= 4
    assert "SEBI" in text and "Sources and references" in text
    assert "SAMPLE" in text


def test_offline_answer_uses_bank_metrics():
    ctx = build_context("SAMPLE-EPSILON", "balance sheet")
    a = offline.answer(ctx, "Is the balance sheet strong?")
    assert "Gross NPA" in a and "CRAR" in a
    facts = a.split("**Automated interpretation")[0]
    total, untraced = grounding_check(facts, ctx.render())
    assert total > 0 and not untraced, untraced


def test_bank_report_builds():
    pdf = build_report("SAMPLE-EPSILON", ReportOptions())
    assert pdf[:4] == b"%PDF"
