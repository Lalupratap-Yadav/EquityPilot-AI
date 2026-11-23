"""Beginner level: money and returns, the economy, how the Indian market works, corporate actions and investor
protection. Regulatory facts were checked against the official sources listed on each lesson (see core.REVIEWED)."""
from __future__ import annotations

from .core import ILLUSTRATIVE, lesson, mcq, module, num, term, v

# ================================================================== 1. Money, interest and returns
money = module("money", "Money, interest and returns", "beginner",
               "Time value of money, simple and compound interest, inflation and real returns, and the link between risk and return.", [
    lesson("money-tvm", "Time value of money",
           concept="""
A rupee today is worth more than a rupee received later, because today's rupee can be invested to earn a return, and because inflation and uncertainty reduce what future money is worth.
**Future value (FV)** grows an amount forward at a rate of return. **Present value (PV)** discounts a future amount back to today.""",
           why="Every investment compares money at different dates: a fixed deposit's maturity amount, a bond's coupons, a company's future cash flows. You cannot compare ₹1 lakh today with ₹1.5 lakh in five years without the time value of money.",
           formulas=["FV = PV × (1 + r)^n", "PV = FV ÷ (1 + r)^n", "r = annual rate as a decimal (8% = 0.08); n = number of years"],
           example=f"""
{ILLUSTRATIVE}
- You invest ₹10,000 at 8% a year for 3 years: FV = 10,000 × 1.08³ = 10,000 × 1.259712 = **₹12,597**.
- Going the other way, ₹12,597 received in 3 years is worth today, at 8%: PV = 12,597 ÷ 1.259712 = **₹10,000**.""",
           interpret="PV falls when the discount rate rises or when you have to wait longer. The discount rate is your opportunity cost: what you could earn elsewhere at similar risk.",
           mistakes=["Typing 8 instead of 0.08 for 8%.", "Mixing a monthly rate with a number of years.",
                     "Comparing amounts received at different dates without discounting them.",
                     "Forgetting that a higher discount rate means a lower present value."],
           application="Use it to compare a deposit with a bond, judge a 'pay ₹X now or ₹Y later' offer, or understand DCF valuation (Advanced level), which is the time value of money applied to a company's future cash flows.",
           revision=["Money today is worth more than the same money later.", "FV = PV × (1 + r)^n compounds forward.",
                     "PV = FV ÷ (1 + r)^n discounts back.", "Higher rate or longer wait means lower PV."],
           check=[
               num("What is the future value of ₹50,000 invested for 2 years at 10% a year, compounded annually?", 60500,
                   "Compounding adds interest on the first year's interest too.", "50,000 × 1.10² = 50,000 × 1.21 = ₹60,500",
                   unit="₹", level="easy", verify=v("fv", 50000, 0.10, 2)),
               mcq("If the discount rate rises, the present value of a fixed future amount…", ["Rises", "Falls", "Stays the same", "Becomes equal to the future value"], 1,
                   "PV = FV ÷ (1 + r)^n: a larger r makes the denominator bigger, so PV falls.",
                   ["A higher rate enlarges the denominator, so PV cannot rise.", None, "PV depends on r, so it must change.",
                    "PV equals FV only when the rate or the time is zero."]),
           ],
           calculators=("interest",), tools=(("valuation", "See discounting at work in a full DCF."),),
           terms=(term("Time value of money", "The idea that money available now is worth more than the same amount in future, because it can earn a return.",
                       formula="FV = PV × (1 + r)^n", aliases=("tvm",), related=("Present value", "Future value", "Compound interest")),
                  term("Present value", "Today's value of an amount to be received in future, found by discounting it at a required rate of return.",
                       formula="PV = FV ÷ (1 + r)^n", example="₹12,597 due in 3 years at 8% is worth ₹10,000 today.",
                       aliases=("pv", "discounting", "discounted value"), related=("Future value", "DCF")),
                  term("Future value", "What an amount invested today grows to at a given rate of return after a number of periods.",
                       formula="FV = PV × (1 + r)^n", example="₹10,000 at 8% for 3 years grows to ₹12,597.", aliases=("fv",),
                       related=("Present value", "Compound interest"))),
           ),
    lesson("money-interest", "Simple and compound interest",
           concept="""
**Simple interest** is paid only on the original principal. **Compound interest** is paid on the principal plus interest already earned, so growth speeds up over time.
How often interest is added (yearly, quarterly, monthly) also matters: the more frequent the compounding, the higher the **effective annual rate**.""",
           why="Deposits, bonds, loans and long-term investing all run on compounding. Over long periods the gap between simple and compound growth becomes very large, and it works against you on debt too.",
           formulas=["Simple interest = P × r × n", "Compound amount = P × (1 + r/m)^(m × n), where m = compounding periods a year",
                     "Effective annual rate = (1 + r/m)^m − 1", "Rule of 72: years to double ≈ 72 ÷ rate in %"],
           example=f"""
{ILLUSTRATIVE} ₹1,00,000 at 9% for 5 years:
- Simple interest: 1,00,000 × 0.09 × 5 = ₹45,000, so you end with **₹1,45,000**.
- Compounded yearly: 1,00,000 × 1.09⁵ = 1,00,000 × 1.538624 = **₹1,53,862**. The extra ₹8,862 is interest on interest.
- Rule of 72: 72 ÷ 9 = about 8 years to double (exact answer: 8.04 years).""",
           interpret="The longer the horizon, the more compounding dominates. Compare deposits by their effective annual rate, not the headline rate, when compounding frequencies differ.",
           mistakes=["Comparing rates with different compounding frequencies without converting them to effective annual rates.",
                     "Using the rule of 72 at high rates, where it is less accurate.",
                     "Assuming past compound returns of shares will continue; equity returns are not fixed like interest.",
                     "Forgetting that loan balances (for example on credit cards) compound against you."],
           application="Bank fixed deposits in India often compound quarterly, so compare effective yields across banks. The same maths explains how a systematic investment plan grows and how loan interest builds up.",
           revision=["Simple: interest on principal only.", "Compound: interest on interest; growth accelerates.",
                     "More frequent compounding means a higher effective rate.", "Rule of 72 gives a quick doubling time."],
           check=[
               num("₹20,000 earns simple interest at 6% a year for 4 years. How much interest is earned?", 4800,
                   "Simple interest ignores interest on interest.", "20,000 × 0.06 × 4 = ₹4,800", unit="₹", level="easy",
                   verify=v("simple_interest", 20000, 0.06, 4)),
               mcq("Using the rule of 72, roughly how long does money take to double at 12% a year?", ["4 years", "6 years", "8 years", "12 years"], 1,
                   "72 ÷ 12 = 6 years. The exact answer, ln 2 ÷ ln 1.12, is 6.1 years.",
                   ["That would need about 18% a year.", None, "That is the doubling time at about 9%.", "That is the doubling time at about 6%."],
                   kind="numerical", verify=v("years_to_double", 0.12, expect=6.1)),
               mcq("Same 8% headline rate: which gives the most after one year?", ["Yearly compounding", "Quarterly compounding", "Simple interest", "They are all the same"], 1,
                   "Quarterly compounding adds interest four times, giving an effective rate of 8.24% against 8.00% for yearly compounding.",
                   ["Yearly compounding gives exactly 8.00%.", None, "Over one year simple interest equals yearly compounding (8.00%).",
                    "Compounding frequency changes the effective rate."], level="medium", kind="numerical",
                   verify=v("effective_rate", 0.08, 4, unit="%", expect=8.24)),
           ],
           calculators=("interest",),
           terms=(term("Compound interest", "Interest calculated on the principal plus all interest already added, so the balance grows faster over time.",
                       formula="A = P × (1 + r/m)^(m × n)", example="₹1,00,000 at 9% for 5 years compounded yearly grows to ₹1,53,862.",
                       aliases=("compounding", "compounded"), related=("Simple interest", "Effective annual rate", "Time value of money")),
                  term("Simple interest", "Interest calculated only on the original principal.", formula="SI = P × r × n",
                       example="₹20,000 at 6% for 4 years earns ₹4,800.", related=("Compound interest",)),
                  term("Effective annual rate", "The true annual rate once compounding within the year is included.",
                       formula="EAR = (1 + r/m)^m − 1", example="12% compounded monthly is an effective 12.68% a year.",
                       aliases=("effective rate", "annual percentage yield", "effective annual yield"), related=("Compound interest",)),
                  term("Rule of 72", "A shortcut for doubling time: divide 72 by the annual rate in percent.", formula="Years to double ≈ 72 ÷ rate %",
                       example="At 9% money doubles in about 8 years.", related=("Compound interest",))),
           ),
    lesson("money-inflation", "Inflation, nominal and real returns",
           concept="""
**Inflation** is the general rise in prices, so each rupee buys less over time. Your **nominal return** is how much your money grows in rupees; your **real return** is the growth in what it can buy, after inflation.
India's retail inflation is measured by the Consumer Price Index (CPI), published monthly by the National Statistics Office of the Ministry of Statistics and Programme Implementation (MoSPI).""",
           why="An investment can grow in rupees while losing purchasing power. Real returns, after inflation and tax, are what build wealth.",
           formulas=["Real return = (1 + nominal return) ÷ (1 + inflation) − 1", "Quick approximation: real ≈ nominal − inflation",
                     "Purchasing power of ₹A after n years = A ÷ (1 + inflation)^n"],
           example=f"""
{ILLUSTRATIVE}
- A deposit pays 7% and inflation is 5%: real return = 1.07 ÷ 1.05 − 1 = **1.9%** (the approximation gives 2%).
- If tax takes 30% of the interest, the after-tax return is 4.9%, and the real return becomes 1.049 ÷ 1.05 − 1 = **−0.1%**: purchasing power falls slightly.
- At 6% inflation, ₹1 lakh in 10 years buys what **₹55,839** buys today (1,00,000 ÷ 1.06¹⁰).""",
           interpret="A positive real return means your purchasing power grows. Inflation also drives interest rates: when inflation rises, RBI may raise rates, which affects bond prices and share valuations.",
           mistakes=["Judging 'safe' returns without subtracting inflation.", "Ignoring tax, which can turn a small real return negative.",
                     "Using the approximation when rates are high; the exact formula is more accurate.",
                     "Planning a long-term goal in today's rupees without inflating the target."],
           application="Compare deposit and bond yields with the latest CPI inflation from MoSPI, and inflate long-term goals (education, retirement) before deciding how much to save.",
           revision=["Nominal = growth in rupees; real = growth in purchasing power.", "Real = (1 + nominal) ÷ (1 + inflation) − 1.",
                     "Tax and inflation together can make 'safe' returns negative in real terms.", "CPI (MoSPI) measures retail inflation in India."],
           check=[
               num("Nominal return 10%, inflation 6%. What is the real return using the exact formula, in %?", 3.77,
                   "The exact formula divides growth factors rather than subtracting rates.", "1.10 ÷ 1.06 − 1 = 0.0377 = 3.77%",
                   unit="%", verify=v("real_return", 0.10, 0.06, unit="%")),
               mcq("An investment grew 5% in a year when inflation was 6%. Its real return was…", ["Positive", "About −1%", "Exactly 11%", "Zero"], 1,
                   "1.05 ÷ 1.06 − 1 = −0.94%, about −1%: the money grew but bought less.",
                   ["Inflation was higher than the return, so the real return is negative.", None, "Inflation is subtracted, not added.",
                    "The real return is zero only when the return equals inflation."], kind="numerical"),
           ],
           calculators=("real-return",), tools=(("news", "Follow CPI inflation releases and RBI commentary."),),
           sources=("mospi", "rbi"),
           terms=(term("Inflation", "The general rise in prices over time, which reduces the purchasing power of money.",
                       aliases=("cpi", "consumer price index", "retail inflation"), related=("Real return", "Repo rate")),
                  term("Real return", "Return after removing the effect of inflation: the growth in purchasing power.",
                       formula="Real = (1 + nominal) ÷ (1 + inflation) − 1", example="7% nominal with 5% inflation is a 1.9% real return.",
                       aliases=("real rate of return", "nominal return", "inflation-adjusted return"), related=("Inflation",))),
           ),
    lesson("money-risk", "Risk and return",
           concept="""
**Risk** is the chance that actual returns differ from what you expect, including losing money. Investors demand a higher **expected return** for taking more risk: the risk-return trade-off.
Expected return is the probability-weighted average of possible outcomes. Common risks: market risk, credit (default) risk, liquidity risk, inflation risk, interest-rate risk and concentration risk.""",
           why="Every product, from a government bond to a small-company share, sits somewhere on the risk-return scale. Knowing where helps you match investments to your goals and time horizon.",
           formulas=["Expected return = Σ (probability × return)", "Risk premium = Expected return − risk-free rate"],
           example=f"""
{ILLUSTRATIVE} A share might return +30% (probability 0.3), +10% (0.5) or −20% (0.2).
- Expected return = 0.3 × 30% + 0.5 × 10% + 0.2 × (−20%) = 9% + 5% − 4% = **10%**.
- A government security yields 7% with near certainty, so the share's **risk premium** is 3 percentage points.
- The 20% chance of losing a fifth of your money is the risk you are paid for.""",
           interpret="A higher expected return is not a promise: risk means the bad outcomes can happen. Spreading money across different investments and holding for longer change how much risk you actually bear (see the Portfolio module).",
           mistakes=["Believing high risk guarantees high returns.", "Judging risk only by recent returns.",
                     "Ignoring liquidity and concentration risk.", "Confusing short-term price swings with permanent loss of capital."],
           application="Compare the risk labels of products (mutual funds carry a riskometer), and try Virtual Invest to experience price swings without real money.",
           revision=["Risk = uncertainty of outcomes, including losses.", "Expected return = Σ probability × return.",
                     "Risk premium = expected return − risk-free rate.", "Higher expected return comes with higher risk, never a guarantee."],
           check=[
               num("Outcomes: +20% with probability 0.4 and +5% with probability 0.6. What is the expected return, in %?", 11,
                   "Weight each outcome by its probability.", "0.4 × 20% + 0.6 × 5% = 8% + 3% = 11%", unit="%", level="easy",
                   verify=v("expected_return", [(0.4, 0.20), (0.6, 0.05)], unit="%")),
               mcq("Which statement about risk and return is correct?",
                   ["Higher risk always gives higher returns", "Investors demand a higher expected return for bearing more risk",
                    "Government securities carry the highest risk", "Spreading money across many investments increases risk"], 1,
                   "The trade-off is about expected returns; actual returns of risky assets can be low or negative.",
                   ["Risk means outcomes can be worse, so higher returns are not guaranteed.", None,
                    "Government securities have the lowest default risk in rupee terms.", "Diversification usually reduces risk."]),
           ],
           tools=(("invest", "Practise with virtual money and watch how prices swing."),),
           terms=(term("Risk premium", "The extra expected return investors require over the risk-free rate for bearing risk.",
                       formula="Risk premium = Expected return − Risk-free rate", aliases=("equity risk premium", "erp"),
                       related=("Expected return", "CAPM")),
                  term("Expected return", "The probability-weighted average of possible returns.", formula="E(R) = Σ pᵢ × Rᵢ",
                       example="30% × 0.3 + 10% × 0.5 − 20% × 0.2 = 10%.", related=("Risk premium",)),
                  term("Risk-free rate", "The return on an investment with (practically) no default risk; in India usually proxied by government security yields.",
                       aliases=("rf", "risk free rate"), related=("CAPM", "Risk premium"))),
           ),
], test=[
    mcq("Why is ₹1,000 today worth more than ₹1,000 in a year?", ["It can be invested to earn a return", "The rupee's value is fixed by law", "Because of income tax only", "It is not; they are equal"], 0,
        "Money available now can earn interest or returns, and future money is eroded by inflation and uncertainty.",
        [None, "The rupee's purchasing power changes with inflation.", "Tax is not the reason; opportunity cost is.", "Money at different dates is not equal in value."]),
    num("What is the present value of ₹1,21,000 receivable in 2 years if the discount rate is 10%?", 100000,
        "Discount by the growth factor (1 + r)^n.", "1,21,000 ÷ 1.10² = 1,21,000 ÷ 1.21 = ₹1,00,000", unit="₹", verify=v("pv", 121000, 0.10, 2)),
    num("₹1,00,000 compounds annually at 8% for 3 years. What is the final amount?", 125971.2,
        "Each year earns 8% on the growing balance.", "1,00,000 × 1.08³ = 1,00,000 × 1.259712 = ₹1,25,971", unit="₹", tolerance=2,
        verify=v("fv", 100000, 0.08, 3)),
    mcq("The effective annual rate of 12% compounded monthly is closest to…", ["12.00%", "12.36%", "12.68%", "13.00%"], 2,
        "(1 + 0.12 ÷ 12)^12 − 1 = 1.01^12 − 1 = 12.68%.",
        ["That ignores the monthly compounding.", "That is 12% compounded half-yearly.", None, "Monthly compounding adds less than a full point."],
        level="medium", kind="numerical", verify=v("effective_rate", 0.12, 12, unit="%", expect=12.68)),
    mcq("Your real return is negative when…", ["Inflation is higher than your nominal return", "Your nominal return is higher than inflation", "Inflation is zero", "Interest is compounded"], 0,
        "Real return = (1 + nominal) ÷ (1 + inflation) − 1, which is below zero when inflation exceeds the nominal return.",
        [None, "That gives a positive real return.", "With zero inflation, real equals nominal.", "Compounding frequency does not decide the sign."]),
    mcq("By the rule of 72, about how long does money take to double at 6% a year?", ["6 years", "9 years", "12 years", "18 years"], 2,
        "72 ÷ 6 = 12 years (exact: 11.9 years).", ["That needs 12% a year.", "That needs 8% a year.", None, "That needs 4% a year."],
        kind="numerical", verify=v("years_to_double", 0.06, expect=11.9)),
    mcq("An investment's expected return is 12% and the risk-free rate is 7%. Its risk premium is…", ["5 percentage points", "19%", "1.71 times", "7%"], 0,
        "Risk premium = 12% − 7% = 5 percentage points.", [None, "The rates are subtracted, not added.", "A premium is a difference, not a ratio.", "7% is the risk-free rate itself."],
        level="medium", kind="numerical"),
    mcq("Bank A offers 7.0% compounded quarterly; bank B offers 7.1% compounded yearly. Which earns more in one year?",
        ["Bank A (7.19% effective)", "Bank B (7.10% effective)", "Both earn the same", "They cannot be compared"], 0,
        "Bank A's effective rate is (1 + 0.07 ÷ 4)^4 − 1 = 7.19%, above bank B's 7.10%.",
        [None, "Bank B's yearly compounding gives exactly 7.10%, less than 7.19%.", "The effective rates differ.",
         "Converting both to effective annual rates makes them comparable."], level="hard", kind="numerical",
        verify=v("effective_rate", 0.07, 4, unit="%", expect=7.19)),
])

