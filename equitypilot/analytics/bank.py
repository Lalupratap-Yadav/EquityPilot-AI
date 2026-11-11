"""Bank / NBFC metrics.

These figures come from banks' quarterly disclosures (results press release, investor
presentation, Basel III Pillar 3 disclosures). The market-data provider does not supply them,
so they are entered by the user with a source reference. Thresholds below are EquityPilot's
screening bands, not regulatory classifications - except the CRAR floor, which reflects the
RBI minimum for scheduled commercial banks (9% plus a 2.5% capital conservation buffer = 11.5%).
"""
from __future__ import annotations

import pandas as pd

# key: (label, help, higher_is_better, (good, warn, serious) cut-offs or None)
BANK_METRICS: dict[str, tuple[str, str, bool, tuple[float, float, float] | None]] = {
    "nim": ("Net interest margin (NIM) %", "Net interest income / average interest-earning assets (annualised).", True, None),
    "gnpa": ("Gross NPA %", "Gross non-performing assets / gross advances.", False, (2.0, 4.0, 7.0)),
    "nnpa": ("Net NPA %", "NPAs net of provisions / net advances.", False, (0.5, 1.5, 3.0)),
    "pcr": ("Provision coverage ratio %", "Provisions held / gross NPAs.", True, (75.0, 65.0, 50.0)),
    "crar": ("Capital adequacy (CRAR) %", "Total capital / risk-weighted assets (Basel III).", True, (16.0, 13.0, 11.5)),
    "casa": ("CASA ratio %", "Current + savings account deposits / total deposits - a low-cost funding indicator.", True, (40.0, 30.0, 20.0)),
    "cost_to_income": ("Cost-to-income %", "Operating expenses / net total income.", False, (45.0, 55.0, 65.0)),
    "credit_cost": ("Credit cost %", "Loan-loss provisions / average advances (annualised).", False, (1.0, 2.0, 3.0)),
}
ORDER = list(BANK_METRICS)


def wide(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = metric key (in display order), columns = period (ascending)."""
    if df is None or df.empty:
        return pd.DataFrame()
    w = df.pivot_table(index="metric", columns="period", values="value", aggfunc="last")
    w = w.reindex(columns=sorted(w.columns))
    return w.reindex([k for k in ORDER if k in w.index])


def _level(key: str, v: float) -> str:
    _, _, higher, cuts = BANK_METRICS[key]
    if pd.isna(v):
        return "na"
    if cuts is None:
        return "info"          # descriptive metric without a screening band (e.g. NIM varies by business model)
    g, w, s = cuts
    if higher:
        return "good" if v >= g else "warning" if v >= w else "serious" if v >= s else "critical"
    return "good" if v <= g else "warning" if v <= w else "serious" if v <= s else "critical"


def assess(df: pd.DataFrame) -> list[dict]:
    """Risk flags (same shape as analytics.risk flags) from the latest quarter, with trend notes."""
    w = wide(df)
    if w.empty:
        return []
    flags = []
    for key in w.index:
        label, help_, higher, cuts = BANK_METRICS[key]
        s = w.loc[key].dropna()
        if s.empty:
            continue
        v = float(s.iloc[-1])
        trend = ""
        if len(s) >= 2:
            d = v - float(s.iloc[0])
            better = (d > 0) == higher
            trend = f" Change since {s.index[0]}: {d:+.2f} pp ({'improving' if better else 'deteriorating'})." if d else ""
        rule = "—" if cuts is None else (
            f"≥{cuts[0]}% low · ≥{cuts[1]}% moderate · ≥{cuts[2]}% elevated · below high" if higher
            else f"≤{cuts[0]}% low · ≤{cuts[1]}% moderate · ≤{cuts[2]}% elevated · above high")
        cat = "Asset quality" if key in ("gnpa", "nnpa", "pcr", "credit_cost") else \
              "Capital" if key == "crar" else "Funding & efficiency"
        detail = help_ + f" Latest quarter {s.index[-1]}." + trend
        if key == "crar":
            detail += " RBI minimum for scheduled commercial banks incl. conservation buffer: 11.5%."
        flags.append({"category": cat, "title": label.replace(" %", ""), "level": _level(key, v),
                      "value": f"{v:.2f}%", "rule": rule, "detail": detail})
    return flags


def latest(df: pd.DataFrame, key: str) -> float | None:
    w = wide(df)
    if w.empty or key not in w.index:
        return None
    s = w.loc[key].dropna()
    return float(s.iloc[-1]) if len(s) else None
