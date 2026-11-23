"""Intermediate level, part 1: financial statements and ratio analysis (with ratio cards).
Part 2 (products, technical analysis, valuation basics) is in intermediate_more.py."""
from __future__ import annotations

from .core import ILLUSTRATIVE, lesson, mcq, module, num, term, v

# Ratio cards: the plain-English metric guide (equitypilot/content/metrics_guide.py: what / why / read / example) plus
# the formula, limitations and when the ratio is unsuitable. `peg` is not in the metric guide, so it is complete here.
RATIO_CARDS: dict[str, dict[str, str]] = {
    "pe": {"name": "P/E ratio", "formula": "P/E = Share price ÷ EPS (= Market cap ÷ Net profit)",
           "limits": "Built on accounting profit, which one-off items distort. Cyclical companies look cheapest at the top of the cycle, when profits peak.",
           "unsuitable": "Loss-making companies (negative EPS) and companies whose profits are temporarily depressed or inflated."},
    "pb": {"name": "P/B ratio", "formula": "P/B = Share price ÷ Book value per share (= Market cap ÷ Shareholders' equity)",
           "limits": "Book value reflects historical cost and leaves out internally built intangibles such as brands, software and people.",
           "unsuitable": "Asset-light businesses (IT services, consumer brands) where book value says little about earning power."},
    "ev_ebitda": {"name": "EV/EBITDA", "formula": "EV/EBITDA = (Market cap + Borrowings − Cash) ÷ EBITDA",
                  "limits": "EBITDA ignores capital spending, working-capital needs and tax, so equal EBITDA can mean very different cash generation.",
                  "unsuitable": "Banks and NBFCs, whose borrowings are raw material, and companies with negative EBITDA."},
    "peg": {"name": "PEG ratio", "what": "The P/E ratio divided by the expected annual growth rate of EPS, in percent.",
            "why": "It adjusts the P/E for growth, so a fast grower on a higher P/E can be compared with a slower grower on a lower one.",
            "read": "Around 1 is often quoted as 'fair' for a growing company, but this is only a rough rule and depends entirely on the growth estimate.",
            "example": "P/E 30 with expected EPS growth of 20% a year gives a PEG of 30 ÷ 20 = 1.5.",
            "formula": "PEG = P/E ÷ Expected annual EPS growth (%)",
            "limits": "Growth forecasts are uncertain, and PEG ignores risk, dividends and how long the growth lasts.",
            "unsuitable": "Low-growth, loss-making or highly cyclical companies, where growth near zero or below makes PEG meaningless."},
    "dividend_yield": {"name": "Dividend yield", "formula": "Dividend yield = Annual dividend per share ÷ Share price",
                       "limits": "Past dividends may not continue, and a falling share price inflates the yield.",
                       "unsuitable": "Growth companies that reinvest profits instead of paying dividends."},
    "eps": {"name": "EPS", "formula": "EPS = Net profit attributable to shareholders ÷ Weighted average shares",
            "limits": "Buybacks, share issues, one-off items and accounting choices all move EPS; on its own it says nothing about price.",
            "unsuitable": "Comparing companies: EPS depends on how many shares exist, so ₹50 EPS is not 'better' than ₹5."},
    "roe": {"name": "ROE", "formula": "ROE = Net profit ÷ Average shareholders' equity",
            "limits": "Borrowing and buybacks can inflate ROE without the business improving.",
            "unsuitable": "Companies with negative or very small equity, and comparisons between companies with very different debt levels."},
    "roce": {"name": "ROCE", "formula": "ROCE = EBIT ÷ Capital employed, where Capital employed = Total assets − Current liabilities",
             "limits": "Old, heavily depreciated assets flatter ROCE; large idle cash balances depress it.",
             "unsuitable": "Banks and insurers, where capital employed in this form is not meaningful."},
    "roa": {"name": "ROA", "formula": "ROA = Net profit ÷ Average total assets",
            "limits": "Levels differ hugely across industries, and assets are carried at book cost.",
            "unsuitable": "Comparisons across industries with different asset intensity. For banks around 1% is a common reference point."},
    "gross_margin": {"name": "Gross margin", "formula": "Gross margin = (Revenue − Cost of materials or goods sold) ÷ Revenue",
                     "limits": "Companies classify direct costs differently, and many service companies do not report a gross profit line.",
                     "unsuitable": "Comparisons across industries."},
    "ebit_margin": {"name": "Operating (EBIT) margin", "formula": "Operating margin = EBIT ÷ Revenue",
                    "limits": "Depends on how other income and one-off items are treated.",
                    "unsuitable": "Comparing companies that account for leases or development costs differently, without adjusting."},
    "ebitda_margin": {"name": "EBITDA margin", "formula": "EBITDA margin = EBITDA ÷ Revenue",
                      "limits": "Leaves out depreciation, so it flatters capital-heavy businesses.",
                      "unsuitable": "Comparisons between asset-light and asset-heavy companies."},
    "net_margin": {"name": "Net margin", "formula": "Net margin = Net profit ÷ Revenue",
                   "limits": "Includes interest, tax and one-off items, which can swing it from year to year.",
                   "unsuitable": "Comparing companies with very different debt or tax positions."},
    "asset_turnover": {"name": "Asset turnover", "formula": "Asset turnover = Revenue ÷ Average total assets",
                       "limits": "Acquisitions and revaluations change it without any operational change.",
                       "unsuitable": "Cross-industry comparisons: retailers turn assets far faster than utilities."},
    "debt_to_equity": {"name": "Debt to equity", "formula": "D/E = Total borrowings ÷ Shareholders' equity",
                       "limits": "Ignores cash (look at net debt too) and lease liabilities if they are not included.",
                       "unsuitable": "Banks and NBFCs, where borrowing is the business; use capital adequacy instead."},
    "net_debt_to_ebitda": {"name": "Net debt to EBITDA", "formula": "Net debt ÷ EBITDA = (Borrowings − Cash) ÷ EBITDA",
                           "limits": "EBITDA can fall sharply in a downturn, so a comfortable ratio can deteriorate fast.",
                           "unsuitable": "Banks and NBFCs, and companies with negative EBITDA."},
    "interest_coverage": {"name": "Interest coverage", "formula": "Interest coverage = EBIT ÷ Finance costs",
                          "limits": "One year's EBIT may be unusually high or low; interest capitalised into projects is not in finance costs.",
                          "unsuitable": "Banks, whose interest cost is their main expense, and companies with almost no debt (the number becomes huge and meaningless)."},
    "current_ratio": {"name": "Current ratio", "formula": "Current ratio = Current assets ÷ Current liabilities",
                      "limits": "Counts inventory and receivables that may not turn into cash quickly.",
                      "unsuitable": "Banks and NBFCs, whose balance sheets are not split into current and non-current items this way. Some FMCG and retail companies run safely below 1 using supplier credit."},
    "quick_ratio": {"name": "Quick ratio", "formula": "Quick ratio = (Current assets − Inventories) ÷ Current liabilities",
                    "limits": "Receivables may still be slow to collect.", "unsuitable": "Banks and NBFCs."},
    "cash_conversion_cycle": {"name": "Cash conversion cycle", "formula": "CCC = Inventory days + Receivable days − Payable days",
                              "limits": "Year-end balances can be managed (window dressing), so look at several years.",
                              "unsuitable": "Banks, and service businesses with little inventory, where inventory days mean little."},
}

