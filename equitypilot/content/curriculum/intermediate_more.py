"""Intermediate level, part 2: investment products, technical analysis and the basics of valuation."""
from __future__ import annotations

from .core import ILLUSTRATIVE, lesson, mcq, module, num, term, v

# ================================================================== 8. Investment products
products = module("products", "Investment products", "intermediate",
                  "Shares, mutual funds, index funds and ETFs, bonds and deposits, REITs and InvITs, and derivatives: how each works, its risks and who it may suit.", [
    lesson("products-funds", "Equity shares and mutual funds",
           concept="""
Buying **shares directly** means owning specific companies. A **mutual fund** pools money from many investors and invests it according to a stated objective; an asset management company (AMC) manages it and SEBI regulates it. You own **units**, valued at the **NAV** (net asset value per unit).
SEBI's categorisation groups schemes into equity (large cap, mid cap, small cap, flexi cap, ELSS and others), debt, hybrid, solution-oriented and other schemes (index funds, ETFs, funds of funds). Every scheme shows a **riskometer**, and costs are charged through the **total expense ratio (TER)**: direct plans cost less than regular plans, which include distributor commission.""",
           why="Most Indian investors reach the equity market through mutual funds. Understanding NAV, costs and categories lets you compare schemes properly.",
           formulas=["NAV per unit = (Market value of assets − Liabilities) ÷ Units outstanding", "Units allotted = Amount invested ÷ NAV",
                     "Annual cost of TER ≈ Value of investment × TER"],
           example=f"""
{ILLUSTRATIVE}
- A fund holds assets of ₹1,020 crore with liabilities of ₹20 crore and 50 crore units: **NAV = ₹20**.
- Investing ₹10,000 buys **500 units**.
- On ₹1,00,000, a TER of 1.5% costs about ₹1,500 a year and 0.5% about ₹500; over decades the gap compounds.""",
           interpret="A low NAV does not make a fund cheap: NAV only reflects the value of its holdings. Compare schemes in the same category on costs, portfolio, risk and consistency against their benchmark.",
           mistakes=["Thinking a low NAV means a cheaper fund.", "Choosing last year's top performer.", "Ignoring the expense ratio and exit load.",
                     "Holding many funds with the same underlying shares.", "Treating the IDCW (dividend) option as an extra return; it is paid out of the fund's own value."],
           application="Scheme data and NAVs are published by AMFI. Track direct shareholdings in Portfolio, and use Compare to study the companies a fund holds.",
           revision=["NAV = (assets − liabilities) ÷ units.", "TER is charged every year; direct plans cost less.", "Compare within a SEBI category.", "Check the riskometer."],
           check=[
               num("A fund has assets of ₹515 crore, liabilities of ₹15 crore and 25 crore units. What is its NAV per unit, in ₹?", 20,
                   "Net assets divided by units.", "(515 − 15) ÷ 25 = ₹20", unit="₹", level="easy", verify=v("nav", 515, 15, 25)),
               mcq("Fund A has a NAV of ₹15 and fund B a NAV of ₹150; both are in the same category. Which is cheaper?",
                   ["A, because its NAV is lower", "Neither: the NAV level says nothing about value; compare costs, portfolio and performance", "B, because its NAV is higher", "A, because you get more units"], 1,
                   "NAV depends on when a fund started and how it has performed, not on whether it is cheap.",
                   ["A lower NAV is not a discount.", None, "A higher NAV is not a sign of quality either.", "More units of lower value are worth the same."], level="medium"),
           ],
           tools=(("portfolio", "Track your holdings."),),
           sources=("amfi", "sebi"),
           terms=(term("Mutual fund", "A SEBI-regulated pooled investment managed by an asset management company; investors own units valued at NAV.",
                       aliases=("mf", "mutual funds", "amc", "asset management company", "sip", "systematic investment plan"), related=("NAV", "Expense ratio")),
                  term("NAV", "Net asset value per unit of a fund: its assets minus liabilities, divided by units outstanding.",
                       formula="NAV = (Assets − Liabilities) ÷ Units", aliases=("net asset value",), related=("Mutual fund",)),
                  term("Expense ratio", "The annual cost of running a fund, charged as a percentage of its assets (TER).",
                       aliases=("ter", "total expense ratio", "direct plan", "regular plan"), related=("Mutual fund", "Index fund")),
                  term("Riskometer", "A SEBI-mandated label showing a mutual fund scheme's risk level, from low to very high.", related=("Mutual fund",)),
                  term("IDCW", "Income distribution cum capital withdrawal: the payout option of a mutual fund (formerly the dividend option); payouts come out of the NAV.",
                       aliases=("dividend option",), related=("NAV",))),
           ),
    lesson("products-index-etf", "Index funds and ETFs",
           concept="""
**Index funds** and **ETFs** (exchange-traded funds) passively track an index such as NIFTY 50. You buy or redeem an index fund with the AMC at the day's NAV. An ETF is listed and traded on the exchange during market hours (you need a demat account), and its market price can differ slightly from its NAV.
Their quality is judged by cost (expense ratio) and by how closely they follow the index: **tracking difference** (fund return minus index return) and **tracking error** (how much that difference varies).""",
           why="Passive funds deliver the index return minus small costs. They remove the risk of picking a poor fund manager, and also the chance of beating the index.",
           formulas=["Tracking difference = Fund return − Index (total return) return", "ETF premium or discount = (Market price − NAV) ÷ NAV"],
           example=f"""
{ILLUSTRATIVE}
- The NIFTY 50 total return index returns 12.0% in a year and an index fund 11.8%: tracking difference **−0.2%**, roughly its costs.
- An ETF's NAV is ₹250 and it trades at ₹251: a **premium of 0.4%**.""",
           interpret="Prefer low costs and low tracking error; for ETFs also check trading volume and the bid-ask spread, because an illiquid ETF can trade well away from its NAV.",
           mistakes=["Buying an illiquid ETF at a large premium.", "Comparing a fund with a price index instead of the total return index (funds reinvest dividends).",
                     "Assuming a passive fund carries no risk; it falls with its index."],
           application="Follow NIFTY 50 and sector indices in the Market Tracker; AMFI publishes data on index funds and ETFs.",
           revision=["Passive = track an index.", "ETFs trade on the exchange; index funds deal at NAV.", "Judge by cost and tracking.", "Compare with the total return index."],
           check=[
               num("An ETF's NAV is ₹400 and it trades at ₹402. What is its premium to NAV, in %?", 0.5, "Compare price with NAV.", "(402 − 400) ÷ 400 = 0.5%", unit="%", level="easy"),
               mcq("You need a demat account to buy…", ["An ETF on the exchange", "An index fund directly from the AMC", "A bank fixed deposit", "A savings account"], 0,
                   "ETFs are listed securities and settle into a demat account.",
                   [None, "Index fund units can be held without demat.", "A deposit is a bank product.", "A savings account is a bank product."]),
           ],
           tools=(("markets", "Follow the indices that passive funds track."),),
           sources=("amfi", "nse", "sebi"),
           terms=(term("Index fund", "A mutual fund that tracks an index, bought and redeemed at NAV.", aliases=("index funds", "passive fund", "passive investing"),
                       related=("ETF", "Tracking error")),
                  term("ETF", "Exchange-traded fund: a fund, usually tracking an index, whose units trade on an exchange like shares.",
                       aliases=("exchange traded fund", "exchange-traded fund", "etfs", "inav"), related=("Index fund",)),
                  term("Tracking error", "How much a passive fund's return deviates from its index; tracking difference is the average gap.",
                       aliases=("tracking difference",), related=("Index fund", "ETF")),
                  term("Total return index", "An index that assumes dividends are reinvested; the fair benchmark for funds.", aliases=("tri",), related=("NIFTY 50",))),
           ),
    lesson("products-bonds", "Bonds, government securities, corporate bonds and fixed deposits",
           concept="""
A **bond** is a loan to the issuer: it pays interest (**coupons**) and returns the face value at maturity.
- **Government securities (G-secs)** are issued through RBI for the central government (state governments issue state development loans; treasury bills are short-term). They carry no default risk in rupee terms. Individuals can buy them through RBI Retail Direct.
- **Corporate bonds** pay more because of credit risk, which credit rating agencies assess.
- **Fixed deposits** are bank deposits at a fixed rate. DICGC insures bank deposits up to ₹5 lakh per depositor per bank, principal and interest together.""",
           why="Bonds and deposits are the stabilising part of most portfolios. Their prices and returns depend on interest rates and on the issuer's ability to pay.",
           formulas=["Current yield = Annual coupon ÷ Market price", "Approximate YTM = [Coupon + (Face value − Price) ÷ Years] ÷ [(Face value + Price) ÷ 2]",
                     "Bond prices move opposite to yields; longer maturities move more (higher duration)"],
           example=f"""
{ILLUSTRATIVE} Face value ₹1,000, coupon 8% (₹80 a year), price ₹950, 5 years to maturity:
- **Current yield** = 80 ÷ 950 = **8.42%**.
- **Approximate YTM** = (80 + 50 ÷ 5) ÷ ((1,000 + 950) ÷ 2) = 90 ÷ 975 = **9.23%**: above the coupon because you also gain ₹50 at maturity.""",
           interpret="A price below face value means a yield above the coupon, and vice versa. Ratings (AAA is the highest) indicate default risk but can be downgraded; a higher yield usually means higher risk. Deposits are simple and insured up to the limit, but premature withdrawal can carry a penalty and the interest is taxable.",
           mistakes=["Chasing high coupons without checking credit quality.", "Ignoring interest-rate risk on long-dated bonds.",
                     "Assuming deposits above ₹5 lakh per bank are insured.", "Forgetting that many corporate bonds are hard to sell quickly."],
           application="The Valuation Lab's risk-free rate is based on G-sec yields; the bond calculator shows how price changes yield.",
           revision=["Bond = loan: coupons plus face value at maturity.", "Price down → yield up.", "Ratings indicate credit risk.", "DICGC: ₹5 lakh per depositor per bank."],
           check=[
               num("A bond pays a ₹70 annual coupon and trades at ₹875. What is its current yield, in %?", 8, "Coupon divided by price.", "70 ÷ 875 = 8%", unit="%", level="easy",
                   verify=v("current_yield", 70, 875, unit="%")),
               mcq("A bond trades below its face value. Its yield to maturity is…", ["Below its coupon rate", "Above its coupon rate", "Equal to its coupon rate", "Zero"], 1,
                   "You earn the coupon plus the gain from the discount to face value.",
                   ["That happens when the bond trades above face value.", None, "That happens only at face value.", "A bond paying coupons has a positive yield."], level="medium"),
           ],
           calculators=("bond",), tools=(("valuation", "See how the G-sec yield sets the risk-free rate."),),
           sources=("rbi", "rbi_retail", "dicgc", "sebi"),
           terms=(term("Bond", "A debt security: the issuer borrows money, pays periodic coupons and repays face value at maturity.",
                       aliases=("bonds", "debenture", "ncd", "coupon", "non-convertible debenture"), related=("Yield to maturity", "Government security")),
                  term("Government security", "A bond or bill issued by the central or a state government; carries no default risk in rupee terms.",
                       aliases=("g-sec", "gsec", "g-secs", "treasury bill", "t-bill", "sdl", "state development loan", "government bond"), related=("Bond", "Risk-free rate")),
                  term("Yield to maturity", "The annual return from holding a bond to maturity, including coupons and any gain or loss against face value.",
                       formula="Approx. YTM = [C + (F − P) ÷ n] ÷ [(F + P) ÷ 2]", aliases=("ytm", "bond yield"), related=("Bond", "Duration")),
                  term("Credit rating", "An agency's opinion of an issuer's ability to repay; AAA is the highest grade.", aliases=("aaa", "rating agency", "credit risk"),
                       related=("Bond",)),
                  term("Fixed deposit", "A bank deposit for a fixed term at a fixed rate; insured by DICGC up to ₹5 lakh per depositor per bank.",
                       aliases=("fd", "fixed deposits", "term deposit", "dicgc", "deposit insurance"), related=("Bond",)),
                  term("Duration", "A measure of how sensitive a bond's price is to interest-rate changes; longer duration means bigger price moves.",
                       aliases=("modified duration", "interest rate risk"), related=("Yield to maturity",))),
           ),
    lesson("products-reits", "REITs and InvITs",
           concept="""
**REITs** (real estate investment trusts) own income-producing property such as offices and malls. **InvITs** (infrastructure investment trusts) own infrastructure such as roads, power transmission lines and pipelines.
Both are SEBI-regulated trusts whose units are listed on exchanges, and both must distribute at least 90% of their net distributable cash flows to unitholders.""",
           why="They give access to rental and infrastructure income with small amounts, exchange liquidity and professional management.",
           formulas=["Distribution yield = Annual distribution per unit ÷ Unit price", "NAV per unit = (Value of assets − Liabilities) ÷ Units"],
           example=f"""
{ILLUSTRATIVE} A unit priced at ₹350 distributes ₹24 a year: **distribution yield = 6.86%**. If part of the ₹24 is a repayment of capital, that part is your own money coming back, not income.""",
           interpret="Distributions depend on occupancy, rents, toll traffic and interest rates. They are made up of interest, dividends, rental income and repayment of capital, each treated differently for tax, so read the distribution breakdown. Unit prices move with interest rates and property or infrastructure cycles.",
           mistakes=["Treating the distribution yield as guaranteed.", "Ignoring leverage, occupancy and the remaining life of concessions.",
                     "Comparing the yield with a deposit rate without considering the different risks.", "Overlooking that part of a distribution may be a return of capital."],
           application="REIT and InvIT units trade like shares, so you can follow them in the Market Tracker and add them to Portfolio.",
           revision=["REITs: property; InvITs: infrastructure.", "At least 90% of net distributable cash flow is paid out.", "Yield = distribution ÷ price.", "Distributions are not guaranteed."],
           check=[
               num("A REIT unit trades at ₹320 and distributes ₹20 a year. What is its distribution yield, in %?", 6.25, "Annual distribution divided by price.", "20 ÷ 320 = 6.25%",
                   unit="%", level="easy"),
               mcq("REITs and InvITs in India must distribute at least what share of their net distributable cash flows?", ["50%", "75%", "90%", "100%"], 2,
                   "SEBI's REIT and InvIT regulations require at least 90%.", ["The requirement is higher.", "The requirement is higher.", None, "They may retain up to 10%."], kind="rule"),
           ],
           sources=("sebi", "nse", "bse"),
           terms=(term("REIT", "Real estate investment trust: a listed trust that owns income-producing property and distributes most of its cash flow.",
                       aliases=("reits", "real estate investment trust"), related=("InvIT", "Distribution yield")),
                  term("InvIT", "Infrastructure investment trust: a listed trust that owns infrastructure assets and distributes most of its cash flow.",
                       aliases=("invits", "infrastructure investment trust"), related=("REIT",)),
                  term("Distribution yield", "A REIT's or InvIT's annual distribution per unit as a percentage of the unit price.",
                       formula="Distribution ÷ Unit price", aliases=("distribution per unit",), related=("REIT",))),
           ),
    lesson("products-derivatives", "Derivatives: futures, options, commodities and currencies",
           concept="""
A **derivative** takes its value from an underlying asset: a share, an index, a commodity or a currency.
- **Futures**: an agreement to buy or sell at a fixed price on a future date. Both sides have obligations, margins are required and positions are marked to market every day.
- **Options**: the buyer pays a **premium** for the right, not the obligation, to buy (**call**) or sell (**put**) at the **strike price**; the seller (writer) takes on the obligation.
Equity futures and options trade on NSE and BSE in fixed lot sizes; commodity derivatives trade on exchanges such as MCX and NCDEX; currency derivatives trade on stock exchanges under RBI and SEBI rules.""",
           why="Derivatives are used to hedge and to speculate. Leverage magnifies both gains and losses. SEBI's study of individual traders in equity F&O for FY22 to FY24 (published in September 2024) found that about 93% of them made net losses; SEBI's later studies (press release of 20 August 2026) track how this has changed.",
           formulas=["Call buyer's profit at expiry = max(Spot − Strike, 0) − Premium", "Put buyer's profit at expiry = max(Strike − Spot, 0) − Premium",
                     "Long futures profit = (Exit price − Entry price) × Lot size", "Contract value = Price × Lot size"],
           example=f"""
{ILLUSTRATIVE} (per share; lot sizes and margins are examples)
- **Call**, strike ₹1,000, premium ₹30: spot ₹1,060 at expiry gives +₹30 (60 − 30); spot ₹980 gives −₹30 (the premium). Break-even is ₹1,030.
- **Put**, strike ₹1,000, premium ₹25: spot ₹950 gives +₹25; spot ₹1,050 gives −₹25.
- **Futures**: one lot of 500 shares bought at ₹1,000 is a ₹5,00,000 contract. If the margin is ₹1,00,000, a 5% fall loses ₹25,000, a quarter of the margin.""",
           interpret="An option buyer's loss is limited to the premium, while a call seller's potential loss is unlimited. With futures, small price moves become large percentage changes on the margin. Costs (brokerage, taxes, spreads) are paid on every trade, win or lose.",
           mistakes=["Treating options as lottery tickets.", "Selling options without understanding the open-ended risk.",
                     "Ignoring transaction costs.", "Using too much leverage.", "Trading without understanding margins, expiry and lot sizes."],
           application="EquityPilot does not offer derivatives trading or practice. Read the exchanges' and SEBI's investor material, and check current lot sizes and rules in exchange circulars.",
           revision=["Futures: obligation on both sides; daily mark to market.", "Options: buyer has the right, seller the obligation.",
                     "Call profit = max(S − K, 0) − premium; put = max(K − S, 0) − premium.", "Leverage magnifies losses; most individual F&O traders lost money in SEBI's study."],
           check=[
               num("You buy a call with a strike of ₹500 for a ₹20 premium. At expiry the share is at ₹540. What is your profit per share, in ₹?", 20,
                   "Intrinsic value at expiry minus the premium paid.", "max(540 − 500, 0) − 20 = 40 − 20 = ₹20", unit="₹", verify=v("call_payoff", 540, 500, 20)),
               mcq("The most a put option buyer can lose is…", ["Unlimited", "The premium paid", "The strike price", "Nothing"], 1,
                   "If the option expires worthless, the buyer loses only the premium.",
                   ["Unlimited loss applies to some option sellers.", None, "The strike is not at risk for the buyer.", "The premium can be lost."]),
           ],
           sources=("sebi", "sebi_fo_study", "sebi_press", "nse", "bse"),
           terms=(term("Derivative", "A contract whose value depends on an underlying asset such as a share, index, commodity or currency.",
                       aliases=("derivatives", "f&o", "futures and options"), related=("Futures", "Option")),
                  term("Futures", "An exchange-traded agreement to buy or sell an asset at a set price on a future date, with daily mark-to-market and margins.",
                       aliases=("future", "futures contract", "mark to market", "mtm", "margin money"), related=("Derivative", "Lot size")),
                  term("Option", "A contract giving the buyer the right, not the obligation, to buy (call) or sell (put) at the strike price, in exchange for a premium.",
                       formula="Call P/L = max(S − K, 0) − Premium; Put P/L = max(K − S, 0) − Premium",
                       aliases=("options", "call option", "put option", "strike price", "option premium", "option writer"), related=("Derivative",)),
                  term("Lot size", "The fixed number of units in one derivatives contract, set by the exchange.", aliases=("lot", "contract size"), related=("Futures",)),
                  term("Commodity derivatives", "Futures and options on commodities such as gold, crude oil and agricultural goods, traded on exchanges such as MCX and NCDEX.",
                       aliases=("mcx", "ncdex", "commodity futures"), related=("Derivative",)),
                  term("Currency derivatives", "Exchange-traded futures and options on exchange rates such as USD-INR, governed by RBI and SEBI rules.",
                       aliases=("usd inr futures", "currency futures", "forex derivatives"), related=("Derivative",))),
           ),
], test=[
    mcq("NAV per unit is calculated as…", ["(Assets − Liabilities) ÷ Units", "Assets ÷ Number of investors", "Price × Units", "Expense ratio ÷ Units"], 0,
        "NAV is net assets per unit.", [None, "Investor count is irrelevant.", "That would be a total value, not per unit.", "The TER is a cost, not the NAV."]),
    num("₹25,000 is invested at a NAV of ₹62.50. How many units are allotted?", 400, "Divide the amount by NAV.", "25,000 ÷ 62.50 = 400 units", unit="units", level="easy", tolerance=0.01),
    mcq("An ETF differs from an index fund mainly because it…", ["Trades on an exchange during market hours", "Has no expense ratio", "Is guaranteed", "Cannot track an index"], 0,
        "ETF units are listed and traded like shares.", [None, "ETFs also charge expenses.", "No fund is guaranteed.", "ETFs usually track indices."]),
    num("Face value ₹1,000, annual coupon ₹60, price ₹1,040, 4 years to maturity. What is the approximate YTM, in %?", 4.9,
        "The premium over face value is lost by maturity, lowering the yield below the coupon.",
        "(60 + (1,000 − 1,040) ÷ 4) ÷ ((1,000 + 1,040) ÷ 2) = (60 − 10) ÷ 1,020 = 4.90%", unit="%", level="hard",
        verify=v("approx_ytm", 60, 1000, 1040, 4, unit="%")),
    mcq("DICGC insures bank deposits up to…", ["₹1 lakh per account", "₹5 lakh per depositor per bank", "₹10 lakh per bank", "An unlimited amount"], 1,
        "The limit has been ₹5 lakh per depositor per bank since 2020.", ["The old limit was ₹1 lakh.", None, "There is no ₹10 lakh limit.", "Cover is limited."], kind="rule"),
    mcq("Interest rates rise sharply. Which price falls the most?", ["A 1-year treasury bill", "A 10-year government bond", "A savings account balance", "A 3-month deposit"], 1,
        "Longer maturity means higher duration and bigger price sensitivity.",
        ["Short maturities move little.", None, "Savings balances have no market price.", "A short deposit's value does not move with market rates."], level="medium"),
    num("You bought a put with a strike of ₹2,000 for a ₹45 premium. At expiry the share is at ₹1,900. What is your profit per share, in ₹?", 55,
        "The put is worth the strike minus the spot, less the premium.", "max(2,000 − 1,900, 0) − 45 = 100 − 45 = ₹55", unit="₹", verify=v("put_payoff", 1900, 2000, 45)),
    mcq("Why are futures risky for a beginner?", ["Leverage: a small adverse move can wipe out the margin and more", "They cannot be sold before expiry", "They never expire", "SEBI guarantees the profits"], 0,
        "The margin is a fraction of the contract value, so losses relative to it are large.",
        [None, "Futures can be closed before expiry.", "Futures have fixed expiry dates.", "No one guarantees trading profits."], level="medium"),
    mcq("A REIT says part of its distribution is a return of capital. This means…", ["Part of the payout is your own capital being returned, not income", "It is always tax-free income", "SEBI guarantees it", "The REIT is insolvent"], 0,
        "A capital repayment reduces your invested amount; it is not a profit.",
        [None, "Tax treatment differs by component; it is not automatically 'income'.", "No regulator guarantees distributions.", "It is a normal component, not a sign of insolvency."], level="hard"),
])

