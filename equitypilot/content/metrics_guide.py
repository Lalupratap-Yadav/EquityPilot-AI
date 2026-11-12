"""Plain-English explanations of financial metrics, plus cautious benchmark assessments.

Each guide entry answers four questions for a beginner:
  what    - what the number measures, in one or two sentences
  why     - why an investor or analyst looks at it
  read    - how to read it, including a general rule of thumb where one is widely used
  example - a small worked example with round numbers

`assess()` labels a value as strong / moderate / weak ONLY for metrics where a broadly used
benchmark exists, and never for valuation multiples (cheap vs expensive depends on growth,
risk and peers, so we point the user to history and peer comparisons instead). Benchmarks
are general rules of thumb across non-financial Indian companies; they are not sector-specific
targets, and the UI says so. For banks/NBFCs leverage, liquidity and margin benchmarks are
not meaningful and are skipped.
"""
from __future__ import annotations

GUIDE: dict[str, dict[str, str]] = {
    # ---------------- growth
    "revenue_growth": {
        "what": "How much the company's sales grew compared with the previous year.",
        "why": "Sales growth is the starting point for profit growth. Without it, profits can only rise by cutting costs, which has limits.",
        "read": "Compare it with inflation (roughly 4-6% in India in recent years) and with peers. Growth below inflation means the business is shrinking in real terms.",
        "example": "Revenue rose from ₹1,000 Cr to ₹1,100 Cr, so growth = 1,100 / 1,000 - 1 = 10%.",
    },
    "ebitda_growth": {
        "what": "Growth in operating profit before depreciation, interest and tax.",
        "why": "Shows whether the core business is earning more, before financing and accounting choices.",
        "read": "If EBITDA grows faster than revenue, margins are expanding; slower means margins are being squeezed.",
        "example": "EBITDA from ₹200 Cr to ₹230 Cr = 15% growth while revenue grew 10%, so the margin improved.",
    },
    "net_income_growth": {
        "what": "Growth in the profit that belongs to shareholders after all expenses and tax.",
        "why": "Over long periods share prices tend to follow profit growth.",
        "read": "One-off gains or losses can distort a single year, so look at several years and at the cash flow statement too.",
        "example": "Net profit from ₹100 Cr to ₹90 Cr is -10% growth.",
    },
    "eps_growth": {
        "what": "Growth in profit per share (EPS).",
        "why": "If a company issues many new shares, total profit can grow while each shareholder's slice does not. EPS growth captures that dilution.",
        "read": "EPS growth well below net profit growth signals dilution; above it can mean share buybacks.",
        "example": "Profit +20% but share count +15% gives EPS growth of about 4%.",
    },
    # ---------------- profitability
    "gross_margin": {
        "what": "The share of sales left after paying for raw materials or direct costs.",
        "why": "Reflects pricing power and input-cost exposure.",
        "read": "Varies hugely by industry - software can exceed 60%, while commodity processors may be under 20%. Compare with peers and with the company's own history.",
        "example": "Sales ₹1,000 Cr, direct costs ₹600 Cr, so gross margin = 400 / 1,000 = 40%.",
    },
    "ebitda_margin": {
        "what": "Operating profit before depreciation, interest and tax, as a share of sales.",
        "why": "A common measure of how efficiently the core business runs, comparable across companies with different debt levels.",
        "read": "Depends heavily on the industry. A stable or rising margin over several years is generally a good sign.",
        "example": "EBITDA ₹250 Cr on sales of ₹1,000 Cr = 25% margin.",
    },
    "ebit_margin": {
        "what": "Operating profit (after depreciation) as a share of sales.",
        "why": "Shows how much of each rupee of sales becomes operating profit, after the cost of wearing out assets.",
        "read": "Compare with peers in the same industry. Capital-heavy businesses show a bigger gap between EBITDA and EBIT margins.",
        "example": "EBIT ₹180 Cr on sales of ₹1,000 Cr = 18% operating margin.",
    },
    "net_margin": {
        "what": "Net profit as a share of sales - the 'bottom line' per rupee of revenue.",
        "why": "Captures everything: operations, interest, tax and one-offs.",
        "read": "Industry-dependent: retailers often earn low single digits, while software and consumer brands can exceed 15%.",
        "example": "Net profit ₹120 Cr on sales of ₹1,000 Cr = 12% net margin.",
    },
    # ---------------- returns
    "roe": {
        "what": "Return on equity - profit earned for every rupee that shareholders have invested in the business.",
        "why": "A business that earns more than its cost of equity creates value for shareholders as it grows.",
        "read": "A common yardstick in India is the cost of equity, roughly 12-14%. ROE consistently above that is generally considered strong. Check that a high ROE is not just the result of heavy debt (see DuPont analysis).",
        "example": "Profit ₹150 Cr, average equity ₹1,000 Cr, so ROE = 15%.",
    },
    "roce": {
        "what": "Return on capital employed - operating profit earned on all long-term capital, both equity and debt.",
        "why": "Unlike ROE, it cannot be inflated by borrowing, so it is a cleaner test of business quality.",
        "read": "ROCE above the cost of capital (often taken as roughly 10-12% for Indian companies) suggests the business earns more than its funding costs.",
        "example": "EBIT ₹200 Cr on capital employed of ₹1,250 Cr = 16% ROCE.",
    },
    "roa": {
        "what": "Return on assets - net profit per rupee of total assets.",
        "why": "Shows how productively the company uses everything it owns. Especially useful for banks, where ROA of about 1% or more is commonly considered healthy.",
        "read": "Asset-light businesses (software, services) have far higher ROA than asset-heavy ones (utilities, steel).",
        "example": "Profit ₹50 Cr on average assets of ₹1,000 Cr = 5% ROA.",
    },
    # ---------------- leverage
    "debt_to_equity": {
        "what": "Borrowings compared with shareholders' equity.",
        "why": "Debt magnifies both gains and losses and must be repaid even in bad years.",
        "read": "For non-financial companies, below 0.5x is generally conservative and above 1x deserves a closer look. Capital-heavy sectors (power, infrastructure) usually carry more. Not meaningful for banks.",
        "example": "Borrowings ₹300 Cr, equity ₹1,000 Cr, so D/E = 0.3x.",
    },
    "net_debt_to_ebitda": {
        "what": "Borrowings minus cash, divided by a year's EBITDA - roughly how many years of operating profit would repay the debt.",
        "why": "Lenders use it to judge whether debt is manageable.",
        "read": "Negative means the company holds more cash than debt. Above about 3x is usually considered high for an industrial company.",
        "example": "Net debt ₹600 Cr, EBITDA ₹300 Cr, so 2.0x.",
    },
    "interest_coverage": {
        "what": "How many times operating profit covers the interest bill.",
        "why": "If coverage is thin, a bad year can make it hard to pay lenders.",
        "read": "Below about 1.5x is weak; 3x or more is generally comfortable.",
        "example": "EBIT ₹200 Cr, interest ₹40 Cr, so coverage = 5x.",
    },
    # ---------------- liquidity
    "current_ratio": {
        "what": "Short-term assets (cash, receivables, inventory) compared with bills due within a year.",
        "why": "Indicates whether the company can meet near-term obligations without stress.",
        "read": "Around 1.2x-2x is commonly seen as comfortable. Below 1x is not always a problem (some FMCG companies get paid before they pay suppliers) but deserves a look.",
        "example": "Current assets ₹600 Cr, current liabilities ₹400 Cr, so 1.5x.",
    },
    "quick_ratio": {
        "what": "Like the current ratio but excludes inventory, which can be slow to turn into cash.",
        "why": "A stricter test of short-term liquidity.",
        "read": "Around 1x or more is generally considered comfortable.",
        "example": "(₹600 Cr - ₹200 Cr inventory) / ₹400 Cr = 1.0x.",
    },
    # ---------------- efficiency & working capital
    "asset_turnover": {
        "what": "Sales generated for every rupee of assets.",
        "why": "One of the three drivers of ROE in DuPont analysis.",
        "read": "Retailers and distributors turn assets over quickly; utilities and infrastructure slowly. Compare within the industry.",
        "example": "Sales ₹2,000 Cr on assets of ₹1,000 Cr = 2.0x.",
    },
    "receivable_days": {
        "what": "The average number of days customers take to pay.",
        "why": "Money stuck with customers is money the company cannot use. Rising days can signal weak demand or aggressive revenue booking.",
        "read": "Lower is generally better. Watch the trend more than the level, and compare with peers.",
        "example": "Receivables ₹150 Cr on annual sales of ₹1,000 Cr = 150/1,000 × 365 ≈ 55 days.",
    },
    "inventory_days": {
        "what": "The average number of days goods sit in stock before being sold.",
        "why": "Excess inventory ties up cash and can become obsolete.",
        "read": "Lower is generally better, though some businesses (jewellery, pharma) hold inventory by nature.",
        "example": "Inventory ₹100 Cr, cost of goods ₹730 Cr, so 100/730 × 365 = 50 days.",
    },
    "payable_days": {
        "what": "The average number of days the company takes to pay its suppliers.",
        "why": "Paying later conserves cash, but very long payable days can mean stress or strained supplier relationships.",
        "read": "Read it with receivable and inventory days; on its own it is neither good nor bad.",
        "example": "Payables ₹80 Cr, cost of goods ₹730 Cr, so 80/730 × 365 = 40 days.",
    },
    "cash_conversion_cycle": {
        "what": "The number of days between paying for inputs and collecting cash from customers.",
        "why": "The longer the cycle, the more working capital the business needs as it grows.",
        "read": "Shorter is generally better; a negative cycle means suppliers effectively fund the business. Blank when any of the three inputs is not reported.",
        "example": "55 receivable days + 50 inventory days - 40 payable days = 65 days.",
    },
    "nwc_to_revenue": {
        "what": "Net working capital (current assets minus current liabilities) as a share of sales.",
        "why": "Shows how much cash is tied up in day-to-day operations for each rupee of sales.",
        "read": "A rising share means growth is consuming more cash. Note: current assets here include cash, so cash-rich companies show a high figure.",
        "example": "(₹600 Cr - ₹400 Cr) / ₹1,000 Cr sales = 20%.",
    },
    # ---------------- cash flow
    "cfo_to_net_income": {
        "what": "Cash generated by operations compared with reported net profit.",
        "why": "Profits are an accounting figure; cash is harder to manipulate. This is a test of earnings quality.",
        "read": "Around 1x or more over several years is healthy. Persistently below about 0.8x means profits are not turning into cash.",
        "example": "Operating cash flow ₹110 Cr, net profit ₹100 Cr, so 1.1x.",
    },
    "fcf_margin": {
        "what": "Free cash flow (operating cash flow minus capital expenditure) as a share of sales.",
        "why": "Free cash flow is what can be paid out as dividends, used to repay debt or reinvested in acquisitions.",
        "read": "Positive and stable is good. Negative FCF is normal during heavy expansion but needs funding.",
        "example": "Operating cash ₹150 Cr - capex ₹70 Cr = ₹80 Cr FCF on sales of ₹1,000 Cr = 8%.",
    },
    "capex_to_revenue": {
        "what": "Spending on fixed assets (plant, equipment, technology) as a share of sales.",
        "why": "Shows how capital-intensive the business is and how much it is investing for growth.",
        "read": "Neither high nor low is good on its own. Compare with depreciation: capex well above depreciation means expansion.",
        "example": "Capex ₹70 Cr on sales of ₹1,000 Cr = 7%.",
    },
    "dividend_payout": {
        "what": "The share of profit paid out as dividends.",
        "why": "Shows the balance between rewarding shareholders now and reinvesting for growth.",
        "read": "Mature companies often pay out more; fast-growing ones retain more. A payout above 100% is not sustainable for long.",
        "example": "Dividends ₹40 Cr on profit of ₹100 Cr = 40% payout.",
    },
    "eps": {
        "what": "Earnings per share - net profit divided by the number of shares.",
        "why": "Lets you relate profit to the share price (P/E = Price / EPS).",
        "read": "Look at the trend over several years rather than the absolute number.",
        "example": "Net profit ₹500 Cr, 50 Cr shares, so EPS = ₹10.",
    },
    "bvps": {
        "what": "Book value per share - shareholders' equity divided by the number of shares.",
        "why": "The accounting net worth behind each share; the basis of the P/B ratio.",
        "read": "Most relevant for banks and asset-heavy businesses. For brand or software companies, book value understates economic value.",
        "example": "Equity ₹2,000 Cr, 50 Cr shares, so BVPS = ₹40.",
    },
    # ---------------- valuation
    "pe": {
        "what": "Price-to-earnings: how many rupees investors pay for one rupee of the company's annual profit.",
        "why": "The most widely quoted valuation measure.",
        "read": "There is no universal 'good' P/E. Compare with the company's own history and with peers, and remember that faster-growing or lower-risk businesses usually trade at higher P/Es.",
        "example": "Price ₹200, EPS ₹10, so P/E = 20x.",
    },
    "pb": {
        "what": "Price-to-book: the share price compared with the accounting net worth per share.",
        "why": "Particularly useful for banks and financials, whose assets are mostly financial and close to their book value.",
        "read": "A bank earning ROE above its cost of equity can justify P/B above 1x. Compare with history and peers.",
        "example": "Price ₹300, book value per share ₹100, so P/B = 3x.",
    },
    "ev_ebitda": {
        "what": "Enterprise value (market cap plus debt minus cash) divided by EBITDA.",
        "why": "Compares companies regardless of how much debt they carry. Not meaningful for banks.",
        "read": "Like P/E, judge it against history and peers rather than a fixed number.",
        "example": "EV ₹12,000 Cr, EBITDA ₹1,000 Cr, so 12x.",
    },
    "dividend_yield": {
        "what": "Annual dividend per share as a percentage of the share price.",
        "why": "The cash return you receive just for holding the share.",
        "read": "Compare with fixed-deposit or G-sec yields. A very high yield can signal that the market expects the dividend to be cut.",
        "example": "Dividend ₹6 a year, price ₹200, so yield = 3%.",
    },
    "market_cap": {
        "what": "The total market value of all the company's shares (price × shares outstanding).",
        "why": "Indicates size. SEBI/AMFI classify the top 100 listed companies by market cap as large caps, 101-250 as mid caps and the rest as small caps.",
        "read": "Larger companies tend to be less volatile; smaller ones can grow faster but carry more risk.",
        "example": "Price ₹500 × 100 Cr shares = ₹50,000 Cr market cap.",
    },
}