# ================================================================== 6. Financial statements
statements = module("statements", "Reading financial statements", "intermediate",
                    "The income statement, balance sheet and cash flow statement, how they link, and Indian reporting conventions.", [
    lesson("statements-income", "The income statement: from revenue to EPS",
           concept="""
The **statement of profit and loss** shows revenue, expenses and profit over a period. Read it from the top down:
- **Revenue from operations** minus operating costs (materials, employee costs, other expenses) = **EBITDA**
- minus depreciation and amortisation = **EBIT** (operating profit)
- minus finance costs, plus other income = **profit before tax (PBT)**
- minus tax = **PAT** (profit after tax, or net profit)
- divided by the weighted average number of shares = **EPS**.
Definitions vary: some analysts include other income in EBIT. Whatever you choose, be consistent.""",
           why="The P&L shows how much of each rupee of sales the business keeps, where the costs go, and whether profit comes from operations or from one-off items.",
           formulas=["EBITDA = Revenue − Operating expenses (before depreciation)", "EBIT = EBITDA − Depreciation & amortisation",
                     "PBT = EBIT − Finance costs + Other income", "PAT = PBT − Tax", "EPS = PAT attributable to shareholders ÷ Weighted average shares"],
           example=f"""
{ILLUSTRATIVE}
| Line | ₹ crore |
|---|---|
| Revenue from operations | 1,000 |
| Operating expenses | (750) |
| **EBITDA** | **250** (25% margin) |
| Depreciation | (50) |
| **EBIT** | **200** (20% margin) |
| Finance costs | (20) |
| Other income | 10 |
| Profit before tax | 190 |
| Tax at 25% | (47.5) |
| **PAT** | **142.5** (14.25% margin) |
With 50 crore shares, EPS = 142.5 ÷ 50 = **₹2.85**.""",
           interpret="Follow margins over several years. Check whether profit growth comes from the core business or from other income and exceptional items, and whether the tax rate is unusually low. Depreciation reflects past capital spending: it reduces profit but not this year's cash.",
           mistakes=["Treating EBITDA as cash.", "Ignoring exceptional (one-off) items.", "Comparing a standalone P&L with a consolidated one.",
                     "Using basic and diluted EPS inconsistently.", "Forgetting that consolidated PAT includes minority interests; EPS uses profit attributable to owners."],
           application="A Company page's Financials tab shows several years of P&L; the Earnings page covers quarterly results. The statements calculator walks the P&L down to PAT with your own numbers.",
           revision=["Revenue → EBITDA → EBIT → PBT → PAT → EPS.", "Depreciation sits between EBITDA and EBIT.",
                     "Check one-offs and other income.", "Margins = each profit line ÷ revenue."],
           check=[
               num("Revenue ₹800 crore, operating expenses ₹600 crore, depreciation ₹40 crore, finance costs ₹10 crore, no other income, tax 25%. What is PAT, in ₹ crore?", 112.5,
                   "Walk down the P&L line by line.", "EBITDA = 800 − 600 = 200; EBIT = 200 − 40 = 160; PBT = 160 − 10 = 150; tax = 37.5; PAT = 150 − 37.5 = ₹112.5 crore",
                   unit="₹ crore", kind="statement"),
               mcq("EBITDA rose 10% but PAT fell 5%. Which is the most likely explanation?", ["Higher depreciation, finance costs or tax", "Revenue fell", "The share count fell", "A stock split"], 0,
                   "Something between EBITDA and PAT grew faster: depreciation, interest, tax or a one-off loss.",
                   [None, "Revenue falling would usually pull EBITDA down too.", "Share count affects EPS, not PAT.", "A split changes per-share figures only."],
                   level="medium", kind="statement"),
           ],
           calculators=("statements",), tools=(("company:TCS.NS", "Open a real company's multi-year P&L."), ("earnings", "See quarterly results as they are filed.")),
           sources=("mca", "nse", "bse"),
           terms=("EBITDA", "EPS",
                  term("EBIT", "Earnings before interest and tax: operating profit after depreciation and amortisation.",
                       formula="EBIT = EBITDA − Depreciation & amortisation", aliases=("operating profit", "earnings before interest and tax"), related=("EBITDA", "ROCE")),
                  term("Revenue", "Income from a company's main operations (sales of goods and services); 'revenue from operations' in Indian statements.",
                       aliases=("sales", "turnover", "top line", "revenue from operations"), related=("EBITDA",)),
                  term("PAT", "Profit after tax: what is left for shareholders after all expenses, interest and tax.",
                       aliases=("net profit", "profit after tax", "net income", "bottom line"), related=("EPS",)),
                  term("Depreciation", "Spreading the cost of a fixed asset over its useful life; amortisation does the same for intangible assets.",
                       formula="Straight-line depreciation = (Cost − Residual value) ÷ Useful life", example="A ₹10 crore machine with ₹1 crore residual value over 9 years: ₹1 crore a year.",
                       aliases=("amortisation", "amortization", "d&a", "depreciation and amortisation"), related=("EBITDA", "Capital expenditure")),
                  term("Exceptional items", "Unusual or one-off gains and losses shown separately in the P&L.",
                       aliases=("exceptional item", "one-off items", "one-offs", "extraordinary items"), related=("PAT",))),
           ),
    lesson("statements-balance", "The balance sheet: assets, liabilities and equity",
           concept="""
The **balance sheet** shows what a company owns (**assets**), what it owes (**liabilities**) and the owners' stake (**equity**) on one date. Assets = Liabilities + Equity.
- Non-current assets: property, plant and equipment (PPE), intangibles, **goodwill**, long-term investments.
- Current assets: inventories, trade receivables, cash.
- Liabilities: borrowings, trade payables, provisions, lease liabilities.
- Equity: share capital plus other equity (mainly **retained earnings** and reserves).""",
           why="It shows financial strength: how much debt there is, how much cash is tied up in working capital, and how much of the assets are intangibles or goodwill from acquisitions.",
           formulas=["Assets = Liabilities + Equity", "Shareholders' equity (net worth) = Share capital + Other equity",
                     "Working capital = Current assets − Current liabilities", "Net debt = Borrowings − Cash and equivalents"],
           example=f"""
{ILLUSTRATIVE}
| Assets | ₹ crore | Liabilities and equity | ₹ crore |
|---|---|---|---|
| PPE | 600 | Borrowings (long-term) | 300 |
| Goodwill | 50 | Trade payables | 150 |
| Inventories | 120 | Share capital | 50 |
| Trade receivables | 100 | Other equity | 450 |
| Cash | 80 | | |
| **Total** | **950** | **Total** | **950** |
Working capital = (120 + 100 + 80) − 150 = **₹150 crore**. Net debt = 300 − 80 = **₹220 crore**. Debt to equity = 300 ÷ 500 = **0.6x**.""",
           interpret="Goodwill arises when a company pays more than the fair value of the net assets it acquires. Under Ind AS it is not amortised but tested for impairment every year, so large goodwill relative to equity is an acquisition risk. Receivables growing faster than sales suggest collection problems.",
           mistakes=["Treating book value as market value.", "Ignoring contingent liabilities disclosed in the notes.",
                     "Forgetting that a balance sheet is a snapshot that can be dressed up at the year-end.",
                     "Overlooking lease liabilities, which Ind AS 116 brings onto the balance sheet."],
           application="Read a company's balance sheet on its Company page, and check leverage and liquidity in its risk and health views.",
           revision=["Assets = Liabilities + Equity.", "Equity = share capital + other equity.", "Net debt = borrowings − cash.",
                     "Goodwill comes from acquisitions and is tested for impairment."],
           check=[
               num("Total assets ₹1,200 crore; total liabilities ₹700 crore. What is shareholders' equity, in ₹ crore?", 500,
                   "Equity is what remains after liabilities.", "1,200 − 700 = ₹500 crore", unit="₹ crore", level="easy", kind="statement"),
               mcq("Goodwill on a balance sheet arises when a company…", ["Pays more than the fair value of the net assets it acquires", "Has good customer relations", "Earns more profit than it pays in dividends", "Has shares trading above face value"], 0,
                   "Goodwill is the premium paid in an acquisition over the fair value of identifiable net assets.",
                   [None, "Internally built reputation is not recorded as goodwill.", "That builds retained earnings, not goodwill.", "Share price does not create goodwill."]),
           ],
           tools=(("company:HINDUNILVR.NS", "Read a real balance sheet."),),
           sources=("mca",),
           terms=("Working capital",
                  term("Balance sheet", "A statement of what a company owns, owes and the owners' stake on a given date.", formula="Assets = Liabilities + Equity",
                       aliases=("statement of financial position",), related=("Net worth", "Goodwill")),
                  term("Goodwill", "The premium paid in an acquisition over the fair value of the net identifiable assets acquired; tested for impairment under Ind AS.",
                       aliases=("impairment", "goodwill impairment"), related=("Balance sheet",)),
                  term("Retained earnings", "Accumulated profits kept in the business rather than paid as dividends; part of other equity.",
                       formula="Closing = Opening + PAT − Dividends", aliases=("reserves and surplus", "other equity", "reserves"), related=("Net worth",)),
                  term("Net worth", "Shareholders' equity: share capital plus other equity.", aliases=("shareholders' equity", "shareholders equity", "total equity"),
                       related=("Retained earnings", "Book value per share")),
                  term("Net debt", "Borrowings minus cash and cash equivalents; negative net debt means net cash.", formula="Net debt = Borrowings − Cash",
                       aliases=("net cash",), related=("Debt to equity", "Enterprise value"))),
           ),
    lesson("statements-cashflow", "The cash flow statement: CFO, capex and free cash flow",
           concept="""
The **cash flow statement** shows cash moving in and out, in three parts:
- **Operating activities (CFO)**: cash generated by the business.
- **Investing activities (CFI)**: capital expenditure (capex), acquisitions, investments.
- **Financing activities (CFF)**: borrowing and repayments, dividends, share issues and buybacks.
Under the indirect method, CFO starts from profit, adds back non-cash charges such as depreciation, and adjusts for changes in working capital. **Free cash flow (FCF)** = CFO − capex.""",
           why="Profit depends on accounting judgements; cash is harder to manipulate. The cash flow statement tests earnings quality and shows how growth is funded.",
           formulas=["CFO (indirect) ≈ PAT + Depreciation ± Other non-cash items − Increase in working capital", "Free cash flow = CFO − Capital expenditure",
                     "Net change in cash = CFO + CFI + CFF", "Cash conversion = CFO ÷ PAT"],
           example=f"""
{ILLUSTRATIVE} Continuing the P&L example:
- PAT ₹142.5 crore + depreciation ₹50 crore − increase in inventories and receivables ₹40 crore = **CFO ₹152.5 crore**.
- Capex ₹90 crore, so **FCF = ₹62.5 crore**.
- Cash conversion = 152.5 ÷ 142.5 = **1.07x**: profit is turning into cash.""",
           interpret="CFO persistently below PAT means profit is not turning into cash (often receivables or inventory building up). Negative FCF can be fine for a fast-growing company investing heavily, but it must be funded with debt or equity. Positive CFO with negative CFI and CFF is the profile of a mature, cash-generative business.",
           mistakes=["Treating EBITDA as cash flow.", "Ignoring swings in working capital.", "Judging FCF from one year; capex is lumpy.",
                     "Comparing FCF across companies without checking how interest, leases and acquisitions are classified."],
           application="The 'Cash generators' screen in the Screener filters on free cash flow; a Company page shows CFO, capex and FCF by year. Try the FCF calculator.",
           revision=["CFO, CFI and CFF explain the change in cash.", "FCF = CFO − capex.", "CFO ÷ PAT tests earnings quality.", "Negative FCF must be funded."],
           check=[
               num("CFO ₹300 crore; capex ₹120 crore. What is free cash flow, in ₹ crore?", 180,
                   "FCF is the cash left after investing in the asset base.", "300 − 120 = ₹180 crore", unit="₹ crore", level="easy", kind="statement",
                   verify=v("free_cash_flow", 300, 120)),
               mcq("Over three years PAT grew strongly but CFO stayed flat and receivables doubled. This most likely suggests…",
                   ["Profits are not turning into cash; check revenue recognition and collections", "Excellent earnings quality", "A lower tax rate", "A share split"], 0,
                   "Profit booked but not collected sits in receivables; it is a classic earnings-quality warning.",
                   [None, "Good earnings quality means cash tracks profit.", "Tax does not explain rising receivables.", "A split has no effect on cash flow."],
                   level="medium", kind="statement"),
           ],
           calculators=("fcf",), tools=(("screener", "Try the 'Cash generators' screen."),),
           sources=("mca",),
           terms=("Free cash flow",
                  term("Cash flow from operations", "Cash generated by a company's core business in a period, after working-capital changes.",
                       aliases=("cfo", "operating cash flow", "cash from operations", "ocf"), related=("Free cash flow", "Cash conversion")),
                  term("Capital expenditure", "Money spent on long-term assets such as plant, machinery and buildings.",
                       aliases=("capex",), related=("Free cash flow", "Depreciation")),
                  term("Cash flow statement", "A statement of cash flows from operating, investing and financing activities over a period.",
                       aliases=("cfi", "cff", "investing cash flow", "financing cash flow", "statement of cash flows"), related=("Cash flow from operations",)),
                  term("Cash conversion", "How much of reported profit turns into operating cash.", formula="Cash conversion = CFO ÷ PAT",
                       aliases=("cash conversion ratio", "cfo to pat", "cfo/pat", "earnings quality"), related=("Cash flow from operations",))),
           ),
    lesson("statements-linked", "How the three statements link",
           concept="""
The three statements form one system:
- PAT from the P&L flows into **retained earnings** on the balance sheet (less dividends).
- Depreciation reduces PPE on the balance sheet and is added back in CFO.
- Capex increases PPE and appears in investing cash flow.
- New borrowing or repayment changes debt and appears in financing cash flow.
- Changes in inventories, receivables and payables link the balance sheet to CFO.
- The cash flow statement explains the change in the cash balance between two balance sheets.""",
           why="Reading the statements together catches inconsistencies, such as profit without cash or assets growing faster than sales. It is also the basis of every financial model and DCF.",
           formulas=["Closing retained earnings = Opening + PAT − Dividends", "Closing PPE = Opening PPE + Capex − Depreciation (− disposals)",
                     "Closing cash = Opening cash + CFO + CFI + CFF", "Closing debt = Opening debt + New borrowing − Repayments"],
           example=f"""
{ILLUSTRATIVE} One year for the company in the balance sheet lesson (opening: cash 80, PPE 600, debt 300, other equity 450; ₹ crore):
- P&L: PAT 142.5, after depreciation of 50. Dividends paid 40. Capex 90. Working capital rises by 40. Debt repaid 30.
- **Cash flow**: CFO = 142.5 + 50 − 40 = 152.5; CFI = −90; CFF = −40 − 30 = −70. Change in cash = **−7.5**, so closing cash = 72.5.
- **Balance sheet**: PPE = 600 + 90 − 50 = 640; inventories and receivables = 220 + 40 = 260; debt = 270; other equity = 450 + 142.5 − 40 = 552.5.
- **Check**: assets 640 + 50 + 260 + 72.5 = **1,022.5**; liabilities and equity 270 + 150 + 50 + 552.5 = **1,022.5**. It balances.""",
           interpret="If a model's balance sheet does not balance, a link is missing. Profit with weak cash flow, or debt rising while profit grows, deserves a closer look.",
           mistakes=["Counting depreciation twice, or forgetting to add it back.", "Treating dividends as an expense in the P&L; they reduce retained earnings.",
                     "Mixing periods or bases (standalone and consolidated).", "Forgetting that the change in working capital, not its level, affects CFO."],
           application="The statements calculator builds this linked example from your own inputs; the Valuation Lab's FCFF uses EBIT, depreciation, capex and the change in working capital from the same links.",
           revision=["PAT → retained earnings (less dividends).", "PPE: + capex − depreciation.", "Cash: + CFO + CFI + CFF.", "A correct model always balances."],
           check=[
               num("Opening retained earnings ₹400 crore, PAT ₹120 crore, dividends ₹30 crore. What are closing retained earnings, in ₹ crore?", 490,
                   "Profit adds to retained earnings; dividends take away.", "400 + 120 − 30 = ₹490 crore", unit="₹ crore", level="easy", kind="statement"),
               mcq("A depreciation charge of ₹50 crore affects…",
                   ["The P&L (lower profit), the balance sheet (lower PPE) and CFO (added back)", "Only the cash flow statement", "Only the balance sheet", "Nothing, because it is a non-cash item"], 0,
                   "Depreciation lowers profit and the asset's book value, and is added back in CFO because no cash leaves.",
                   [None, "It starts in the P&L.", "It also reduces profit.", "Non-cash does not mean no effect: profit and book values change."], level="medium"),
           ],
           calculators=("statements",), tools=(("valuation", "See how EBIT, capex and working capital feed FCFF."),),
           terms=(term("Three-statement link", "How profit, the balance sheet and cash flow connect: PAT feeds retained earnings, and cash flow explains the change in cash.",
                       aliases=("linked statements", "three statements", "financial model"), related=("Retained earnings", "Cash flow statement")),),
           ),
    lesson("statements-indian", "Indian reporting: Ind AS, standalone vs consolidated, and where to find statements",
           concept="""
Listed Indian companies prepare their statements under **Ind AS** (Indian Accounting Standards, converged with IFRS), notified under the Companies Act, 2013.
**Standalone** statements cover the listed company alone; **consolidated** statements combine it with its subsidiaries (and its share of associates and joint ventures).
Figures are usually in ₹ crore or ₹ lakh, and the financial year runs from April to March. Quarterly results are filed with the exchanges under SEBI's Listing Obligations and Disclosure Requirements (LODR) Regulations, 2015; audited annual statements appear in the annual report.""",
           why="Comparing the wrong basis or the wrong period is one of the most common analysis errors. Consolidated figures matter for groups with large subsidiaries.",
           rules=["Ind AS (converged with IFRS) apply to listed companies.", "Standalone = the listed company only; consolidated = parent plus subsidiaries (plus share of associates and joint ventures).",
                  "₹1 lakh = 1,00,000; ₹1 crore = 100 lakh = 1,00,00,000 (10 million).", "FY2026 = 1 April 2025 to 31 March 2026.",
                  "SEBI LODR: quarterly results within 45 days of the quarter-end; audited annual results within 60 days of the year-end.",
                  "Annual reports contain the audited statements, notes, the auditor's report and management discussion and analysis (MD&A)."],
           example=f"""
{ILLUSTRATIVE}
- A group's standalone revenue is ₹10,000 crore, but its consolidated revenue is ₹16,000 crore because subsidiaries add ₹6,000 crore. Dividing the group's market value by standalone profit would misstate its P/E.
- Unit check: ₹2,50,00,00,000 = ₹250 crore = ₹2.5 billion.""",
           interpret="Use consolidated figures for groups; standalone may be adequate when subsidiaries are small. EquityPilot's third-party statements do not say which basis they use, while annual reports you upload record it (see the Data quality page).",
           mistakes=["Mixing standalone and consolidated figures.", "Mixing financial and calendar years.", "Misreading lakh and crore.",
                     "Skipping the auditor's report (qualifications, emphasis of matter).", "Treating unaudited quarterly figures as final."],
           application="Upload annual reports in Documents and ask questions with page references; check data provenance on the Data quality page; follow filings on NSE and BSE.",
           revision=["Ind AS = IFRS-converged standards.", "Consolidated for groups; never mix bases.", "1 crore = 100 lakh = 10 million.",
                     "Quarterly results within 45 days; annual within 60 days."],
           check=[
               num("₹4,50,00,00,000 equals how many ₹ crore?", 450, "One crore is 1,00,00,000.", "4,50,00,00,000 ÷ 1,00,00,000 = 450 crore", unit="₹ crore", level="easy"),
               mcq("For an Indian company, FY2026 usually means…", ["January to December 2026", "April 2025 to March 2026", "April 2026 to March 2027", "July 2025 to June 2026"], 1,
                   "The financial year ends on 31 March and is named after the year in which it ends.",
                   ["That is the calendar year.", None, "That is FY2027.", "That is not the Indian financial year."], kind="rule"),
           ],
           tools=(("documents", "Upload an annual report and query it."), ("data-quality", "See where EquityPilot's statement data comes from.")),
           sources=("mca", "sebi", "nse", "bse"),
           terms=("Consolidated vs standalone",
                  term("Ind AS", "Indian Accounting Standards, converged with IFRS, used by listed Indian companies.", aliases=("indian accounting standards", "ifrs"),
                       related=("Consolidated vs standalone",)),
                  term("Crore and lakh", "Indian number units: 1 lakh = 1,00,000; 1 crore = 100 lakh = 1,00,00,000 (10 million).", aliases=("crore", "lakh", "cr"),
                       example="₹250 crore = ₹2.5 billion."),
                  term("Financial year", "The April-March accounting year used by most Indian companies, named after the year in which it ends.",
                       aliases=("fy", "fiscal year"), example="FY2026 runs from April 2025 to March 2026."),
                  term("LODR", "SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015: the disclosure rules for listed companies.",
                       aliases=("sebi lodr", "listing obligations"), related=("Annual report",)),
                  term("Annual report", "A company's yearly report with audited statements, notes, the auditor's report and management discussion and analysis.",
                       aliases=("auditor's report", "md&a", "management discussion and analysis"), related=("LODR",))),
           ),
], test=[
    mcq("Which statement shows the position at a single point in time?", ["Profit and loss", "Balance sheet", "Cash flow statement", "Statement of changes in equity"], 1,
        "The balance sheet is a snapshot; the others cover a period.",
        ["The P&L covers a period.", None, "Cash flows cover a period.", "This statement also covers a period."]),
    mcq("Depreciation is added back in operating cash flow because…", ["It is a cash expense", "It reduces profit but involves no cash outflow in the period", "It is a tax", "It is an investing activity"], 1,
        "The cash left when the asset was bought (capex); depreciation spreads that cost over time.",
        ["No cash is paid when depreciation is charged.", None, "Depreciation is not a tax.", "Capex is the investing flow; depreciation is not."]),
    mcq("A company's consolidated statements include…", ["Only the parent company", "The parent and its subsidiaries", "Only the subsidiaries", "Only foreign operations"], 1,
        "Consolidation combines the parent with the entities it controls.",
        ["That is the standalone basis.", None, "The parent is included too.", "Domestic subsidiaries are included as well."]),
    mcq("₹1 crore equals…", ["₹1 lakh", "₹10 lakh", "₹100 lakh (10 million)", "₹1 billion"], 2, "1 crore = 100 lakh = 10,000,000.",
        ["A crore is 100 times a lakh.", "A crore is 100 lakh, not 10.", None, "₹1 billion = ₹100 crore."]),
    mcq("Rising receivables with flat sales usually…", ["Increase operating cash flow", "Reduce operating cash flow", "Have no cash effect", "Increase revenue"], 1,
        "Cash is tied up in unpaid customer bills, a common earnings-quality warning sign.",
        ["Higher receivables absorb cash.", None, "Working capital changes affect CFO.", "Receivables do not create revenue."], kind="statement"),
    num("Revenue ₹2,000 crore, EBITDA margin 20%, depreciation ₹100 crore. What is EBIT, in ₹ crore?", 300,
        "Find EBITDA first, then subtract depreciation.", "EBITDA = 2,000 × 20% = 400; EBIT = 400 − 100 = ₹300 crore", unit="₹ crore", kind="statement"),
    mcq("A company reports PAT of ₹500 crore but CFO of −₹100 crore, with receivables up ₹550 crore. What is the best reading?",
        ["Profit has not turned into cash; collections need checking", "Cash flow is strong", "The company is debt-free", "Dividends are safe"], 0,
        "Almost all the profit is sitting in uncollected receivables.",
        [None, "CFO is negative.", "Nothing here says the company has no debt.", "Dividends need cash, which is not being generated."], level="hard", kind="statement"),
    num("Opening PPE ₹800 crore, capex ₹150 crore, depreciation ₹70 crore, no disposals. What is closing PPE, in ₹ crore?", 880,
        "Capex adds to PPE; depreciation reduces it.", "800 + 150 − 70 = ₹880 crore", unit="₹ crore", kind="statement"),
    mcq("Under SEBI's LODR Regulations, quarterly results (other than for the last quarter) must be filed within…", ["15 days", "30 days", "45 days", "90 days"], 2,
        "Listed companies have 45 days from the quarter-end; annual audited results have 60 days.",
        ["15 days is too short.", "30 days is not the LODR limit.", None, "90 days is too long."], level="medium", kind="rule"),
])