# ================================================================== 2. The economy and markets
economy = module("economy", "The economy and markets", "beginner",
                 "GDP and growth, interest rates and RBI's monetary policy, and the government's fiscal policy and Budget.", [
    lesson("economy-gdp", "GDP and economic growth",
           concept="""
**GDP (gross domestic product)** is the value of all final goods and services produced in a country in a period. **Nominal GDP** uses current prices; **real GDP** removes price changes, so it shows growth in actual output.
India's GDP estimates are published by the National Statistics Office (MoSPI), quarterly and annually, and are revised as more data arrives.""",
           why="Company revenues grow with the economy: consumer demand, credit growth and investment all follow GDP. Long-run nominal GDP growth is also a ceiling for sensible long-term growth assumptions in valuation.",
           formulas=["GDP (expenditure view) = C + I + G + (X − M): consumption + investment + government spending + exports − imports",
                     "Real growth = (1 + nominal growth) ÷ (1 + GDP deflator inflation) − 1"],
           example=f"""
{ILLUSTRATIVE} Nominal GDP grows 10% and economy-wide prices (the GDP deflator) rise 4%.
- Real growth = 1.10 ÷ 1.04 − 1 = **5.8%**.
- A company growing sales at 6% in this economy is growing slower than nominal GDP: it is losing share of the economy.""",
           interpret="Real growth shows whether the economy produces more; nominal growth matters for company sales in rupees. Look at trends across several quarters, since single prints get revised.",
           mistakes=["Confusing nominal with real growth.", "Expecting stock returns to equal GDP growth; markets follow profits and valuations and move ahead of the data.",
                     "Ignoring revisions to earlier estimates.", "Comparing a quarter's year-on-year growth with an annual figure."],
           application="Cyclical sectors (banks, autos, capital goods, metals) are more sensitive to GDP than defensive ones (FMCG, pharma). Use the Industries page for sector context and the News page for GDP releases.",
           revision=["GDP = value of final goods and services produced.", "Real GDP removes inflation; nominal does not.",
                     "GDP = C + I + G + (X − M).", "Long-run nominal GDP growth caps sensible terminal growth in a DCF."],
           check=[
               mcq("Which measure shows growth in the actual volume of output?", ["Nominal GDP", "Real GDP", "Market capitalisation", "The SENSEX level"], 1,
                   "Real GDP strips out price changes, leaving volume growth.",
                   ["Nominal GDP includes price increases.", None, "Market capitalisation is the value of listed shares, not output.", "An index measures share prices, not output."]),
               mcq("In GDP = C + I + G + (X − M), what is M?", ["Money supply", "Imports", "Manufacturing output", "Market capitalisation"], 1,
                   "Imports are subtracted because they are produced abroad.",
                   ["Money supply is a monetary measure, not part of GDP.", None, "Manufacturing is part of output, not a separate term here.", "Share values are not part of GDP."]),
           ],
           tools=(("industries", "See which sectors move most with the economic cycle."), ("news", "Follow GDP and economic releases.")),
           sources=("mospi", "rbi"),
           terms=(term("GDP", "Gross domestic product: the value of all final goods and services produced in a country in a period.",
                       formula="GDP = C + I + G + (X − M)", aliases=("gross domestic product", "real gdp", "nominal gdp", "gdp growth"),
                       related=("Inflation", "Fiscal deficit")),
                  term("Cyclical and defensive sectors", "Cyclical sectors' profits rise and fall with the economy (autos, metals, capital goods); defensive sectors' demand is steadier (FMCG, pharma, utilities).",
                       aliases=("cyclical", "defensive", "cyclical stock", "defensive stock"), related=("GDP",))),
           ),
    lesson("economy-rates", "Interest rates and monetary policy",
           concept="""
**Monetary policy** is how the central bank manages interest rates and money in the economy to keep inflation in check while supporting growth.
In India, the Reserve Bank of India's six-member **Monetary Policy Committee (MPC)** sets the **policy repo rate**, the rate at which RBI lends money to banks overnight against government securities. Changes pass through, with a lag, to deposit rates, loan rates and bond yields.""",
           why="Interest rates are the price of money. They change borrowing costs, company profits (through finance costs and demand), and the discount rate used in valuations: lower rates tend to support higher valuations, higher rates the reverse.",
           rules=["The policy repo rate is set by RBI's Monetary Policy Committee (three RBI members including the Governor, and three members appointed by the Government).",
                  "India follows flexible inflation targeting: the Government sets the target with RBI for five-year periods. Since 2016 it has been 4% CPI inflation with a band of 2% to 6%; check RBI for the current framework and the latest repo rate.",
                  "RBI's other tools include the cash reserve ratio (CRR), the standing deposit facility and open market operations.",
                  "Bond prices move opposite to yields: when rates rise, existing bonds fall in price."],
           example=f"""
{ILLUSTRATIVE} A company has ₹1,000 crore of floating-rate debt and pre-tax profit of ₹50 crore.
- Its borrowing rate rises by 0.50 percentage points: extra interest = 1,000 × 0.005 = **₹5 crore** a year.
- Pre-tax profit falls to ₹45 crore, a **10%** drop, from a half-point rate move.""",
           interpret="Rate-sensitive areas include banks and NBFCs (lending margins), real estate and autos (loan-financed demand) and heavily indebted companies. Markets react to surprises: a widely expected change is often already in prices.",
           mistakes=["Thinking RBI directly sets every loan rate; banks set their own rates, linked to benchmarks.",
                     "Ignoring the lag between a policy change and its effect.", "Assuming every rate cut lifts share prices.",
                     "Confusing the repo rate (RBI lends) with deposit facilities where banks park money with RBI."],
           application="Follow RBI policy announcements in the News page (RBI section), watch bank and real-estate indices in the Market Tracker, and note that the risk-free rate in the Valuation Lab is based on government security yields.",
           revision=["MPC sets the policy repo rate.", "Inflation target: 4% CPI within 2-6% since 2016 (check RBI for the current framework).",
                     "Higher rates raise borrowing costs and discount rates.", "Bond prices fall when yields rise."],
           check=[
               mcq("Who sets India's policy repo rate?", ["SEBI", "The Ministry of Finance", "RBI's Monetary Policy Committee", "NSE"], 2,
                   "The MPC, chaired by the RBI Governor, decides the policy repo rate.",
                   ["SEBI regulates securities markets, not interest rates.", "The Government sets the inflation target with RBI but not the repo rate.", None, "NSE is a stock exchange."], kind="rule"),
               mcq("If market interest rates rise, what typically happens to the prices of existing bonds?", ["They rise", "They fall", "They do not change", "They double"], 1,
                   "Existing bonds pay fixed coupons, so their prices fall until their yields match the new, higher rates.",
                   ["Prices rise when rates fall, not when they rise.", None, "Fixed-coupon bond prices respond to rate changes.", "Price changes are proportional to duration, never a fixed doubling."]),
           ],
           tools=(("news", "Read RBI policy announcements and circulars."), ("markets", "Watch how bank and real-estate stocks react.")),
           sources=("rbi",),
           terms=(term("Repo rate", "The rate at which RBI lends money to banks overnight against government securities; India's main policy rate.",
                       aliases=("policy rate", "repo", "policy repo rate", "mpc", "monetary policy committee"), related=("Monetary policy", "Inflation")),
                  term("Monetary policy", "The central bank's management of interest rates and liquidity to keep inflation in check while supporting growth.",
                       aliases=("rbi policy", "rate cut", "rate hike"), related=("Repo rate", "Fiscal policy")),
                  term("Cash reserve ratio", "The share of deposits banks must keep as cash balances with RBI.", aliases=("crr",), related=("Monetary policy",))),
           ),
    lesson("economy-fiscal", "Fiscal policy and the Budget",
           concept="""
**Fiscal policy** is the government's use of spending, taxes and borrowing. The **Union Budget**, presented each year (on 1 February in recent years), sets out receipts, expenditure and the **fiscal deficit**: the gap the government fills by borrowing, mainly through government securities (G-secs).""",
           why="Budgets change taxes (for example on capital gains or company profits), spending on infrastructure and subsidies, and how much the government borrows, which affects bond yields and interest rates across the economy.",
           formulas=["Fiscal deficit = Total expenditure − (Revenue receipts + Non-debt capital receipts)", "Fiscal deficit (% of GDP) = Fiscal deficit ÷ Nominal GDP"],
           example=f"""
{ILLUSTRATIVE} Round numbers, not actual Budget figures:
- Expenditure ₹50 lakh crore; revenue receipts ₹33 lakh crore; non-debt capital receipts (loan recoveries, disinvestment) ₹1 lakh crore.
- Fiscal deficit = 50 − (33 + 1) = **₹16 lakh crore**.
- With nominal GDP of ₹330 lakh crore, that is 16 ÷ 330 = **4.8% of GDP**.""",
           interpret="Larger deficits mean more government borrowing, which can push up bond yields and crowd out private borrowers. Capital spending (roads, railways) supports sectors such as cement, steel and capital goods; tax changes directly affect investor returns.",
           mistakes=["Confusing fiscal policy (Government) with monetary policy (RBI).", "Reacting to headlines without reading the Budget details.",
                     "Treating budget estimates as actual outcomes; estimates are revised and actuals come later.",
                     "Assuming every announcement takes effect immediately."],
           application="Read the documents on indiabudget.gov.in, watch sector reactions in the Market Tracker and Industries pages, and track the 10-year G-sec yield, which feeds the risk-free rate in valuations.",
           revision=["Fiscal policy = government spending, taxes and borrowing.", "Fiscal deficit = expenditure − (revenue + non-debt capital receipts).",
                     "Deficits are funded mainly by G-sec borrowing.", "Higher borrowing can push yields up."],
           check=[
               num("Expenditure ₹40 lakh crore, revenue receipts ₹28 lakh crore, non-debt capital receipts ₹2 lakh crore. What is the fiscal deficit, in ₹ lakh crore?", 10,
                   "Borrowing fills the gap between spending and non-debt receipts.", "40 − (28 + 2) = ₹10 lakh crore", unit="₹ lakh crore", level="easy"),
               mcq("Which is a tool of fiscal policy?", ["Changing the repo rate", "Changing income-tax rates", "Changing the cash reserve ratio", "RBI's open market operations"], 1,
                   "Taxes and government spending are fiscal tools; the others are RBI's monetary tools.",
                   ["The repo rate is monetary policy (RBI).", None, "CRR is a monetary tool of RBI.", "Open market operations are conducted by RBI."]),
           ],
           tools=(("markets", "See how sectors react on Budget day."), ("valuation", "The risk-free rate in a DCF comes from G-sec yields.")),
           sources=("budget", "rbi"),
           terms=(term("Fiscal deficit", "The gap between the government's total expenditure and its receipts other than borrowing.",
                       formula="Fiscal deficit = Expenditure − (Revenue receipts + Non-debt capital receipts)",
                       aliases=("fiscal policy", "budget deficit", "union budget"), related=("Government security", "Monetary policy")),),
           ),
], test=[
    mcq("Real GDP growth differs from nominal GDP growth because it…", ["Removes the effect of price changes", "Adds indirect taxes", "Includes share prices", "Excludes services"], 0,
        "Real GDP is measured at constant prices.", [None, "Taxes are not the difference.", "Share prices are not part of GDP.", "Both include services."]),
    num("Nominal GDP grew 11% and the GDP deflator rose 5%. What was real growth (exact formula), in %?", 5.71,
        "Divide the growth factors.", "1.11 ÷ 1.05 − 1 = 0.0571 = 5.71%", unit="%", verify=v("real_return", 0.11, 0.05, unit="%")),
    mcq("An increase in the repo rate is most likely to…", ["Lower borrowing costs", "Raise borrowing costs over time", "Increase government spending", "Cut income tax"], 1,
        "Banks' funding costs rise and loan rates follow with a lag.",
        ["A hike makes borrowing dearer, not cheaper.", None, "Government spending is fiscal policy.", "Tax rates are set in the Budget."]),
    mcq("Which company is most exposed to rising interest rates?", ["One with large floating-rate borrowings", "One with no debt and large cash balances", "A company that just split its shares", "One that pays a steady dividend"], 0,
        "Floating-rate interest costs rise directly with rates.", [None, "A cash-rich company may even earn more interest.", "A split changes share count, not rate exposure.", "Dividends do not create rate exposure."],
        level="medium", kind="case"),
    num("A company's ₹2,000 crore floating-rate loan reprices 0.75 percentage points higher. What is the extra annual interest, in ₹ crore?", 15,
        "Multiply the debt by the rate change.", "2,000 × 0.0075 = ₹15 crore", unit="₹ crore"),
    mcq("The Union Budget is mainly an instrument of…", ["Monetary policy", "Fiscal policy", "Securities regulation", "Exchange rate targeting"], 1,
        "It sets government spending, taxes and borrowing.", ["Monetary policy is RBI's domain.", None, "SEBI regulates securities markets.", "The Budget does not target the exchange rate."]),
    mcq("Why can a large fiscal deficit push bond yields up?", ["More government borrowing competes for the same savings", "It lowers tax rates automatically", "It forces RBI to cut rates", "It reduces GDP by definition"], 0,
        "Heavy borrowing raises the supply of government bonds, so investors demand higher yields.",
        [None, "A deficit does not change tax law.", "RBI's decisions are independent and aimed at inflation.", "The deficit is not subtracted from GDP."], level="hard"),
    mcq("Which sector is usually considered the most defensive in an economic slowdown?", ["Capital goods", "FMCG (consumer staples)", "Real estate", "Metals"], 1,
        "Demand for everyday consumer products is relatively steady through the cycle.",
        ["Capital goods orders fall when investment slows.", None, "Property demand depends on credit and confidence.", "Metal demand and prices are highly cyclical."], level="medium"),
])

