"""v2.4: market clock, real-time provider plumbing, push-on-change WebSocket and the research agent.
Offline: providers, the network and the Anthropic client are replaced by fakes."""
import json
import os
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

import api.assistant as A  # noqa: E402
import api.routes_market as RM  # noqa: E402
from api.main import app  # noqa: E402
from equitypilot.data import marketdata as M  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _ist(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=M.IST)


# ------------------------------------------------------------------ market clock
def test_market_phases_and_next_open():
    s = M.market_status(_ist(2026, 11, 13, 9, 5))          # Friday pre-open
    assert s["phase"] == "pre-open" and not s["open"] and s["next_open"].startswith("2026-11-13T09:15")
    s = M.market_status(_ist(2026, 11, 13, 11, 0))
    assert s["phase"] == "open" and s["open"] and s["closes_at"].startswith("2026-11-13T15:30")
    s = M.market_status(_ist(2026, 11, 13, 16, 0))         # Friday evening -> Monday
    assert s["phase"] == "closed" and s["next_open"].startswith("2026-11-16T09:15")
    s = M.market_status(_ist(2026, 11, 14, 10, 0))         # Saturday
    assert s["phase"] == "closed" and s["next_open"].startswith("2026-11-16T09:15")


def test_holiday_detected_from_data(monkeypatch):
    now = _ist(2026, 11, 13, 11, 0)
    fetched = _ist(2026, 11, 13, 10, 55).timestamp()
    monkeypatch.setattr(M.QUOTES, "peek", lambda s: (fetched, {"price": 1, "time": "2026-11-12T09:59:00"}))
    s = M.market_status(now)
    assert s["phase"] == "closed" and s["holiday"] and s["next_open"].startswith("2026-11-16T09:15")
    # a quote fetched before the open (e.g. stale cache after a restart) must not trigger the holiday rule
    monkeypatch.setattr(M.QUOTES, "peek", lambda s: (_ist(2026, 11, 13, 8, 0).timestamp(), {"price": 1, "time": "2026-11-12T09:59:00"}))
    assert M.market_status(now)["phase"] == "open"
    monkeypatch.setattr(M.QUOTES, "peek", lambda s: (fetched, {"price": 1, "time": "2026-11-13T05:20:00"}))
    assert M.market_status(now)["phase"] == "open"


# ------------------------------------------------------------------ Zerodha Kite Connect provider (mocked HTTP)
class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Fallback(M.MarketDataProvider):
    name = "fallback"

    def __init__(self):
        self.asked = []

    def quotes(self, symbols):
        self.asked += symbols
        return {s: M.Quote(s, 1.0, 1.0, 0.0, 0.0, None, None, "delayed", "fallback") for s in symbols}


def test_kite_symbol_mapping():
    k = M.KiteConnectProvider("k", "t", _Fallback())
    assert k.instrument("TCS.NS") == "NSE:TCS" and k.instrument("500325.BO") == "BSE:500325"
    assert k.instrument("^NSEI") == "NSE:NIFTY 50" and k.instrument("^BSESN") == "BSE:SENSEX"
    assert k.instrument("SAMPLE-ALPHA") is None


def test_kite_quotes_parsed_and_unknown_symbols_fall_back(monkeypatch):
    import requests
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen.update(url=url, params=params, headers=headers)
        return _Resp(200, {"status": "success", "data": {
            "NSE:TCS": {"last_price": 3500.5, "ohlc": {"close": 3450.0}, "volume": 12345, "last_trade_time": "2026-11-13 11:00:05"}}})
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(M.config, "OFFLINE", False)
    fb = _Fallback()
    k = M.KiteConnectProvider("key", "tok", fb)
    out = k.quotes(["TCS.NS", "WEIRD"])
    q = out["TCS.NS"]
    assert q.price == 3500.5 and q.prev_close == 3450.0 and q.change_pct == pytest.approx(3500.5 / 3450 - 1)
    assert q.time == "2026-11-13T05:30:05" and q.source.startswith("Zerodha")          # IST -> UTC
    assert seen["headers"]["Authorization"] == "token key:tok" and ("i", "NSE:TCS") in seen["params"]
    assert "WEIRD" in out and fb.asked == ["WEIRD"]                                   # unmapped -> delayed fallback


def test_kite_expired_token_falls_back(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(403, {"status": "error", "error_type": "TokenException"}))
    monkeypatch.setattr(M.config, "OFFLINE", False)
    fb = _Fallback()
    k = M.KiteConnectProvider("key", "tok", fb)
    out = k.quotes(["TCS.NS"])
    assert out["TCS.NS"].source == "fallback" and "expired" in k.last_error


def test_provider_selection_needs_both_credentials(monkeypatch):
    monkeypatch.setenv("EQUITYPILOT_MARKET_PROVIDER", "kite")
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("KITE_API_KEY", "x")
    assert isinstance(M._make_provider(), M.YahooDelayedProvider)
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "y")
    assert isinstance(M._make_provider(), M.KiteConnectProvider)


