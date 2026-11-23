"""Formulas used by the Learning Centre: numeric quiz answers are checked against these in the tests, the offline
assistant uses them to build fresh practice examples, and the web calculators implement the same formulas
(web/src/lib/learnCalc.ts, tested against the same hand calculations).

All rates are fractions (0.08 = 8%). Every function returns plain floats so results can be shown with steps."""
from __future__ import annotations

import math


# ---------------------------------------------------------------- time value of money
def fv(pv: float, rate: float, years: float, times_per_year: int = 1) -> float:
    """Future value with compounding: FV = PV x (1 + r/m)^(m x n)."""
    return pv * (1 + rate / times_per_year) ** (times_per_year * years)


def pv(future: float, rate: float, years: float) -> float:
    """Present value of one future amount: PV = FV / (1 + r)^n."""
    return future / (1 + rate) ** years


def pv_stream(flows: list[float], rate: float) -> float:
    """Present value of cash flows received at the end of years 1, 2, 3 ..."""
    return sum(f / (1 + rate) ** t for t, f in enumerate(flows, start=1))


def simple_interest(principal: float, rate: float, years: float) -> float:
    return principal * rate * years


def effective_rate(rate: float, times_per_year: int) -> float:
    """Effective annual rate of a nominal rate compounded m times a year: (1 + r/m)^m - 1."""
    return (1 + rate / times_per_year) ** times_per_year - 1


def years_to_double(rate: float) -> float:
    """Exact doubling time ln 2 / ln(1 + r) (the 'rule of 72' approximates it as 72 / rate%)."""
    return math.log(2) / math.log(1 + rate)


def real_return(nominal: float, inflation: float) -> float:
    """Fisher relation: (1 + nominal) / (1 + inflation) - 1."""
    return (1 + nominal) / (1 + inflation) - 1


def annualised(multiple: float, years: float) -> float:
    """Annual compound rate that turns 1 into `multiple` in `years`."""
    return multiple ** (1 / years) - 1


def expected_return(outcomes: list[tuple[float, float]]) -> float:
    """sum(probability x return)."""
    return sum(p * r for p, r in outcomes)


# ---------------------------------------------------------------- statements and ratios
def eps(net_profit: float, shares: float) -> float:
    return net_profit / shares


def pe(price: float, eps_value: float) -> float:
    return price / eps_value


def peg(pe_value: float, growth_pct: float) -> float:
    """PEG = P/E / expected annual EPS growth in percent (e.g. 20 / 15)."""
    return pe_value / growth_pct


def roe(net_profit: float, equity_start: float, equity_end: float) -> float:
    return net_profit / ((equity_start + equity_end) / 2)


def roce(ebit: float, total_assets: float, current_liabilities: float) -> float:
    return ebit / (total_assets - current_liabilities)


def margin(part: float, revenue: float) -> float:
    return part / revenue


def free_cash_flow(cfo: float, capex: float) -> float:
    """FCF = cash from operations - capital expenditure (capex given as a positive amount)."""
    return cfo - capex


def fcff(ebit: float, tax: float, da: float, capex: float, delta_nwc: float) -> float:
    return ebit * (1 - tax) + da - capex - delta_nwc


def fcfe(fcff_value: float, interest: float, tax: float, net_borrowing: float) -> float:
    return fcff_value - interest * (1 - tax) + net_borrowing


def straight_line(cost: float, residual: float, life_years: float) -> float:
    return (cost - residual) / life_years


def enterprise_value(market_cap: float, debt: float, cash: float) -> float:
    return market_cap + debt - cash


def nim(interest_earned: float, interest_expended: float, earning_assets: float) -> float:
    return (interest_earned - interest_expended) / earning_assets


# ---------------------------------------------------------------- valuation
def capm(rf: float, beta: float, erp: float) -> float:
    return rf + beta * erp


def wacc(ke: float, kd: float, tax: float, weight_equity: float) -> float:
    return weight_equity * ke + (1 - weight_equity) * kd * (1 - tax)


