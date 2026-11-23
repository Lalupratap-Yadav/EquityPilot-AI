"""v2.7 AI assistant: question understanding (common words, close matches, thresholds, follow-ups), the direct-answer
layout, quarterly results, plain-English explanations, documents and grounding. Offline: no network, no paid API."""
from __future__ import annotations

import json
import os

import pandas as pd
import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

import api.assistant as A  # noqa: E402
from api.main import app  # noqa: E402
from equitypilot.ai import offline  # noqa: E402
from equitypilot.ai.context import build_context, grounding_check  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _stream(client, q, **kw):
    r = client.post("/api/assistant/stream", json={"question": q, **kw})
    assert r.status_code == 200
    return [json.loads(line[6:]) for line in r.text.split("\n") if line.startswith("data: ")]


def _index(monkeypatch, extra=()):
    from equitypilot.data import securities as S
    rows = [("HAVELLS.NS", "Havells India Limited", 60, True), ("IOC.NS", "Indian Oil Corporation Limited", 30, True),
            ("ASIANPAINT.NS", "Asian Paints Limited", 25, True), ("UNITDSPR.NS", "United Spirits Limited", 80, True),
            ("TMCV.NS", "Tata Motors Limited", 70, True), ("TMPV.NS", "Tata Motors Passenger Vehicles Limited", 65, True),
            ("TCS.NS", "Tata Consultancy Services Limited", 2, True), ("INFY.NS", "Infosys Limited", 6, True),
            ("TITAN.NS", "Titan Company Limited", 20, True), ("RELIANCE.NS", "Reliance Industries Limited", 3, True),
            ("CGCL.NS", "Capri Global Capital Limited", 400, True), *extra]
    idx = S.build_index([{"symbol": s, "name": n, "rank": r, "category": None, "tracked": t} for s, n, r, t in rows])
    monkeypatch.setattr(S, "name_index", lambda ttl=600: idx)


# ------------------------------------------------------------------ question understanding
def test_common_words_never_pick_a_company(monkeypatch):
    _index(monkeypatch)
    assert A.find_companies("Which companies have ROE above 20%?")[0] == []          # was Havells
    assert A.find_companies("What is happening in Indian markets?")[0] == []         # was Indian Oil
    assert A.find_companies("How are asian markets doing?")[0] == []
    assert A.find_companies("united states inflation")[0] == []
    assert A.find_companies("companies with market cap above 5 lakh crore")[0] == []  # was Capri Global ("cap")
    # ...but the same words inside a real name, and exact brand words, still work
    assert A.find_companies("Asian Paints margins")[0] == ["ASIANPAINT.NS"]
    assert A.find_companies("Is Indian Oil debt high?")[0] == ["IOC.NS"]
    assert A.find_companies("tell me about titan")[0] == ["TITAN.NS"]


def test_close_second_match_is_mentioned(monkeypatch):
    _index(monkeypatch)
    syms, notes = A.find_companies("What is the debt of Tata Motors?")
    assert syms == ["TMCV.NS"] and any("Tata Motors Passenger Vehicles" in n for n in notes)


def test_numeric_conditions_are_parsed():
    f = A.parse_screen_filters
    assert f("Which companies have ROE above 20%?") == [{"metric": "roe", "op": ">", "value": 0.2}]
    assert f("show IT stocks with P/E below 25 and ROE over 25 percent") == [
        {"metric": "pe", "op": "<", "value": 25.0}, {"metric": "roe", "op": ">", "value": 0.25}]      # question order
    assert f("market cap above 5 lakh crore")[0]["value"] == 5e12
    assert f("market cap of at least 50,000 crore")[0] == {"metric": "market_cap", "op": ">=", "value": 5e11}
    assert f("debt to equity under 0.5")[0] == {"metric": "debt_to_equity", "op": "<", "value": 0.5}
    assert f("dividend yield more than 3 per cent")[0]["value"] == pytest.approx(0.03)
    assert f("What is the ROE of TCS?") == []