# ================================================================== 3. How the Indian stock market works
markets = module("markets", "How the Indian stock market works", "beginner",
                 "Who does what in the market, primary and secondary markets, accounts and KYC, orders, settlement, circuit limits and indices.", [
    lesson("markets-structure", "Who's who: SEBI, exchanges, clearing and depositories",
           concept="""
- **SEBI** regulates the securities market.
- **Stock exchanges**, mainly **NSE** and **BSE**, run the trading platforms.
- **Clearing corporations** (NSE Clearing and Indian Clearing Corporation) settle trades and guarantee settlement.
- **Depositories**, **NSDL** and **CDSL**, hold shares electronically; you reach them through a **Depository Participant (DP)**.
- **Stock brokers** registered with SEBI place your orders on the exchanges.""",
           why="Knowing who does what tells you where your shares and money sit, whom to complain to, and why you do not need to trust the unknown person on the other side of your trade.",
           rules=["SEBI was set up in 1988 and given statutory powers by the SEBI Act, 1992.",
                  "NSE and BSE are nationwide exchanges; their benchmark indices are NIFTY 50 and SENSEX.",
                  "The clearing corporation becomes the buyer to every seller and the seller to every buyer (novation), guaranteeing settlement.",
                  "Brokers and DPs must be registered with SEBI; check registration on SEBI's website."],
           example="""
_A typical trade, step by step:_
1. You place an order to buy 10 shares through your broker's app.
2. The exchange matches it with a seller's order.
3. The clearing corporation guarantees both sides.
4. On settlement day the shares move from the seller's demat account to yours through the depository, and the money moves the other way.""",
           interpret="Because the clearing corporation guarantees settlement, counterparty risk is minimal. Your shares are held in your own demat account, not by the broker, so check your depository statements as well as your broker's.",
           mistakes=["Thinking the exchange holds your shares; depositories do.", "Confusing the regulator (SEBI) with the exchanges.",
                     "Dealing with unregistered 'brokers' or tipsters.", "Ignoring contract notes and statements."],
           application="Before opening an account, check that the broker and DP appear on SEBI's list of registered intermediaries. The Market Tracker shows NIFTY 50, SENSEX and sector indices.",
           revision=["SEBI regulates; NSE/BSE run trading.", "Clearing corporations guarantee settlement.",
                     "NSDL/CDSL hold shares through DPs.", "Use only SEBI-registered brokers."],
           check=[
               mcq("Which entity guarantees the settlement of trades on an exchange?", ["SEBI", "The clearing corporation", "The company whose shares are traded", "Your bank"], 1,
                   "Through novation the clearing corporation stands between buyer and seller.",
                   ["SEBI regulates but does not guarantee trades.", None, "The company is not party to secondary-market trades.", "Banks move money but do not guarantee trades."], kind="rule"),
               mcq("Your shares in electronic form are held…", ["By the stock exchange", "With a depository, through your DP", "By SEBI", "By your broker in its own name"], 1,
                   "NSDL and CDSL hold securities in investors' demat accounts, accessed through DPs.",
                   ["Exchanges provide trading, not custody.", None, "SEBI is the regulator, not a custodian.", "Shares sit in your demat account in your name."]),
           ],
           tools=(("markets", "See NIFTY 50, SENSEX and sector indices."),),
           sources=("sebi", "nse", "bse", "nsdl", "cdsl"),
           terms=(term("SEBI", "Securities and Exchange Board of India: the statutory regulator of India's securities market under the SEBI Act, 1992.",
                       aliases=("securities and exchange board of india", "sebi act"), related=("Stock exchange", "Depository")),
                  term("Stock exchange", "A regulated marketplace where securities are bought and sold; in India mainly NSE and BSE.",
                       aliases=("nse", "bse", "national stock exchange", "stock exchanges"), related=("SEBI", "Clearing corporation")),
                  term("Clearing corporation", "The entity that settles exchange trades and guarantees settlement by becoming the counterparty to both sides.",
                       aliases=("clearing house", "nse clearing", "indian clearing corporation", "novation"), related=("Settlement",)),
                  term("Depository", "An institution that holds securities in electronic form for investors; in India NSDL and CDSL.",
                       aliases=("nsdl", "cdsl", "depository participant", "dp"), related=("Demat account",))),
           ),
    lesson("markets-primary", "Primary and secondary markets, IPOs and equity shares",
           concept="""
In the **primary market** companies issue new securities to raise money: an **IPO** (first public offer, after which the shares list), an **FPO** (further public offer by a listed company), a **rights issue** (to existing shareholders) or a **QIP** (to qualified institutional buyers). In an **offer for sale (OFS)**, existing shareholders sell and the company receives nothing.
In the **secondary market** investors trade existing shares among themselves on the exchange; the company receives no money.
An **equity share** is part-ownership: voting rights, dividends when declared, and a residual claim after lenders and other creditors are paid.""",
           why="Whether an IPO raises fresh money for the business or mainly lets existing owners sell changes how you read it. Shareholders are paid last, which is why equity carries more risk than debt.",
           formulas=["Fresh-issue proceeds = New shares issued × Issue price (goes to the company)", "Market capitalisation = Share price × Shares outstanding"],
           rules=["IPOs are made through offer documents filed with SEBI (a draft red herring prospectus, then the red herring prospectus); read the objects of the issue and the risk factors.",
                  "Individual investors apply through ASBA (including UPI): the money is blocked in your bank account and debited only if shares are allotted."],
           example=f"""
{ILLUSTRATIVE} An IPO of ₹1,000 crore made up of a ₹400 crore fresh issue and a ₹600 crore offer for sale.
- Only **₹400 crore** reaches the company; ₹600 crore goes to the selling shareholders.
- After listing, the share moves from ₹300 to ₹360. The company receives nothing from this: it is secondary-market trading between investors.""",
           interpret="Heavy oversubscription shows demand, not value, and listing gains are not guaranteed. Compare the IPO valuation with listed peers and read why the money is being raised.",
           mistakes=["Treating subscription numbers as a sign of quality.", "Ignoring how much of the issue is an offer for sale.",
                     "Skipping the risk factors in the offer document.", "Confusing face value with market price."],
           application="Follow IPO and listing news on the News page and compare an IPO's valuation with listed peers in Compare.",
           revision=["Primary market: company raises money.", "Secondary market: investors trade with each other.",
                     "OFS money goes to selling shareholders, not the company.", "Equity holders are residual claimants."],
           check=[
               mcq("In an offer for sale, the money raised goes to…", ["The company", "The selling shareholders", "SEBI", "The stock exchange"], 1,
                   "An OFS transfers existing shares; the sellers receive the proceeds.",
                   ["Only a fresh issue brings money into the company.", None, "SEBI regulates but receives no proceeds.", "The exchange earns fees, not proceeds."]),
               num("An IPO has a ₹250 crore fresh issue and a ₹750 crore offer for sale. What share of the total issue goes to the company, in %?", 25,
                   "Only the fresh issue is new money for the company.", "250 ÷ (250 + 750) = 0.25 = 25%", unit="%", level="easy"),
           ],
           tools=(("news", "Track IPO filings and listing announcements."), ("compare", "Compare an IPO's valuation with listed peers.")),
           sources=("sebi", "nse", "bse"),
           terms=(term("IPO", "Initial public offer: a company's first sale of shares to the public, after which the shares are listed on an exchange.",
                       aliases=("initial public offer", "initial public offering"), related=("Offer for sale", "Primary market")),
                  term("Offer for sale", "Existing shareholders sell their shares to the public; the company receives no money.",
                       aliases=("ofs",), related=("IPO",)),
                  term("Primary market", "Where securities are issued for the first time and the issuer raises money (IPO, FPO, rights issue, QIP).",
                       aliases=("primary", "fpo", "qip", "qualified institutions placement", "follow-on public offer"), related=("Secondary market", "IPO")),
                  term("Secondary market", "Where investors trade already-issued securities with each other on an exchange.",
                       aliases=("secondary",), related=("Primary market", "Stock exchange")),
                  term("Equity share", "A unit of ownership in a company that carries voting rights, dividends when declared and a residual claim on assets.",
                       aliases=("equity share", "ordinary share", "equity shares"), related=("Market capitalisation",)),
                  term("ASBA", "Application Supported by Blocked Amount: IPO money stays in your bank account, blocked, until allotment.",
                       aliases=("upi mandate",), related=("IPO",)),
                  "Market capitalisation"),
           ),
    lesson("markets-accounts", "Demat and trading accounts, brokers and KYC",
           concept="""
To invest you need three linked accounts:
- a **trading account** with a SEBI-registered stock broker, to place orders;
- a **demat account** with a Depository Participant, to hold securities electronically at NSDL or CDSL;
- a **bank account**, for money in and out.
Opening them requires **KYC (Know Your Customer)**: identity, address and PAN checks. KYC records are kept by **KYC Registration Agencies (KRAs)**, so other SEBI-registered intermediaries can retrieve them.""",
           why="The separation protects you: shares sit in your own demat account while the broker executes orders. You should check statements from both the broker (contract notes, ledger) and the depository (Consolidated Account Statement).",
           rules=["PAN is mandatory for transacting in the securities market, with limited exemptions.",
                  "KYC completed with one SEBI-registered intermediary is recorded with a KRA.",
                  "Your broker must send a contract note for your trades, normally by email within 24 hours.",
                  "Depositories send a Consolidated Account Statement (CAS) of your holdings and transactions."],
           example="""
_A first purchase, step by step:_
1. Asha opens a trading and demat account with a broker that is also a DP, completing e-KYC with her PAN, and links her bank account.
2. She buys 5 shares.
3. The same evening she gets a contract note by email.
4. After settlement the shares appear in her demat holdings, and her next CAS from the depository lists them.""",
           interpret="If a holding appears in the broker's app but not in your CAS, ask why immediately. Never share passwords or OTPs; nobody else should trade your account without proper authorisation.",
           mistakes=["Sharing login details or OTPs with 'advisers'.", "Ignoring contract notes and CAS statements.",
                     "Signing broad authorisations (a power of attorney or DDPI) without reading what they allow.",
                     "Leaving large idle balances with a broker."],
           application="Practise placing orders with virtual money in Virtual Invest before using a real account, and track real holdings in Portfolio.",
           revision=["Trading account = orders; demat account = holdings.", "KYC is held by KRAs and reused across intermediaries.",
                     "Check every contract note and your CAS.", "Never share passwords or OTPs."],
           check=[
               mcq("Which account holds your shares in electronic form?", ["Trading account", "Demat account", "Savings account", "Margin account"], 1,
                   "Demat (dematerialised) accounts hold securities with NSDL or CDSL.",
                   ["A trading account is used to place orders.", None, "A bank account holds money, not shares.", "Margin relates to trading limits, not custody."]),
               mcq("What should you do when you receive a contract note?", ["Ignore it if the trade shows in the app", "Check it against your order and report any mismatch", "Post it on social media", "Forward it to SEBI"], 1,
                   "The contract note is the legal record of your trade; mismatches should be raised with the broker at once.",
                   ["The app is not the legal record; the contract note is.", None, "It contains personal financial details.", "SEBI does not need routine contract notes."]),
           ],
           tools=(("invest", "Practise orders with virtual money first."), ("portfolio", "Track your real holdings.")),
           sources=("sebi_investor", "nsdl", "cdsl"),
           terms=(term("Demat account", "An account with a Depository Participant that holds your securities in electronic form.",
                       aliases=("demat", "dematerialised", "dematerialized", "beneficiary account"), related=("Depository", "Trading account")),
                  term("Trading account", "An account with a stock broker used to place buy and sell orders on an exchange.",
                       aliases=("broking account",), related=("Demat account", "Stock broker")),
                  term("Stock broker", "A SEBI-registered intermediary that places orders on exchanges for clients.",
                       aliases=("broker", "brokerage"), related=("Trading account", "Contract note")),
                  term("KYC", "Know Your Customer: verification of identity, address and PAN required before investing; records are held by KYC Registration Agencies.",
                       aliases=("know your customer", "kra", "kyc registration agency", "e-kyc"), related=("Demat account",)),
                  term("Contract note", "The broker's legal confirmation of trades executed for you, with prices, charges and taxes.",
                       aliases=("contract notes",), related=("Stock broker",)),
                  term("Consolidated Account Statement", "A statement from the depository listing your holdings and transactions across demat accounts (and mutual funds).",
                       aliases=("cas",), related=("Demat account",))),
           ),
    lesson("markets-orders", "Placing orders: market, limit and stop-loss",
           concept="""
An order says what to buy or sell, how many, and on what price condition.
- **Market order**: executes immediately at the best available price.
- **Limit order**: executes only at your price or better.
- **Stop-loss order**: activates when the price reaches a trigger, to limit losses (as a limit or a market order).
Waiting orders sit in the **order book**, ranked by price and then time. The gap between the best buy price (**bid**) and the best sell price (**ask**) is the **spread**.""",
           why="Order type trades price control against certainty of execution. In thinly traded shares a market order can fill far from the last traded price.",
           rules=["Market order: certain execution, no price control.", "Limit order: price control, no certainty of execution.",
                  "Stop-loss: the trigger activates the order; a stop-loss limit order may not fill in a fast fall.",
                  "Price-time priority: the best price is matched first, then the earliest order.",
                  "The normal trading session on NSE and BSE runs from 9:15 am to 3:30 pm IST on trading days, after a pre-open session (check the exchange for holidays)."],
           example=f"""
{ILLUSTRATIVE} Best bid ₹499.50, best ask ₹500.00.
- A **market buy** fills at about ₹500, or higher if your quantity exceeds what is offered at ₹500.
- A **limit buy** at ₹495 waits until a seller accepts ₹495.
- You hold shares bought at ₹500 and set a **stop-loss** with trigger ₹460 and limit ₹458. If the price falls to ₹460, a sell order at ₹458 or better goes to the book. If the share opens at ₹450, the order may not fill.""",
           interpret="The spread and the quantities waiting at each price show liquidity. A stop-loss manages risk but does not guarantee your exit price.",
           mistakes=["Using market orders in illiquid shares.", "Setting stop-losses so tight that normal swings trigger them.",
                     "Believing a stop-loss guarantees the exit price.", "Confusing the trigger price with the limit price."],
           application="Practise every order type with virtual money in Virtual Invest, and watch the day's movers in the Market Tracker.",
           revision=["Market = speed; limit = price control.", "Stop-loss activates at a trigger price.",
                     "Order book: price first, then time.", "Spread = best ask − best bid."],
           check=[
               mcq("You want to buy only if the price is ₹250 or lower. Which order fits?", ["Market order", "Limit order at ₹250", "Stop-loss sell order", "No order can do this"], 1,
                   "A limit buy executes only at ₹250 or better (lower).",
                   ["A market order takes whatever price is available.", None, "A stop-loss sell is for exiting a holding.", "Limit orders do exactly this."]),
               mcq("Why might a stop-loss limit order fail to execute?", ["The price gapped below the limit price", "Stop-losses are not allowed", "Exchanges ignore stop-losses", "Limit orders always execute"], 0,
                   "If the price jumps past your limit, no buyer may be available at your limit or better.",
                   [None, "Stop-loss orders are permitted.", "Exchanges and brokers process them as described.", "Limit orders execute only at the limit or better."], level="medium"),
           ],
           tools=(("invest", "Try market, limit and stop-loss orders with virtual money."), ("markets", "See today's movers.")),
           sources=("nse", "bse"),
           terms=(term("Market order", "An order to buy or sell immediately at the best available price.", related=("Limit order",)),
                  term("Limit order", "An order to buy or sell only at a stated price or better.", related=("Market order", "Stop-loss order")),
                  term("Stop-loss order", "An order that becomes active when the price reaches a trigger, used to limit losses.",
                       aliases=("stop loss", "sl order", "trigger price", "stop-loss"), related=("Limit order",)),
                  term("Bid-ask spread", "The difference between the best price buyers offer (bid) and the best price sellers ask.",
                       aliases=("bid ask spread", "bid-ask", "order book", "market depth", "best bid"), related=("Liquidity",)),
                  term("Liquidity", "How easily an asset can be bought or sold quickly without moving its price much.",
                       aliases=("liquid", "illiquid", "liquidity risk"), related=("Bid-ask spread",))),
           ),
    lesson("markets-settlement", "Settlement, price bands and circuit breakers",
           concept="""
**Settlement** is the exchange of shares and money after a trade. Indian equities settle on **T+1**: one working day after the trade day.
**Price bands** limit how far an individual share can move in a day. **Market-wide circuit breakers** halt trading across the market when an index (NIFTY 50 or SENSEX) moves sharply.""",
           why="Settlement timing decides when shares reach your demat account and when sale money arrives. Bands and circuits explain why you sometimes cannot buy or sell a share.",
           rules=["Listed equities settle on T+1 (India completed the move in January 2023). An optional shorter cycle exists for a limited set of shares; check exchange circulars for its current scope.",
                  "Exchanges set price bands for individual shares (commonly 2%, 5%, 10% or 20%); shares in the derivatives segment use dynamic price bands instead.",
                  "Market-wide circuit breakers trigger at index moves of 10%, 15% and 20%; the length of the halt depends on the time of day.",
                  "Exchanges place some shares under additional surveillance measures (ASM/GSM) with stricter trading conditions."],
           example=f"""
{ILLUSTRATIVE}
- You buy on Monday; the shares are settled on Tuesday (T+1), if both are trading days.
- A share closed at ₹200 and has a 5% band, so the next day it can trade only between **₹190 and ₹210**.
- If it reaches ₹210 with only buyers left, it is at its **upper circuit**: buyers may not get shares at all.""",
           interpret="A share locked at its upper or lower circuit shows a one-sided market, often in small, illiquid companies, and it can be hard to exit. Bands slow panic but do not remove risk.",
           mistakes=["Expecting to sell a share stuck at its lower circuit.", "Confusing a share's price band with the market-wide circuit breaker.",
                     "Assuming shares are in your demat account on the trade day.", "Trading shares under surveillance measures without understanding the restrictions."],
           application="Check the Market Tracker for movers and shares hitting their limits; ex-dates on the Corporate actions page follow the T+1 cycle.",
           revision=["T+1: settlement one working day after the trade.", "Price bands cap a share's daily move.",
                     "Index moves of 10%, 15%, 20% trigger market-wide halts.", "Circuit-locked shares can be hard to exit."],
           check=[
               num("A share closed at ₹480 and has a 10% price band. What is the highest price it can trade at the next day, in ₹?", 528,
                   "The upper band is the previous close plus the band percentage.", "480 × 1.10 = ₹528", unit="₹", level="easy",
                   verify=v("price_band", 480, 0.10, pick=1)),
               mcq("You buy shares on a Wednesday of a normal trading week. When does the trade settle?", ["The same day", "Thursday (T+1)", "Friday (T+2)", "The next Wednesday"], 1,
                   "Indian equities settle one working day after the trade.",
                   ["Same-day settlement is only an optional cycle for a limited set of shares.", None, "India moved from T+2 to T+1.", "Settlement is not weekly."], kind="rule"),
           ],
           tools=(("markets", "See the day's biggest movers."), ("corporate-actions", "Ex-dates follow the settlement cycle.")),
           sources=("nse", "bse", "sebi"),
           terms=(term("Settlement", "The transfer of securities to the buyer and money to the seller after a trade; T+1 in Indian equities.",
                       aliases=("t+1", "settlement cycle", "t+0"), related=("Clearing corporation",)),
                  term("Price band", "The maximum percentage a share's price may move in a day, set by the exchange.",
                       aliases=("circuit limit", "upper circuit", "lower circuit", "circuit filter"), related=("Market-wide circuit breaker",)),
                  term("Market-wide circuit breaker", "A trading halt across the market when NIFTY 50 or SENSEX moves 10%, 15% or 20% in a day.",
                       aliases=("circuit breaker", "index circuit"), related=("Price band",)),
                  term("Surveillance measures", "Exchange measures such as ASM and GSM that impose stricter trading conditions on some shares.",
                       aliases=("asm", "gsm", "additional surveillance measure", "graded surveillance measure"), related=("Price band",))),
           ),
    lesson("markets-indices", "Market indices: NIFTY 50 and SENSEX",
           concept="""
An **index** tracks a basket of shares to represent the market or a segment. **NIFTY 50** (NSE) contains 50 large companies; **SENSEX** (BSE) contains 30.
Both are weighted by **free-float market capitalisation**: only shares available for trading (excluding, for example, promoter holdings) count, so companies with larger free floats carry more weight.""",
           why="Indices are the benchmark for judging performance (your portfolio, a mutual fund), the basis for index funds, ETFs and index derivatives, and a quick read of the market's mood.",
           formulas=["Free-float market cap = Price × Shares outstanding × Free-float factor",
                     "Weight of a share = Its free-float market cap ÷ Total free-float market cap of the index",
                     "Index change ≈ Σ (weight × share's % change)"],
           example=f"""
{ILLUSTRATIVE} A three-share index:
| Share | Weight | Day's move | Contribution |
|---|---|---|---|
| A | 50% | +2% | +1.0% |
| B | 30% | −1% | −0.3% |
| C | 20% | +4% | +0.8% |
Index change = 1.0 − 0.3 + 0.8 = **+1.5%**.""",
           interpret="A few heavyweights can drive the index, and the index can rise while most shares fall, so check breadth (advances against declines). Price indices exclude dividends; total-return indices include them.",
           mistakes=["Thinking an index is an average share price.", "Comparing a portfolio that earns dividends with a price index.",
                     "Assuming the index represents the whole economy.", "Ignoring how concentrated the top weights are."],
           application="The Market Tracker shows NIFTY 50, SENSEX, sector indices and breadth; compare your Portfolio's return with NIFTY 50.",
           revision=["NIFTY 50: 50 shares on NSE; SENSEX: 30 on BSE.", "Weights come from free-float market cap.",
                     "Index move = Σ weight × move.", "Check breadth: heavyweights can mask a weak market."],
           check=[
               num("Two shares make up an index: 60% weight rises 3%, 40% weight falls 2%. What is the index change, in %?", 1.0,
                   "Multiply each move by its weight and add.", "0.6 × 3% + 0.4 × (−2%) = 1.8% − 0.8% = 1.0%", unit="%", level="easy",
                   verify=v("index_move", [0.6, 0.4], [0.03, -0.02], unit="%")),
               mcq("NIFTY 50 and SENSEX weight their constituents by…", ["Share price", "Free-float market capitalisation", "Revenue", "Number of shareholders"], 1,
                   "Free-float market capitalisation counts only the shares available for trading.",
                   ["Price-weighted indices exist elsewhere, but not these.", None, "Revenue does not set index weights.", "Shareholder count is not used."], kind="rule"),
           ],
           tools=(("markets", "Follow NIFTY 50, SENSEX, sector indices and breadth."), ("portfolio", "Compare your returns with NIFTY 50.")),
           sources=("nse", "bse"),
           terms=(term("NIFTY 50", "NSE's benchmark index of 50 large, liquid companies, weighted by free-float market capitalisation.",
                       aliases=("nifty", "nifty50"), related=("SENSEX", "Free-float market capitalisation")),
                  term("SENSEX", "BSE's benchmark index of 30 large companies, weighted by free-float market capitalisation.",
                       aliases=("sensex", "bse sensex"), related=("NIFTY 50",)),
                  term("Free-float market capitalisation", "Market value of only the shares available for public trading.",
                       formula="Price × Shares outstanding × Free-float factor", aliases=("free float", "free-float"), related=("NIFTY 50",)),
                  term("Market breadth", "How many shares are rising compared with falling; shows whether a move is broad or driven by a few heavyweights.",
                       aliases=("breadth", "advance decline", "advances", "declines"), related=("NIFTY 50",))),
           ),
], test=[
    mcq("Which body regulates the Indian securities market?", ["RBI", "SEBI", "NSE", "Ministry of Corporate Affairs"], 1,
        "SEBI is the securities-market regulator; RBI regulates banks and runs monetary policy.",
        ["RBI regulates banks and monetary policy.", None, "NSE is an exchange that SEBI regulates.", "MCA administers company law."], kind="rule"),
    mcq("Shares held in demat form are held with…", ["Stock exchanges", "Clearing corporations", "Depositories (NSDL/CDSL)", "Registrars only"], 2,
        "NSDL and CDSL are India's depositories; investors reach them through Depository Participants.",
        ["Exchanges provide trading platforms.", "Clearing corporations settle trades but do not hold your holdings.", None, "Registrars keep shareholder records for companies."]),
    mcq("Under SEBI's categorisation, a company ranked 180th by full market capitalisation is…", ["Large-cap", "Mid-cap", "Small-cap", "Micro-cap"], 1,
        "Large-cap = top 100, mid-cap = 101st to 250th, small-cap = 251st onwards.",
        ["Large-cap covers only the top 100.", None, "Small-cap starts at 251st.", "SEBI's categorisation has no micro-cap band."], level="medium", kind="rule"),
    mcq("When a company raises money through an IPO, this takes place in the…", ["Secondary market", "Primary market", "Derivatives market", "Money market"], 1,
        "New issues are primary-market transactions; later trading is the secondary market.",
        ["The secondary market trades existing shares.", None, "Derivatives are contracts, not new share issues.", "The money market deals in short-term debt."]),
    mcq("Indian equity trades settle on a…", ["T+3 basis", "T+2 basis", "T+1 basis", "T+5 basis"], 2,
        "India completed the move to T+1 settlement for listed equities in January 2023.",
        ["T+3 was used many years ago.", "India moved from T+2 to T+1.", None, "There is no T+5 cycle."], kind="rule"),
    mcq("Best bid ₹99.80, best ask ₹100.00. You place a small market buy order. You will most likely pay about…", ["₹99.80", "₹100.00", "₹99.90", "₹101.00"], 1,
        "A market buy takes the best available selling price, the ask.",
        ["₹99.80 is what buyers are offering; you would receive it if you sold.", None, "Trades happen at quoted prices, not the midpoint.", "A small order fills at the best ask."],
        level="medium", kind="case"),
    num("Price ₹1,200, 50 crore shares outstanding, free-float factor 0.45. What is the free-float market capitalisation, in ₹ crore?", 27000,
        "Only the free-floating shares count.", "1,200 × 50 crore × 0.45 = ₹27,000 crore", unit="₹ crore"),
    mcq("A share is locked at its lower circuit. What is the main risk for someone holding it?", ["They may be unable to sell because there are few or no buyers", "The company must buy the shares back", "SEBI refunds the loss", "The price can never fall again"], 0,
        "At the lower limit there are only sellers, so orders may not execute.",
        [None, "No such obligation exists.", "SEBI does not compensate market losses.", "The band resets each day, so falls can continue."], level="medium", kind="case"),
    mcq("Which of these is NOT a primary-market transaction?", ["An IPO", "A rights issue", "A QIP", "Buying a listed company's shares from another investor on NSE"], 3,
        "Buying from another investor on the exchange is secondary-market trading.",
        ["An IPO issues new shares.", "A rights issue issues new shares.", "A QIP issues new shares to institutions.", None]),
    mcq("Why do NIFTY 50 and SENSEX use free-float weighting?", ["It reflects the shares actually available to trade", "It gives every share an equal weight", "It weights by profit", "RBI requires it"], 0,
        "Promoter and locked-in holdings rarely trade, so excluding them better represents the investable market.",
        [None, "Equal weighting is a different method.", "Profits do not set the weights.", "Index rules are set by the index providers, not RBI."], level="hard"),
])

