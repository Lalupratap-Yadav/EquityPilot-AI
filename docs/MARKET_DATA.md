# Market data in EquityPilot

## What you get by default (free)

| Data | Source | Freshness |
|---|---|---|
| Index and stock quotes | Yahoo Finance via `yfinance` | Delayed (typically ~15 min for NSE). Labelled **DELAYED** in the app |
| Charts (1D to MAX) | Yahoo Finance | Intraday bars delayed; daily/weekly end-of-day |
| Financial statements | Yahoo Finance (third-party) | Verify with annual reports / NSE-BSE filings |
| Disclosures, RBI, SEBI | Official RSS feeds | As published |

While the market is in session, the server refreshes every index and every symbol someone has on screen every
20 seconds (`EQUITYPILOT_HOT_INTERVAL`). The browser receives only the quotes that changed, over a WebSocket. This is
"auto-updating delayed data". It is **not** real-time, and the app never labels it as live.

The market clock knows the pre-open (09:00–09:15 IST), the regular session (09:15–15:30 IST) and weekends. It
detects exchange holidays from the data: if a freshly fetched NIFTY 50 quote still belongs to an earlier day 20 minutes
after the open, the market is reported closed for the day.

## Real-time quotes (optional, paid): Zerodha Kite Connect

Groww, Zerodha and other brokers show real-time prices because they pay the exchanges for a licensed feed. The
legitimate way for an individual to get real-time NSE/BSE quotes in their own app is a broker API linked to their own
trading account. EquityPilot includes a connector for **Zerodha Kite Connect**. It is switched off unless you configure it.

**Requirements and cost (check the current price on https://kite.trade before subscribing):**
- A Zerodha trading account.
- A Kite Connect developer app (developers.kite.trade). It is a paid subscription, around ₹500 per month at the time of writing.
- An **access token that expires every day**. You must log in to Kite each trading day and generate a new token
  through the Kite Connect login flow. EquityPilot does not automate the Zerodha login and never asks for your
  Zerodha password.

**Setup** (environment variables on the server; never commit them to Git):

```
EQUITYPILOT_MARKET_PROVIDER=kite
KITE_API_KEY=your_api_key
KITE_ACCESS_TOKEN=todays_access_token
```

Restart the server. `GET /api/health` then shows `"market_data": {"provider": "Zerodha Kite Connect (real-time)", "realtime": true}`.

**What changes:**
- Quotes come from Kite and are labelled **LIVE** during market hours.
- Charts still use Yahoo history, but their last point is the live quote.
- Symbols Kite does not recognise fall back to the delayed source and keep the DELAYED label.
- If the token expires or Kite is unreachable, quotes fall back to delayed data automatically. `/api/health` shows the error.

Kite's terms allow the data for your **personal use**. Do not redistribute it to the public from a shared deployment.

The connector is tested against mocked Kite responses. It has not been tested against a live Kite account.

## Adding another provider

Implement `MarketDataProvider.quotes()` (and optionally `bars()`) in `equitypilot/data/marketdata.py`, set
`realtime = True` only for a licensed real-time feed, and select it in `_make_provider()`.