# ------------------------------------------------------------------ hot set + WebSocket push-on-change
def test_hot_set_tracks_watchers():
    h = M.HotSet()
    h.set("a", ["TCS.NS", "^NSEI"])
    h.set("b", ["INFY.NS", "SAMPLE-ALPHA"])
    syms = h.symbols()
    assert syms[0] == "^NSEI" and "TCS.NS" in syms and "INFY.NS" in syms and "SAMPLE-ALPHA" not in syms
    assert syms.count("^NSEI") == 1 and h.clients() == 2
    h.drop("a")
    assert "TCS.NS" not in h.symbols()


def test_websocket_sends_snapshot_then_only_changes(client, monkeypatch):
    state = {"TCS.NS": {"price": 100.0, "time": "t1"}, "INFY.NS": {"price": 50.0, "time": "t1"}}
    monkeypatch.setattr(RM, "WS_TICK", 0.05)
    monkeypatch.setattr(M.QUOTES, "get", lambda syms, stale_ok=False: {s: dict(state[s]) for s in syms})
    monkeypatch.setattr(M.QUOTES, "peek", lambda s: (time.time(), state.get(s)))
    with client.websocket_connect("/api/ws/quotes") as ws:
        ws.send_json({"subscribe": ["TCS.NS", "INFY.NS"]})
        first = ws.receive_json()
        assert set(first["quotes"]) == {"TCS.NS", "INFY.NS"} and first["full"] is True and "phase" in first["market"]
        assert M.HOT.clients() >= 1
        state["TCS.NS"] = {"price": 101.0, "time": "t2"}
        nxt = ws.receive_json()
        assert set(nxt["quotes"]) == {"TCS.NS"} and nxt["quotes"]["TCS.NS"]["price"] == 101.0 and nxt["full"] is False


def test_health_reports_market_data_provider(client):
    h = client.get("/api/health").json()
    assert h["version"] == "2.7.0" and h["market_data"]["realtime"] is False and "provider" in h["market_data"]


# ------------------------------------------------------------------ research agent: free offline router
def _stream(client, q, **kw):
    r = client.post("/api/assistant/stream", json={"question": q, **kw})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line[6:]) for line in r.text.split("\n") if line.startswith("data: ")]


def test_offline_router_company_question_cites_sources(client):
    ev = _stream(client, "How have revenue and profit grown?", symbol="SAMPLE-ALPHA")
    final = ev[-1]
    assert final["type"] == "final" and "[S" in final["text"] and any(s["ID"].startswith("S") for s in final["sources"])
    assert any(e["type"] == "status" for e in ev)


def test_offline_router_compares_named_companies(client):
    ev = _stream(client, "Compare SAMPLE-ALPHA and SAMPLE-BETA")
    final = ev[-1]
    assert "| Metric |" in final["text"] and "SAMPLE-ALPHA" in final["text"] and "SAMPLE-BETA" in final["text"]
    assert final["sources"][0]["ID"] == "T1" and "not a recommendation" in final["text"]


def test_offline_router_declines_recommendations(client):
    final = _stream(client, "Should I buy this?", symbol="SAMPLE-GAMMA")[-1]
    assert "can't give buy, sell or hold recommendations" in final["text"]


def test_offline_router_concept_and_help(client):
    assert "EBIT" in _stream(client, "What is ROCE?")[-1]["text"]
    assert _stream(client, "hello there")[-1]["text"].startswith(A.HELP_PREFIX)


def _fake_index(monkeypatch):
    from equitypilot.data import securities as S
    rows = [("ADANIENT.NS", "Adani Enterprises Ltd.", 30, True), ("ADANIPORTS.NS", "Adani Ports and Special Economic Zone Limited", 20, True),
            ("ADANIPOWER.NS", "Adani Power Limited", 25, True), ("TATAPOWER.NS", "The Tata Power Company Limited", 60, True),
            ("TCS.NS", "Tata Consultancy Services Limited", 2, True), ("TATASTEEL.NS", "Tata Steel Limited", 40, True),
            ("SBIN.NS", "State Bank of India", 5, True), ("INFY.NS", "Infosys Limited", 6, True), ("HDFCBANK.NS", "HDFC Bank Limited", 1, True),
            ("HDFCLIFE.NS", "HDFC Life Insurance Company Limited", 50, True), ("BESTAGRO.NS", "Best Agrolife Limited", 1800, False),
            ("ETERNAL.NS", "Eternal Limited", 35, True), ("RELIANCE.NS", "Reliance Industries Limited", 3, True)]
    idx = S.build_index([{"symbol": s, "name": n, "rank": r, "category": None, "tracked": t} for s, n, r, t in rows])
    monkeypatch.setattr(S, "name_index", lambda ttl=600: idx)
    return S


