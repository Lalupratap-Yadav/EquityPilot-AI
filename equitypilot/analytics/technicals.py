"""Technical indicators and market-risk statistics computed from daily OHLCV data.

Indicator readings describe past price behaviour; they are not trading signals or recommendations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    return close.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI: 100 - 100/(1+RS), RS = smoothed avg gain / smoothed avg loss."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(avg_loss != 0, 100.0).where(avg_gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"MACD": line, "Signal": sig, "Histogram": line - sig})


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return pd.DataFrame({"Upper": mid + k * sd, "Middle": mid, "Lower": mid - k * sd})


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def annualised_volatility(close: pd.Series, window: int | None = None) -> float | pd.Series:
    r = daily_returns(close)
    if window:
        return r.rolling(window, min_periods=window).std() * np.sqrt(TRADING_DAYS)
    return float(r.std() * np.sqrt(TRADING_DAYS))


def drawdown(close: pd.Series) -> pd.Series:
    return close / close.cummax() - 1


def max_drawdown(close: pd.Series) -> float:
    return float(drawdown(close).min()) if len(close) else float("nan")


def beta(stock_close: pd.Series, bench_close: pd.Series, min_obs: int = 60) -> tuple[float | None, float | None, int]:
    """Beta = Cov(r_s, r_m) / Var(r_m) on aligned daily returns. Returns (beta, correlation, observations)."""
    df = pd.concat([stock_close.pct_change(), bench_close.pct_change()], axis=1, join="inner").dropna()
    if len(df) < min_obs:
        return None, None, len(df)
    cov = np.cov(df.iloc[:, 0], df.iloc[:, 1], ddof=1)
    b = cov[0, 1] / cov[1, 1] if cov[1, 1] else None
    return (float(b) if b is not None else None), float(df.corr().iloc[0, 1]), len(df)


def period_return(close: pd.Series, dates: pd.Series, days: int) -> float | None:
    if close.empty:
        return None
    end = dates.iloc[-1]
    past = close[dates <= end - pd.Timedelta(days=days)]
    if past.empty:
        return None
    return float(close.iloc[-1] / past.iloc[-1] - 1)


def indicator_frame(px: pd.DataFrame) -> pd.DataFrame:
    c = px["close"]
    out = pd.DataFrame({"date": px["date"], "close": c,
                        "SMA 20": sma(c, 20), "SMA 50": sma(c, 50), "SMA 200": sma(c, 200),
                        "EMA 20": ema(c, 20), "RSI 14": rsi(c, 14)})
    out = pd.concat([out, macd(c), bollinger(c).add_prefix("BB ")], axis=1)
    out["ATR 14"] = atr(px)
    out["Volatility 20D"] = annualised_volatility(c, 20)
    out["Drawdown"] = drawdown(c)
    return out


def readings(ind: pd.DataFrame) -> list[dict]:
    """Plain-English description of the latest indicator values (descriptive, not advice)."""
    last = ind.iloc[-1]
    out = []

    def add(name, value, text, tone="neutral"):
        out.append({"Indicator": name, "Value": value, "Reading": text, "tone": tone})

    c = last["close"]
    for n in (50, 200):
        s = last.get(f"SMA {n}")
        if pd.notna(s):
            above = c > s
            add(f"Price vs {n}-day SMA", f"{(c / s - 1):+.1%}",
                f"Price is {'above' if above else 'below'} its {n}-day average", "good" if above else "warning")
    s50, s200 = ind["SMA 50"], ind["SMA 200"]
    cross = (s50 > s200).astype(float).diff()
    recent = cross[cross != 0].dropna()
    if len(recent):
        idx = recent.index[-1]
        kind = "Golden cross (50-day rose above 200-day)" if recent.iloc[-1] > 0 else "Death cross (50-day fell below 200-day)"
        add("Last moving-average crossover", ind.loc[idx, "date"].strftime("%d %b %Y"), kind,
            "good" if recent.iloc[-1] > 0 else "warning")
    r = last.get("RSI 14")
    if pd.notna(r):
        state = "overbought zone (>70)" if r > 70 else "oversold zone (<30)" if r < 30 else "neutral range (30-70)"
        add("RSI (14)", f"{r:.1f}", f"In the {state}", "warning" if r > 70 or r < 30 else "neutral")
    m, sg = last.get("MACD"), last.get("Signal")
    if pd.notna(m) and pd.notna(sg):
        add("MACD vs signal", f"{m - sg:+.2f}", "MACD above signal line (positive momentum)" if m > sg
            else "MACD below signal line (negative momentum)", "good" if m > sg else "warning")
    up, lo = last.get("BB Upper"), last.get("BB Lower")
    if pd.notna(up) and pd.notna(lo):
        pos = (c - lo) / (up - lo) if up != lo else np.nan
        add("Bollinger %B", f"{pos:.2f}", "Near upper band" if pos > 0.9 else "Near lower band" if pos < 0.1
            else "Within bands", "warning" if pos > 1 or pos < 0 else "neutral")
    return out