def gordon(next_cash_flow: float, rate: float, growth: float) -> float:
    """Value of a cash flow growing for ever: CF(1) / (r - g). Undefined when g >= r."""
    if growth >= rate:
        raise ValueError("growth must be below the discount rate")
    return next_cash_flow / (rate - growth)


def dcf(fcf0: float, growth: float, years: int, rate: float, terminal_growth: float, net_debt: float = 0.0,
        shares: float = 1.0) -> dict:
    """A simple DCF: FCF grows at `growth` for `years`, then at `terminal_growth` for ever."""
    flows = [fcf0 * (1 + growth) ** t for t in range(1, years + 1)]
    pvs = [f / (1 + rate) ** t for t, f in enumerate(flows, start=1)]
    tv = gordon(flows[-1] * (1 + terminal_growth), rate, terminal_growth)
    pv_tv = tv / (1 + rate) ** years
    ev = sum(pvs) + pv_tv
    equity = ev - net_debt
    return {"flows": flows, "pvs": pvs, "terminal_value": tv, "pv_terminal": pv_tv, "enterprise_value": ev,
            "equity_value": equity, "per_share": equity / shares, "terminal_share": pv_tv / ev}


def margin_of_safety(intrinsic: float, price: float) -> float:
    return (intrinsic - price) / intrinsic


def terp(old_shares: float, price: float, new_shares: float, issue_price: float) -> float:
    """Theoretical ex-rights price."""
    return (old_shares * price + new_shares * issue_price) / (old_shares + new_shares)


# ---------------------------------------------------------------- bonds, funds and markets
def current_yield(coupon: float, price: float) -> float:
    return coupon / price


def approx_ytm(coupon: float, face: float, price: float, years: float) -> float:
    """Approximate yield to maturity: (C + (F - P) / n) / ((F + P) / 2)."""
    return (coupon + (face - price) / years) / ((face + price) / 2)


def nav(assets: float, liabilities: float, units: float) -> float:
    return (assets - liabilities) / units


def index_move(weights: list[float], moves: list[float]) -> float:
    return sum(w * m for w, m in zip(weights, moves))


def price_band(prev_close: float, band: float) -> tuple[float, float]:
    return prev_close * (1 - band), prev_close * (1 + band)


def call_payoff(spot: float, strike: float, premium: float) -> float:
    return max(spot - strike, 0.0) - premium


def put_payoff(spot: float, strike: float, premium: float) -> float:
    return max(strike - spot, 0.0) - premium


# ---------------------------------------------------------------- technicals
def sma(values: list[float]) -> float:
    return sum(values) / len(values)


def ema_next(close: float, previous_ema: float, periods: int) -> float:
    k = 2 / (periods + 1)
    return close * k + previous_ema * (1 - k)


def rsi(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def annualise_volatility(daily_sd: float, days: int = 252) -> float:
    return daily_sd * math.sqrt(days)


# ---------------------------------------------------------------- portfolio
def portfolio_return(weights: list[float], returns: list[float]) -> float:
    return sum(w * r for w, r in zip(weights, returns))


def two_asset_sd(w1: float, sd1: float, sd2: float, corr: float) -> float:
    w2 = 1 - w1
    return math.sqrt(w1 ** 2 * sd1 ** 2 + w2 ** 2 * sd2 ** 2 + 2 * w1 * w2 * corr * sd1 * sd2)


def sharpe(rp: float, rf: float, sd: float) -> float:
    return (rp - rf) / sd


def treynor(rp: float, rf: float, beta: float) -> float:
    return (rp - rf) / beta


def jensen_alpha(rp: float, rf: float, beta: float, rm: float) -> float:
    return rp - (rf + beta * (rm - rf))


def drawdown(peak: float, trough: float) -> float:
    return (trough - peak) / peak


def position_size(capital: float, risk_fraction: float, entry: float, stop: float) -> float:
    """Shares to buy so that a fall from entry to stop loses `risk_fraction` of capital."""
    return (capital * risk_fraction) / (entry - stop)


FUNCTIONS = {name: fn for name, fn in globals().items() if callable(fn) and not name.startswith("_") and name not in ("math",)}
