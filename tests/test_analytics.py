"""Unit tests for ratio and valuation maths, checked against hand-computed values."""
import math

import pandas as pd
import pytest

from equitypilot.analytics import ratios as R
from equitypilot.analytics import valuation as V
from equitypilot.data.repository import FinancialData
from equitypilot import formatting as F


def make_fd(data: dict[str, list[float]], years=(2024, 2025)) -> FinancialData:
    cols = [pd.Timestamp(f"{y}-03-31") for y in years]
    wide = pd.DataFrame(data, index=cols).T
    return FinancialData(wide=wide, period_type="annual", basis="consolidated")


FD = make_fd({
    "revenue": [1000.0, 1200.0], "cogs": [600.0, 700.0], "gross_profit": [400.0, 500.0],
    "ebitda": [250.0, 300.0], "ebit": [200.0, 240.0], "interest_expense": [20.0, 30.0],
    "net_income": [120.0, 150.0], "eps_diluted": [12.0, 15.0], "total_equity": [800.0, 1000.0],
    "total_assets": [1500.0, 1700.0], "current_assets": [500.0, 600.0], "current_liabilities": [250.0, 300.0],
    "inventory": [100.0, 120.0], "receivables": [100.0, 150.0], "total_debt": [300.0, 400.0],
    "cash": [50.0, 100.0], "cfo": [140.0, 180.0], "capex": [-60.0, -80.0], "dividends_paid": [-30.0, -45.0],
    "shares_outstanding": [10.0, 10.0], "total_liabilities": [700.0, 700.0],
})


def test_margins_and_growth():
    rt = R.compute_ratios(FD)
    last = rt.iloc[:, -1]
    assert last["revenue_growth"] == pytest.approx(0.20)
    assert last["net_income_growth"] == pytest.approx(0.25)
    assert last["gross_margin"] == pytest.approx(500 / 1200)
    assert last["ebitda_margin"] == pytest.approx(0.25)
    assert last["net_margin"] == pytest.approx(0.125)
    assert math.isnan(rt.iloc[:, 0]["revenue_growth"])  # no prior year -> missing, not zero


def test_returns_use_average_balances():
    last = R.compute_ratios(FD).iloc[:, -1]
    assert last["roe"] == pytest.approx(150 / 900)                       # avg equity (800+1000)/2
    cap_emp = [(1500 - 250), (1700 - 300)]
    assert last["roce"] == pytest.approx(240 / (sum(cap_emp) / 2))
    assert last["roa"] == pytest.approx(150 / 1600)


def test_leverage_liquidity_cashflow():
    last = R.compute_ratios(FD).iloc[:, -1]
    assert last["debt_to_equity"] == pytest.approx(0.4)
    assert last["net_debt_to_ebitda"] == pytest.approx(300 / 300)
    assert last["interest_coverage"] == pytest.approx(8.0)
    assert last["current_ratio"] == pytest.approx(2.0)
    assert last["quick_ratio"] == pytest.approx((600 - 120) / 300)
    assert last["fcf_margin"] == pytest.approx((180 - 80) / 1200)       # FCF derived when not reported
    assert last["cfo_to_net_income"] == pytest.approx(1.2)
    assert last["dividend_payout"] == pytest.approx(0.3)
    assert last["receivable_days"] == pytest.approx(150 / 1200 * 365)
    assert last["bvps"] == pytest.approx(100.0)


def test_missing_inputs_stay_missing():
    fd = make_fd({"revenue": [100.0, 110.0], "net_income": [10.0, float("nan")]})
    last = R.compute_ratios(fd).iloc[:, -1]
    assert math.isnan(last["net_margin"])
    assert math.isnan(last["roe"])            # no equity at all


def test_negative_base_growth_is_not_meaningful():
    fd = make_fd({"revenue": [100.0, 110.0], "net_income": [-10.0, 5.0]})
    assert math.isnan(R.compute_ratios(fd).iloc[:, -1]["net_income_growth"])


def test_cagr():
    s = pd.Series([100.0, 121.0], index=[pd.Timestamp("2023-03-31"), pd.Timestamp("2025-03-31")])
    assert R.cagr(s) == pytest.approx(0.10)
    assert R.cagr(pd.Series([-5.0, 10.0], index=s.index)) is None