def test_threshold_screen_runs_without_naming_a_company(client):
    ev = _stream(client, "Which companies have ROE above 20%?")
    final = ev[-1]["text"]
    assert "ROE > 20.0%" in final and "not a recommendation" in final
    assert not any(e["type"] == "status" and e["text"].startswith("Recognised") for e in ev)


def test_follow_up_questions_use_the_conversation(client):
    hist = [{"role": "user", "content": "Tell me about SAMPLE-ALPHA"}, {"role": "assistant", "content": "..."}]
    ev = _stream(client, "what about its margins?", history=hist)
    steps = [e["text"] for e in ev if e["type"] == "status"]
    assert any("Continuing with SAMPLE-ALPHA" in s for s in steps)
    assert ev[-1]["text"].startswith("**Answer**") and "net profit margin" in ev[-1]["text"]
    hist = [{"role": "user", "content": "Compare SAMPLE-ALPHA and SAMPLE-BETA"}, {"role": "assistant", "content": "..."}]
    final = _stream(client, "which has better margins", history=hist)[-1]["text"]
    assert "Higher Net margin" in final and "| Metric |" in final


def test_documents_requested_without_a_selection(client):
    assert "No document is selected" in _stream(client, "Summarise this uploaded annual report")[-1]["text"]


def test_screen_status_text_describes_filters():
    tb = A.ToolBox()
    assert tb.describe("screen_companies", {"filters": [{"metric": "roe", "op": ">", "value": 0.2}]}) == \
        "Screening tracked companies: ROE > 20.0%"


# ------------------------------------------------------------------ answer layout and grounding
@pytest.fixture(scope="module")
def alpha():
    return build_context("SAMPLE-ALPHA", "")


def _before_interpretation(md: str) -> str:
    return md.split("**Automated interpretation")[0]


def test_metric_question_gets_a_direct_traceable_answer(alpha):
    a = offline.answer(alpha, "What is the debt-to-equity ratio?")
    assert a.startswith("**Answer**") and "Debt / Equity" in a.split("\n")[1]
    assert "In simple terms: For every ₹1 of shareholders' money" in a and "**Sources and periods**" in a
    total, untraced = grounding_check(_before_interpretation(a), alpha.render())
    assert total > 0 and not untraced, untraced


def test_lender_metric_explained_not_computed():
    a = offline.answer(build_context("SAMPLE-EPSILON", ""), "What is the debt to equity ratio?")
    assert "not a meaningful measure" in a and "CRAR" in a


def test_quarterly_results_answer(alpha):
    assert any(b.title.startswith("Quarterly results") for b in alpha.blocks)
    a = offline.answer(alpha, "Explain the latest quarterly results")
    assert a.startswith("**Answer**\nIn the quarter ended") and "results filing" in a
    total, untraced = grounding_check(_before_interpretation(a), alpha.render())
    assert total > 0 and not untraced, untraced


def test_plain_english_explanation_is_grounded(alpha):
    a = offline.answer(alpha, "Explain this company in simple English")
    assert "For every ₹100 of shareholders' money" in a and "FICTIONAL" in a
    total, untraced = grounding_check(_before_interpretation(a), alpha.render())
    assert total > 0 and not untraced, untraced


def test_large_jumps_are_flagged_as_likely_mergers(alpha):
    rt = alpha.data["ratios"].copy()
    rt.loc["revenue_growth", rt.columns[-2]] = 0.65
    ctx = build_context("SAMPLE-ALPHA", "")
    ctx.data["ratios"] = rt
    a = offline.Answer()
    offline._growth(ctx, a)
    assert any("merger, acquisition" in i for i in a.interp)


