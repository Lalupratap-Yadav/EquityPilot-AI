"""Advanced level: discounted cash flow valuation, portfolio construction and risk, and equity research in practice
(including case studies built from EquityPilot's stored statements for real companies)."""
from __future__ import annotations

from .core import ILLUSTRATIVE, lesson, mcq, module, num, term, v

# ================================================================== 11. Discounted cash flow valuation
dcf = module("dcf", "Discounted cash flow valuation", "advanced",
             "Present value of cash-flow streams, FCFF and FCFE, CAPM and WACC, terminal value, building a DCF, and sensitivity and reverse DCF.", [
    lesson("dcf-pv", "Discounting a stream of cash flows",
           concept="""
The value of any asset is the present value of the cash it will produce. For a stream of cash flows, discount each one by (1 + r)^t and add them up.
A **perpetuity** pays a fixed amount for ever; a **growing perpetuity** grows at a constant rate g, which must be below the discount rate r.""",
           why="DCF valuation, bond pricing and loan maths are all this one idea applied to different cash flows.",
           formulas=["PV of a stream = Σ CF_t ÷ (1 + r)^t", "Perpetuity: PV = CF ÷ r", "Growing perpetuity: PV = CF₁ ÷ (r − g), only when g < r",
                     "Discount factor for year t = 1 ÷ (1 + r)^t"],
           example=f"""
{ILLUSTRATIVE} At a 10% discount rate:
- Cash flows of 100, 110 and 121 in years 1-3 are each worth 90.91 today, so the **PV is 272.73**.
- ₹100 a year for ever is worth 100 ÷ 0.10 = **₹1,000**.
- A cash flow of ₹104 next year, growing 4% a year for ever, is worth 104 ÷ (0.10 − 0.04) = **₹1,733**.""",
           interpret="Near cash flows count for more than distant ones. The discount rate is the return investors require for the risk; a riskier business deserves a higher rate and therefore a lower value.",
           mistakes=["Discounting year 1's cash flow by (1 + r)⁰.", "Using a nominal discount rate with real (inflation-adjusted) cash flows, or the reverse.",
                     "Applying the growing perpetuity formula when g is at or above r."],
           application="The DCF calculator and the Valuation Lab discount each year's forecast and show the discount factor used.",
           revision=["PV = Σ CF_t ÷ (1 + r)^t.", "Perpetuity = CF ÷ r.", "Growing perpetuity = CF₁ ÷ (r − g), g < r.", "Match nominal with nominal, real with real."],
           check=[
               num("What is the present value of ₹100 received in one year and another ₹100 in two years, at 10%?", 173.55,
                   "Discount each cash flow separately.", "100 ÷ 1.1 + 100 ÷ 1.21 = 90.91 + 82.64 = ₹173.55", unit="₹", tolerance=0.1, verify=v("pv_stream", [100, 100], 0.10)),
               num("A cash flow of ₹50 a year continues for ever. At a discount rate of 8%, what is it worth today, in ₹?", 625, "Use the perpetuity formula.", "50 ÷ 0.08 = ₹625",
                   unit="₹", level="easy", verify=v("gordon", 50, 0.08, 0.0)),
           ],
           calculators=("dcf",),
           terms=("Present value",
                  term("Perpetuity", "A cash flow that continues for ever; a growing perpetuity grows at a constant rate.", formula="PV = CF ÷ r; growing: CF₁ ÷ (r − g)",
                       aliases=("growing perpetuity", "annuity"), related=("Terminal value", "Present value")),
                  term("Discount rate", "The required rate of return used to convert future cash flows into present value.",
                       aliases=("required return", "hurdle rate", "discount factor", "required rate of return"), related=("WACC", "Present value"))),
           ),
    lesson("dcf-fcf", "Free cash flow to the firm (FCFF) and to equity (FCFE)",
           concept="""
**FCFF** is the cash available to all providers of capital, lenders and shareholders, after tax on operating profit and after reinvestment in fixed assets and working capital.
**FCFE** is the cash left for shareholders after interest and net debt flows. Discount FCFF at the **WACC** to get enterprise value; discount FCFE at the **cost of equity** to get equity value directly.""",
           why="A DCF values cash, not accounting profit. Using the right cash flow with the matching discount rate is what makes the result consistent.",
           formulas=["FCFF = EBIT × (1 − tax rate) + D&A − Capex − ΔNWC", "FCFE = FCFF − Interest × (1 − tax rate) + Net borrowing",
                     "FCFF at WACC → enterprise value; FCFE at cost of equity → equity value"],
           example=f"""
{ILLUSTRATIVE} EBIT ₹200 crore, tax 25%, D&A ₹50 crore, capex ₹90 crore, working capital up ₹40 crore:
- **FCFF** = 200 × 0.75 + 50 − 90 − 40 = **₹70 crore**.
- With interest of ₹20 crore and ₹30 crore of debt repaid: **FCFE** = 70 − 20 × 0.75 − 30 = **₹25 crore**.""",
           interpret="FCFF suits most companies, especially when leverage will change. FCFE suits companies with stable leverage and lenders such as banks. Negative FCFF in heavy investment years is normal for a growing business, as long as the investment earns more than its cost of capital.",
           mistakes=["Discounting FCFF at the cost of equity (or FCFE at WACC).", "Deducting interest when computing FCFF.", "Forgetting the investment in working capital.",
                     "Using reported 'free cash flow' (CFO − capex) as FCFF without checking where interest is classified."],
           application="The Valuation Lab offers both FCFF and FCFE models, built from a company's stored statements.",
           revision=["FCFF = EBIT(1 − t) + D&A − capex − ΔNWC.", "FCFE = FCFF − interest(1 − t) + net borrowing.", "FCFF ↔ WACC; FCFE ↔ cost of equity.",
                     "Growth needs reinvestment, which lowers near-term FCF."],
           check=[
               num("EBIT ₹400 crore, tax 25%, D&A ₹60 crore, capex ₹120 crore, increase in working capital ₹30 crore. What is FCFF, in ₹ crore?", 210,
                   "Tax the operating profit, add back D&A, subtract reinvestment.", "400 × 0.75 + 60 − 120 − 30 = 300 + 60 − 150 = ₹210 crore", unit="₹ crore",
                   verify=v("fcff", 400, 0.25, 60, 120, 30)),
               mcq("FCFF should be discounted at…", ["The cost of equity", "The WACC", "The risk-free rate", "The inflation rate"], 1,
                   "FCFF belongs to all capital providers, so it is discounted at the blended cost of all capital.",
                   ["The cost of equity matches FCFE.", None, "The risk-free rate ignores business risk.", "Inflation is not a required return."]),
           ],
           calculators=("dcf",), tools=(("valuation", "Run FCFF and FCFE models on a real company."),),
           terms=(term("FCFF", "Free cash flow to the firm: cash available to lenders and shareholders after tax and reinvestment.",
                       formula="FCFF = EBIT(1 − t) + D&A − Capex − ΔNWC", aliases=("free cash flow to the firm", "free cash flow to firm", "unlevered free cash flow"),
                       related=("FCFE", "WACC", "DCF")),
                  term("FCFE", "Free cash flow to equity: cash available to shareholders after interest and net borrowing.",
                       formula="FCFE = FCFF − Interest(1 − t) + Net borrowing", aliases=("free cash flow to equity", "levered free cash flow"), related=("FCFF", "CAPM"))),
           ),
    lesson("dcf-wacc", "Cost of capital: CAPM and WACC",
           concept="""
The **cost of equity** is usually estimated with **CAPM**: Ke = Rf + β × ERP. In India the risk-free rate (Rf) is commonly the 10-year G-sec yield; the equity risk premium (ERP) is a judgement, not an official number.
The **cost of debt** is the company's borrowing rate, which is tax-deductible, so its after-tax cost is Kd × (1 − t). **WACC** blends the two using market-value weights.""",
           why="The discount rate is one of the two or three inputs that move a DCF the most. A disciplined, documented estimate matters more than false precision.",
           formulas=["Ke = Rf + β × ERP", "After-tax cost of debt = Kd × (1 − t)", "WACC = We × Ke + Wd × Kd × (1 − t), with market-value weights We + Wd = 1"],
           example=f"""
{ILLUSTRATIVE}
- Rf 7%, β 1.1, ERP 6%: **Ke = 7% + 1.1 × 6% = 13.6%**.
- Kd 9% and tax 25%: after-tax cost of debt = **6.75%**.
- Equity 80% and debt 20% of capital at market values: **WACC = 0.8 × 13.6% + 0.2 × 6.75% = 12.23%**.""",
           interpret="Small changes in WACC move the value a lot. Betas estimated from past prices carry estimation error, and the ERP is a judgement, so show the sensitivity rather than defending one decimal place.",
           mistakes=["Using book-value weights instead of market values.", "Using the pre-tax cost of debt.", "Mixing a US dollar risk-free rate with rupee cash flows.",
                     "Treating beta as precise."],
           application="The WACC calculator shows each step; the Valuation Lab lets you set Rf, beta, ERP and the debt weight and see the effect on value.",
           revision=["CAPM: Ke = Rf + β × ERP.", "Debt is cheaper after tax: Kd(1 − t).", "WACC uses market-value weights.", "Show sensitivity to the discount rate."],
           check=[
               num("Rf 7%, beta 0.9, equity risk premium 7%. What is the cost of equity, in %?", 13.3, "Apply CAPM.", "7% + 0.9 × 7% = 7% + 6.3% = 13.3%", unit="%",
                   verify=v("capm", 0.07, 0.9, 0.07, unit="%")),
               num("Ke 14%, Kd 10%, tax 25%, equity 70% of capital. What is the WACC, in %?", 12.05, "Weight the after-tax costs.",
                   "0.7 × 14% + 0.3 × 10% × 0.75 = 9.8% + 2.25% = 12.05%", unit="%", verify=v("wacc", 0.14, 0.10, 0.25, 0.7, unit="%")),
           ],
           calculators=("wacc",), tools=(("valuation", "Change the discount-rate inputs and watch the value move."),),
           sources=("rbi",),
           terms=("WACC", "CAPM", "Beta", "Risk-free rate",
                  term("Cost of debt", "The rate a company pays on its borrowings; its after-tax cost is Kd × (1 − t) because interest is tax-deductible.",
                       formula="After-tax Kd = Kd × (1 − t)", aliases=("kd", "post-tax cost of debt", "after-tax cost of debt"), related=("WACC",))),
           ),
    lesson("dcf-terminal", "Terminal value and the Gordon Growth Model",
           concept="""
A DCF forecasts cash flows explicitly for 5-10 years and then captures everything after that with a **terminal value (TV)**.
The **Gordon Growth Model** (perpetuity growth) assumes cash flows grow at a constant rate g for ever: TV at year N = FCF_N × (1 + g) ÷ (r − g). An alternative is an exit multiple (for example EV/EBITDA) applied to year-N figures.""",
           why="The terminal value is often more than half of the total value, so its assumptions deserve the most scrutiny.",
           formulas=["TV_N = FCF_N × (1 + g) ÷ (r − g)", "PV of TV = TV_N ÷ (1 + r)^N",
                     "g must be below r, and should not exceed long-run nominal GDP growth"],
           example=f"""
{ILLUSTRATIVE} Year-5 FCF ₹100 crore, g = 5%, WACC = 11%:
- TV = 100 × 1.05 ÷ (0.11 − 0.05) = **₹1,750 crore**.
- PV of TV = 1,750 ÷ 1.11⁵ = 1,750 ÷ 1.685 = **₹1,039 crore**.
- With WACC at 10%, raising g from 4% to 5% lifts the TV multiple from 17.3x to 21.0x of FCF_N, about **+21%**.""",
           interpret="The gap r − g drives the terminal value: the closer g gets to r, the more the value explodes. Long-run growth should be modest because no company can outgrow the economy for ever.",
           mistakes=["Setting g at or above the discount rate.", "Using a terminal growth rate above long-run nominal GDP growth.",
                     "Discounting the TV by N + 1 years instead of N, or forgetting to discount it at all.", "Assuming high growth for ever without the reinvestment it needs."],
           application="The DCF calculator reports the terminal value's share of enterprise value, and refuses a growth rate at or above the discount rate.",
           revision=["TV = FCF_N(1 + g) ÷ (r − g).", "Discount TV by N years.", "g < r and ≤ long-run nominal GDP growth.", "TV often dominates the value."],
           check=[
               num("FCF in the final forecast year is ₹200 crore, terminal growth 4%, discount rate 12%. What is the terminal value at that year, in ₹ crore?", 2600,
                   "Grow the final cash flow one year, then divide by (r − g).", "200 × 1.04 ÷ (0.12 − 0.04) = 208 ÷ 0.08 = ₹2,600 crore", unit="₹ crore",
                   verify=v("gordon", 208, 0.12, 0.04)),
               mcq("With WACC at 10%, terminal growth rises from 4% to 5%. The terminal value…", ["Rises by about 21%", "Falls", "Does not change", "Becomes negative"], 0,
                   "1.05 ÷ 0.05 = 21.0 against 1.04 ÷ 0.06 = 17.3: about 21% higher.",
                   [None, "Higher growth raises the TV.", "TV depends directly on g.", "TV stays positive while g < r."], level="hard", kind="numerical"),
           ],
           calculators=("dcf",),
           terms=("Terminal growth",
                  term("Terminal value", "The value of all cash flows after the explicit forecast period, usually by perpetuity growth or an exit multiple.",
                       formula="TV = FCF_N × (1 + g) ÷ (r − g)", aliases=("tv", "exit multiple", "continuing value"), related=("Terminal growth", "DCF"))),
           ),
    lesson("dcf-build", "Building a DCF step by step",
           concept="""
1. Forecast revenue and margins for 5-10 years from the business's drivers.
2. Turn them into FCFF each year (EBIT after tax, plus D&A, minus capex and working-capital investment).
3. Estimate the WACC.
4. Estimate a terminal value.
5. Discount everything to today: that is **enterprise value**.
6. Move from EV to **equity value**: subtract net debt and minority interests, add non-operating assets.
7. Divide by diluted shares for **value per share**, and compare it with the price as a range, not a point.""",
           why="A DCF forces every assumption into the open, which is its real strength: you can see exactly what has to be true for a valuation to hold.",
           formulas=["EV = Σ FCFF_t ÷ (1 + WACC)^t + TV ÷ (1 + WACC)^N", "Equity value = EV − Net debt − Minority interest + Non-operating assets",
                     "Value per share = Equity value ÷ Diluted shares"],
           example=f"""
{ILLUSTRATIVE} FCF ₹100 crore today, growing 10% a year for 5 years; WACC 12%; terminal growth 5%; net debt ₹200 crore; 10 crore shares.
| Year | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| FCF | 110.0 | 121.0 | 133.1 | 146.4 | 161.1 |
| PV at 12% | 98.2 | 96.5 | 94.7 | 93.0 | 91.4 |
- Sum of PVs = 473.8. TV = 161.1 × 1.05 ÷ 0.07 = 2,415.8, worth 1,370.8 today.
- **EV = 1,844.6**; equity = 1,844.6 − 200 = **1,644.6**; **value per share = ₹164.5**.
- The terminal value is **74%** of EV.""",
           interpret="With three-quarters of the value in the terminal value, the long-run assumptions matter most. Compare the result with the market price and ask what the price implies (reverse DCF, next lesson).",
           mistakes=["High growth with low reinvestment (growth is not free).", "Counting cash twice (in FCF and again in the bridge).", "Using basic instead of diluted shares.",
                     "Forgetting minority interests.", "Presenting one number as 'the' value."],
           application="Build this exact model in the DCF calculator, then run a full DCF on a real company in the Valuation Lab.",
           revision=["Forecast → FCFF → discount → EV.", "EV − net debt − minorities = equity.", "÷ diluted shares = value per share.", "Report a range and the TV share."],
           check=[
               num("EV ₹5,000 crore, net debt ₹1,000 crore, 20 crore diluted shares. What is the value per share, in ₹?", 200, "Bridge from EV to equity, then divide.",
                   "(5,000 − 1,000) ÷ 20 = ₹200", unit="₹", level="easy"),
               num("PV of forecast FCF is ₹600 crore and PV of terminal value ₹1,400 crore. What share of EV comes from the terminal value, in %?", 70,
                   "Divide PV of TV by total EV.", "1,400 ÷ (600 + 1,400) = 70%", unit="%", level="easy"),
           ],
           calculators=("dcf",), tools=(("valuation", "Run a full DCF on a real company."),),
           terms=("DCF",
                  term("Equity bridge", "The step from enterprise value to equity value: subtract net debt and minority interests, add non-operating assets.",
                       aliases=("ev to equity bridge", "equity value", "value per share"), related=("Enterprise value", "DCF"))),
           ),
    lesson("dcf-sensitivity", "Sensitivity, scenarios and reverse DCF",
           concept="""
A **sensitivity table** shows value per share across a grid of the inputs that matter most, usually WACC and terminal growth. **Scenarios** change several assumptions together (bear, base, bull). A **reverse DCF** turns the question round: what growth does today's price imply?""",
           why="They replace false precision with an honest range and show which assumptions you must get right.",
           rules=["Sensitivity: vary WACC and terminal growth (or margins) one grid step at a time.", "Scenarios: keep each case internally consistent (growth, margins and reinvestment together).",
                  "Reverse DCF: solve for the growth that makes the DCF value equal the current price, then compare it with history and peers.",
                  "Common errors: g ≥ WACC, growth without reinvestment, ignoring dilution, and ranges too narrow to be useful."],
           example=f"""
{ILLUSTRATIVE} Value per share (₹) for the model in the previous lesson:
| WACC ↓ / g → | 4% | 5% | 6% |
|---|---|---|---|
| 11% | 170.7 | 195.9 | 231.3 |
| 12% | 146.2 | **164.5** | 188.8 |
| 13% | 127.2 | 140.9 | 158.5 |
One percentage point on WACC moves the base value from ₹164.5 to between ₹140.9 and ₹195.9.""",
           interpret="If the price sits near the bull corner of the table, the market is already paying for an optimistic outcome. If a reverse DCF needs growth far above the company's history, expectations are demanding.",
           mistakes=["Ranges that are too narrow to show real uncertainty.", "Treating the base case as the truth.", "Moving WACC and growth independently when they are linked through reinvestment and risk.",
                     "Reading the table as a set of forecasts rather than 'what if' answers."],
           application="The Valuation Lab shows a WACC × growth sensitivity table and bear, base and bull scenarios for any tracked company.",
           revision=["Sensitivity grid: WACC × g.", "Scenarios: consistent sets of assumptions.", "Reverse DCF: growth implied by the price.", "Report the range."],
           check=[
               mcq("A reverse DCF shows the price needs 25% annual cash-flow growth for 10 years; the company grew 8% a year historically. What does this suggest?",
                   ["Market expectations look demanding compared with history", "The share is certainly undervalued", "WACC must be zero", "DCF does not apply to this company"], 0,
                   "The price embeds growth roughly three times the historical rate.",
                   [None, "Demanding expectations point the other way, and nothing is certain.", "WACC is an input, not a conclusion.", "Reverse DCF works for any cash-generating business."], kind="case"),
               num("A DCF gives ₹180 per share at a WACC of 12% and ₹150 at 13%. By what percentage does the value fall?", 16.67, "Compare the change with the starting value.",
                   "(150 − 180) ÷ 180 = −16.67%, so a fall of 16.67%", unit="%"),
           ],
           tools=(("valuation", "Open the sensitivity table and scenarios."),),
           terms=("Sensitivity analysis", "Scenario analysis",
                  term("Reverse DCF", "Working backwards from the share price to the growth or margins it implies.", aliases=("implied growth", "market-implied growth"),
                       related=("DCF", "Sensitivity analysis"))),
           ),
], test=[
    mcq("Rf = 7%, β = 1.2, ERP = 6%. The cost of equity is…", ["13.0%", "14.2%", "8.2%", "15.4%"], 1, "7% + 1.2 × 6% = 14.2%.",
        ["That uses a beta of 1.0.", None, "That multiplies beta by 1% instead of the ERP.", "That uses an ERP of 7%."], kind="numerical", verify=v("capm", 0.07, 1.2, 0.06, unit="%", expect=14.2)),
    mcq("If WACC rises with everything else unchanged, DCF value per share…", ["Rises", "Falls", "Is unchanged", "Becomes negative"], 1, "Future cash flows are discounted more heavily.",
        ["A higher discount rate lowers present values.", None, "The discount rate affects every present value.", "Values stay positive with positive cash flows."]),
    mcq("The Gordon growth terminal value is undefined when…", ["g > 0", "WACC > g", "WACC ≤ g", "FCFF > 0"], 2, "The formula divides by (WACC − g), which must be positive.",
        ["Positive growth is normal.", "That is the required condition.", None, "Positive cash flow is normal."], level="medium"),
    num("Cash flows of ₹200 in year 1 and ₹300 in year 2. What is their present value at 10%, in ₹?", 429.75, "Discount each year separately.",
        "200 ÷ 1.1 + 300 ÷ 1.21 = 181.82 + 247.93 = ₹429.75", unit="₹", tolerance=0.1, verify=v("pv_stream", [200, 300], 0.10)),
    num("FCFF ₹500 crore, interest ₹80 crore, tax 25%, net new borrowing ₹40 crore. What is FCFE, in ₹ crore?", 480, "Subtract after-tax interest, add net borrowing.",
        "500 − 80 × 0.75 + 40 = 500 − 60 + 40 = ₹480 crore", unit="₹ crore", verify=v("fcfe", 500, 80, 0.25, 40)),
    mcq("Which assumption is most clearly unrealistic in a rupee DCF of a mature Indian company?", ["Terminal growth of 15% a year for ever", "Terminal growth of 5%", "A WACC of 12%", "A five-year explicit forecast"], 0,
        "No company can grow far faster than the economy for ever; terminal growth should not exceed long-run nominal GDP growth.",
        [None, "5% is within typical long-run ranges.", "12% is a plausible rupee WACC.", "Five years is a common forecast period."], level="medium"),
    mcq("In your DCF the terminal value is 92% of EV. What should you do?", ["Check the long-term assumptions and show sensitivity, because almost all the value rests on them", "Nothing; this is ideal", "Delete the terminal value", "Raise WACC to 30%"], 0,
        "When TV dominates, the result is only as good as the long-run assumptions.",
        [None, "A very high share deserves scrutiny.", "Removing TV ignores all cash after the forecast period.", "Inflating WACC to change the answer is not analysis."], level="hard", kind="case"),
    num("EV ₹12,000 crore, net debt ₹2,000 crore, minority interest ₹500 crore, 50 crore shares. What is equity value per share, in ₹?", 190, "Bridge from EV to equity.",
        "(12,000 − 2,000 − 500) ÷ 50 = 9,500 ÷ 50 = ₹190", unit="₹"),
    mcq("FCFE should be discounted at…", ["The cost of equity", "The WACC", "The cost of debt", "Zero"], 0, "FCFE belongs to shareholders, so it is discounted at their required return.",
        [None, "WACC matches FCFF.", "Debt holders are already paid in FCFE.", "Money has a time value."]),
])

