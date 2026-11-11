"""Default research universe.

This is a hand-picked list of large, liquid NSE-listed companies used to seed the screener.
It is NOT an index-constituent list (index membership changes; check NSE Indices for that).
Users can add or remove companies in the Data Manager. Names, sectors and all numbers are
fetched from the data provider - nothing here is a financial figure.
"""

# Yahoo Finance symbols for NSE listings use the ".NS" suffix (".BO" for BSE).
DEFAULT_UNIVERSE: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "LT.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS", "SUNPHARMA.NS",
    "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "POWERGRID.NS",
    "NTPC.NS", "ONGC.NS", "COALINDIA.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS",
    "ADANIPORTS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "BRITANNIA.NS", "TATACONSUM.NS", "GRASIM.NS",
    "APOLLOHOSP.NS", "PIDILITIND.NS", "DABUR.NS", "HAVELLS.NS",
]


def normalise_symbol(raw: str) -> str:
    """Turn user input like 'reliance', 'RELIANCE.NS', 'NSE:TCS', '500325' into a provider symbol."""
    s = raw.strip().upper().replace(" ", "")
    if s.startswith("SAMPLE-"):
        return s
    for prefix in ("NSE:", "BSE:"):
        if s.startswith(prefix):
            body = s[len(prefix):]
            return body + (".NS" if prefix == "NSE:" else ".BO")
    if s.startswith("^") or s.endswith(".NS") or s.endswith(".BO"):
        return s
    if s.isdigit():          # BSE scrip code
        return s + ".BO"
    return s + ".NS"


def exchange_of(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol.startswith("SAMPLE-"):
        return "SAMPLE"
    return "—"


def base_ticker(symbol: str) -> str:
    return symbol.rsplit(".", 1)[0] if symbol.endswith((".NS", ".BO")) else symbol