# ================================================================== 9. Technical analysis
technical = module("technical", "Technical analysis", "intermediate",
                   "Candlesticks, support and resistance, trendlines, volume, moving averages, RSI, MACD, Bollinger Bands and volatility, and the limits of all of them.", [
    lesson("technical-charts", "Charts: candlesticks, support, resistance, trendlines and volume",
           concept="""
**Technical analysis** studies the history of prices and volume.
- A **candlestick** shows a period's open, high, low and close. The body runs from open to close (green or hollow when the close is higher, red or filled when lower); the wicks mark the high and the low.
- **Support** is a price zone where buying has repeatedly stopped falls; **resistance** is where selling has capped rises.
- **Trendlines** join rising lows in an uptrend or falling highs in a downtrend.
- **Volume** shows how many shares changed hands, and so how much participation lay behind a move.""",
           why="Charts summarise how the market has behaved and help with timing and risk management, such as where to place a stop-loss.",
           rules=["Candle body = open to close; wicks = high and low.", "Uptrend: higher highs and higher lows. Downtrend: lower highs and lower lows.",
                  "A breakout on high volume is usually treated as more meaningful than one on low volume.", "Patterns describe past behaviour; they do not guarantee future moves."],
           example=f"""
{ILLUSTRATIVE}
- A day opens at ₹100, reaches ₹108, dips to ₹97 and closes at ₹106: a green candle with a ₹6 body, a ₹2 upper wick and a ₹3 lower wick.
- A share has bounced from about ₹450 three times in six months: ₹450 is a support zone. A fall below it on heavy volume would be read as a breakdown.""",
           interpret="Support and resistance are zones, not exact lines, and a level tested many times gets more attention. Volume confirms or questions a move. None of this is certain: levels break all the time.",
           mistakes=["Seeing patterns everywhere (confirmation bias).", "Ignoring fundamentals and news.", "Drawing trendlines to fit the view you already hold.",
                     "Over-trading on intraday noise."],
           application="Open a company's price chart to see candles and volume, and watch the day's movers in the Market Tracker.",
           revision=["Candles show open, high, low and close.", "Support stops falls; resistance caps rises.", "Trendlines join lows (up) or highs (down).", "Volume confirms moves."],
           check=[
               mcq("A candle has open ₹200, close ₹190, high ₹205 and low ₹188. It is…", ["A green (rising) candle", "A red (falling) candle with a ₹10 body", "A candle with no body", "Impossible"], 1,
                   "The close is below the open, so the candle is red, with a body of 200 − 190 = ₹10.",
                   ["The close is lower than the open.", None, "Open and close differ by ₹10.", "All four prices are consistent."], kind="numerical"),
               mcq("Which statement about support levels is most accurate?", ["They guarantee the price will not fall further", "They are zones where buying has previously halted falls", "They are set by SEBI", "They are calculated from EPS"], 1,
                   "Support is an observation about past buying, not a promise.",
                   ["Support often breaks.", None, "Regulators do not set price levels.", "Support comes from price history, not earnings."]),
           ],
           tools=(("company:RELIANCE.NS", "Open a price chart with candles and volume."), ("markets", "See today's movers.")),
           terms=(term("Candlestick", "A chart bar showing a period's open, high, low and close.", aliases=("candlestick chart", "candle", "ohlc", "candlesticks"),
                       related=("Support and resistance",)),
                  term("Support and resistance", "Price zones where buying (support) or selling (resistance) has previously stopped the price.",
                       aliases=("support", "resistance", "breakout", "breakdown"), related=("Trendline",)),
                  term("Trendline", "A line joining rising lows (uptrend) or falling highs (downtrend) on a price chart.",
                       aliases=("trend line", "uptrend", "downtrend"), related=("Support and resistance", "Moving average")),
                  term("Trading volume", "The number of shares traded in a period; shows participation behind a price move.",
                       aliases=("volume", "delivery volume"), related=("Candlestick",))),
           ),
    lesson("technical-ma", "Moving averages: SMA and EMA",
           concept="""
A **simple moving average (SMA)** is the average of the last n closing prices. An **exponential moving average (EMA)** gives more weight to recent prices, so it reacts faster.
Common periods are 20, 50 and 200 days. A price above a rising 200-day average is commonly read as a long-term uptrend; a **golden cross** is the 50-day average crossing above the 200-day, a **death cross** the reverse.""",
           why="Moving averages smooth out daily noise so the underlying direction is easier to see.",
           formulas=["SMA(n) = Sum of the last n closes ÷ n", "EMA today = Close × k + EMA yesterday × (1 − k), where k = 2 ÷ (n + 1)"],
           example=f"""
{ILLUSTRATIVE}
- Closes of 100, 102, 101, 105 and 107: **SMA(5) = 515 ÷ 5 = 103**.
- EMA(5) with yesterday's EMA at 103 and today's close at 109: k = 2 ÷ 6 = 0.333, so **EMA = 109 × 0.333 + 103 × 0.667 = 105.0**.""",
           interpret="Moving averages lag: they confirm a trend after it has started. In sideways markets crossovers whipsaw, giving many false signals.",
           mistakes=["Using crossovers as stand-alone buy or sell signals.", "Forgetting the lag.", "Tuning the periods until they fit past data (curve fitting)."],
           application="Company price charts in EquityPilot can show moving averages; Technicals in the classic workbench compute them on full history.",
           revision=["SMA = plain average; EMA weights recent prices more.", "k = 2 ÷ (n + 1).", "Golden cross: 50-day above 200-day.", "Averages lag the price."],
           check=[
               num("What is the 4-day SMA of closes 50, 52, 54 and 56?", 53, "Add the closes and divide by the count.", "(50 + 52 + 54 + 56) ÷ 4 = 212 ÷ 4 = 53",
                   level="easy", verify=v("sma", [50, 52, 54, 56])),
               num("A 9-day EMA was 110 yesterday; today's close is 120. What is today's EMA?", 112, "Use k = 2 ÷ (n + 1).",
                   "k = 2 ÷ 10 = 0.2; EMA = 120 × 0.2 + 110 × 0.8 = 24 + 88 = 112", verify=v("ema_next", 120, 110, 9)),
           ],
           tools=(("company:INFY.NS", "View a price chart with moving averages."),),
           terms=("Moving average",
                  term("Golden cross", "The 50-day moving average crossing above the 200-day average; the reverse is a death cross.",
                       aliases=("death cross", "crossover", "moving average crossover"), related=("Moving average",))),
           ),
    lesson("technical-momentum", "Momentum: RSI and MACD",
           concept="""
**RSI (relative strength index)** is a 0-100 oscillator comparing average gains with average losses, usually over 14 days. By convention, above 70 is 'overbought' and below 30 'oversold'.
**MACD** is the 12-day EMA minus the 26-day EMA; its **signal line** is a 9-day EMA of MACD, and the histogram is the difference between them.
A **divergence** occurs when the price makes a new high (or low) but the indicator does not, suggesting momentum is fading.""",
           why="Momentum indicators show whether a move is strengthening or weakening, which helps judge trends and timing.",
           formulas=["RSI = 100 − 100 ÷ (1 + Average gain ÷ Average loss)", "MACD = EMA(12) − EMA(26); Signal = EMA(9) of MACD; Histogram = MACD − Signal"],
           example=f"""
{ILLUSTRATIVE}
- Over 14 days the average gain is ₹1.50 and the average loss ₹0.50: RS = 3, so **RSI = 100 − 100 ÷ 4 = 75**, in the 'overbought' zone.
- MACD is 4.2 and its signal line 3.5: the histogram is **+0.7**, so MACD is above its signal line (strengthening upward momentum).""",
           interpret="In a strong trend RSI can stay overbought or oversold for a long time; it tends to work better in sideways markets. Treat these readings as descriptions to combine with trend, volume and fundamentals.",
           mistakes=["Selling only because RSI is above 70 in a strong uptrend.", "Using default settings without understanding them.", "Ignoring the timeframe of the chart."],
           application="Price charts on Company pages can show RSI and MACD alongside price.",
           revision=["RSI: 0-100; >70 overbought, <30 oversold by convention.", "MACD = EMA(12) − EMA(26) with a 9-day signal.", "Divergence = fading momentum.",
                     "Readings describe; they do not predict."],
           check=[
               num("Average gain 2 and average loss 1 over 14 days. What is the RSI?", 66.67, "RS = average gain ÷ average loss.", "RS = 2; RSI = 100 − 100 ÷ 3 = 66.67",
                   verify=v("rsi", 2, 1)),
               mcq("MACD crossing above its signal line is usually read as…", ["Strengthening upward momentum", "A guaranteed rally", "A dividend announcement", "Lower volatility"], 0,
                   "It shows the fast average pulling away upward from the slow one.",
                   [None, "No indicator guarantees anything.", "MACD has nothing to do with dividends.", "MACD measures momentum, not volatility."]),
           ],
           terms=("RSI", "MACD",
                  term("Divergence", "When price makes a new high or low but a momentum indicator does not, suggesting the move is losing strength.",
                       aliases=("bearish divergence", "bullish divergence"), related=("RSI", "MACD")),
                  term("Overbought and oversold", "Conventional RSI zones: above 70 overbought, below 30 oversold; descriptive readings, not signals on their own.",
                       aliases=("overbought", "oversold"), related=("RSI",))),
           ),
    lesson("technical-volatility", "Volatility, Bollinger Bands and the limits of technical analysis",
           concept="""
**Volatility** measures how much prices swing, usually as the standard deviation of returns; daily figures are annualised by multiplying by √252 (trading days a year).
**Bollinger Bands** are a 20-day SMA plus and minus two standard deviations of price: they widen when volatility rises and narrow (a 'squeeze') when it falls. **ATR** (average true range) measures a typical day's range.""",
           why="Volatility sets the range of likely outcomes; it guides position size and stop-loss distance (see the Portfolio module).",
           formulas=["Annualised volatility = Daily standard deviation × √252", "Bollinger Bands = SMA(20) ± 2 × σ(20)"],
           example=f"""
{ILLUSTRATIVE}
- A daily standard deviation of 1.5% annualises to 1.5% × 15.87 = **23.8%**.
- With a 20-day SMA of ₹500 and a standard deviation of ₹10, the bands sit at **₹480 and ₹520**.""",
           interpret="Higher volatility means a wider range of outcomes, both up and down. The limits of technical analysis matter as much as the tools: indicators describe the past, many signals fail, and trading costs and slippage eat into frequent trading. No indicator predicts prices with certainty.",
           mistakes=["Treating a touch of a band as an automatic buy or sell.", "Assuming volatility stays constant.", "Underestimating how costs and frequent trading erode returns.",
                     "Using technical signals without any risk limit."],
           application="Company pages show volatility and maximum drawdown in price performance; Virtual Invest lets you see how volatile holdings feel without real money.",
           revision=["Volatility = standard deviation of returns.", "Annualise daily figures with √252.", "Bollinger = SMA(20) ± 2σ.", "No indicator gives certainty."],
           check=[
               num("A share's daily standard deviation is 2%. What is its annualised volatility, in %?", 31.75, "Multiply by the square root of 252.", "2% × √252 = 2% × 15.87 = 31.75%",
                   unit="%", tolerance=0.1, verify=v("annualise_volatility", 0.02, unit="%")),
               mcq("A share's 20-day SMA is ₹300 and its 20-day standard deviation is ₹12. The upper Bollinger Band is…", ["₹312", "₹324", "₹336", "₹288"], 1,
                   "Upper band = SMA + 2 standard deviations = 300 + 24.", ["That uses one standard deviation.", None, "That uses three standard deviations.", "That is below the SMA."],
                   kind="numerical"),
           ],
           tools=(("invest", "Feel volatility with virtual money."),),
           terms=("Volatility",
                  term("Bollinger Bands", "Bands two standard deviations above and below a 20-day moving average; they widen as volatility rises.",
                       formula="SMA(20) ± 2σ", aliases=("bollinger", "bollinger band", "squeeze"), related=("Volatility", "Moving average")),
                  term("ATR", "Average true range: the average size of a period's price range, including gaps.", aliases=("average true range",), related=("Volatility",))),
           ),
], test=[
    mcq("An RSI reading of 78 is conventionally described as…", ["Oversold", "Neutral", "Overbought", "A bearish divergence"], 2, "Above 70 is the conventional overbought zone.",
        ["Oversold is below 30.", "Neutral readings sit between 30 and 70.", None, "Divergence compares price with the indicator; one reading cannot show it."]),
    mcq("A 'golden cross' occurs when…", ["Price crosses above the 50-day SMA", "The 50-day SMA crosses above the 200-day SMA", "RSI crosses 50", "Volume doubles"], 1,
        "It is a moving-average crossover associated with a strengthening trend.", ["That is a price crossover.", None, "That is an RSI level.", "That is a volume event."]),
    mcq("MACD is calculated as…", ["EMA(26) − EMA(12)", "EMA(12) − EMA(26)", "SMA(50) − SMA(200)", "RSI − 50"], 1, "Fast EMA minus slow EMA.",
        ["The order is reversed.", None, "That is a moving-average spread, not MACD.", "That is not MACD."]),
    mcq("Bollinger Bands widen when…", ["Volatility rises", "Volume falls", "Price is flat", "RSI is 50"], 0, "Band width is proportional to standard deviation.",
        [None, "Volume does not set band width.", "Flat prices narrow the bands.", "RSI does not affect the bands."]),
    mcq("Which statement is most accurate?", ["Indicators guarantee future prices", "Indicators summarise past price behaviour", "RSI measures earnings", "MACD measures debt"], 1,
        "They are descriptive tools; combine them with fundamentals and risk management.",
        ["No indicator can guarantee prices.", None, "RSI uses prices only.", "MACD uses prices only."]),
    num("Average gain 0.8 and average loss 1.2 over 14 days. What is the RSI?", 40, "RS = 0.8 ÷ 1.2.", "RS = 0.667; RSI = 100 − 100 ÷ 1.667 = 40", verify=v("rsi", 0.8, 1.2)),
    mcq("A share in a strong uptrend has had an RSI above 70 for three weeks. What is the most balanced reading?",
        ["Momentum is strong; overbought readings can last in trends, so combine with other evidence", "Sell immediately", "The company must be overvalued", "RSI has stopped working"], 0,
        "Overbought is a description, not a sell signal, especially in trends.",
        [None, "A single indicator is not a reason to act.", "RSI says nothing about fundamental value.", "Persistent readings are normal in strong trends."], level="hard", kind="case"),
    num("Daily volatility is 1.2%. What is the annualised volatility, in % (using √252)?", 19.05, "Multiply by √252.", "1.2% × 15.87 = 19.05%", unit="%", tolerance=0.1,
        verify=v("annualise_volatility", 0.012, unit="%")),
])