# ================================================================== 12. Portfolio construction and risk
portfolio = module("portfolio", "Portfolio construction and risk", "advanced",
                   "Diversification, correlation and asset allocation; standard deviation, beta and drawdown; Sharpe, Treynor and Jensen's alpha; position sizing and time horizon.", [
    lesson("portfolio-diversification", "Diversification, correlation and asset allocation",
           concept="""
Total risk has two parts. **Systematic (market) risk** affects almost all shares (interest rates, inflation, the economic cycle) and cannot be diversified away. **Unsystematic (specific) risk** comes from a company or industry and can be reduced by holding many different investments.
**Correlation** (from −1 to +1) measures how two assets move together; the lower it is, the more combining them reduces risk. **Asset allocation**, the split between equity, debt, gold and cash, is the main driver of a portfolio's overall risk.""",
           why="Diversification is the one way to reduce risk without necessarily giving up expected return.",
           formulas=["Portfolio return = Σ wᵢ × Rᵢ", "Two-asset risk: σp = √(w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρσ₁σ₂)", "Effective number of holdings = 1 ÷ Σ wᵢ²"],
           example=f"""
{ILLUSTRATIVE} Half in each of two assets, each with 20% volatility:
| Correlation | Portfolio volatility |
|---|---|
| +1.0 | 20.0% (no benefit) |
| +0.3 | 16.1% |
| 0.0 | 14.1% |
| −1.0 | 0% |""",
           interpret="Diversification helps most when holdings do not move together. Correlations tend to rise in crises, exactly when protection is needed, so asset allocation (including debt) matters as well as the number of shares.",
           mistakes=["Owning many shares in one sector and calling it diversified.", "Holding so many positions that you cannot follow them.",
                     "Assuming correlations stay stable.", "Ignoring asset allocation and focusing only on share selection."],
           application="Portfolio shows sector concentration and the effective number of holdings; Virtual Invest lets you build a diversified practice portfolio.",
           revision=["Systematic risk stays; specific risk diversifies away.", "Low correlation = bigger diversification benefit.", "Effective N = 1 ÷ Σw².",
                     "Asset allocation drives overall risk."],
           check=[
               num("60% in asset A (volatility 25%) and 40% in asset B (volatility 10%), correlation 0.2. What is the portfolio volatility, in %?", 16.28,
                   "Use the two-asset formula.", "√(0.36 × 0.0625 + 0.16 × 0.01 + 2 × 0.6 × 0.4 × 0.2 × 0.25 × 0.10) = √0.0265 = 16.28%", unit="%", level="hard",
                   tolerance=0.1, verify=v("two_asset_sd", 0.6, 0.25, 0.10, 0.2, unit="%")),
               mcq("Owning 12 different private-sector bank shares gives you…", ["Little diversification, because they share the same sector risks", "Full diversification", "No risk at all", "Lower systematic risk"], 0,
                   "Holdings in one sector are highly correlated, so specific risk at the sector level remains.",
                   [None, "Same-sector holdings move together.", "Every equity portfolio carries risk.", "Systematic risk cannot be diversified away."], kind="case"),
           ],
           calculators=("diversification", "portfolio"), tools=(("portfolio", "Check concentration and sector exposure."), ("invest", "Build a diversified practice portfolio.")),
           terms=(term("Diversification", "Spreading money across investments that do not move together, to reduce specific risk.",
                       aliases=("diversify", "diversified", "spread risk"), related=("Correlation", "Systematic and unsystematic risk")),
                  term("Correlation", "A measure from −1 to +1 of how two assets' returns move together.", aliases=("correlation coefficient", "covariance"),
                       related=("Diversification",)),
                  term("Asset allocation", "Dividing a portfolio between asset classes such as equity, debt, gold and cash.", aliases=("allocation",),
                       related=("Diversification", "Rebalancing")),
                  term("Systematic and unsystematic risk", "Systematic risk affects the whole market and cannot be diversified away; unsystematic risk is specific to a company or industry and can be.",
                       aliases=("systematic risk", "unsystematic risk", "market risk", "specific risk", "idiosyncratic risk", "diversifiable risk"),
                       related=("Beta", "Diversification"))),
           ),
    lesson("portfolio-risk", "Measuring risk: standard deviation, beta and maximum drawdown",
           concept="""
- **Standard deviation** of returns (volatility) measures total risk: how widely returns swing.
- **Beta** measures sensitivity to the market, the systematic part of risk: β 1.3 means the share has tended to move 1.3 times the market.
- **Maximum drawdown** is the worst fall from a peak to a later trough: the loss you would actually have felt.""",
           why="Different measures capture different kinds of pain. Volatility describes swings; drawdown shows how bad things got and how long recovery can take.",
           formulas=["Volatility = standard deviation of returns (daily figures × √252 to annualise)", "β = Cov(Rᵢ, Rm) ÷ Var(Rm)",
                     "Maximum drawdown = (Trough − Peak) ÷ Peak, the worst over the period", "Gain needed to recover = 1 ÷ (1 + drawdown) − 1"],
           example=f"""
{ILLUSTRATIVE}
- β 1.3 and the market falls 10%: on average the share would fall about **13%**.
- A portfolio peaks at ₹12 lakh and falls to ₹9 lakh: **drawdown −25%**, and it then needs a **33.3%** gain just to get back to ₹12 lakh.""",
           interpret="Beta is backward-looking and changes over time. Standard deviation treats upside and downside swings alike. Drawdowns show why avoiding large losses matters: the deeper the fall, the bigger the gain needed to recover.",
           mistakes=["Treating beta as fixed.", "Looking only at volatility and not at drawdowns.", "Forgetting that recovery needs a larger percentage gain than the loss."],
           application="Company pages show volatility and maximum drawdown; Portfolio shows your holdings' risk figures.",
           revision=["Volatility = total risk; beta = market risk.", "Drawdown = peak-to-trough loss.", "−50% needs +100% to recover.", "All are backward-looking."],
           check=[
               num("A share rose to ₹500 and then fell to ₹350. What was the drawdown, in %? (Enter a negative number.)", -30, "Measure the fall from the peak.", "(350 − 500) ÷ 500 = −30%",
                   unit="%", level="easy", verify=v("drawdown", 500, 350, unit="%")),
               num("After a 50% fall, what percentage gain is needed to get back to the starting value?", 100, "Recovery is measured from the lower base.", "1 ÷ 0.5 − 1 = 100%",
                   unit="%"),
           ],
           tools=(("portfolio", "See your portfolio's risk figures."),),
           terms=("Beta", "Volatility",
                  term("Maximum drawdown", "The largest fall from a peak to a subsequent trough over a period.", formula="(Trough − Peak) ÷ Peak",
                       aliases=("drawdown", "max drawdown", "peak to trough"), related=("Volatility",)),
                  term("Standard deviation", "A measure of how widely returns spread around their average; the usual measure of volatility.",
                       aliases=("sd", "sigma", "std dev"), related=("Volatility", "Sharpe ratio"))),
           ),
    lesson("portfolio-riskadjusted", "Risk-adjusted returns: Sharpe, Treynor and Jensen's alpha",
           concept="""
Comparing returns without considering risk misleads. **Risk-adjusted return** measures put return and risk together:
- **Sharpe ratio**: excess return per unit of total risk (standard deviation).
- **Treynor ratio**: excess return per unit of systematic risk (beta).
- **Jensen's alpha**: the return above what CAPM predicts for the portfolio's beta.""",
           why="A fund that earned more by taking far more risk may not have done a better job. These ratios are standard in fund factsheets and research.",
           formulas=["Sharpe = (Rp − Rf) ÷ σp", "Treynor = (Rp − Rf) ÷ βp", "Jensen's alpha = Rp − [Rf + βp × (Rm − Rf)]"],
           example=f"""
{ILLUSTRATIVE} Rf = 7%, market return Rm = 12%:
| | Return | σ | β | Sharpe | Treynor | Alpha |
|---|---|---|---|---|---|---|
| Fund A | 16% | 20% | 1.2 | 0.45 | 7.5% | +3.0% |
| Fund B | 13% | 12% | 0.8 | 0.50 | 7.5% | +2.0% |
A earned more and has the higher alpha; B earned more per unit of total risk (higher Sharpe).""",
           interpret="Use the Sharpe ratio for a whole portfolio (total risk matters) and Treynor or alpha for a well-diversified portfolio (only systematic risk matters). All are backward-looking and depend on the period measured.",
           mistakes=["Comparing ratios measured over different periods.", "Using Treynor for an undiversified portfolio.", "Calling a short spell of positive alpha 'skill'.",
                     "Forgetting that the risk-free rate used changes the results."],
           application="Portfolio reports return and risk for your holdings; compare a fund's factsheet ratios with its peers over the same period.",
           revision=["Sharpe: per unit of total risk.", "Treynor: per unit of beta.", "Alpha: return above CAPM's prediction.", "Same period, same Rf, or the comparison fails."],
           check=[
               num("Portfolio return 14%, risk-free rate 6%, beta 0.8. What is the Treynor ratio, in %?", 10, "Excess return divided by beta.", "(14% − 6%) ÷ 0.8 = 10%",
                   unit="%", verify=v("treynor", 0.14, 0.06, 0.8, unit="%")),
               num("Portfolio return 15%, Rf 7%, beta 1.1, market return 13%. What is Jensen's alpha, in %?", 1.4, "Subtract CAPM's required return.",
                   "15% − [7% + 1.1 × (13% − 7%)] = 15% − 13.6% = 1.4%", unit="%", level="hard", verify=v("jensen_alpha", 0.15, 0.07, 1.1, 0.13, unit="%")),
           ],
           calculators=("portfolio",), tools=(("portfolio", "See your portfolio's return and risk."),),
           terms=(term("Sharpe ratio", "Excess return per unit of total risk.", formula="Sharpe = (Rp − Rf) ÷ σp", aliases=("sharpe",),
                       related=("Treynor ratio", "Risk-adjusted return")),
                  term("Treynor ratio", "Excess return per unit of systematic risk (beta).", formula="Treynor = (Rp − Rf) ÷ βp", aliases=("treynor",),
                       related=("Sharpe ratio", "Beta")),
                  term("Jensen's alpha", "The return a portfolio earned above what CAPM predicts for its beta.", formula="α = Rp − [Rf + β(Rm − Rf)]",
                       aliases=("alpha", "jensen", "jensens alpha", "jensen alpha"), related=("CAPM", "Treynor ratio")),
                  term("Risk-adjusted return", "Return measured against the risk taken to earn it.", aliases=("risk adjusted return", "risk-adjusted returns"),
                       related=("Sharpe ratio",))),
           ),
    lesson("portfolio-sizing", "Position sizing, time horizon and rebalancing",
           concept="""
**Position sizing** decides how much goes into each holding so that no single mistake can sink the portfolio. One method limits the loss if a stop-loss is hit to a set share of capital; another caps each holding at a maximum weight.
**Time horizon** matters: money needed soon should not sit in volatile assets. **Rebalancing** brings the portfolio back to its target allocation after markets move.""",
           why="You cannot control returns, but you can control how much a single error costs and whether the portfolio's risk matches its purpose.",
           formulas=["Shares to buy = (Capital × Risk per trade) ÷ (Entry price − Stop-loss price)", "Position weight = (Shares × Entry price) ÷ Portfolio value"],
           example=f"""
{ILLUSTRATIVE}
- Capital ₹10,00,000; you accept a 1% loss (₹10,000) if wrong. Entry ₹500, stop-loss ₹460: risk per share ₹40, so buy **250 shares**, a ₹1,25,000 position (12.5% of capital).
- Rebalancing: the target is 60% equity and 40% debt; after a rally equity is 70%. Selling some equity and adding debt restores 60/40.""",
           interpret="Sizing manages the downside you can control. Matching the horizon prevents forced selling at the wrong time. Rebalancing builds in 'trim what has risen, add to what has fallen', although it has costs and tax consequences.",
           mistakes=["Putting a large share of the portfolio in one idea.", "Averaging down without a plan or a limit.", "Ignoring liquidity when sizing positions in small companies.",
                     "Never rebalancing, or rebalancing so often that costs pile up."],
           application="Practise sizing and rebalancing with virtual money in Virtual Invest, and check real weights in Portfolio.",
           revision=["Size from the loss you accept, not the gain you hope for.", "Short horizon = low volatility assets.", "Rebalance back to target periodically.",
                     "Watch liquidity in small companies."],
           check=[
               num("Capital ₹5,00,000, risk per trade 2%, entry ₹250, stop-loss ₹230. How many shares should you buy?", 500,
                   "Divide the rupee risk by the risk per share.", "(5,00,000 × 0.02) ÷ (250 − 230) = 10,000 ÷ 20 = 500 shares", unit="shares", tolerance=0.01,
                   verify=v("position_size", 500000, 0.02, 250, 230)),
               mcq("Money you need for a house down payment in one year is best kept in…", ["Low-risk, liquid instruments such as deposits or liquid funds", "Small-company shares", "Options", "A single share"], 0,
                   "A short horizon cannot absorb a large fall in value.",
                   [None, "They can fall sharply within a year.", "Options can lose their entire value.", "One share concentrates risk."], kind="case"),
           ],
           tools=(("invest", "Practise position sizing with virtual money."), ("portfolio", "Check your real weights.")),
           terms=(term("Position sizing", "Deciding how much to invest in each holding so that a single loss stays within a chosen limit.",
                       formula="Shares = (Capital × Risk %) ÷ (Entry − Stop)", aliases=("position size", "risk per trade"), related=("Stop-loss order", "Diversification")),
                  term("Rebalancing", "Restoring a portfolio to its target allocation after market moves.", aliases=("rebalance",), related=("Asset allocation",)),
                  term("Investment horizon", "How long money can stay invested before it is needed.", aliases=("time horizon", "holding period"), related=("Asset allocation",))),
           ),
], test=[
    mcq("Which risk can be reduced by diversification?", ["Systematic risk", "Unsystematic risk", "Interest-rate risk for all shares", "Inflation"], 1,
        "Company-specific risk diversifies away; market risk does not.",
        ["Market-wide risk remains however many shares you hold.", None, "Rate changes affect the whole market.", "Inflation affects the whole market."]),
    mcq("A share with a beta of 1.5 is expected to move, on average…", ["50% less than the market", "In line with the market", "50% more than the market", "Opposite to the market"], 2,
        "Beta 1.5 implies 1.5 times the market's moves on average.", ["That is beta 0.5.", "That is beta 1.0.", None, "That needs a negative beta."]),
    mcq("Portfolio return 15%, risk-free rate 6.5%, volatility 17%. The Sharpe ratio is…", ["0.50", "0.88", "1.15", "0.38"], 0, "(15 − 6.5) ÷ 17 = 0.50.",
        [None, "That divides by a smaller risk figure.", "That uses the return without subtracting Rf.", "That subtracts too much."], kind="numerical",
        verify=v("sharpe", 0.15, 0.065, 0.17, expect=0.5)),
    mcq("Four equally weighted holdings have an effective number of…", ["1", "2", "4", "16"], 2, "Σw² = 4 × 0.25² = 0.25; 1 ÷ 0.25 = 4.",
        ["That would be a single holding.", "That would be two equal holdings.", None, "That inverts the calculation incorrectly."], level="medium", kind="numerical"),
    mcq("High promoter pledging is a risk because…", ["It increases dividends", "Lenders may sell pledged shares if the price falls", "It reduces the free float", "It is illegal"], 1,
        "Margin calls on pledged shares can trigger forced selling.",
        ["Pledging has nothing to do with dividends.", None, "Pledged shares are still part of promoter holdings.", "Pledging is legal but must be disclosed."]),
    num("50% earns 12%, 30% earns 8% and 20% earns −5%. What is the portfolio return, in %?", 7.4, "Weight each return.", "0.5 × 12% + 0.3 × 8% + 0.2 × (−5%) = 6% + 2.4% − 1% = 7.4%",
        unit="%", verify=v("portfolio_return", [0.5, 0.3, 0.2], [0.12, 0.08, -0.05], unit="%")),
    mcq("Two assets have a correlation of −0.2. Combining them…", ["Can reduce portfolio volatility substantially", "Always raises risk", "Has no effect", "Guarantees a profit"], 0,
        "Assets that tend to move in opposite directions offset each other's swings.",
        [None, "Low correlation reduces risk.", "Correlation below 1 always gives some benefit.", "Nothing guarantees profit."]),
    mcq("Fund X returned more than fund Y but has a lower Sharpe ratio. This means…", ["X took more total risk per unit of excess return", "X is always the better fund", "Y lost money", "Sharpe ratios cannot be compared"], 0,
        "Sharpe scales excess return by volatility; X's extra return came with proportionally more risk.",
        [None, "Higher return alone does not make it better.", "Nothing says Y lost money.", "They can be compared over the same period."], level="hard", kind="case"),
])