# (strong-if, weak-if) thresholds. higher_better=True: strong if v >= hi, weak if v < lo.
# higher_better=False: strong if v <= lo, weak if v > hi.  Only widely used rules of thumb.
_BENCH: dict[str, tuple[bool, float, float, bool]] = {
    # key: (higher_better, lo, hi, applies_to_financials)
    "roe": (True, 0.10, 0.15, True),
    "roce": (True, 0.10, 0.15, False),
    "roa": (True, 0.005, 0.01, True),     # bank-style ROA thresholds are applied only to financials, see assess()
    "debt_to_equity": (False, 0.5, 1.0, False),
    "net_debt_to_ebitda": (False, 1.0, 3.0, False),
    "interest_coverage": (True, 1.5, 3.0, False),
    "current_ratio": (True, 1.0, 1.2, False),
    "cfo_to_net_income": (True, 0.8, 1.0, True),
    "revenue_growth": (True, 0.05, 0.12, True),
    "net_income_growth": (True, 0.0, 0.12, True),
}


def assess(key: str, value: float | None, financial: bool = False) -> dict | None:
    """Return {'level', 'text'} for a widely used benchmark, or None when no fair benchmark exists."""
    if value is None or key not in _BENCH:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    higher, lo, hi, fin_ok = _BENCH[key]
    if financial and not fin_ok:
        return None
    if key == "roa" and not financial:
        return None  # ROA levels differ too much across non-financial industries
    if key == "cfo_to_net_income" and financial:
        return None  # bank operating cash flow swings with deposits/loans; not an earnings-quality test
    if higher:
        level = "strong" if v >= hi else "weak" if v < lo else "moderate"
    else:
        level = "strong" if v <= lo else "weak" if v > hi else "moderate"
    if key == "interest_coverage" and v < 0:
        level = "weak"
    text = {
        "roe": {"strong": "Above a typical Indian cost of equity (~12-14%).", "moderate": "Around or slightly below a typical cost of equity.", "weak": "Below a typical cost of equity."},
        "roce": {"strong": "Comfortably above a typical cost of capital.", "moderate": "Close to a typical cost of capital.", "weak": "Below a typical cost of capital."},
        "roa": {"strong": "At or above the ~1% often cited as healthy for banks.", "moderate": "Below the ~1% often cited for banks.", "weak": "Low for a bank or NBFC."},
        "debt_to_equity": {"strong": "Conservative borrowing.", "moderate": "Moderate borrowing.", "weak": "High borrowing - check interest coverage and cash flow."},
        "net_debt_to_ebitda": {"strong": "Debt is small relative to operating profit (or net cash).", "moderate": "Manageable debt.", "weak": "High debt relative to operating profit."},
        "interest_coverage": {"strong": "Profit covers interest comfortably.", "moderate": "Adequate cover.", "weak": "Thin cover - a bad year could strain repayments."},
        "current_ratio": {"strong": "Comfortable short-term liquidity.", "moderate": "Adequate liquidity.", "weak": "Short-term liabilities exceed short-term assets."},
        "cfo_to_net_income": {"strong": "Profits are converting into cash.", "moderate": "Most profit is converting into cash.", "weak": "Profits are not converting into cash this year."},
        "revenue_growth": {"strong": "Growing well ahead of inflation.", "moderate": "Growing around the pace of inflation.", "weak": "Little or no real growth."},
        "net_income_growth": {"strong": "Strong profit growth.", "moderate": "Modest profit growth.", "weak": "Profit fell."},
    }[key][level]
    return {"level": level, "text": text}


BENCHMARK_NOTE = ("Ratings use general rules of thumb for Indian companies, not industry-specific targets. "
                  "Always compare with peers and with the company's own history.")
