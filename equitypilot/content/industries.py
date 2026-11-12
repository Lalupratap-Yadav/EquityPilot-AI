"""Industry Intelligence Centre - editorial content and industry-appropriate metrics.

Text here is general, educational background on Indian industries (EquityPilot editorial, not
real-time and not company-specific). Company lists are symbols verified against the NSE / AMFI
securities lists. `compare_metrics` are the fields EquityPilot can compute from available data
for that industry; `disclosure_kpis` are operating metrics analysts read in company disclosures
(not available from free data feeds, so they are shown as a checklist, never as numbers).
"""
from __future__ import annotations

INDUSTRIES: list[dict] = [
    {"id": "banking", "name": "Banking", "icon": "landmark",
     "symbols": "HDFCBANK ICICIBANK SBIN KOTAKBANK AXISBANK INDUSINDBK BANKBARODA PNB CANBK FEDERALBNK IDFCFIRSTB AUBANK",
     "overview": "India's banking system is led by large private banks and public-sector banks (PSBs). Banks earn mainly from net interest income (the spread between lending and deposit rates) and fees. Credit growth tends to track nominal GDP growth and the investment cycle.",
     "drivers": ["Credit demand from retail, MSME and corporate borrowers", "Low-cost deposit franchises (CASA)", "Digital payments and distribution reach", "Improving asset quality after the last credit cycle"],
     "trends": ["Retail and unsecured lending growth, with regulatory tightening of risk weights", "Deposit competition raising funding costs", "Digital onboarding and UPI-driven customer acquisition", "Consolidation among public-sector banks"],
     "risks": ["Asset-quality deterioration in a downturn (rising GNPA/credit costs)", "Net interest margin compression when rates change", "Regulatory changes by the RBI (provisioning, capital, risk weights)", "Concentration in specific sectors or large borrowers"],
     "valuation": ["Price-to-book (P/B) anchored on sustainable ROE versus cost of equity", "Justified P/B = (ROE - g) / (Ke - g)", "EV/EBITDA, debt/equity and FCFF DCF are not meaningful for banks"],
     "compare_metrics": ["market_cap", "pb", "pe", "roe", "net_income_growth", "dividend_yield"],
     "bank_metrics": True,
     "disclosure_kpis": ["NIM", "GNPA / NNPA", "Provision coverage", "CASA ratio", "Capital adequacy (CRAR / CET1)", "Credit cost", "Loan and deposit growth"]},
    {"id": "financial-services", "name": "Financial services", "icon": "wallet",
     "symbols": "BAJFINANCE BAJAJFINSV SHRIRAMFIN CHOLAFIN HDFCLIFE SBILIFE ICICIGI MUTHOOTFIN JIOFIN LICI",
     "overview": "Non-bank lenders (NBFCs), insurers, asset managers and other financial intermediaries. NBFCs often specialise in segments such as consumer finance, vehicle finance or gold loans; insurers earn from underwriting and investment income.",
     "drivers": ["Under-penetration of credit and insurance in India", "Financialisation of household savings", "Digital distribution and data-driven underwriting"],
     "trends": ["Tighter RBI regulation of NBFCs (scale-based regulation)", "Growth of protection and annuity insurance products", "Consolidation and conversion of large NBFCs"],
     "risks": ["Funding cost and liquidity risk for NBFCs", "Credit quality in unsecured segments", "Regulatory changes (IRDAI, RBI, SEBI)", "Interest-rate and investment-market risk for insurers"],
     "valuation": ["P/B and P/E with ROE for lenders", "Embedded value (EV) and value of new business (VNB) for life insurers", "Avoid EV/EBITDA and FCFF-based DCF"],
     "compare_metrics": ["market_cap", "pb", "pe", "roe", "revenue_growth", "net_income_growth"],
     "bank_metrics": True,
     "disclosure_kpis": ["AUM growth", "GNPA / NNPA (lenders)", "Cost of funds", "VNB margin (life insurers)", "Combined ratio (general insurers)", "Solvency ratio"]},
    {"id": "it", "name": "Information technology", "icon": "cpu",
     "symbols": "TCS INFY HCLTECH WIPRO TECHM PERSISTENT COFORGE MPHASIS",
     "overview": "Indian IT services firms deliver software development, maintenance, consulting, cloud and engineering services, largely to clients in North America and Europe. Revenue is mostly in foreign currency and the business is people-intensive and asset-light.",
     "drivers": ["Global technology spending and digital transformation", "Cloud migration, data and AI adoption", "Cost advantage and large talent pool", "Large multi-year deal wins"],
     "trends": ["Generative AI changing delivery models and pricing", "Vendor consolidation by large clients", "Growth of global capability centres (GCCs) in India"],
     "risks": ["Slowdown in client spending (especially BFSI and retail verticals)", "Currency movements (INR vs USD/EUR)", "Wage inflation and attrition", "Visa and immigration policy changes"],
     "valuation": ["P/E relative to growth and history", "EV/EBIT; high cash conversion supports FCF-based DCF", "Payout ratio and buybacks matter for total return"],
     "compare_metrics": ["market_cap", "pe", "revenue_growth", "ebitda_margin", "roe", "fcf_margin"],
     "disclosure_kpis": ["Constant-currency revenue growth", "EBIT margin", "Deal wins (TCV)", "Attrition", "Headcount & utilisation", "Revenue by vertical and geography"]},
    {"id": "pharma", "name": "Pharmaceuticals", "icon": "pill",
     "symbols": "SUNPHARMA DRREDDY CIPLA DIVISLAB LUPIN AUROPHARMA TORNTPHARM ZYDUSLIFE MANKIND",
     "overview": "Indian pharma companies sell branded generics in India, generics in regulated markets such as the US, and active pharmaceutical ingredients (APIs). Several are expanding into specialty and complex products.",
     "drivers": ["Domestic healthcare demand and chronic therapies", "US generic launches and complex products", "Contract development and manufacturing (CDMO) opportunities"],
     "trends": ["Shift towards specialty, biosimilars and complex generics", "Supply-chain diversification benefiting Indian API makers", "Consolidation in domestic distribution"],
     "risks": ["USFDA inspection outcomes (warning letters, import alerts)", "US generic price erosion", "Domestic price controls (DPCO/NPPA)", "Patent litigation"],
     "valuation": ["P/E and EV/EBITDA versus growth mix (India vs US vs specialty)", "Pipeline value for specialty-led companies", "Quality of earnings: one-off launches inflate single years"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "revenue_growth", "ebitda_margin", "roce"],
     "disclosure_kpis": ["R&D spend (% of sales)", "ANDA filings / approvals pipeline", "US vs India revenue mix", "Regulatory inspection status"]},
    {"id": "healthcare", "name": "Healthcare services", "icon": "heart-pulse",
     "symbols": "APOLLOHOSP MAXHEALTH FORTIS MEDANTA LALPATHLAB",
     "overview": "Hospital chains and diagnostics companies. Hospitals earn from in-patient and out-patient services; profitability depends on bed occupancy and revenue per bed. Diagnostics is a high-volume testing business.",
     "drivers": ["Rising incomes and health insurance penetration", "Under-supply of quality hospital beds", "Medical tourism"],
     "trends": ["Brownfield and greenfield bed additions", "Consolidation in diagnostics", "Digital health platforms"],
     "risks": ["Execution risk on new hospitals (ramp-up losses)", "Pricing regulation and insurer negotiations", "Doctor retention"],
     "valuation": ["EV/EBITDA is common; mature vs new beds differ in profitability", "Occupancy and ARPOB trends drive estimates"],
     "compare_metrics": ["market_cap", "ev_ebitda", "pe", "revenue_growth", "ebitda_margin", "roce"],
     "disclosure_kpis": ["Bed capacity & occupancy", "ARPOB (average revenue per occupied bed)", "Average length of stay", "Tests per patient (diagnostics)"]},
    {"id": "automobiles", "name": "Automobiles", "icon": "car",
     "symbols": "MARUTI M&M BAJAJ-AUTO EICHERMOT HEROMOTOCO TVSMOTOR ASHOKLEY TMPV TMCV",
     "overview": "Passenger vehicles, two-wheelers, tractors and commercial vehicles. Demand is cyclical and sensitive to incomes, interest rates, fuel prices and rural conditions. Manufacturers operate with high fixed costs.",
     "drivers": ["Rising incomes and first-time buyers", "Rural demand (monsoon, farm incomes)", "Premiumisation (SUVs, premium motorcycles)", "Exports"],
     "trends": ["Electric-vehicle transition and battery supply chains", "Shift to SUVs in passenger vehicles", "Stricter emission and safety norms"],
     "risks": ["Commodity costs (steel, aluminium, precious metals)", "Demand cyclicality and inventory build-up", "Regulatory cost increases", "EV disruption to incumbents"],
     "valuation": ["P/E and EV/EBITDA through the cycle", "Volume growth and realisation per vehicle drive estimates"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "revenue_growth", "ebitda_margin", "roce"],
     "disclosure_kpis": ["Monthly sales volumes", "Realisation per vehicle", "Capacity utilisation", "Market share by segment", "EV share of sales"]},
    {"id": "fmcg", "name": "FMCG", "icon": "shopping-basket",
     "symbols": "HINDUNILVR ITC NESTLEIND BRITANNIA DABUR TATACONSUM MARICO GODREJCP COLPAL",
     "overview": "Fast-moving consumer goods: foods, beverages, personal and home care. Businesses rely on brands and distribution reach, generate high returns on capital and typically carry little debt.",
     "drivers": ["Population and income growth", "Rural penetration and premiumisation", "Distribution expansion (modern trade, e-commerce, quick commerce)"],
     "trends": ["Quick-commerce changing channel economics", "Competition from direct-to-consumer brands", "Health and wellness positioning"],
     "risks": ["Raw-material inflation (agri commodities, crude derivatives)", "Weak rural demand", "Down-trading in slowdowns"],
     "valuation": ["High P/E multiples reflect stable growth and ROCE; compare with own history", "Volume growth matters more than price-led growth"],
     "compare_metrics": ["market_cap", "pe", "revenue_growth", "ebitda_margin", "roce", "dividend_yield"],
     "disclosure_kpis": ["Underlying volume growth", "Gross margin", "A&P (advertising) spend", "Rural vs urban growth", "Direct distribution reach"]},
    {"id": "agriculture", "name": "Agriculture & agri-inputs", "icon": "sprout",
     "symbols": "UPL PIIND COROMANDEL CHAMBLFERT RALLIS DHANUKA",
     "overview": "Fertilisers, crop protection chemicals and seeds. Demand follows the monsoon and crop prices; fertiliser economics are shaped by government subsidies.",
     "drivers": ["Food demand and farm mechanisation", "Crop-protection adoption", "Custom synthesis and manufacturing for global agrochemical firms"],
     "trends": ["Global agrochemical inventory cycles", "Specialty and nano fertilisers", "Direct benefit transfer reforms"],
     "risks": ["Monsoon variability", "Subsidy payment delays and policy changes", "Global price cycles and channel inventory"],
     "valuation": ["P/E and EV/EBITDA through the cycle", "Working-capital intensity (receivables, subsidy dues)"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "revenue_growth", "ebitda_margin", "debt_to_equity"],
     "disclosure_kpis": ["Volumes by product", "Subsidy receivables", "Channel inventory", "Export share"]},
    {"id": "energy", "name": "Energy & utilities", "icon": "zap",
     "symbols": "RELIANCE ONGC NTPC POWERGRID COALINDIA BPCL IOC TATAPOWER ADANIGREEN",
     "overview": "Oil & gas, refining and marketing, coal, power generation, transmission and renewables. Many companies are state-owned; regulated utilities earn returns set by regulators.",
     "drivers": ["Rising energy demand", "Renewable capacity additions", "Transmission investment"],
     "trends": ["Energy transition: solar, wind, storage, green hydrogen", "Government pricing interventions in fuels", "Coal demand from power"],
     "risks": ["Commodity price volatility (crude, gas, coal)", "Regulatory and pricing intervention", "Execution risk on large projects"],
     "valuation": ["EV/EBITDA and P/E; P/B for regulated utilities", "Dividend yield matters for state-owned companies", "Sum-of-the-parts for conglomerates"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "pb", "dividend_yield", "debt_to_equity"],
     "disclosure_kpis": ["Gross refining margin", "Plant load factor (PLF)", "Capacity added (MW)", "Regulated equity"]},
    {"id": "infrastructure", "name": "Infrastructure & cement", "icon": "construction",
     "symbols": "LT ADANIPORTS GMRAIRPORT ULTRACEMCO GRASIM SHREECEM AMBUJACEM IRB",
     "overview": "Engineering & construction, ports, airports, roads and building materials such as cement. Growth follows public and private capital expenditure.",
     "drivers": ["Government infrastructure spending", "Private capex cycle", "Housing demand (for cement)"],
     "trends": ["Asset monetisation and public-private partnerships", "Cement capacity consolidation", "Logistics and port expansion"],
     "risks": ["Execution delays and cost overruns", "Working-capital stretch", "Input costs (fuel, steel)", "Policy and approval risk"],
     "valuation": ["EV/EBITDA; EV per tonne for cement", "Order book to sales for E&C companies", "Sum-of-the-parts for diversified groups"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "revenue_growth", "ebitda_margin", "debt_to_equity"],
     "disclosure_kpis": ["Order book & inflows", "Cement volumes and EBITDA per tonne", "Capacity utilisation", "Cargo / passenger traffic"]},
    {"id": "metals", "name": "Metals & mining", "icon": "pickaxe",
     "symbols": "TATASTEEL JSWSTEEL HINDALCO VEDL SAIL NMDC NATIONALUM JINDALSTEL",
     "overview": "Steel, aluminium, zinc, copper and iron-ore mining. Highly cyclical, capital-intensive businesses where profits swing with global commodity prices.",
     "drivers": ["Domestic steel demand from infrastructure and housing", "Global commodity cycles", "Capacity expansion"],
     "trends": ["Decarbonisation pressure (green steel)", "Trade measures and safeguard duties", "Integration into raw materials"],
     "risks": ["Commodity price swings", "High leverage during expansion", "Environmental regulation", "Cheap imports"],
     "valuation": ["EV/EBITDA on mid-cycle earnings", "P/B for cyclicals at the bottom of the cycle", "Net debt/EBITDA is critical"],
     "compare_metrics": ["market_cap", "ev_ebitda", "pb", "ebitda_margin", "debt_to_equity", "roce"],
     "disclosure_kpis": ["Sales volumes (tonnes)", "EBITDA per tonne", "Net debt", "Capacity & utilisation"]},
    {"id": "real-estate", "name": "Real estate", "icon": "building-2",
     "symbols": "DLF GODREJPROP LODHA OBEROIRLTY PRESTIGE PHOENIXLTD",
     "overview": "Residential developers and owners of commercial and retail assets. Residential developers recognise revenue on project completion, so reported profit lags sales; pre-sales are the key activity indicator.",
     "drivers": ["Housing demand and affordability", "Office demand from global capability centres", "Consolidation towards listed developers after RERA"],
     "trends": ["Strong residential pre-sales from branded developers", "Rental assets and REITs", "Joint-development land deals"],
     "risks": ["Interest rates and affordability", "Execution and approval delays", "Land and regulatory risk"],
     "valuation": ["NAV-based valuation and P/B", "Reported P/E is distorted by completion-based accounting"],
     "compare_metrics": ["market_cap", "pb", "pe", "revenue_growth", "debt_to_equity", "roe"],
     "disclosure_kpis": ["Pre-sales (bookings)", "Collections", "Net debt", "Launches", "Rental income (annuity assets)"]},
    {"id": "telecom", "name": "Telecommunications", "icon": "radio-tower",
     "symbols": "BHARTIARTL IDEA INDUSTOWER TATACOMM",
     "overview": "Mobile and broadband operators, tower companies and enterprise connectivity. A capital-intensive, consolidated market where pricing power depends on industry structure.",
     "drivers": ["Data consumption growth", "Tariff increases", "5G and fixed broadband"],
     "trends": ["Three-player market structure", "Enterprise and data-centre services", "Spectrum auctions and 5G monetisation"],
     "risks": ["High debt and spectrum liabilities", "Regulation by TRAI/DoT", "Price competition"],
     "valuation": ["EV/EBITDA is standard", "ARPU and subscriber trends drive estimates", "Net debt including lease and spectrum liabilities"],
     "compare_metrics": ["market_cap", "ev_ebitda", "revenue_growth", "ebitda_margin", "debt_to_equity", "roce"],
     "disclosure_kpis": ["ARPU", "Subscribers", "Data usage per user", "Capex", "Tenancy ratio (towers)"]},
    {"id": "consumer-durables", "name": "Consumer durables", "icon": "tv",
     "symbols": "TITAN HAVELLS VOLTAS DIXON BLUESTARCO CROMPTON WHIRLPOOL",
     "overview": "Jewellery, electricals, appliances, air-conditioners and electronics manufacturing services. Demand is discretionary and seasonal.",
     "drivers": ["Rising incomes and urbanisation", "Low penetration of appliances", "Production-linked incentive (PLI) schemes for electronics"],
     "trends": ["Electronics manufacturing in India", "Premiumisation", "Organised players gaining share in jewellery"],
     "risks": ["Discretionary demand slowdown", "Commodity costs (copper, aluminium, gold)", "Weather-driven seasonality (cooling products)"],
     "valuation": ["P/E reflects brand strength and growth", "Working capital and ROCE separate quality franchises"],
     "compare_metrics": ["market_cap", "pe", "revenue_growth", "ebitda_margin", "roce", "debt_to_equity"],
     "disclosure_kpis": ["Category growth", "Channel inventory", "Store additions", "Export / EMS order book"]},
    {"id": "chemicals", "name": "Chemicals & paints", "icon": "flask-conical",
     "symbols": "PIDILITIND ASIANPAINT SRF DEEPAKNTR AARTIIND NAVINFLUOR TATACHEM",
     "overview": "Specialty chemicals, fluorochemicals, adhesives and paints. Specialty chemical makers supply global customers; paints and adhesives are brand- and distribution-led consumer businesses.",
     "drivers": ["China+1 sourcing by global customers", "Domestic consumption (paints, adhesives)", "Capacity expansion in specialty chemistry"],
     "trends": ["Global destocking cycles", "New entrants in decorative paints", "Fluorochemicals and agrochemical intermediates"],
     "risks": ["Raw-material (crude-linked) volatility", "Chinese overcapacity and pricing", "Environmental compliance"],
     "valuation": ["P/E and EV/EBITDA versus growth and ROCE", "Capex intensity and asset turnover matter"],
     "compare_metrics": ["market_cap", "pe", "ev_ebitda", "revenue_growth", "ebitda_margin", "roce"],
     "disclosure_kpis": ["Volume growth", "Capacity utilisation", "Export share", "Gross margin"]},
]

