"""FastAPI tests (offline, temporary DB, sample data): users, watchlists, alerts, virtual invest, DCF, RAG, security."""
import io
import os

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from equitypilot import db  # noqa: E402
from equitypilot.analytics import paper as P  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health_and_guest_session(client):
    assert client.get("/api/health").json()["status"] == "ok"
    me = client.get("/api/me").json()["user"]
    assert me["is_guest"] and me["display_name"].startswith("Guest")
    assert client.get("/api/me").json()["user"]["id"] == me["id"]      # same cookie -> same user


def test_users_are_isolated():
    with TestClient(app) as a, TestClient(app) as b:
        wa = a.get("/api/watchlists").json()[0]["id"]
        assert a.post(f"/api/watchlists/{wa}/items", json={"symbol": "SAMPLE-ALPHA", "note": "brand moat"}).status_code == 200
        assert a.get("/api/watchlists").json()[0]["items"][0]["note"] == "brand moat"
        assert b.get("/api/watchlists").json()[0]["items"] == []
        assert b.delete(f"/api/watchlists/{wa}").status_code == 404    # cannot touch another user's list


def test_register_login_logout(client):
    uid = client.get("/api/me").json()["user"]["id"]
    r = client.post("/api/auth/register", json={"username": "student_01", "password": "s3cure-pass!", "display_name": "Student"})
    assert r.status_code == 200 and r.json()["user"]["username"] == "student_01"
    assert client.post("/api/auth/register", json={"username": "student_01", "password": "another-pass"}).status_code == 400
    client.post("/api/auth/logout")
    assert client.get("/api/me").json()["user"]["id"] != uid
    assert client.post("/api/auth/login", json={"username": "student_01", "password": "wrong-pass1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "student_01", "password": "s3cure-pass!"}).json()["user"]["id"] == uid
    row = db.read_df(db.select(db.users.c.password_hash).where(db.users.c.id == uid)).iloc[0, 0]
    assert row.startswith("scrypt$") and "s3cure" not in row


def test_virtual_invest_rules(client):
    s = client.get("/api/invest/summary").json()
    assert s["cash"] == pytest.approx(P.INITIAL_CASH) and s["holdings"] == []
    price = client.get("/api/quotes?symbols=SAMPLE-BETA").json()["quotes"]["SAMPLE-BETA"]["price"]
    r = client.post("/api/invest/orders", json={"symbol": "SAMPLE-BETA", "side": "BUY", "qty": 10})
    assert r.status_code == 200 and r.json()["price_status"] == "sample"
    s = client.get("/api/invest/summary").json()
    assert s["cash"] == pytest.approx(P.INITIAL_CASH - 10 * price)
    assert s["holdings"][0]["qty"] == 10 and s["total_value"] == pytest.approx(P.INITIAL_CASH)
    too_many = int(P.INITIAL_CASH / price) + 10
    r = client.post("/api/invest/orders", json={"symbol": "SAMPLE-BETA", "side": "BUY", "qty": too_many})
    assert r.status_code == 400 and "Insufficient virtual funds" in r.json()["detail"]
    r = client.post("/api/invest/orders", json={"symbol": "SAMPLE-BETA", "side": "SELL", "qty": 11})
    assert r.status_code == 400
    assert client.post("/api/invest/orders", json={"symbol": "SAMPLE-BETA", "side": "SELL", "qty": 4}).status_code == 200
    s = client.get("/api/invest/summary").json()
    assert s["holdings"][0]["qty"] == 6 and s["realised"] == pytest.approx(0, abs=1e-6)
    assert len(client.get("/api/invest/trades").json()) == 2
    assert any(a["id"] == "first_trade" and a["earned"] for a in s["achievements"])
    s = client.post("/api/invest/reset").json()
    assert s["cash"] == pytest.approx(P.INITIAL_CASH) and s["resets"] == 1


def test_paper_split_and_dividend_adjustments():
    from datetime import date, timedelta
    with TestClient(app) as c:
        uid = c.get("/api/me").json()["user"]["id"]
        c.post("/api/invest/orders", json={"symbol": "SAMPLE-DELTA", "side": "BUY", "qty": 10})
        # simulate corporate actions after the buy (ex-dates in the future relative to the trade)
        db.upsert(db.corporate_actions, [
            {"symbol": "SAMPLE-DELTA", "date": date.today() + timedelta(days=2), "type": "dividend", "value": 5.0, "source": "test"},
            {"symbol": "SAMPLE-DELTA", "date": date.today() + timedelta(days=3), "type": "split", "value": 2.0, "source": "test"}],
            ["symbol", "date", "type"])
        db.execute(db.update(db.paper_trades).where(db.paper_trades.c.user_id == uid).values(
            ts=db.utcnow() - timedelta(days=10)))                     # pretend the buy happened earlier
        cash_before = P.account(uid)["cash"]
        db.execute(db.update(db.corporate_actions).where(db.corporate_actions.c.symbol == "SAMPLE-DELTA").values(
            date=date.today() - timedelta(days=1)))
        db.execute(db.update(db.corporate_actions).where(db.corporate_actions.c.symbol == "SAMPLE-DELTA")
                   .where(db.corporate_actions.c.type == "split").values(date=date.today()))
        assert P.apply_corporate_actions(uid) == 2
        assert P.apply_corporate_actions(uid) == 0                       # idempotent
        s = P.summary(uid, with_quotes=False)
        h = s["holdings"][0]
        # The provider restates dividends for later splits: 5.0 per share today = 10.0 per share before the 2:1 split,
        # so 10 shares held on the dividend ex-date receive 100 (verified on TCS: 0.375 x 8 = the Rs 3 actually paid in 2004).
        assert h["qty"] == 20 and s["cash"] == pytest.approx(cash_before + 100.0)
        db.execute(db.delete(db.corporate_actions).where(db.corporate_actions.c.source == "test"))


def test_alert_triggers_notification(client):
    price = client.get("/api/quotes?symbols=SAMPLE-ALPHA").json()["quotes"]["SAMPLE-ALPHA"]["price"]
    assert client.post("/api/alerts", json={"symbol": "SAMPLE-ALPHA", "direction": "above", "price": price * 0.5}).status_code == 200
    n = client.get("/api/notifications").json()
    assert n["unread"] == 1 and "SAMPLE-ALPHA" in n["items"][0]["title"]
    assert client.get("/api/alerts").json()[0]["active"] is False
    client.post("/api/notifications/read")
    assert client.get("/api/notifications").json()["unread"] == 0


def test_dcf_endpoint_and_validation(client):
    v = client.get("/api/companies/SAMPLE-ALPHA/valuation").json()
    body = {**v["dcf_defaults"], "wacc": 0.11}
    r = client.post("/api/companies/SAMPLE-ALPHA/dcf", json=body).json()
    assert r["per_share"] > 0 and len(r["projection"]) == body["years"] and set(r["scenarios"]) == {"Bear", "Base", "Bull"}
    assert len(r["sensitivity"]["values"]) == 5
    bad = client.post("/api/companies/SAMPLE-ALPHA/dcf", json={**body, "wacc": 0.04, "terminal_growth": 0.05})
    assert bad.status_code == 400 and "WACC" in bad.json()["detail"]


def test_bank_valuation_and_industry(client):
    assert client.get("/api/companies/SAMPLE-EPSILON/valuation").json()["is_financial"] is True
    b = client.get("/api/companies/SAMPLE-EPSILON/bank").json()
    assert "gnpa" in b["values"] and b["flags"]
    ind = client.get("/api/industries/banking").json()
    assert "nim" in ind["metrics"] and ind["drivers"]


def test_search_and_notes(client):
    res = client.get("/api/search?q=alpha").json()["results"]
    assert res and res[0]["symbol"] == "SAMPLE-ALPHA"
    r = client.put("/api/companies/SAMPLE-ALPHA/notes", json={"business_model": "Brands + distribution", "source": "AR p.12"})
    assert r.status_code == 200
    assert client.get("/api/companies/SAMPLE-ALPHA").json()["notes"]["business_model"] == "Brands + distribution"
    assert client.get("/api/companies/NOPE.NS").status_code == 404


def test_document_upload_and_rag(client):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.drawString(72, 750, "Chairman's letter: we focused on customers.")
    cv.showPage()
    cv.drawString(72, 750, "Revenue from operations grew 12% to Rs 1,000 crore driven by exports.")
    cv.drawString(72, 730, "Net debt fell to zero during the year.")
    cv.save()
    r = client.post("/api/documents", files={"file": ("ar.pdf", buf.getvalue(), "application/pdf")},
                    data={"symbol": "SAMPLE-BETA", "doc_type": "Annual Report", "period": "FY2026"})
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]
    hits = client.get(f"/api/documents/{doc_id}/search?q=revenue growth exports").json()["passages"]
    assert hits and hits[0]["page"] == 2
    ans = client.post("/api/assistant/ask", json={"question": "How did revenue grow?", "doc_ids": [doc_id]}).json()
    assert "p. 2" in ans["answer"] and any(s["ID"] == "D1" for s in ans["sources"])
    bad = client.post("/api/documents", files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
    assert bad.status_code == 400
    other = TestClient(app)
    assert other.delete(f"/api/documents/{doc_id}").status_code == 404   # another user cannot delete it
    assert other.get(f"/api/documents/{doc_id}/search?q=revenue").status_code == 404   # ...or search it
    leak = other.post("/api/assistant/ask", json={"question": "How did revenue grow?", "doc_ids": [doc_id]}).json()
    assert not any(s["ID"].startswith("D") for s in leak["sources"]) and "exports" not in leak["answer"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 200


def test_assistant_declines_recommendations(client):
    a = client.post("/api/assistant/ask", json={"question": "Should I buy this?", "symbol": "SAMPLE-GAMMA"}).json()
    assert "can't give buy, sell or hold recommendations" in a["answer"]


def test_report_pdf(client):
    r = client.post("/api/reports/SAMPLE-ALPHA", json={"analyst": "Tester"})
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_screener_compare_explore(client):
    s = client.get("/api/screener").json()
    assert len(s["rows"]) >= 5 and "Quality compounders" in s["presets"]
    sid = client.post("/api/screens", json={"name": "My quality", "filters": {"roe": [0.15, None]}}).json()["id"]
    assert client.get("/api/screens").json()[0]["id"] == sid
    c = client.get("/api/compare?symbols=SAMPLE-ALPHA,SAMPLE-BETA").json()
    assert len(c["rows"]) == 2
    assert client.get("/api/explore").status_code == 200


def test_security_headers_and_validation(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert client.post("/api/invest/orders", json={"symbol": "SAMPLE-BETA", "side": "HOLD", "qty": 1}).status_code == 422
    assert client.post("/api/alerts", json={"symbol": "SAMPLE-ALPHA", "direction": "above", "price": -5}).status_code == 422
    assert client.post("/api/companies/<script>/track").status_code in (400, 404)


def test_shareholding_entry(client):
    from equitypilot import db
    db.upsert(db.companies, [{"symbol": "TESTCO.NS", "name": "Test Co Ltd", "is_sample": False}], ["symbol"])
    url = "/api/companies/TESTCO.NS/shareholding"
    rows = [{"category": "Promoter & Promoter Group", "pct": 50.1, "pledged_pct": 0},
            {"category": "FII/FPI", "pct": 20}, {"category": "DII", "pct": 19.9}, {"category": "Public & Others", "pct": 10}]
    assert client.post("/api/companies/SAMPLE-ALPHA/shareholding", json={"period": "2025-09-30", "rows": rows}).status_code == 400
    assert client.post(url, json={"period": "2025-09-30", "rows": rows[:2]}).status_code == 400      # does not total 100%
    assert client.post(url, json={"period": "30-09-2025", "rows": rows}).status_code == 422           # bad date
    r = client.post(url, json={"period": "2025-09-30", "rows": rows, "source_url": "javascript:alert(1)"})
    assert r.status_code == 200 and r.json()["saved"] == 4
    sh = client.get("/api/companies/TESTCO.NS/ownership").json()["shareholding"]
    q = [x for x in sh if x["period"] == "2025-09-30"]
    assert len(q) == 4 and all(x["data_type"] == "user_entered" and not x["source_url"] for x in q)


def test_server_ai_key_needs_opt_in(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    monkeypatch.delenv("EQUITYPILOT_SHARED_AI_KEY", raising=False)
    assert client.get("/api/assistant/settings").json()["key_configured"] is False   # visitors can't spend the owner's key
    monkeypatch.setenv("EQUITYPILOT_SHARED_AI_KEY", "1")
    assert client.get("/api/assistant/settings").json()["key_configured"] is True


def test_paper_account_creation_is_idempotent(client):
    uid = client.get("/api/me").json()["user"]["id"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:
        accounts = list(ex.map(lambda _: P.account(uid), range(4)))
    assert {a["cash"] for a in accounts} == {P.INITIAL_CASH}
    assert client.get("/api/invest/summary").status_code == 200


def test_failed_feed_backs_off(monkeypatch):
    from equitypilot import config
    from equitypilot.data import feeds as N
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise OSError("truncated download")
    monkeypatch.setattr(config, "OFFLINE", False)
    monkeypatch.setattr(N.requests, "get", boom)
    db.set_setting("feed_refreshed:rbi_press", "2000-01-01T00:00:00")
    db.set_setting("feed_failed:rbi_press", "2000-01-01T00:00:00")
    assert N.refresh_feed("rbi_press")[0] is False
    assert N.refresh_feed("rbi_press")[0] is False      # second call within the back-off window: no new request
    assert len(calls) == 1