# ================================================================== 4. Corporate actions
corporate = module("corporate", "Corporate actions and governance", "beginner",
                   "Dividends, record and ex-dates, bonus issues, splits, buybacks, rights issues and governance signals.", [
    lesson("corporate-dividends", "Dividends, record date and ex-date",
           concept="""
A **dividend** is a distribution of profit to shareholders: an **interim** dividend is declared by the board during the year, a **final** dividend is approved by shareholders at the annual general meeting.
To receive it you must be a shareholder on the **record date**. From the **ex-date** the share trades without the right to that dividend. Under T+1 settlement the ex-date usually falls on the record date, so you must buy before the ex-date.""",
           why="Dividends are part of shareholder return. Knowing the dates avoids the common mistake of buying 'for the dividend' and finding the price has dropped by about the same amount.",
           formulas=["Dividend yield = Dividend per share ÷ Share price", "Payout ratio = Dividends ÷ Net profit (or DPS ÷ EPS)",
                     "Dividend per share = Declared % × Face value"],
           example=f"""
{ILLUSTRATIVE}
- Dividend ₹24 per share on a share priced at ₹1,200: yield = 24 ÷ 1,200 = **2%**.
- EPS is ₹60, so the payout ratio = 24 ÷ 60 = **40%**.
- Indian companies often announce dividends as a percentage of face value: '150%' on a ₹2 face value share is **₹3 per share**.
- On the ex-date the price typically adjusts down by roughly the dividend, other market moves aside.""",
           interpret="A high yield may reflect a falling share price or a payout the company cannot sustain: check the payout ratio and free cash flow. In India dividends are taxed in the shareholder's hands.",
           mistakes=["Buying just before the ex-date expecting a free gain; the price adjusts.",
                     "Reading '200% dividend' as a 200% return; it is a percentage of face value.",
                     "Chasing high yields without checking whether earnings and cash flow cover them.",
                     "Mixing up the record date, ex-date and payment date."],
           application="The Corporate actions page lists upcoming dividends and ex-dates; the Screener can filter by dividend yield; a Company page shows payout history.",
           revision=["Record date decides who is paid; buy before the ex-date.", "Yield = DPS ÷ price; payout = DPS ÷ EPS.",
                     "Declared % applies to face value, not price.", "Check sustainability with payout and cash flow."],
           check=[
               num("A company declares a dividend of 150% on shares with a face value of ₹2. What is the dividend per share, in ₹?", 3,
                   "Indian dividend percentages apply to face value.", "150% × ₹2 = ₹3", unit="₹", level="easy"),
               mcq("Under T+1 settlement, by when must shares be bought to be entitled to a declared dividend?", ["On the record date", "Before the ex-date", "After the ex-date", "On the payment date"], 1,
                   "Shares bought on or after the ex-date do not carry the declared dividend.",
                   ["A purchase on the record date settles too late.", None, "From the ex-date the share trades without the dividend.", "The payment date is far too late."], kind="rule"),
           ],
           tools=(("corporate-actions", "See upcoming dividends and ex-dates."), ("screener", "Filter companies by dividend yield.")),
           sources=("nse", "bse"),
           terms=(term("Dividend", "A distribution of a company's profit to its shareholders, interim (by the board) or final (approved at the AGM).",
                       aliases=("dividends", "interim dividend", "final dividend", "dps", "dividend per share"), related=("Dividend yield", "Payout ratio", "Record date")),
                  term("Record date", "The date on which a company checks its register to decide who receives a dividend or other benefit.",
                       aliases=("book closure",), related=("Ex-date", "Dividend")),
                  term("Ex-date", "The first day a share trades without the right to a declared dividend or other benefit.",
                       aliases=("ex-dividend", "ex date", "ex dividend"), related=("Record date",)),
                  term("Payout ratio", "The share of profit paid out as dividends.", formula="Payout = Dividends ÷ Net profit",
                       example="DPS ₹24 with EPS ₹60 is a 40% payout.", aliases=("dividend payout", "dividend payout ratio"), related=("Dividend",)),
                  term("Face value", "The nominal value of a share in the company's books (for example ₹1, ₹2 or ₹10), unrelated to its market price. Indian dividends are often declared as a percentage of face value.",
                       example="A 150% dividend on a ₹2 face value share is ₹3 per share.", aliases=("par value", "nominal value"), related=("Dividend", "Stock split")),
                  "Dividend yield"),
           ),
    lesson("corporate-bonus-split", "Bonus issues and stock splits",
           concept="""
A **bonus issue** gives shareholders free extra shares by converting reserves into share capital (1:1 = one bonus share for every share held). A **stock split** divides each share into more shares of a lower face value (for example from ₹10 to ₹2, so one share becomes five).
Both increase the number of shares and lower the price in proportion: the total value of your holding does not change.""",
           why="Both events change share counts and per-share figures, so prices, EPS and dividends must be adjusted before comparing periods. Knowing that value is unchanged protects you from 'free shares' excitement.",
           formulas=["Bonus a:b (a new shares for every b held): new holding = old × (a + b) ÷ b; adjusted price ≈ old price × b ÷ (a + b)",
                     "Split from face value F₁ to F₂: new shares = old × F₁ ÷ F₂; adjusted price ≈ old price × F₂ ÷ F₁"],
           example=f"""
{ILLUSTRATIVE} You hold 100 shares at ₹1,500, worth ₹1,50,000.
- After a **1:1 bonus**: 200 shares at about ₹750, still ₹1,50,000.
- After a **split from ₹10 to ₹2 face value**: 500 shares at about ₹300, still ₹1,50,000.
- EPS of ₹60 before the bonus is ₹30 after it; compare like with like.""",
           interpret="These events are cosmetic for value. They can improve liquidity and make shares look affordable. A bonus moves money from reserves to share capital in the books; no cash leaves the company.",
           mistakes=["Thinking a bonus or split makes you richer.", "Comparing unadjusted EPS or prices across the event.",
                     "Assuming dividends per share stay the same after a bonus.", "Confusing a split (face value changes) with a bonus (reserves capitalised)."],
           application="Check upcoming bonus issues and splits on the Corporate actions page; EquityPilot's price charts use the provider's adjusted history where available.",
           revision=["Bonus: free shares from reserves.", "Split: face value divided into more shares.",
                     "Value of your holding is unchanged in both.", "Adjust EPS and prices before comparing."],
           check=[
               num("You hold 60 shares at ₹900. After a 1:2 bonus (one bonus share for every two held), how many shares do you hold?", 90,
                   "You receive one share for every two held.", "60 × (1 + 2) ÷ 2 = 90 shares", unit="shares", level="easy", tolerance=0.01),
               mcq("After a stock split, the total value of your holding is…", ["Doubled", "Unchanged, apart from normal price moves", "Halved", "Converted into debt"], 1,
                   "More shares at a proportionally lower price leave the value the same.",
                   ["The price falls in proportion, so value does not double.", None, "Value is not lost in a split.", "A split does not create debt."]),
           ],
           tools=(("corporate-actions", "See upcoming bonus issues and splits."),),
           sources=("nse", "bse"),
           terms=(term("Bonus issue", "Free shares issued to existing shareholders by capitalising reserves; value per holding is unchanged.",
                       aliases=("bonus shares", "bonus", "capitalisation issue"), related=("Stock split",)),
                  term("Stock split", "Dividing each share into several shares of lower face value; value per holding is unchanged.",
                       aliases=("split", "sub-division", "share split"), related=("Bonus issue",))),
           ),
    lesson("corporate-buyback-rights", "Buybacks, rights issues and governance signals",
           concept="""
In a **buyback** a company repurchases its own shares (through a tender offer or the open market), reducing the share count. In a **rights issue** it offers new shares to existing shareholders in proportion to their holdings, usually at a discount, to raise money.
**Governance**, how the company is run and in whose interest, shows in board independence, related-party transactions, auditor remarks, promoter pledges and the quality and timeliness of disclosures.""",
           why="Buybacks and rights issues change your share of the company and say something about management's view and the company's needs. Weak governance is behind many of the largest investor losses.",
           formulas=["Theoretical ex-rights price (TERP) = (Old shares × Market price + New shares × Issue price) ÷ (Old shares + New shares)",
                     "EPS after a buyback = Net profit ÷ Reduced share count (if profit is unchanged)"],
           example=f"""
{ILLUSTRATIVE}
- **Rights 1:4 at ₹80** while the share trades at ₹100: TERP = (4 × 100 + 1 × 80) ÷ 5 = **₹96**. If you neither subscribe nor sell your rights entitlement, your 4 shares fall from ₹400 to ₹384.
- **Buyback**: profit ₹1,000 crore; shares fall from 100 crore to 95 crore. EPS rises from ₹10.00 to **₹10.53**.""",
           interpret="Buybacks return cash and can signal confidence, but buying back shares at high prices can destroy value. Rights issues may fund growth or repair a stressed balance sheet, so read the stated use of proceeds and whether promoters subscribe. Red flags: repeated auditor resignations, large related-party dealings, rising promoter pledges and delayed results.",
           mistakes=["Ignoring rights entitlements, which can be sold or renounced.", "Assuming every buyback is good news.",
                     "Overlooking promoter pledges.", "Treating governance as a soft issue."],
           application="The Corporate actions page lists buybacks and rights issues; a Company page shows promoter holding and pledges; the News page carries board outcomes and auditor changes.",
           revision=["Buyback: fewer shares, cash returned.", "Rights: new shares to existing holders; TERP shows the diluted price.",
                     "Act on rights entitlements: subscribe or sell.", "Governance red flags often precede large losses."],
           check=[
               num("A 1:5 rights issue is priced at ₹150 while the share trades at ₹180. What is the theoretical ex-rights price, in ₹?", 175,
                   "TERP averages the old and new shares at their prices.", "(5 × 180 + 1 × 150) ÷ 6 = 1,050 ÷ 6 = ₹175", unit="₹",
                   verify=v("terp", 5, 180, 1, 150)),
               mcq("Which of these is a governance red flag?", ["An independent audit committee", "Frequent unexplained auditor resignations", "Results published on time", "A consistent dividend record"], 1,
                   "Auditors leaving without clear reasons warrants investigation.",
                   ["Independent oversight is a good sign.", None, "Timely disclosure is a good sign.", "Consistency is generally positive."]),
           ],
           tools=(("corporate-actions", "Track buybacks and rights issues."), ("news", "Read board outcomes and auditor changes.")),
           sources=("sebi", "nse", "bse"),
           terms=(term("Buyback", "A company repurchasing its own shares, reducing the number outstanding.",
                       aliases=("share buyback", "buy back", "repurchase"), related=("EPS",)),
                  term("Rights issue", "New shares offered to existing shareholders in proportion to their holdings, usually at a discount.",
                       aliases=("rights entitlement", "renunciation", "rights offer"), related=("TERP",)),
                  term("TERP", "Theoretical ex-rights price: the expected share price after a rights issue.",
                       formula="TERP = (N_old × P + N_new × Issue price) ÷ (N_old + N_new)", example="1:4 rights at ₹80 with the share at ₹100 gives ₹96.",
                       aliases=("theoretical ex-rights price", "ex-rights price"), related=("Rights issue",)),
                  term("Promoter pledge", "Promoters using their shares as collateral for loans; lenders may sell them if the price falls.",
                       aliases=("pledge", "pledged shares", "promoter pledging"), related=("Corporate governance",)),
                  term("Corporate governance", "The rules and practices by which a company is directed and controlled, including board independence, disclosures and fairness to minority shareholders.",
                       aliases=("governance", "related-party transaction", "related party transactions", "rpt"), related=("Promoter pledge",))),
           ),
], test=[
    mcq("After a 1:1 bonus issue, an investor holding 100 shares at ₹1,000 will have about…", ["100 shares at ₹2,000", "200 shares at ₹500", "200 shares at ₹1,000", "50 shares at ₹2,000"], 1,
        "The share count doubles and the price roughly halves; total value is unchanged.",
        ["The share count rises; it does not stay at 100.", None, "That would double the value out of nothing.", "A bonus increases, not reduces, shares."], kind="numerical"),
    mcq("A buyback generally…", ["Increases shares outstanding", "Reduces shares outstanding", "Has no effect on the share count", "Creates debt automatically"], 1,
        "Repurchased shares are extinguished, so EPS on the remaining shares can rise.",
        ["New shares are created by issues, not buybacks.", None, "Bought-back shares are cancelled.", "A buyback may be funded by cash; debt is not automatic."]),
    mcq("A rights issue is offered to…", ["The public at large", "Existing shareholders", "Only promoters", "Only institutions"], 1,
        "Rights are offered pro rata to existing shareholders.",
        ["A public offer is an FPO.", None, "All shareholders get rights, not only promoters.", "A QIP is for institutions."]),
    num("Dividend per share ₹18, share price ₹600. What is the dividend yield, in %?", 3,
        "Yield divides the annual dividend by the price.", "18 ÷ 600 = 0.03 = 3%", unit="%", level="easy"),
    mcq("A company announces a '300% dividend' on shares with a face value of ₹1. The dividend per share is…", ["₹300", "₹3", "₹30", "₹0.30"], 1,
        "300% of the ₹1 face value is ₹3.",
        ["The percentage applies to face value, not to a ₹100 base.", None, "That would be 300% of ₹10.", "That would be 30% of ₹1."], level="medium", kind="numerical"),
    mcq("A heavily indebted company announces a large rights issue 'to reduce debt'. What should you check first?",
        ["The use of proceeds, the issue price against the market price, and whether promoters subscribe", "Only how many times it is subscribed", "The company's logo and brand", "Nothing; rights issues are always good news"], 0,
        "These show whether the issue genuinely fixes the balance sheet and how much dilution you face.",
        [None, "Subscription shows demand, not whether the plan works.", "Branding says nothing about the issue.", "Rights issues can signal stress."], level="medium", kind="case"),
    num("Profit is ₹500 crore and a buyback cuts shares from 50 crore to 40 crore. What is the new EPS, in ₹, if profit is unchanged?", 12.5,
        "Divide profit by the reduced share count.", "500 ÷ 40 = ₹12.50 (up from ₹10.00)", unit="₹", verify=v("eps", 500, 40)),
    mcq("Why does a share price usually fall on the ex-dividend date?", ["New buyers no longer receive the declared dividend", "The company is penalised", "Trading is halted", "SEBI caps the price"], 0,
        "The dividend's value leaves the share price because buyers from the ex-date are not entitled to it.",
        [None, "There is no penalty involved.", "Trading continues normally.", "SEBI does not cap prices on ex-dates."], level="hard"),
])