for _ind in INDUSTRIES:
    _ind["symbols"] = [f"{s}.NS" for s in _ind["symbols"].split()]

BY_ID = {i["id"]: i for i in INDUSTRIES}
SYMBOL_INDUSTRY = {s: i["id"] for i in INDUSTRIES for s in i["symbols"]}

# fallback: map Yahoo sector/industry text to our industries for companies added later
_KEYWORDS = [("banking", ["bank"]), ("financial-services", ["insurance", "credit services", "capital markets", "asset management", "financial"]),
             ("it", ["information technology", "software"]), ("pharma", ["drug", "pharma"]), ("healthcare", ["medical", "health", "diagnostic"]),
             ("automobiles", ["auto", "vehicle", "motorcycle", "farm & heavy"]), ("fmcg", ["packaged foods", "household", "personal products", "tobacco", "beverages", "confectioner"]),
             ("agriculture", ["agricultural"]), ("energy", ["oil", "gas", "coal", "utilities", "power", "renewable"]),
             ("infrastructure", ["engineering & construction", "building materials", "infrastructure", "marine shipping", "airport"]),
             ("metals", ["steel", "aluminum", "metal", "mining", "copper"]), ("real-estate", ["real estate"]),
             ("telecom", ["telecom"]), ("consumer-durables", ["appliances", "electronic", "luxury", "electrical equipment", "furnishings"]),
             ("chemicals", ["chemical", "specialty"])]


def industry_of(symbol: str, sector: str | None = None, industry: str | None = None) -> str | None:
    if symbol in SYMBOL_INDUSTRY:
        return SYMBOL_INDUSTRY[symbol]
    text = f"{industry or ''} {sector or ''}".lower()
    for iid, words in _KEYWORDS:
        if any(w in text for w in words):
            return iid
    return None


def all_symbols() -> list[str]:
    return list(dict.fromkeys(s for i in INDUSTRIES for s in i["symbols"]))