def test_unusually_low_pe_is_flagged(monkeypatch):
    tb = A.ToolBox()
    df = pd.DataFrame([{"symbol": "X.NS", "name": "X Ltd", "is_sample": False, "is_financial": False, "industry_id": "it",
                        "market_cap": 1e12, "pe": 1.4, "roe": 0.7, "revenue_cagr_3y": 0.1, "debt_to_equity": 0.2}])
    monkeypatch.setattr(tb, "_metrics", lambda: df)
    out = tb.run("screen_companies", {"sort_by": "roe"})
    assert "P/E below 3 (X Ltd)" in out


# ------------------------------------------------------------------ Claude agent (fake client - no paid API calls)
from types import SimpleNamespace  # noqa: E402

from equitypilot.ai import providers as P  # noqa: E402
from equitypilot.ai.context import grounding_report  # noqa: E402


class _Stream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        for b in self.msg.content:
            if b.type == "text":
                yield SimpleNamespace(type="text", text=b.text)

    def get_final_message(self):
        return self.msg


class _Client:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kw):
        self.calls.append(kw)
        return _Stream(self.script.pop(0))


def _msg(content, stop, model="claude-opus-5-5", iterations=None):
    u = SimpleNamespace(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0,
                        iterations=iterations)
    return SimpleNamespace(content=content, stop_reason=stop, usage=u, model=model)


def _b(**kw):
    return SimpleNamespace(**kw)


def test_predictable_questions_are_prefetched_and_answered_in_one_turn(monkeypatch):
    import anthropic
    fake = _Client([_msg([_b(type="text", text="**Answer** ALPHA has the higher ROE [T1].")], "end_turn")])
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    tb = A.ToolBox()
    ev = list(A.run_claude("Compare SAMPLE-ALPHA and SAMPLE-BETA", [], None, tb, "claude-opus-5-5", "k", []))
    assert ev[0]["type"] == "status" and "Comparing" in ev[0]["text"]          # progress shown before the model runs
    assert len(fake.calls) == 1                                                  # one model turn, not two
    first = fake.calls[0]["messages"][-1]["content"]
    assert "Research data EquityPilot already retrieved" in first and "| Metric |" in first and "[T1]" in first
    assert ev[-1]["meta"]["prefetched"] == 1 and tb.sources[0]["ID"] == "T1"
    # refusal fallbacks and an explicit effort level are requested for Opus
    assert fake.calls[0]["betas"] == ["server-side-fallback-2026-07-01"] and fake.calls[0]["fallbacks"] == "default"
    assert fake.calls[0]["output_config"] == {"effort": "medium"}


def test_haiku_has_no_fallback_beta(monkeypatch):
    import anthropic
    fake = _Client([_msg([_b(type="text", text="done")], "end_turn", model="claude-haiku-5-5")])
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    list(A.run_claude("hello", [], None, A.ToolBox(), "claude-haiku-5-5", "k", [], effort="low"))
    assert "betas" not in fake.calls[0] and "fallbacks" not in fake.calls[0] and fake.calls[0]["output_config"] == {"effort": "low"}