# ================================================================== 10. Valuation basics
valuation = module("valuation", "Valuation basics and relative valuation", "intermediate",
                   "Price versus value, market capitalisation and enterprise value, valuing a company against its peers, margin of safety and scenarios.", [
    lesson("valuation-basics", "Price, value, market cap and enterprise value",
           concept="""
**Price** is what the market charges today; **value** is what the business is worth given the cash it will generate. **Market capitalisation** values the equity; **enterprise value (EV)** adds debt and subtracts cash to value the whole business.
**Intrinsic value** is an estimate of worth from fundamentals, for example a DCF; **relative valuation** compares multiples with similar companies.""",
           why="Separating price from value is the core of investment analysis. EV lets you compare companies that finance themselves differently.",
           formulas=["Market cap = Share price × Shares outstanding", "EV = Market cap + Borrowings − Cash (+ minority interest and preference capital)",
                     "Equity value = EV − Net debt"],
           example=f"""
{ILLUSTRATIVE}
- Price ₹250 × 40 crore shares = **market cap ₹10,000 crore**.
- Borrowings ₹3,000 crore and cash ₹1,000 crore give **EV = ₹12,000 crore**.
- A debt-free company with the same market cap and ₹1,000 crore of cash has an EV of ₹9,000 crore: the same equity value, a cheaper business.""",
           interpret="EV-based multiples compare companies with different capital structures fairly. SEBI's categories use full market capitalisation: large cap is the top 100 companies, mid cap the 101st to 250th, small cap from the 251st.",
           mistakes=["Comparing the P/E of a heavily indebted company with a debt-free one.", "Forgetting minority interest in EV.",
                     "Treating market cap as a measure of revenue or size of operations.", "Confusing price with value."],
           application="A Company page shows market cap and EV-based multiples; the Valuation Lab bridges from EV to equity value per share.",
           revision=["Price is what you pay; value is what you get.", "EV = market cap + debt − cash.", "Equity value = EV − net debt.",
                     "Large cap = top 100; mid = 101-250; small = 251+."],
           check=[
               num("Market cap ₹20,000 crore, borrowings ₹5,000 crore, cash ₹2,000 crore. What is the enterprise value, in ₹ crore?", 23000,
                   "Add debt, subtract cash.", "20,000 + 5,000 − 2,000 = ₹23,000 crore", unit="₹ crore", level="easy", verify=v("enterprise_value", 20000, 5000, 2000)),
               mcq("Two companies have the same market cap. A has ₹5,000 crore of net debt; B has net cash. Which has the higher EV?", ["A", "B", "They are the same", "It cannot be known"], 0,
                   "EV adds net debt, so A's EV is higher than B's.", [None, "Net cash reduces EV.", "Their net debt differs.", "The information given is enough."]),
           ],
           tools=(("valuation", "See the bridge from EV to value per share."),),
           sources=("sebi", "amfi"),
           terms=("Market capitalisation", "Enterprise value",
                  term("Intrinsic value", "An estimate of what a business is worth based on its expected future cash flows, independent of today's price.",
                       aliases=("fair value", "intrinsic worth"), related=("DCF", "Margin of safety"))),
           ),
    lesson("valuation-relative", "Relative valuation and comparable companies",
           concept="""
**Relative valuation** values a company by comparing its multiples (P/E, EV/EBITDA, P/B, EV/Sales) with similar companies and with its own history:
1. Choose comparable peers (same business, similar size, growth and risk).
2. Pick the multiple that suits the sector.
3. Take the peer median.
4. Adjust for differences in growth, returns, balance sheet and governance.
5. Apply the multiple to the company's own metric.""",
           why="It is quick, grounded in what investors are paying today, and widely used in research reports. It also shows what the market expects.",
           formulas=["Implied price = Peer multiple × Company metric per share (for example peer P/E × EPS)",
                     "Implied EV = Peer EV/EBITDA × Company EBITDA; equity value = EV − Net debt", "Justified P/B = (ROE − g) ÷ (Ke − g)"],
           example=f"""
{ILLUSTRATIVE}
- Five peers trade on P/E multiples of 18, 20, 22, 25 and 30: the **median is 22**.
- The company's EPS is ₹40, so the implied price is **₹880**.
- If it grows more slowly or carries more debt than the peers, a discount to 22 may be justified, and you should say why.""",
           interpret="Relative valuation tells you whether a company is cheap or expensive against its peers, not whether the whole sector is fairly valued. The median limits the effect of outliers. For banks, justified P/B links the multiple to ROE.",
           mistakes=["Choosing flattering peers.", "Mixing trailing and forward multiples.", "Ignoring differences in business mix or accounting.", "Using averages distorted by outliers."],
           application="Compare puts peers side by side; the Industries page groups companies; the Valuation Lab includes relative valuation against peers.",
           revision=["Pick real peers and the right multiple.", "Use the median.", "Adjust for growth, risk and returns.", "Relative ≠ absolute value."],
           check=[
               num("Peers' median EV/EBITDA is 12x. The company's EBITDA is ₹500 crore and net debt ₹1,000 crore. What is the implied equity value, in ₹ crore?", 5000,
                   "Find EV first, then subtract net debt.", "EV = 12 × 500 = 6,000; equity = 6,000 − 1,000 = ₹5,000 crore", unit="₹ crore"),
               mcq("Why use the median of peer multiples rather than the average?", ["It is less affected by outliers", "It is always higher", "SEBI requires it", "It includes debt"], 0,
                   "One extreme multiple can distort an average; the median resists it.",
                   [None, "It can be higher or lower.", "There is no such rule.", "Median versus average has nothing to do with debt."]),
           ],
           tools=(("compare", "Compare peers side by side."), ("industries", "Find a company's peer group."), ("valuation", "Run relative valuation in the Valuation Lab.")),
           terms=(term("Relative valuation", "Valuing a company by comparing its multiples with similar companies and with its own history.",
                       aliases=("comparables", "comparable companies", "peer valuation", "comps", "trading multiples", "peer comparison"),
                       related=("P/E ratio", "EV/EBITDA", "Justified P/B")),
                  term("Justified P/B", "The P/B a company deserves given its ROE, growth and cost of equity.", formula="Justified P/B = (ROE − g) ÷ (Ke − g)",
                       example="ROE 16%, g 6%, Ke 13%: (16 − 6) ÷ (13 − 6) = 1.43x.", aliases=("justified pb", "justified price to book"), related=("P/B ratio", "ROE"))),
           ),
    lesson("valuation-safety", "Margin of safety, scenarios and sensitivity",
           concept="""
Every valuation is an estimate. A **margin of safety** is the gap between your estimate of value and the price, kept to allow for errors.
**Scenario analysis** values the company under different sets of assumptions (bear, base and bull). **Sensitivity analysis** changes one input at a time (growth, margin, discount rate) to show which assumptions matter most.""",
           why="A range of values is more honest, and more useful, than a single precise-looking number.",
           formulas=["Margin of safety = (Intrinsic value − Price) ÷ Intrinsic value", "Probability-weighted value = Σ (probability × scenario value)"],
           example=f"""
{ILLUSTRATIVE}
- Base-case value ₹1,000 and price ₹750: **margin of safety = 25%**.
- Scenarios: bear ₹600 (25% probability), base ₹1,000 (50%), bull ₹1,400 (25%). Weighted value = 150 + 500 + 350 = **₹1,000**, but the range runs from ₹600 to ₹1,400.""",
           interpret="The more uncertain the business, the wider the range and the larger the margin of safety worth demanding. A sensitivity table shows which assumption you most need to get right.",
           mistakes=["False precision (a value of ₹1,043.27).", "Scenarios that are only ±10% of the base case.", "Ignoring the probability of the bear case.",
                     "Anchoring on the current price when setting assumptions."],
           application="The Valuation Lab runs bear, base and bull scenarios and sensitivity tables for any tracked company.",
           revision=["MoS = (value − price) ÷ value.", "Scenarios change several assumptions together.", "Sensitivity changes one at a time.", "Report a range, not a point."],
           check=[
               num("Your estimate of intrinsic value is ₹800 and the price is ₹600. What is the margin of safety, in %?", 25,
                   "Measure the gap against intrinsic value.", "(800 − 600) ÷ 800 = 25%", unit="%", level="easy", verify=v("margin_of_safety", 800, 600, unit="%")),
               num("Scenarios: bear ₹400 (30%), base ₹700 (50%), bull ₹1,000 (20%). What is the probability-weighted value, in ₹?", 670,
                   "Weight each scenario by its probability.", "0.3 × 400 + 0.5 × 700 + 0.2 × 1,000 = 120 + 350 + 200 = ₹670", unit="₹",
                   verify=v("expected_return", [(0.3, 400), (0.5, 700), (0.2, 1000)])),
           ],
           tools=(("valuation", "Run scenarios and a sensitivity table."),),
           terms=(term("Margin of safety", "The discount of price to your estimate of intrinsic value, kept as a buffer against errors.",
                       formula="MoS = (Intrinsic value − Price) ÷ Intrinsic value", aliases=("mos",), related=("Intrinsic value", "Scenario analysis")),
                  term("Scenario analysis", "Valuing a business under several consistent sets of assumptions, such as bear, base and bull cases.",
                       aliases=("bull case", "bear case", "base case", "scenarios", "bull base bear"), related=("Sensitivity analysis", "Margin of safety")),
                  term("Sensitivity analysis", "Changing one valuation input at a time to see how much the result moves.", aliases=("sensitivity", "sensitivity table"),
                       related=("Scenario analysis", "DCF"))),
           ),
], test=[
    mcq("Enterprise value equals…", ["Market cap + cash − debt", "Market cap + debt − cash", "Book equity + debt", "Revenue × P/E"], 1,
        "EV = market capitalisation + borrowings − cash (plus minorities and preference capital where relevant).",
        ["Cash is subtracted and debt added, not the reverse.", None, "EV uses market value of equity, not book value.", "That is not a valuation identity."]),
    mcq("A bank with ROE 16%, cost of equity 13% and growth 6% has a justified P/B of about…", ["0.8x", "1.0x", "1.43x", "2.7x"], 2,
        "(16% − 6%) ÷ (13% − 6%) = 10 ÷ 7 ≈ 1.43x.",
        ["That would need ROE below the cost of equity.", "That would need ROE equal to the cost of equity.", None, "That ignores growth in the formula."], level="hard", kind="numerical"),
    num("A share trades at ₹125 and there are 80 crore shares. What is the market capitalisation, in ₹ crore?", 10000, "Price × shares.", "125 × 80 crore = ₹10,000 crore",
        unit="₹ crore", level="easy"),
    mcq("The price is ₹500 and your estimate of intrinsic value is ₹400. The margin of safety is…", ["Negative: the price is above your estimate of value", "25%", "20%", "Exactly zero"], 0,
        "(400 − 500) ÷ 400 = −25%: there is no margin of safety.",
        [None, "That treats the gap the wrong way round.", "That divides by the price and ignores the sign.", "Price and value differ."], level="medium", kind="numerical"),
    mcq("The peers' median P/E is 25, but your company grows much more slowly and carries more debt. What is appropriate?",
        ["Apply a discount to the peer multiple and explain why", "Use the peers' highest P/E", "Ignore the differences", "Use a bank's EV/EBITDA"], 0,
        "Relative valuation needs adjustment for differences in growth and risk.",
        [None, "That flatters the company.", "Differences in growth and risk should change the multiple.", "Bank multiples are irrelevant here."], level="medium", kind="case"),
    num("Peers' median P/E is 18 and the company's EPS is ₹55. What is the implied price, in ₹?", 990, "Multiply the multiple by EPS.", "18 × 55 = ₹990", unit="₹", level="easy"),
    mcq("What is scenario analysis best used for?", ["Seeing a range of values under different assumptions", "Finding the single exact value", "Predicting next week's price", "Avoiding assumptions"], 0,
        "Scenarios make assumptions explicit and show the spread of outcomes.",
        [None, "No method gives an exact value.", "Valuation is not a short-term price forecast.", "Scenarios are built from assumptions."]),
    mcq("EV/Sales is most useful when…", ["Comparing companies with low or negative earnings within the same sector", "Valuing banks", "Comparing companies across unrelated sectors", "Earnings are stable and high"], 0,
        "Sales exist even when profits do not, but margins must be considered within a sector.",
        [None, "Bank revenue is not comparable this way.", "Margins differ too much across sectors.", "Then earnings-based multiples are better."], level="hard"),
])

MODULES = [products, technical, valuation]