# ================================================================== 7. Ratio analysis
ratios = module("ratios", "Ratio analysis", "intermediate",
                "Valuation, return, margin, leverage and liquidity ratios with their limits, DuPont analysis, and how ratios differ for banks, manufacturers and IT companies.", [
    lesson("ratios-valuation", "Valuation ratios: P/E, P/B, EV/EBITDA, PEG and dividend yield",
           concept="""
Valuation multiples relate a share's price, or the whole business's value, to what it earns or owns:
- **P/E**: price per rupee of earnings. **P/B**: price per rupee of book equity.
- **EV/EBITDA**: value of the whole business per rupee of operating profit.
- **PEG**: P/E adjusted for expected growth. **Dividend yield**: the cash return from dividends.""",
           why="Multiples are the quickest way to see what the market expects. Comparing them with close peers and with the company's own history gives a first view of whether expectations look demanding.",
           formulas=["P/E = Price ÷ EPS", "P/B = Price ÷ Book value per share", "EV/EBITDA = (Market cap + Borrowings − Cash) ÷ EBITDA",
                     "PEG = P/E ÷ Expected EPS growth (%)", "Dividend yield = DPS ÷ Price"],
           example=f"""
{ILLUSTRATIVE}
- Price ₹500, EPS ₹25: **P/E = 20x**. Book value per share ₹125: **P/B = 4x**.
- Market cap ₹50,000 crore + borrowings ₹10,000 crore − cash ₹5,000 crore = EV ₹55,000 crore; EBITDA ₹5,500 crore: **EV/EBITDA = 10x**.
- Expected EPS growth 16%: **PEG = 20 ÷ 16 = 1.25**. Dividend ₹10: **yield = 2%**.""",
           interpret="A high multiple means high expectations, not necessarily overvaluation; a low multiple can be a value trap if profits are about to fall. Compare like with like: same sector, same basis (trailing or forward), same accounting.",
           mistakes=["Comparing P/E across unrelated sectors.", "Using P/E for loss-making companies.", "Using EV/EBITDA for banks.",
                     "Mixing trailing (last 12 months) and forward (estimated) multiples.", "Calling a cyclical 'cheap' on peak profits."],
           application="A Company page shows current multiples; Compare puts peers side by side; the Screener filters on P/E and dividend yield.",
           revision=["Multiples = price ÷ a measure of earnings or assets.", "EV-based multiples suit different debt levels.",
                     "PEG adjusts P/E for growth.", "Always compare with peers and history."],
           check=[
               num("Share price ₹840, EPS ₹42. What is the P/E ratio?", 20, "Price divided by earnings per share.", "840 ÷ 42 = 20x", unit="x", level="easy", verify=v("pe", 840, 42)),
               mcq("Which multiple is least suitable for valuing a bank?", ["P/B", "P/E", "EV/EBITDA", "Dividend yield"], 2,
                   "A bank's borrowings are its raw material, so enterprise value and EBITDA lose meaning.",
                   ["P/B is the standard bank multiple.", "P/E can be used for profitable banks.", None, "Dividend yield applies to banks too."]),
               num("P/E is 36 and expected EPS growth is 24% a year. What is the PEG ratio?", 1.5, "Divide the P/E by the growth rate in percent.", "36 ÷ 24 = 1.5",
                   unit="x", level="easy", verify=v("peg", 36, 24)),
           ],
           calculators=("eps-pe",), cards=("pe", "pb", "ev_ebitda", "peg", "dividend_yield", "eps"),
           tools=(("compare", "Compare multiples of close peers."), ("screener", "Filter companies by P/E or dividend yield.")),
           terms=("P/E ratio", "P/B ratio", "EV/EBITDA", "Enterprise value", "EPS", "Dividend yield",
                  term("PEG ratio", "P/E divided by expected annual EPS growth in percent.", formula="PEG = P/E ÷ EPS growth (%)",
                       example="P/E 30 with 20% growth gives PEG 1.5.", aliases=("peg",), related=("P/E ratio",)),
                  term("Trailing and forward multiples", "Trailing multiples use the last 12 months' reported figures (TTM); forward multiples use estimates for the next year.",
                       aliases=("ttm", "trailing twelve months", "forward p/e", "forward pe", "trailing p/e"), related=("P/E ratio",)),
                  term("Book value per share", "Shareholders' equity divided by the number of shares.", formula="BVPS = Equity ÷ Shares outstanding",
                       aliases=("bvps", "book value"), related=("P/B ratio", "Net worth"))),
           ),
    lesson("ratios-returns", "Return ratios: ROE, ROCE, ROA and DuPont",
           concept="""
Return ratios show how much profit a business earns on the money invested in it:
- **ROE**: net profit on shareholders' equity.
- **ROCE**: pre-tax operating profit (EBIT) on all long-term capital, equity and debt.
- **ROA**: net profit on total assets.
**DuPont analysis** splits ROE into profitability (net margin), efficiency (asset turnover) and leverage (equity multiplier).""",
           why="A business that earns more than its cost of capital creates value as it grows; one that earns less destroys value even while growing.",
           formulas=["ROE = Net profit ÷ Average shareholders' equity", "ROCE = EBIT ÷ Capital employed (Total assets − Current liabilities)",
                     "ROA = Net profit ÷ Average total assets", "ROE = Net margin × Asset turnover × Equity multiplier (Assets ÷ Equity)"],
           example=f"""
{ILLUSTRATIVE}
- PAT ₹150 crore; equity ₹900 crore at the start and ₹1,100 crore at the end, average ₹1,000 crore: **ROE = 15%**.
- EBIT ₹280 crore; total assets ₹2,000 crore; current liabilities ₹400 crore; capital employed ₹1,600 crore: **ROCE = 17.5%**.
- DuPont with revenue ₹1,500 crore: net margin 10% × asset turnover 0.75 (1,500 ÷ 2,000) × equity multiplier 2.0 (2,000 ÷ 1,000) = **15%**, matching ROE.""",
           interpret="ROE or ROCE sustained above the cost of capital (a cost of equity of roughly 12-14% is often used in India) indicates value creation. DuPont shows the quality of ROE: returns driven by margins and efficiency are sturdier than returns driven by leverage. EquityPilot uses average opening and closing capital in its own calculations.",
           mistakes=["Praising ROE that comes mostly from debt or buybacks.", "Reading ROE when equity is negative or tiny.",
                     "Forgetting that old, depreciated assets flatter ROCE.", "Comparing ROA across industries.", "Using year-end instead of average capital without saying so."],
           application="A Company page shows ROE, ROCE and DuPont over several years; the Screener's quality screens filter on ROE and ROCE. Try the ROE and ROCE calculator.",
           revision=["ROE: return to shareholders.", "ROCE: pre-tax return on all capital; independent of financing.",
                     "DuPont: margin × turnover × leverage.", "Compare with the cost of capital."],
           check=[
               num("PAT ₹90 crore; opening equity ₹550 crore; closing equity ₹650 crore. What is ROE, in %?", 15,
                   "Use average equity.", "Average equity = (550 + 650) ÷ 2 = 600; ROE = 90 ÷ 600 = 15%", unit="%", verify=v("roe", 90, 550, 650, unit="%")),
               num("EBIT ₹300 crore; total assets ₹2,500 crore; current liabilities ₹500 crore. What is ROCE, in %?", 15,
                   "Capital employed = total assets − current liabilities.", "300 ÷ (2,500 − 500) = 300 ÷ 2,000 = 15%", unit="%", verify=v("roce", 300, 2500, 500, unit="%")),
           ],
           calculators=("roe-roce",), cards=("roe", "roce", "roa"),
           tools=(("company:TCS.NS", "See ROE, ROCE and DuPont for a real company."), ("screener", "Screen for high ROCE.")),
           terms=("ROE", "ROCE", "DuPont analysis",
                  term("ROA", "Return on assets: net profit as a share of average total assets.", formula="ROA = Net profit ÷ Average total assets",
                       aliases=("return on assets",), related=("ROE", "DuPont analysis")),
                  term("Capital employed", "The long-term capital used in a business: total assets minus current liabilities.",
                       formula="Capital employed = Total assets − Current liabilities", related=("ROCE",)),
                  term("Equity multiplier", "Total assets divided by shareholders' equity; the leverage part of DuPont analysis.",
                       formula="Equity multiplier = Assets ÷ Equity", aliases=("financial leverage",), related=("DuPont analysis",))),
           ),
    lesson("ratios-margins", "Margins and efficiency: gross, operating and net margin, asset turnover",
           concept="""
**Margins** show how much of each rupee of revenue is kept at each level of the P&L: gross, operating (EBIT) and net. **Asset turnover** shows how much revenue each rupee of assets generates.
Together they describe the business model: high margin and low turnover (luxury goods, software products) or low margin and high turnover (supermarkets, distribution).""",
           why="Margin trends reveal pricing power and cost pressure; turnover reveals how efficiently capital is used. Their product, ROA, ties them together.",
           formulas=["Gross margin = (Revenue − COGS) ÷ Revenue", "Operating margin = EBIT ÷ Revenue", "Net margin = PAT ÷ Revenue",
                     "Asset turnover = Revenue ÷ Average total assets", "ROA = Net margin × Asset turnover"],
           example=f"""
{ILLUSTRATIVE} Revenue ₹1,000 crore:
- Cost of goods sold ₹600 crore: **gross margin 40%**. EBIT ₹150 crore: **operating margin 15%**. PAT ₹90 crore: **net margin 9%**.
- Average assets ₹800 crore: **asset turnover 1.25x**. ROA = 9% × 1.25 = **11.25%**.""",
           interpret="A falling gross margin points to input-cost pressure or weaker pricing. Fixed costs create operating leverage: operating margins rise faster than revenue in good years and fall faster in bad ones.",
           mistakes=["Comparing margins across industries.", "Ignoring one-off items in net margin.",
                     "Judging quality from margin alone without turnover.", "Ignoring changes in business or segment mix."],
           application="Compare margins of close peers in Compare and see an industry's typical margins on the Industries page.",
           revision=["Gross → operating → net margin.", "Asset turnover = revenue ÷ assets.", "ROA = margin × turnover.", "Operating leverage amplifies cycles."],
           check=[
               num("Revenue ₹500 crore; cost of goods sold ₹325 crore. What is the gross margin, in %?", 35,
                   "Gross profit divided by revenue.", "(500 − 325) ÷ 500 = 175 ÷ 500 = 35%", unit="%", level="easy", verify=v("margin", 175, 500, unit="%")),
               mcq("A supermarket chain typically has…", ["High margins and low asset turnover", "Low margins and high asset turnover", "High margins and high asset turnover", "No inventory"], 1,
                   "Grocery retail earns thin margins on a large volume of fast-moving stock.",
                   ["That describes luxury or software businesses.", None, "That combination is rare and usually competed away.", "Supermarkets hold large inventories."]),
           ],
           cards=("gross_margin", "ebit_margin", "ebitda_margin", "net_margin", "asset_turnover"),
           tools=(("compare", "Compare peers' margins."), ("industries", "See typical margins by industry.")),
           terms=("Gross margin", "EBITDA margin", "Net margin", "Asset turnover",
                  term("Operating leverage", "The effect of fixed costs: when revenue rises, operating profit rises faster (and falls faster when revenue falls).",
                       related=("Operating margin",)),
                  term("Operating margin", "EBIT as a share of revenue.", formula="Operating margin = EBIT ÷ Revenue", aliases=("ebit margin",),
                       related=("EBIT", "Operating leverage"))),
           ),
    lesson("ratios-leverage", "Leverage and solvency: debt to equity and interest coverage",
           concept="""
Leverage ratios show how much a company relies on borrowed money and whether it can service it:
- **Debt to equity (D/E)**: borrowings compared with shareholders' funds.
- **Net debt to EBITDA**: debt net of cash compared with a year's operating profit.
- **Interest coverage**: how many times operating profit covers interest.""",
           why="Debt magnifies returns in good years and losses in bad ones. Companies rarely fail because of low profits alone; they fail when they cannot pay their debts.",
           formulas=["D/E = Total borrowings ÷ Shareholders' equity", "Net debt to EBITDA = (Borrowings − Cash) ÷ EBITDA", "Interest coverage = EBIT ÷ Finance costs"],
           example=f"""
{ILLUSTRATIVE} Borrowings ₹600 crore, cash ₹100 crore, equity ₹1,000 crore, EBITDA ₹250 crore, EBIT ₹200 crore, finance costs ₹50 crore:
- **D/E = 0.6x**; **net debt to EBITDA = 500 ÷ 250 = 2.0x**; **interest coverage = 200 ÷ 50 = 4.0x**.""",
           interpret="Acceptable levels depend on how stable cash flows are: utilities can carry more debt than cyclical businesses. Interest coverage below about 1.5x is a warning sign; lenders often look for 3x or more. Negative net debt means net cash.",
           mistakes=["Looking at gross debt and ignoring cash.", "Leaving out lease liabilities.", "Applying D/E to banks.",
                     "Judging from a single year.", "Ignoring when the debt has to be repaid or refinanced."],
           application="A Company page shows leverage trends and rule-based risk checks; the Screener's low-debt screens filter on D/E.",
           revision=["D/E = borrowings ÷ equity.", "Net debt ÷ EBITDA = years of profit to repay debt.", "Coverage below ~1.5x is a warning.", "Banks need different measures."],
           check=[
               num("EBIT ₹120 crore; finance costs ₹40 crore. What is the interest coverage?", 3, "EBIT divided by finance costs.", "120 ÷ 40 = 3.0x", unit="x", level="easy"),
               mcq("All else equal, which company carries the most financial risk?", ["D/E 0.2x, interest coverage 12x", "D/E 2.5x, interest coverage 1.3x", "Net cash; coverage not meaningful", "D/E 0.5x, interest coverage 8x"], 1,
                   "High borrowing with profit barely covering interest leaves little room for a bad year.",
                   ["Low debt and ample cover.", None, "Net cash means no debt-servicing risk.", "Moderate debt with comfortable cover."], level="medium", kind="case"),
           ],
           cards=("debt_to_equity", "net_debt_to_ebitda", "interest_coverage"),
           tools=(("screener", "Try the low-debt screens."),),
           terms=("Debt to equity", "Interest coverage", "Net debt to EBITDA"),
           ),
    lesson("ratios-liquidity", "Liquidity and working capital: current ratio, quick ratio and cash conversion cycle",
           concept="""
Liquidity ratios show whether short-term obligations can be met from short-term assets. The **current ratio** compares current assets with current liabilities; the **quick (acid-test) ratio** leaves out inventory, which may be slow to sell.
**Working-capital days** show how long cash is tied up: inventory days + receivable days − payable days = the **cash conversion cycle**.""",
           why="A profitable company can still run out of cash if its money is stuck in stock and customer bills. Liquidity problems usually show up in working capital first.",
           formulas=["Current ratio = Current assets ÷ Current liabilities", "Quick ratio = (Current assets − Inventories) ÷ Current liabilities",
                     "Receivable days = Receivables ÷ Revenue × 365", "Inventory days = Inventory ÷ COGS × 365", "Payable days = Payables ÷ COGS × 365",
                     "Cash conversion cycle = Inventory days + Receivable days − Payable days"],
           example=f"""
{ILLUSTRATIVE} Current assets ₹500 crore (inventory 200, receivables 180, cash 120); current liabilities ₹400 crore (including payables 150); revenue ₹1,460 crore; COGS ₹1,095 crore.
- **Current ratio = 1.25x**; **quick ratio = (500 − 200) ÷ 400 = 0.75x**.
- Receivable days = 180 ÷ 1,460 × 365 = 45; inventory days = 200 ÷ 1,095 × 365 = 66.7; payable days = 150 ÷ 1,095 × 365 = 50.
- **Cash conversion cycle = 45 + 66.7 − 50 ≈ 62 days**.""",
           interpret="A current ratio below 1x can signal liquidity pressure, although FMCG and retail companies with strong supplier credit often run below 1 safely. Rising receivable days mean slower collections; a negative cash conversion cycle (customers pay before suppliers are paid) is a strength.",
           mistakes=["Assuming a high current ratio is always good; it may hide unsold stock.", "Ignoring the quality of receivables.",
                     "Using liquidity ratios for banks.", "Reading one year-end balance in isolation."],
           application="A Company page shows working-capital days and liquidity ratios; rule-based risk checks flag weak liquidity.",
           revision=["Current ratio = CA ÷ CL; quick ratio excludes inventory.", "CCC = inventory days + receivable days − payable days.",
                     "Rising receivable days = slower collections.", "Context matters: some sectors run below 1x safely."],
           check=[
               num("Current assets ₹300 crore including inventory of ₹120 crore; current liabilities ₹200 crore. What is the quick ratio?", 0.9,
                   "Leave inventory out of current assets.", "(300 − 120) ÷ 200 = 0.9x", unit="x", level="easy"),
               mcq("Receivable days rise from 45 to 75 while sales are flat. This suggests…", ["Customers are paying more slowly", "Collections have improved", "Inventory has fallen", "Margins have risen"], 0,
                   "More days of sales are sitting uncollected.",
                   [None, "Better collections would cut receivable days.", "Receivable days do not measure inventory.", "Receivable days say nothing about margins."], kind="statement"),
           ],
           cards=("current_ratio", "quick_ratio", "cash_conversion_cycle"),
           terms=("Current ratio", "Quick ratio", "Working capital", "Receivable days", "Inventory days", "Payable days"),
           ),
    lesson("ratios-sectors", "Reading ratios by sector: banks, manufacturers and IT services",
           concept="""
The right ratios depend on the business model:
- **Banks and NBFCs**: borrowing is raw material, so D/E, current ratio and EV/EBITDA are not meaningful. Use net interest margin (NIM), asset quality (gross and net NPAs), the CASA ratio, capital adequacy, ROA, ROE and P/B.
- **Manufacturers** are asset-heavy: focus on ROCE, asset turnover, capex intensity, working-capital days, EV/EBITDA and debt. For cyclicals, judge across the whole cycle.
- **IT services** are asset-light: focus on margins, revenue growth, cash conversion, ROE and P/E; P/B says little.""",
           why="Applying a manufacturer's checklist to a bank, or a bank's to a software company, produces confident but wrong conclusions.",
           formulas=["NIM = (Interest earned − Interest expended) ÷ Average earning assets", "Gross NPA ratio = Gross NPAs ÷ Gross advances",
                     "CASA ratio = (Current + Savings deposits) ÷ Total deposits", "Capital adequacy ratio = Eligible capital ÷ Risk-weighted assets"],
           example=f"""
{ILLUSTRATIVE} A bank with interest earned ₹10,000 crore, interest expended ₹6,000 crore and average earning assets ₹1,20,000 crore:
- **NIM = 4,000 ÷ 1,20,000 = 3.33%**.
- Gross NPAs ₹2,400 crore on gross advances ₹80,000 crore: **gross NPA ratio = 3.0%**.""",
           interpret="For banks an ROA of around 1% is often cited as healthy. A loan becomes a non-performing asset when interest or principal is overdue for more than 90 days (RBI norms). RBI sets minimum capital requirements; check RBI for current levels. Compare banks with banks, IT companies with IT companies.",
           mistakes=["Applying D/E or the current ratio to banks.", "Valuing an IT services company mainly on P/B.",
                     "Comparing a cyclical's margins at different points of the cycle.", "Ignoring provisions when reading bank profits."],
           application="Bank pages in EquityPilot have a Bank metrics tab (gross NPA, capital adequacy); the Industries page groups peers.",
           revision=["Banks: NIM, NPAs, CASA, capital adequacy, ROA, P/B.", "Manufacturers: ROCE, turnover, capex, working capital.",
                     "IT services: margins, growth, cash conversion, P/E.", "Compare within the same sector."],
           check=[
               num("A bank earns interest of ₹8,000 crore, pays interest of ₹5,000 crore, and has average earning assets of ₹1,00,000 crore. What is its NIM, in %?", 3,
                   "Net interest income divided by earning assets.", "(8,000 − 5,000) ÷ 1,00,000 = 3%", unit="%", verify=v("nim", 8000, 5000, 100000, unit="%")),
               mcq("For an IT services company, which ratio is usually the least informative?", ["Operating margin", "Revenue growth", "P/B ratio", "Cash conversion"], 2,
                   "Its value lies in people and client relationships that are not on the balance sheet, so book value says little.",
                   ["Margins are central for IT services.", "Growth drives IT services valuations.", None, "Cash conversion tests earnings quality."]),
           ],
           tools=(("company:HDFCBANK.NS", "See bank metrics for a real bank."), ("industries", "Compare companies within a sector.")),
           sources=("rbi",),
           terms=(term("Net interest margin", "A lender's interest income minus interest expense, as a share of its earning assets.",
                       formula="NIM = (Interest earned − Interest expended) ÷ Average earning assets", aliases=("nim",), related=("NPA", "CASA ratio")),
                  term("NPA", "Non-performing asset: a loan on which interest or principal is overdue for more than 90 days under RBI norms.",
                       formula="Gross NPA ratio = Gross NPAs ÷ Gross advances", aliases=("gnpa", "nnpa", "gross npa", "net npa", "non-performing asset", "bad loans"),
                       related=("Net interest margin", "Capital adequacy ratio")),
                  term("CASA ratio", "Current and savings account deposits as a share of total deposits; a higher ratio usually means cheaper funding.",
                       formula="CASA = (Current + Savings deposits) ÷ Total deposits", aliases=("casa",), related=("Net interest margin",)),
                  term("Capital adequacy ratio", "A bank's eligible capital as a share of its risk-weighted assets; RBI sets the minimum.",
                       formula="CRAR = Eligible capital ÷ Risk-weighted assets", aliases=("crar", "capital adequacy", "tier 1", "car"), related=("NPA",))),
           ),
], test=[
    mcq("ROE of 20% with a net margin of 5% and asset turnover of 1.0x implies an equity multiplier of…", ["2x", "4x", "5x", "0.25x"], 1,
        "20% = 5% × 1.0 × EM, so EM = 4x: ROE here is driven mostly by leverage.",
        ["2x would give ROE of 10%.", None, "5x would give ROE of 25%.", "An equity multiplier below 1 is impossible."], level="medium", kind="numerical"),
    mcq("Which ratio best compares the operating returns of companies with different debt levels?", ["ROE", "ROCE", "EPS growth", "Dividend yield"], 1,
        "ROCE uses EBIT and all capital employed, so it does not depend on the financing mix.",
        ["ROE is boosted by leverage.", None, "EPS growth is not a return on capital.", "Dividend yield measures cash return on price."]),
    mcq("Interest coverage of 1.2x means…", ["Debt is very safe", "Operating profit barely covers interest", "The company has no debt", "ROE is 1.2%"], 1,
        "EBIT is only 1.2 times interest; a small fall in profit could make interest unaffordable.",
        ["1.2x is thin cover.", None, "Coverage exists only when there is interest to cover.", "Coverage is not a return measure."]),
    mcq("CFO ÷ net profit consistently around 0.5x suggests…", ["Excellent earnings quality", "Profits are not converting into cash", "High dividends", "A low tax rate"], 1,
        "Persistently low cash conversion warrants a look at receivables, inventory and revenue recognition.",
        ["Good quality means CFO close to or above profit.", None, "Dividends are financing flows, not CFO.", "Tax does not explain this pattern."], kind="statement"),
    mcq("Which of these is NOT meaningful for a bank?", ["P/B", "ROE", "EV/EBITDA", "Net interest margin"], 2,
        "For banks debt is raw material, so enterprise-value and EBITDA measures lose meaning.",
        ["P/B is the standard bank multiple.", "ROE is central for banks.", None, "NIM is a core bank metric."]),
    num("Market cap ₹40,000 crore, borrowings ₹8,000 crore, cash ₹3,000 crore, EBITDA ₹4,500 crore. What is EV/EBITDA?", 10,
        "Build EV first.", "EV = 40,000 + 8,000 − 3,000 = 45,000; 45,000 ÷ 4,500 = 10x", unit="x", verify=v("enterprise_value", 40000, 8000, 3000, expect=45000)),
    mcq("Company A: ROE 25%, D/E 3.0x. Company B: ROE 18%, D/E 0.1x. Which statement is fair?",
        ["A's higher ROE comes largely from leverage, so it carries more risk; B's returns are earned more conservatively", "A is always the better business", "B must be overvalued", "ROE cannot be compared at all"], 0,
        "DuPont reminds us that leverage can lift ROE; the quality of returns matters.",
        [None, "Higher ROE from debt is not automatically better.", "Valuation needs price information.", "ROE can be compared once leverage is considered."], level="hard", kind="case"),
    mcq("Why can P/E mislead for a cyclical company at peak profits?", ["Peak earnings make the P/E look low just before profits fall", "P/E ignores the share price", "Cyclicals have no earnings", "P/E is only used for banks"], 0,
        "When earnings are at a cyclical high the denominator is inflated, so the multiple looks deceptively cheap.",
        [None, "P/E uses the share price.", "Cyclicals have earnings, just volatile ones.", "P/E is widely used outside banks."], level="medium"),
    num("Current assets ₹450 crore; current liabilities ₹300 crore. What is the current ratio?", 1.5, "Current assets divided by current liabilities.", "450 ÷ 300 = 1.5x",
        unit="x", level="easy"),
])

MODULES = [statements, ratios]