def test_parallel_tool_calls_return_in_one_message_in_order(monkeypatch):
    import anthropic
    script = [_msg([_b(type="tool_use", id="a", name="explain_metric", input={"term": "ROE"}),
                    _b(type="tool_use", id="b", name="explain_metric", input={"term": "ROCE"})], "tool_use"),
              _msg([_b(type="text", text="ok")], "end_turn")]
    fake = _Client(script)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    tb = A.ToolBox()
    list(A.run_claude("q", [], None, tb, "claude-opus-5-5", "k", [], prefetch=False))
    results = fake.calls[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"] and len({s["ID"] for s in tb.sources}) == len(tb.sources)


def test_declined_attempt_blocks_are_not_echoed_or_run(monkeypatch):
    """After a mid-output refusal fallback, blocks before the `fallback` block belong to the declined attempt."""
    import anthropic
    fb = _b(type="fallback")
    content = [_b(type="thinking", thinking=""), _b(type="text", text="Partial. "),
               _b(type="tool_use", id="old", name="explain_metric", input={"term": "ROE"}), fb,
               _b(type="text", text="Continuing."), _b(type="tool_use", id="new", name="explain_metric", input={"term": "ROCE"})]
    iters = [_b(type="message", model="claude-opus-5-5", input_tokens=1000, output_tokens=50, cache_read_input_tokens=0,
                cache_creation_input_tokens=0),
             _b(type="fallback_message", model="claude-opus-4-8", input_tokens=1000, output_tokens=150,
                cache_read_input_tokens=0, cache_creation_input_tokens=0)]
    script = [_msg(content, "tool_use", model="claude-opus-4-8", iterations=iters), _msg([_b(type="text", text="Done.")], "end_turn")]
    fake = _Client(script)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    ev = list(A.run_claude("q", [], None, A.ToolBox(), "claude-opus-5-5", "k", [], prefetch=False))
    echoed = fake.calls[1]["messages"][-2]["content"]
    assert [getattr(b, "type") for b in echoed] == ["text", "fallback", "text", "tool_use"] and echoed[-1].id == "new"
    assert [r["tool_use_id"] for r in fake.calls[1]["messages"][-1]["content"]] == ["new"]
    meta = ev[-1]["meta"]
    assert "claude-opus-4-8" in meta["note"]
    # each attempt priced at its own model's rates
    expected = (1000 * 4.0 + 50 * 20.0 + 1000 * 5.0 + 150 * 25.0) / 1e6 + (1000 * 4.0 + 200 * 20.0) / 1e6
    assert meta["cost_usd"] == pytest.approx(expected)


def test_cost_counts_cache_reads_at_cache_prices():
    assert P.cost_of([("claude-opus-5-5", 0, 0, 1_000_000, 0)]) == pytest.approx(0.20)
    assert P.cost_of([("claude-opus-5-5", 1_000_000, 0, 0, 0)]) == pytest.approx(4.00)
    assert P.cost_of([("unknown-model", 1, 1, 0, 0)]) is None


def test_grounding_report_separates_calculations_and_bad_citations():
    ctx = "[T1] Revenue ₹1,000 Cr; net profit ₹150 Cr; ROE 18.4%"
    ans = ("**Answer** Net margin = 150 / 1,000 = 15.0% [T1].\n"
           "Revenue grew to ₹1,234 Cr [T9].\n"
           "Profit was ₹150 Cr.")
    r = grounding_report(ans, ctx, ["T1"])
    assert r["calculated"] == ["15.0"] and r["untraced"] == ["1,234"] and r["unknown_citations"] == ["T9"]
    assert r["uncited_lines"] == 1


def _api_error(cls, status, message):
    import anthropic
    resp = SimpleNamespace(status_code=status, request=SimpleNamespace(method="POST", url="https://api.anthropic.com/v1/messages"),
                           headers={})
    return getattr(anthropic, cls)(message, response=resp, body=None)


def test_api_errors_are_explained_and_the_offline_engine_answers(monkeypatch):
    import anthropic

    class Failing:
        def __init__(self, exc):
            self.exc = exc
            self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

        def _stream(self, **kw):
            raise self.exc
    exc = _api_error("AuthenticationError", 401, "invalid x-api-key")
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: Failing(exc))
    events = [json.loads(x[6:]) for x in A.stream_answer("What is ROCE?", [], None, [], 1,
              {"provider": "anthropic", "consent": True, "model": "claude-opus-5-5"}, "sk-test", []) if x.startswith("data: ")]
    final = events[-1]
    assert final["meta"]["engine"] == "offline analyst (fallback)" and "API key was rejected" in final["meta"]["warning"]
    assert "Capital employed" in final["text"] or "ROCE" in final["text"]
    low_credit = _api_error("BadRequestError", 400, "Your credit balance is too low to access the Anthropic API.")
    assert "separate from Claude Pro/Max" in P.explain_anthropic_error(low_credit)