# ================================================================== 13. Equity research in practice
analysis = module("analysis", "Equity research in practice", "advanced",
                  "The research process and SEBI's rules for research analysts, earnings-quality checks and red flags, and case studies with real Indian companies.", [
    lesson("analysis-process", "The research process and SEBI's rules for research analysts",
           concept="""
Professional equity research follows a sequence:
1. **Understand the business**: products, customers, competitors, industry structure, management.
2. **Analyse the financials**: growth, margins, returns, balance sheet and cash flows; check accounting quality.
3. **Forecast**: revenue drivers, margins, capex and working capital.
4. **Value**: relative (multiples against peers and history) and intrinsic (DCF), with sensitivity and scenarios.
5. **Assess risks**: business, financial, governance and regulatory.
6. **Communicate**: a clear, sourced report with disclosures.""",
           why="A good process makes conclusions checkable. It is also what SEBI's rules and the NISM Series XV (Research Analyst) certification expect of analysts.",
           rules=["Persons who publish research reports or buy, sell or hold recommendations to the public must generally be registered with SEBI as research analysts (subject to the exemptions in the regulations).",
                  "Reports must disclose conflicts of interest, for example whether the analyst or associates own 1% or more of the subject company, compensation received from it, or service as its officer or director.",
                  "Under the SEBI (Research Analysts) Regulations, 2014, an analyst should not deal in a covered security from 30 days before to 5 days after publishing a report on it, or trade against their own recommendation.",
                  "Recommendations need a reasonable basis, and research records must be kept.",
                  "The regulations have been amended since 2014: read the current text on sebi.gov.in."],
           example="""
_Outline of a hypothetical research note:_
- **Business**: what the company sells, to whom, and why customers choose it.
- **Financials**: five years of growth, margins, ROCE and cash conversion, with sources.
- **Forecasts**: drivers and assumptions in a table.
- **Valuation**: a range from DCF scenarios and peer multiples.
- **Risks**: what would make the view wrong.
- **Disclosures**: holdings, conflicts and data sources.""",
           interpret="The process matters more than the conclusion: a good report shows its evidence and assumptions and says what would change the view. EquityPilot is an educational tool, not a registered research analyst, so it shows evidence, calculations and assumptions and leaves the judgement to you.",
           mistakes=["Starting from a target price and working backwards.", "Skipping risks, or listing generic ones.", "Copying management guidance into forecasts unchecked.",
                     "Leaving out disclosures and data sources."],
           application="The Research page brings together a company's data; Reports builds a sourced PDF research report; the AI Assistant answers questions with citations.",
           revision=["Business → financials → forecasts → valuation → risks → report.", "Recommendations to the public need SEBI RA registration.",
                     "Disclose holdings of 1% or more and other conflicts.", "2014 rules: no dealing from 30 days before to 5 days after a report."],
           check=[
               mcq("A research report should disclose…", ["Whether the analyst or associates own 1% or more of the subject company", "The analyst's home address", "Only the target price", "Nothing, if the analyst is experienced"], 0,
                   "Ownership above the threshold is a standard conflict-of-interest disclosure.",
                   [None, "Personal addresses are not a disclosure item.", "Disclosures cover conflicts, not just the target.", "Disclosure rules apply to everyone."], kind="rule"),
               mcq("Under the 2014 regulations, around a report's publication an analyst should not deal in the covered security…", ["From 30 days before to 5 days after", "Only on the publication day", "For one full year", "At no time; there is no restriction"], 0,
                   "The regulations set a 30-day window before and a 5-day window after publication.",
                   [None, "The window is wider.", "The window is narrower.", "A restriction exists."], level="medium", kind="rule"),
           ],
           tools=(("assistant", "Ask research questions with cited sources."),),
           sources=("sebi", "nism"),
           terms=("Research analyst",
                  term("Research report", "A written analysis of a company or security, with evidence, forecasts, valuation, risks and disclosures.",
                       aliases=("research note", "equity research", "initiating coverage"), related=("Research analyst",))),
           ),
    lesson("analysis-quality", "Earnings quality and red flags",
           concept="""
Earnings quality asks whether reported profits are real and repeatable. Checks that catch most problems:
- **Cash conversion**: does CFO keep pace with PAT?
- **Working capital**: are receivables or inventory growing much faster than sales?
- **One-offs**: is profit propped up by exceptional gains or other income?
- **Accounting changes**: new depreciation lives, revenue-recognition changes, capitalised costs.
- **Related-party transactions**, **contingent liabilities** and the **auditor's report** (qualifications or emphasis of matter).
- **Funding**: repeated equity or debt raising despite reported profits; rising promoter pledges.
Screening scores such as the Piotroski F-score and the Altman Z-score combine several of these.""",
           why="Large investor losses are often preceded by visible warning signs in the statements and notes.",
           formulas=["Cash conversion = CFO ÷ PAT (consistently below about 0.8 deserves a closer look)", "Accruals ≈ PAT − CFO",
                     "Compare receivable growth with revenue growth"],
           example="""
_A hypothetical company:_
- PAT grows 25% a year for three years while CFO stays flat.
- Receivable days rise from 60 to 110.
- It raises equity twice in that period.
- The auditor adds an emphasis of matter about whether a large loan to a related party can be recovered.
Any one of these could be innocent; together they are a serious warning.""",
           interpret="No single flag proves wrongdoing, and many have innocent explanations. Look for patterns over several years and read the notes to the accounts, where the explanations (or their absence) sit.",
           mistakes=["Skipping the notes to accounts and the auditor's report.", "Relying on 'adjusted' profit figures chosen by management.", "Dismissing a pattern because each flag alone looks small."],
           application="Company pages run rule-based risk checks, the Piotroski F-score and the Altman Z-score; upload annual reports in Documents to search the notes and auditor's report.",
           revision=["Profit should turn into cash.", "Watch receivables and inventory against sales.", "Read the notes and the auditor's report.", "Patterns matter more than single flags."],
           check=[
               num("PAT is ₹300 crore and CFO ₹120 crore. What is the cash conversion ratio (CFO ÷ PAT)?", 0.4, "Divide CFO by PAT.", "120 ÷ 300 = 0.4x", unit="x", level="easy",
                   kind="statement"),
               mcq("Which combination is the strongest warning sign?", ["Rising receivable days, flat CFO, and an auditor's emphasis of matter on a related-party loan", "Steady margins and rising CFO", "A dividend increase backed by free cash flow", "Timely results with a clean audit report"], 0,
                   "Profit without cash, slower collections and auditor concern together point to an earnings-quality problem.",
                   [None, "These are signs of health.", "Cash-backed dividends are a good sign.", "These are signs of good governance."], level="medium", kind="statement"),
           ],
           tools=(("company:TATASTEEL.NS", "See rule-based risk checks, Piotroski and Altman scores."), ("documents", "Search the notes and auditor's report of an annual report.")),
           terms=("Piotroski F-score", "Altman Z-score", "Cash conversion",
                  term("Accruals", "The part of profit not yet received in cash; large or rising accruals can signal lower earnings quality.", formula="Accruals ≈ PAT − CFO",
                       related=("Cash conversion",)),
                  term("Contingent liability", "A possible obligation that depends on a future event, such as a lawsuit or a guarantee, disclosed in the notes.",
                       aliases=("contingent liabilities", "guarantees given"), related=("Balance sheet",)),
                  term("Emphasis of matter", "A paragraph in the auditor's report drawing attention to an important issue; a qualified opinion is more serious.",
                       aliases=("qualified opinion", "audit qualification", "auditor qualification", "modified opinion"), related=("Annual report",))),
           ),
    lesson("analysis-cases", "Case studies: reading real Indian companies",
           concept="""
This lesson applies the toolkit to five real listed companies from different sectors, using the financial statements EquityPilot has stored for them. For each one the case study shows the company, the financial year, the data source and when it was fetched, whether the basis (standalone or consolidated) is stated, and every ratio worked out step by step.
Reported figures are facts from the named source; ratios are EquityPilot's calculations from those figures; the reading notes are educational interpretation, not a view on the shares.""",
           why="Seeing how the same ratios look across business models (IT services, consumer goods, steel, banking and a conglomerate) is the fastest way to learn which ones matter where.",
           rules=["IT services (TCS): margins, cash conversion and ROE matter; P/B says little about an asset-light business.",
                  "Consumer goods (Hindustan Unilever): margins, ROCE, working capital and the steadiness of growth.",
                  "Steel (Tata Steel): a cyclical, capital-heavy business; look at capex, debt, interest coverage and how profits move across the cycle.",
                  "Bank (HDFC Bank): NIM, asset quality, capital adequacy, ROA and P/B; debt to equity, the current ratio and EV/EBITDA do not apply.",
                  "Conglomerate (Reliance Industries): segment mix, consolidated figures, capex and debt."],
           example="""
**Real data.** Pick a company in the case study below. Its figures come from EquityPilot's stored statements (a third-party source) for the financial year shown. Always check important numbers against the annual report on NSE or BSE; the case study links to them.""",
           interpret="Compare companies within a sector, not across sectors: a steel maker's margins and a software company's margins reflect different business models, not better or worse management. Third-party data can contain errors and does not state its basis, which is why the source and links are shown.",
           mistakes=["Comparing ratios across unrelated sectors.", "Treating third-party figures as audited.", "Mixing standalone and consolidated figures.",
                     "Reading one year in isolation for a cyclical company."],
           application="Open each company's page for multi-year history, use Compare for peers in the same sector, and upload the annual report in Documents to check the numbers.",
           revision=["Match the ratios to the business model.", "Facts (source) ≠ calculations ≠ interpretation.", "Verify against the annual report.",
                     "Cyclicals: judge across the cycle."],
           check=[
               mcq("Which set of measures suits HDFC Bank best?", ["NIM, asset quality, capital adequacy, ROA and P/B", "EV/EBITDA and the current ratio", "Inventory days and gross margin", "Debt to equity and interest coverage"], 0,
                   "A bank's business is lending, so its ratios measure lending margins, loan quality and capital.",
                   [None, "Neither is meaningful for a bank.", "A bank holds no inventory.", "Borrowing is a bank's raw material."], kind="case"),
               mcq("Why might Tata Steel's P/E look misleadingly low at the top of a steel cycle?", ["Peak profits inflate EPS just before they fall", "Steel companies do not report EPS", "P/E is only for banks", "The share count changes every day"], 0,
                   "For cyclicals, the P/E is lowest when earnings are at their peak.",
                   [None, "They report EPS like any listed company.", "P/E is used widely.", "Share counts change only with corporate actions."], level="medium", kind="case"),
           ],
           case=("TCS.NS", "HINDUNILVR.NS", "TATASTEEL.NS", "HDFCBANK.NS", "RELIANCE.NS"),
           tools=(("compare", "Compare companies within the same sector."), ("documents", "Check the numbers against an annual report.")),
           sources=("nse", "bse"),
           terms=(),
           ),
], test=[
    mcq("Under the SEBI (Research Analysts) Regulations, 2014, a person publishing buy or sell recommendations to the public generally must…",
        ["Be registered with SEBI as a research analyst", "Only hold a demat account", "Be a member of NSE", "Be a chartered accountant"], 0,
        "Registration with SEBI is required unless an exemption in the regulations applies.",
        [None, "A demat account is not a licence.", "Exchange membership is for brokers.", "Professional qualifications do not replace registration."], kind="rule"),
    mcq("A research report must disclose if the analyst or associates own at least what share of the subject company?", ["0.1%", "1%", "5%", "10%"], 1,
        "The 1% ownership threshold is a standard disclosure item.", ["The threshold is higher.", None, "The threshold is lower.", "The threshold is lower."], kind="rule"),
    mcq("Which step should come BEFORE valuation in a research process?", ["Publishing the report", "Understanding the business and analysing the financials", "Setting the target price", "Trading the share"], 1,
        "Valuation rests on an understanding of the business and its financials.",
        ["Publishing comes last.", None, "A target is an output of valuation, not an input.", "Trading is not part of research."]),
    mcq("Why do research firms separate research from investment banking?", ["To reduce costs", "To manage conflicts of interest", "Because SEBI bans investment banking", "To speed up reports"], 1,
        "Information barriers stop banking relationships from influencing research views.",
        ["Cost is not the reason.", None, "Investment banking is legal.", "Speed is not the reason."]),
    mcq("The 2014 regulations restrict analysts from dealing in a covered security…", ["For 1 day before and after a report", "From 30 days before to 5 days after a report", "For 90 days before a report only", "Never"], 1,
        "The window runs from 30 days before to 5 days after publication.",
        ["The window is wider.", None, "The window also covers the days after.", "A restriction exists."], kind="rule"),
    mcq("PAT grows 30% a year but CFO is flat and receivable days have doubled. What is the right next step?", ["Read the notes on revenue recognition and receivables, and check the auditor's report", "Assume the profits are fine", "Look only at the P/E", "Ignore cash flow"], 0,
        "The pattern points to an earnings-quality question that the notes and audit report can help answer.",
        [None, "The cash flow evidence contradicts that.", "Valuation does not answer a quality question.", "Cash flow is the key evidence here."], level="medium", kind="statement"),
    mcq("In a case study, a figure comes from a third-party data provider and the basis is not stated. What should you do before relying on it?", ["Check it against the company's annual report or exchange filing", "Assume it is consolidated", "Assume it is standalone", "Nothing; all data providers are audited"], 0,
        "Primary sources settle both the number and its basis.",
        [None, "Assumptions about basis can be wrong.", "Assumptions about basis can be wrong.", "Third-party data is not audited."], kind="case"),
    mcq("For a capital-heavy cyclical business, which approach is most sensible?", ["Judge returns and valuation across a full cycle, not at one point", "Use only the latest quarter", "Value it on P/B like a bank", "Ignore debt"], 0,
        "Profits swing with the cycle, so single-point ratios mislead.",
        [None, "One quarter is too short.", "Bank methods do not fit.", "Debt is a major risk in downturns."], level="hard", kind="case"),
])

MODULES = [dcf, portfolio, analysis]