# ================================================================== 5. Investor protection and regulation
protection = module("protection", "Investor protection and regulation", "beginner",
                    "SEBI's role and your rights, market abuse, investment frauds and red flags, and how to complain through SCORES and SMART ODR.", [
    lesson("protection-sebi", "SEBI's role and your rights as an investor",
           concept="""
**SEBI** is the statutory regulator of the securities market under the SEBI Act, 1992. Its mandate is to protect the interests of investors, and to develop and regulate the securities market.
It registers and supervises intermediaries (stock brokers, depository participants, mutual funds, investment advisers, research analysts, portfolio managers), makes regulations, and investigates and penalises violations.""",
           why="Knowing what SEBI does tells you which protections exist, and which do not: SEBI does not guarantee returns or make good losses from normal market movements.",
           rules=["SEBI Act, 1992: protect investors' interests; develop and regulate the securities market.",
                  "Only SEBI-registered entities may offer regulated services such as broking, investment advice, research recommendations and portfolio management.",
                  "You are entitled to contract notes, statements of your funds and securities, disclosure documents (such as a mutual fund's scheme information document) and grievance redressal.",
                  "Registered intermediaries publish investor charters that set out your rights and their duties."],
           example="""
_A situation to recognise:_ someone on social media offers 'guaranteed 5% a month' stock tips for a fee.
1. Check SEBI's website: are they a registered investment adviser or research analyst? If not, they cannot legally sell investment advice.
2. Even a registered adviser cannot promise guaranteed returns.
3. Either failure is a reason to walk away.""",
           interpret="Registration is a minimum check, not an endorsement of quality. EquityPilot is an educational tool, not a registered adviser, which is why it explains evidence and never gives buy or sell calls.",
           mistakes=["Assuming SEBI insures your investments.", "Trusting a claimed registration without checking the number on SEBI's website.",
                     "Confusing SEBI (securities) with RBI (banks) or IRDAI (insurance)."],
           application="Use SEBI's investor website for education, and check registrations on sebi.gov.in before paying anyone for advice.",
           revision=["SEBI: statutory regulator since the SEBI Act, 1992.", "Mandate: protect investors; develop and regulate the market.",
                     "Use only SEBI-registered intermediaries.", "SEBI does not guarantee returns."],
           check=[
               mcq("Which of these is part of SEBI's statutory mandate?", ["Guaranteeing share returns", "Protecting investors and regulating the securities market", "Setting the repo rate", "Insuring bank deposits"], 1,
                   "The SEBI Act sets out investor protection and the development and regulation of the market.",
                   ["No regulator guarantees market returns.", None, "The repo rate is set by RBI's MPC.", "Deposit insurance is DICGC's role."], kind="rule"),
               mcq("A person with no SEBI registration offers paid stock tips with 'guaranteed' returns. This is…", ["Normal and legal", "A red flag: unregistered advice and promised returns", "Legal if they have many followers", "Legal if paid by UPI"], 1,
                   "Paid investment advice requires SEBI registration, and no one can guarantee market returns.",
                   ["It breaches the registration requirement.", None, "Popularity is not registration.", "The payment method does not matter."], kind="case"),
           ],
           sources=("sebi", "sebi_investor"),
           terms=(term("Investment adviser", "A person registered with SEBI to give investment advice for a fee.",
                       aliases=("ria", "registered investment adviser", "sebi ria", "investment advisor"), related=("SEBI", "Research analyst")),
                  term("Investor charter", "A document published by registered intermediaries setting out investors' rights, the services offered and how complaints are handled.",
                       related=("SEBI",))),
           ),
    lesson("protection-misconduct", "Market abuse: manipulation, insider trading and front-running",
           concept="""
**Market abuse** distorts prices or exploits unfair information:
- **Price manipulation**, such as circular or synchronised trades that create false volume, including **pump-and-dump** schemes in which operators hype a share and sell at inflated prices.
- **Insider trading**: dealing while in possession of **unpublished price-sensitive information (UPSI)**.
- **Front-running**: trading ahead of a large client or fund order using knowledge of that order.
These are prohibited under SEBI's Prohibition of Fraudulent and Unfair Trade Practices (PFUTP) Regulations, 2003 and Prohibition of Insider Trading (PIT) Regulations, 2015.""",
           why="Retail investors are usually the ones left holding overpriced shares when a pump-and-dump ends. Recognising the pattern helps you avoid becoming someone else's exit.",
           rules=["Trading while in possession of UPSI is prohibited (PIT Regulations, 2015); listed companies close the trading window for designated persons around results.",
                  "UPSI includes financial results, dividends, changes in capital structure, mergers and acquisitions, and changes in key managerial personnel.",
                  "Manipulation and front-running are fraudulent and unfair trade practices (PFUTP Regulations, 2003).",
                  "Penalties include disgorgement of gains, monetary penalties and bans from the market."],
           example="""
_A hypothetical pattern:_ a small company's share triples in a month on heavy volume.
- There are no new filings on the exchange.
- Messages on chat apps promise '100% returns'.
- The latest shareholding pattern shows promoters selling.
Price rise without fundamentals, unsolicited tips and insider selling are classic pump-and-dump signs.""",
           interpret="Unsolicited tips plus no disclosures plus sudden volume is a reason to stay away. Check the exchange's surveillance lists and SEBI's orders.",
           mistakes=["Acting on 'inside information' tips, which is illegal and usually false.", "Assuming high volume means genuine interest.",
                     "Ignoring promoter selling in shareholding filings."],
           application="Verify any claim against exchange filings on the News page, and check shareholding changes on the Company page.",
           revision=["Manipulation creates false prices or volume.", "Insider trading = dealing with UPSI.",
                     "Front-running = trading ahead of a known client order.", "PFUTP 2003 and PIT 2015 prohibit them."],
           check=[
               mcq("Which of these is UPSI?", ["A company's published annual report", "Unannounced quarterly results known to a finance manager", "A newspaper editorial", "A share's closing price"], 1,
                   "Results not yet made public are price-sensitive and unpublished.",
                   ["Published information is no longer UPSI.", None, "Opinion pieces are public.", "Market prices are public."], kind="rule"),
               mcq("A dealer buys a share for himself just before placing a large buy order for a fund client. This is…", ["Arbitrage", "Front-running", "Hedging", "Market making"], 1,
                   "He exploits advance knowledge of the client's order.",
                   ["Arbitrage exploits price differences between markets.", None, "Hedging reduces an existing risk.", "Market makers quote two-way prices openly."]),
           ],
           tools=(("news", "Check claims against exchange filings."),),
           sources=("sebi", "sebi_investor", "nse", "bse"),
           terms=(term("Insider trading", "Dealing in securities while in possession of unpublished price-sensitive information; prohibited by SEBI's PIT Regulations, 2015.",
                       aliases=("upsi", "unpublished price sensitive information", "trading window"), related=("Front-running",)),
                  term("Front-running", "Trading ahead of a large pending order using knowledge of that order.",
                       aliases=("front running",), related=("Insider trading", "Market manipulation")),
                  term("Pump and dump", "Hyping a share to inflate its price and then selling to the buyers attracted by the hype.",
                       aliases=("pump-and-dump", "operator stock"), related=("Market manipulation",)),
                  term("Market manipulation", "Trading or spreading information to create a false or misleading price or volume; prohibited by SEBI's PFUTP Regulations, 2003.",
                       aliases=("price manipulation", "circular trading", "pfutp"), related=("Pump and dump",))),
           ),
    lesson("protection-fraud", "Investment frauds, red flags and your broker's duties",
           concept="""
Common frauds include 'guaranteed return' and Ponzi schemes, unregistered tipsters and 'advisory' groups on social media, fake trading apps and websites impersonating brokers or fund houses, 'account handling' offers where someone trades your account for a share of profits, and phishing for OTPs and passwords.
Registered brokers have duties: execute orders as instructed, issue contract notes, keep client money and securities separate from their own, send statements, settle client accounts at the intervals SEBI prescribes, and resolve complaints.""",
           why="Most fraud losses follow the same script. Spotting red flags early is the best protection, because money sent to fraudsters is often impossible to recover.",
           rules=["Red flags: guaranteed or very high fixed returns, pressure to act fast, requests for OTPs or passwords, payments to personal accounts, no SEBI registration number.",
                  "Check any intermediary on SEBI's website before paying; pay only into the intermediary's own registered bank account.",
                  "Never share login credentials; exchanges and depositories send alerts for your trades and holdings, so read them.",
                  "Report cyber fraud on the National Cyber Crime Reporting Portal (cybercrime.gov.in) or helpline 1930."],
           example="""
_A hypothetical scam:_ a chat group shares screenshots of huge profits and invites you to a 'VIP trading app' through a link.
- Deposits go to a personal UPI ID.
- Withdrawals are blocked unless you first pay a 'tax'.
Every step is a red flag: an unverified app, a personal account, promised profits and a fee to withdraw.""",
           interpret="If it sounds too good to be true, it is. Dealing with a registered entity gives you SEBI's grievance channels; with unregistered operators your main route is the police and cybercrime authorities.",
           mistakes=["Sharing OTPs or passwords.", "Trusting screenshots of profits.", "Paying 'fees' to unlock withdrawals.",
                     "Letting someone else trade your account.", "Ignoring trade alerts from exchanges and depositories."],
           application="Practise in Virtual Invest instead of 'trial' apps, and verify registrations on SEBI's website.",
           revision=["Guaranteed returns = red flag.", "Verify SEBI registration before paying.", "Pay only to the entity's own account.",
                     "Brokers must segregate client funds and send contract notes."],
           check=[
               mcq("Which of these is NOT a red flag?", ["Guaranteed 4% monthly returns", "A request for your trading OTP", "Paying an intermediary's own bank account after checking its SEBI registration", "Pressure to invest today"], 2,
                   "Verifying registration and paying the entity's own account is the safe way to deal.",
                   ["Guaranteed high returns are a classic sign of fraud.", "No genuine intermediary needs your OTP.", None, "Urgency is a pressure tactic."], kind="case"),
               mcq("Your stock broker must…", ["Guarantee your profits", "Send contract notes and keep client funds separate from its own", "Trade without your instructions", "Share your password with partners"], 1,
                   "Segregating client assets and confirming trades are core duties.",
                   ["No broker may guarantee profits.", None, "Trading without instructions is unauthorised trading.", "Credentials must never be shared."], kind="rule"),
           ],
           tools=(("invest", "Practise safely with virtual money."),),
           sources=("sebi", "sebi_investor", "cybercrime", "i4c"),
           terms=(term("Ponzi scheme", "A fraud that pays earlier investors with money from new investors, promising high or guaranteed returns until it collapses.",
                       aliases=("ponzi", "guaranteed returns", "investment fraud", "investment scam"), related=("Pump and dump",)),),
           ),
    lesson("protection-grievance", "Complaints: SCORES, SMART ODR and exchange support",
           concept="""
If you have a complaint against a listed company or a SEBI-registered intermediary, it usually helps to raise it with the entity first. If it is not resolved, lodge it on SEBI's **SCORES** portal (scores.sebi.gov.in), which routes it to the entity.
The entity must resolve the complaint and upload an **Action Taken Report (ATR)** within **21 calendar days**. If you are not satisfied, you can seek a first-level review within 15 calendar days of the ATR, and then a second-level review by SEBI within a further 15 calendar days. You can also use **SMART ODR** (smartodr.in) for online conciliation and arbitration.""",
           why="Knowing the route and the timelines gets complaints resolved faster and tells you what evidence to keep.",
           rules=["SCORES: the entity must resolve the complaint and upload the ATR within 21 calendar days of receipt.",
                  "First-level review: request within 15 calendar days of the ATR; the designated body (such as the exchange or depository) responds within 10 calendar days.",
                  "Second-level review: request within 15 calendar days; SEBI then takes up the complaint.",
                  "SMART ODR can be used at any time; opting for it while a SCORES complaint is pending closes that complaint on SCORES.",
                  "Exchanges and depositories run investor service cells, and exchanges maintain Investor Protection Funds for valid claims against brokers declared defaulters (subject to limits)."],
           example="""
_A hypothetical complaint:_ your broker has not returned the unused balance in your trading account despite several emails.
1. You lodge a complaint on SCORES with your client ID and evidence.
2. The broker must upload an ATR within 21 days.
3. If the ATR does not resolve it, you ask for a first-level review within 15 days; the exchange reviews it.
4. Still unresolved? You seek a second-level review by SEBI, or take the dispute to SMART ODR for conciliation and arbitration.""",
           interpret="Keep records: contract notes, statements, emails and screenshots. SCORES covers listed companies and registered entities; it cannot act against unregistered fraudsters, which are matters for the police and cybercrime authorities.",
           mistakes=["Waiting months before complaining.", "Not keeping evidence.", "Filing on SCORES against unregistered entities, which is outside its scope.",
                     "Expecting compensation for normal market losses."],
           application="SCORES can fetch your details from the KYC Registration Agency database when you register. Unclaimed dividends and shares moved to the Investor Education and Protection Fund can be claimed from the IEPF Authority.",
           revision=["Entity first, then SCORES.", "ATR within 21 calendar days.", "Reviews: 15 days to ask at each level.",
                     "SMART ODR for conciliation and arbitration.", "Keep evidence of everything."],
           check=[
               mcq("Within how many calendar days must an entity resolve a SCORES complaint and upload its Action Taken Report?", ["7", "21", "45", "90"], 1,
                   "The SCORES framework gives the entity 21 calendar days from receipt.",
                   ["7 days is not the SCORES timeline.", None, "45 days is longer than the rule allows.", "90 days is far longer than the rule allows."], kind="rule"),
               mcq("Which complaint can SCORES handle?", ["A dispute with a SEBI-registered stock broker", "A fraud by an unregistered chat-group tipster", "An ATM failure at your bank", "An insurance claim"], 0,
                   "SCORES covers listed companies and SEBI-registered intermediaries.",
                   [None, "Unregistered operators are a police and cybercrime matter.", "Bank complaints go to the bank and RBI's ombudsman.", "Insurance falls under IRDAI."], kind="case"),
           ],
           sources=("scores", "scores_faq", "scores_circular", "smartodr", "sebi_investor", "iepf"),
           terms=(term("SCORES", "SEBI's online complaint system for grievances against listed companies and SEBI-registered intermediaries.",
                       aliases=("sebi complaint", "sebi scores", "scores portal", "complaint against broker"), related=("SMART ODR", "Action Taken Report")),
                  term("SMART ODR", "SEBI's online dispute resolution portal for conciliation and arbitration of securities-market disputes.",
                       aliases=("odr", "online dispute resolution", "smartodr"), related=("SCORES",)),
                  term("Action Taken Report", "The entity's response to a SCORES complaint, due within 21 calendar days.", aliases=("atr",), related=("SCORES",)),
                  term("Investor Protection Fund", "A fund kept by an exchange to compensate investors for valid claims against a broker declared a defaulter, subject to limits.",
                       aliases=("ipf",), related=("SCORES",)),
                  term("IEPF", "Investor Education and Protection Fund: unclaimed dividends and the related shares move here after seven years and can be claimed back from the IEPF Authority.",
                       aliases=("investor education and protection fund", "unclaimed dividend"), related=("Dividend",))),
           ),
], test=[
    mcq("SEBI received its statutory powers under…", ["The Companies Act, 2013", "The SEBI Act, 1992", "The RBI Act, 1934", "The Banking Regulation Act"], 1,
        "SEBI was set up in 1988 and made a statutory body by the SEBI Act, 1992.",
        ["The Companies Act governs companies.", None, "The RBI Act governs the central bank.", "That Act governs banks."], kind="rule"),
    mcq("Trading while in possession of UPSI is…", ["Allowed for directors", "Insider trading, prohibited under SEBI's PIT Regulations", "Allowed after market hours", "Legal if the gain is small"], 1,
        "The PIT Regulations, 2015 prohibit it whatever the size or timing.",
        ["Directors are designated persons and face stricter rules.", None, "Timing does not change the prohibition.", "There is no size exemption."], kind="rule"),
    mcq("A first-level review on SCORES must be requested within…", ["15 calendar days of the ATR", "90 days", "One year", "Any time"], 0,
        "The SCORES framework allows 15 calendar days from the ATR.", [None, "That is far too late.", "That is far too late.", "There is a deadline."], level="medium", kind="rule"),
    mcq("A share with no news rises 200% in a month on heavy volume while promoters sell. What should you investigate?", ["A possible pump-and-dump", "A dividend announcement", "A bonus issue", "An index rebalancing"], 0,
        "A price surge without fundamentals while insiders sell fits the pump-and-dump pattern.",
        [None, "A dividend would appear in filings and would not explain a 200% rise.", "A bonus lowers the price; it does not triple it.", "Index changes are announced and would not explain this."],
        level="medium", kind="case"),
    mcq("Who can legally charge you a fee for personalised investment advice in India?", ["Anyone with a large following", "A SEBI-registered investment adviser", "Any broker's sales staff", "A chat-group admin"], 1,
        "Fee-based advice requires registration under SEBI's Investment Advisers Regulations.",
        ["Followers are not a licence.", None, "Sales staff are not registered advisers by default.", "Chat-group admins are usually unregistered."], kind="rule"),
    mcq("If you opt for SMART ODR while your SCORES complaint is pending, the SCORES complaint is…", ["Kept running in parallel", "Treated as disposed", "Doubled in priority", "Unaffected"], 1,
        "The SCORES FAQs say a pending complaint is treated as disposed once you choose ODR.",
        ["The two routes are not run in parallel.", None, "No priority change applies.", "The SCORES complaint is closed."], level="hard", kind="rule"),
    mcq("PAN in the securities market is…", ["Optional", "Mandatory for transacting, with limited exemptions", "Needed only for IPOs", "Needed only above ₹10 lakh"], 1,
        "PAN is a mandatory KYC requirement, with specific exemptions.",
        ["It is mandatory.", None, "It applies to all transactions, not only IPOs.", "There is no such threshold."], kind="rule"),
    mcq("Which statement about SEBI is correct?", ["It compensates investors for market losses", "It registers and supervises intermediaries such as brokers and research analysts", "It sets interest rates", "It insures demat accounts"], 1,
        "Registration and supervision of intermediaries are central to SEBI's role.",
        ["SEBI does not cover market losses.", None, "Interest rates are RBI's domain.", "Demat holdings are not insured by SEBI."]),
])

MODULES = [money, economy, markets, corporate, protection]