def test_dupont_identity():
    dp = R.dupont(FD)
    last = dp.iloc[:, -1]
    assert last["ROE (product)"] == pytest.approx(R.compute_ratios(FD).iloc[:, -1]["roe"])


def test_balance_sheet_check_flags_mismatch():
    issues = R.quality_checks(FD)  # assets 1700 vs 700+1000 = 1700 balances; 2024: 1500 vs 1500 balances
    assert not any("does not balance" in i["check"] for i in issues)
    bad = make_fd({"total_assets": [1000.0], "total_liabilities": [400.0], "total_equity": [500.0]}, years=(2025,))
    assert any("does not balance" in i["check"] for i in R.quality_checks(bad))


def test_market_snapshot_multiples():
    quote = {"price": 200.0, "shares_outstanding": 10.0, "market_cap": 2000.0, "dividend_rate": 4.0}
    snap = V.market_snapshot(quote, FD)
    assert snap["pe"] == pytest.approx(2000 / 150)
    assert snap["pb"] == pytest.approx(2.0)
    assert snap["ev"] == pytest.approx(2000 + 400 - 100)
    assert snap["ev_ebitda"] == pytest.approx(2300 / 300)
    assert snap["dividend_yield"] == pytest.approx(0.02)


def test_wacc():
    w = V.wacc(rf=0.07, beta=1.2, erp=0.06, kd_pre_tax=0.09, tax_rate=0.25, equity_value=800, debt_value=200)
    assert w["ke"] == pytest.approx(0.142)
    assert w["kd_post_tax"] == pytest.approx(0.0675)
    assert w["wacc"] == pytest.approx(0.8 * 0.142 + 0.2 * 0.0675)


def test_dcf_hand_calculation():
    inp = V.DCFInputs(base_revenue=1000, growth_start=0.10, growth_end=0.10, ebit_margin=0.20, tax_rate=0.25,
                      da_pct=0.05, capex_pct=0.05, nwc_pct=0.0, wacc=0.10, terminal_growth=0.05,
                      net_debt=100, shares=10, years=1)
    res = V.run_dcf(inp)
    fcff = 1100 * 0.20 * 0.75                       # 165 (D&A = capex, no NWC)
    tv = fcff * 1.05 / 0.05                         # 3465
    ev = fcff / 1.1 + tv / 1.1
    assert res.projection["FCFF"].iloc[0] == pytest.approx(fcff)
    assert res.enterprise_value == pytest.approx(ev)
    assert res.per_share == pytest.approx((ev - 100) / 10)


def test_dcf_rejects_wacc_below_growth():
    inp = V.DCFInputs(1000, 0.1, 0.1, 0.2, 0.25, 0.05, 0.05, 0.1, wacc=0.05, terminal_growth=0.06,
                      net_debt=0, shares=10)
    with pytest.raises(V.DCFError):
        V.run_dcf(inp)


def test_reverse_dcf_recovers_growth():
    base = V.DCFInputs(1000, 0.12, 0.12, 0.2, 0.25, 0.04, 0.05, 0.1, 0.11, 0.05, 0, 10)
    target = V.run_dcf(base).per_share
    g = V.reverse_dcf(base, target)
    assert g == pytest.approx(0.12, abs=1e-3)


def test_sensitivity_monotonic():
    base = V.DCFInputs(1000, 0.1, 0.08, 0.2, 0.25, 0.04, 0.05, 0.1, 0.11, 0.05, 0, 10)
    grid = V.sensitivity(base, [0.10, 0.12], [0.04, 0.05])
    assert grid.iloc[0, 0] > grid.iloc[1, 0]          # higher WACC -> lower value
    assert grid.iloc[0, 1] > grid.iloc[0, 0]          # higher g -> higher value


def test_justified_pb():
    assert V.justified_pb(0.16, 0.13, 0.06) == pytest.approx(0.10 / 0.07)
    assert V.justified_pb(0.16, 0.05, 0.06) is None


def test_formatting():
    assert F.indian_group(1234567.891) == "12,34,567.89"
    assert F.crore(2.5e9) == "₹250 Cr"
    assert F.pct(0.1534) == "15.3%"
    assert F.pct(None) == F.MISSING
    assert F.fiscal_label(pd.Timestamp("2025-03-31")) == "FY2025"