def test_find_companies_brands_typos_and_common_words(monkeypatch):
    _fake_index(monkeypatch)
    assert A.find_companies("Compare Adani and Tata Power") == (["ADANIENT.NS", "TATAPOWER.NS"], [])
    assert A.find_companies("Compare Adani Ports and Adani Power")[0] == ["ADANIPORTS.NS", "ADANIPOWER.NS"]
    assert A.find_companies("How is HDFC Bank doing?")[0] == ["HDFCBANK.NS"]
    assert A.find_companies("Compare State Bank of India with Infosys")[0] == ["SBIN.NS", "INFY.NS"]
    syms, notes = A.find_companies("Is Relaince debt high")
    assert syms == ["RELIANCE.NS"] and "reliance" in notes[0]
    syms, notes = A.find_companies("what about tata?")                 # ambiguous brand -> largest + a note
    assert syms == ["TCS.NS"] and "several companies" in notes[0]
    assert A.find_companies("state of the market")[0] == []
    assert A.find_companies("best dividend stocks")[0] == []           # common word, small unrelated company
    assert A.find_companies("tell me about zomato")[0] == ["ETERNAL.NS"]


def test_search_tolerates_typos(monkeypatch):
    S = _fake_index(monkeypatch)
    r = S.resolve("Adani Enterprwses")
    assert r[0]["symbol"] == "ADANIENT.NS" and r[0]["corrected"] == "adani enterprises"
    assert S.resolve("tata powr")[0]["symbol"] == "TATAPOWER.NS"
    assert S.resolve("hdfc")[0]["symbol"] == "HDFCBANK.NS"


def test_screen_tool_validates_and_excludes_lenders():
    tb = A.ToolBox()
    with pytest.raises(A.ToolError):
        tb.run("screen_companies", {"filters": [{"metric": "nonsense", "op": ">", "value": 1}]})
    with pytest.raises(A.ToolError):
        tb.run("nope", {})
    out = tb.run("screen_companies", {"sort_by": "debt_to_equity", "ascending": True, "limit": 5})
    assert "banks/NBFCs excluded" in out and out.startswith("[T1]")


# ------------------------------------------------------------------ research agent: Claude tool-use loop (fake client)
class _Block(SimpleNamespace):
    pass


class _FakeStream:
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


class _FakeClient:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.messages = SimpleNamespace(stream=self._stream)
        self.beta = SimpleNamespace(messages=self.messages)    # the agent streams on the beta endpoint (refusal fallbacks)

    def _stream(self, **kw):
        self.calls.append(kw)
        return _FakeStream(self.script.pop(0))


def _msg(content, stop):
    return SimpleNamespace(content=content, stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=0, cache_creation_input_tokens=0))


def test_claude_agent_runs_tools_and_streams(monkeypatch):
    import anthropic
    script = [
        _msg([_Block(type="text", text="Let me look that up."),
              _Block(type="tool_use", id="tu1", name="compare_companies", input={"symbols": ["SAMPLE-ALPHA", "SAMPLE-BETA"]})], "tool_use"),
        _msg([_Block(type="text", text="**Summary** ALPHA has the higher ROE [T1].")], "end_turn"),
    ]
    fake = _FakeClient(script)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    tb = A.ToolBox()
    events = list(A.run_claude("Compare alpha and beta", [], None, tb, "claude-opus-5-5", "sk-test", [], prefetch=False))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "delta" and "interim" in kinds and "status" in kinds and kinds[-1] == "final"
    final = events[-1]
    assert final["text"].startswith("**Summary**") and final["meta"]["steps"] == 2 and final["meta"]["cost_usd"] > 0
    # the tool result went back to the model, matched to the tool_use id
    second = fake.calls[1]["messages"]
    assert second[-1]["content"][0]["tool_use_id"] == "tu1" and "| Metric |" in second[-1]["content"][0]["content"]
    assert fake.calls[0]["tools"][0]["eager_input_streaming"] is True and fake.calls[0]["thinking"] == {"type": "adaptive"}
    assert fake.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_claude_agent_reports_tool_errors_to_the_model(monkeypatch):
    import anthropic
    script = [_msg([_Block(type="tool_use", id="x", name="company_research", input={"symbol": ""})], "tool_use"),
              _msg([_Block(type="text", text="That data is not available.")], "end_turn")]
    fake = _FakeClient(script)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    events = list(A.run_claude("q", [], None, A.ToolBox(), "claude-haiku-5-5", "k", [], prefetch=False))
    res = fake.calls[1]["messages"][-1]["content"][0]
    assert res["is_error"] is True and "symbol is required" in res["content"]
    assert "thinking" not in fake.calls[0] and events[-1]["text"] == "That data is not available."


def test_claude_agent_never_runs_truncated_tool_input(monkeypatch):
    import anthropic
    script = [_msg([_Block(type="tool_use", id="x", name="compare_companies", input={"symbols": ["SAMPLE-ALPHA"]})], "max_tokens")]
    fake = _FakeClient(script)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    tb = A.ToolBox()
    events = list(A.run_claude("q", [], None, tb, "claude-opus-5-5", "k", [], prefetch=False))
    assert len(fake.calls) == 1 and tb.texts == [] and "ran out of room" in events[-1]["meta"]["note"]
