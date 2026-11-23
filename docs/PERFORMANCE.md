# EquityPilot AI - Performance report (v2.7.0, 23 Nov 2026)

Every number below was measured on the owner's Windows 11 laptop (12 logical processors) on 22-23 Nov 2026, with the
market closed. "Before" is v2.6.0 (commit 6e95f0f), "after" is v2.7.0. Live measurements used a copy of the real
database (127 tracked companies, 96,000 stored news items) and the real Yahoo Finance, NSE, RBI, SEBI and publisher feeds.
The owner's own v2.6.0 server kept running on port 8000 during all measurements, so both versions shared the machine.
Nothing was hidden behind placeholder data: every page still reads real, labelled data.

## 1. What was slow, and why

| Problem | Cause found |
|---|---|
| Slow first minute after a restart | Request handlers waited for Yahoo (quote refreshes, chart bars) and for publisher feeds (`/api/news` downloaded every feed inside the request). In the background, the ~140-symbol quote download (yfinance spends ~0.1 s of CPU per symbol) and the universe-metrics recompute (8-36 s of pandas work) ran inside the server process and held Python's interpreter lock. |
| News & Intelligence 8-15 s | `dedupe()` compared every media headline with every other one (1.9 million comparisons), and `_clean_summary()` compiled a new regular expression for every headline (2,261 compiles, overflowing Python's regex cache). |
| Valuation 2.5-4 s, Peers 2-3.5 s, Compare 1.3-2 s | The metrics of 6-7 companies were recomputed from scratch on every request (statements read and pivoted, ~30 ratios computed), with one database query per company detail. |
| Universe metrics 8-36 s per recompute | Same per-company work for all 127 companies, every 10 minutes, even though statements change at most weekly. |
| Every database call | `db.get_engine()` created the three data folders (`mkdir`) on every query - the largest single item in a profile of the running server. |
| First page load | The whole recharts library (440 KB, 123 KB gzipped) was downloaded and parsed on every first visit: the bundler had put React and `clsx` inside the recharts chunk. |
| Every new browser connection to `http://localhost:8000` | The server listened on IPv4 only; Windows tries IPv6 (`::1`) first and waited ~0.21 s per connection before falling back. |
| Single-symbol quotes (orders, first view of a symbol) | yfinance 1.x keeps the ticker column level even for one symbol; the old parser expected a flat layout and silently returned no quote, so the last stored price was used. |
| PDF upload | Text and table detection by pdfplumber on every page (~0.1 s a page), run directly in the async request handler - which froze every other request and the live-quote WebSocket for the duration. |

## 2. Restart: what a browser on Home sees

A copy of the database with a 30-minute-old metrics snapshot was started; every ~3.5 s the 11 Home requests plus 5 others
(search, company page, top news, screener, NIFTY 1D chart) were fired together (6 at a time), for 100-110 s.

| Moment | Before (v2.6.0) | After (v2.7.0) |
|---|---|---|
| Server answers its first request | 7.0 s | 3.5 s |
| First burst - slowest Home request | 10.8 s | 0.58 s |
| First burst - company page | 40.2 s | 0.47 s |
| First burst - NIFTY 1D chart | 32.3 s | 3.6 s |
| First burst - News (top) | 17.6 s | 3.2 s |
| First burst - search | 10.1 s | 1.0 s |
| ~50 s after start - slowest Home request | 5.5 s | 0.45 s |
| ~60 s after start | 1.8 s | 0.38-0.46 s |
| Rest of the window | 0.26-4.4 s, company page 4-7 s, chart up to 14 s | 0.24-0.47 s; one background window of 1.0-2.1 s around 90-104 s |

An earlier after-run (before the last two fixes) had one request that waited until the probe's 60-second timeout around
50 s after start. It could not be reproduced afterwards; the chart path, the only remaining place where a request could
still wait for Yahoo, has since been changed to stale-while-revalidate (section 4).

## 3. Steady state, per endpoint (warm servers, median of 3 calls over 127.0.0.1)

See the table in TEST_REPORT.md section 3 (both versions measured back to back on the same machine).

## 4. Fixes and their measured effect

| Area | Change | Measured |
|---|---|---|
| Statement tables | Built once per company and reused until the stored rows change (row count, last fetch time and value total checked with one small query); callers get copies | Company page 0.58 → 0.04 s, Valuation 3.09 → 0.11 s, Peers 3.44 → 0.09 s, Compare 1.87 → 0.11 s, Risk 0.60 → 0.03 s (in-process, warm) |
| Universe metrics | Statement-based figures cached per company; recomputes run in a worker process | Recompute 7.9 s → 0.9-1.0 s; the first one after a restart (7.8 s) no longer runs in the server process. Output identical to v2.6.0 for all 127 companies (`assert_frame_equal`) |
| News | Exact prefix-filter index for near-duplicates; one compiled regex; ASCII fast path and memo in the company matcher; stale-while-revalidate cache whose rebuild runs in the worker; feed checks at most once a minute | Top section uncached: ~15 s → 0.56-0.74 s. All 13 sections × 2 windows: 21.3 s → 9.0 s, output identical (randomised test against the old algorithm) |
| `/api/news` (Home) | Feeds refreshed in the background instead of inside the request | 23-29 s on a restart → under 1.5 s |
| Quotes | Pages read cached quotes and refresh stale ones in the background (the WebSocket pushes the new values); after the close, final quotes kept 30 min; daily bars that already include the last session skip the 1-minute download; batches of 8+ symbols run in the worker process | 127-symbol refresh: 22 s of CPU in the server process → 0 (12-13 s in the worker); 10-symbol batch after the close: 3.0 → 1.2 s CPU |
| Charts | Cached bars served at once and refreshed in the background; bars fetched after the session kept 30 min | Repeat views no longer wait for the provider |
| Database | Data folders created once; batched reads for quotes, companies and feed status; counting queries on Explore; raw rows for statement signatures | The largest item in the server profile removed |
| Search | News results from publisher and regulator feeds only (exchange filing titles are company names, 95% of the table), matched in memory and reloaded every 2 minutes | News part of a search: 10-230 ms → 1-5 ms, whatever the words |
| Start-up | PDF report module (matplotlib, reportlab) imported only when a report is generated | Server import 13.7 s → 6.5 s (busy machine, back-to-back runs) |
| `python -m api` | Listens on 127.0.0.1 and ::1 (loopback only); `start.bat` uses it | New connection to `localhost`: 0.21 s → 0.0006 s |
| First visit | Explicit, prioritised code-splitting groups (React and first-page libraries before the chart libraries) | JavaScript parsed on first visit 835 KB → 389 KB; transferred (gzip, JS + CSS) 259 KB → 136 KB; recharts loads only on pages with charts |
| PDF upload | pdfium for page text; pdfplumber tables only on pages with figures (at most 60); extraction and indexing in a worker thread | 300-page synthetic report: 60.9 s → 12.1 s, same 60 tables; other requests are no longer blocked |
| Worker process | One long-lived worker (spawned, loopback only) for bulk quotes, metrics recomputes and news rebuilds; exits when the server process ends, however it ends | Orphaned workers found during testing; now verified to exit within 0.5 s of a force-kill |

## 5. AI assistant response time

| Engine | Measured |
|---|---|
| Offline analyst | 0.02-0.4 s for concepts, screens, comparisons and follow-ups; 0.5-3.3 s for a company's first question (context built from the database); up to ~9 s for the very first question in a fresh process while caches load |
| Claude API | Not measured: no API key was available, and no paid call was made. Predictable questions now arrive with the needed data already retrieved (in parallel), so a typical company, comparison, market or news question needs one model turn instead of two (verified with a fake client); parallel tool calls also run at once |

## 6. How to reproduce

The probe and benchmark scripts used are simple (curl, a Python HTTP client and the in-process timings shown in
TEST_REPORT.md). Any measurement depends on the machine, the network and Yahoo's response times; compare versions on the
same machine, one after the other.
