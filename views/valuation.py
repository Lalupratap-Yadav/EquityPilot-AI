"""Valuation: multiples, DCF (FCFF), scenarios, sensitivity, reverse DCF, relative and bank valuation."""
from dataclasses import asdict, replace

import numpy as np
import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.analytics import ratios as R
from equitypilot.analytics import valuation as V
from equitypilot.analytics.screener import company_metrics
from equitypilot.data import repository as repo
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Valuation", "Relative and intrinsic valuation with transparent, editable assumptions")
ui.company_header(company, quote)

fd = repo.get_financials(sym)
fq = repo.get_financials(sym, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
snap = V.market_snapshot(quote, fd, fq)
price = snap.get("price")
fin = R.is_financial(company)
ui.note("Valuation outputs are model estimates that depend entirely on the assumptions shown. They are an "
        "analytical exercise, not a recommendation to buy or sell.", "info")

tabs = st.tabs(["Multiples", "DCF (FCFF)", "Scenarios & sensitivity", "Relative to peers", "Banks: justified P/B"])

# ------------------------------------------------------------------ multiples
with tabs[0]:
    ui.kpis([
        {"label": "Market cap", "value": F.big_inr(snap.get("market_cap"))},
        {"label": "Enterprise value", "value": "n.m." if fin else F.big_inr(snap.get("ev")), "help": V.MULTIPLE_FORMULAS["ev"]},
        {"label": "P/E", "value": F.mult(snap.get("pe")), "delta": snap["basis"].get("earnings") or "", "help": V.MULTIPLE_FORMULAS["pe"]},
        {"label": "P/B", "value": F.mult(snap.get("pb")), "help": V.MULTIPLE_FORMULAS["pb"]},
        {"label": "EV/EBITDA", "value": "n.m." if fin else F.mult(snap.get("ev_ebitda")), "delta": "" if fin else (snap["basis"].get("ebitda") or ""), "help": V.MULTIPLE_FORMULAS["ev_ebitda"]},
        {"label": "EV/Sales", "value": "n.m." if fin else F.mult(snap.get("ev_sales"), 2), "help": V.MULTIPLE_FORMULAS["ev_sales"]},
        {"label": "Earnings yield", "value": F.pct(snap.get("earnings_yield")), "help": "Net profit / Market cap (inverse of P/E)."},
        {"label": "Dividend yield", "value": F.pct(snap.get("dividend_yield")), "help": V.MULTIPLE_FORMULAS["dividend_yield"]},
    ])
    with st.expander("How these are calculated", icon=":material/function:"):
        for k, f in V.MULTIPLE_FORMULAS.items():
            ui.formula(f)
        st.caption("Earnings basis: " + (snap["basis"].get("earnings") or "—") + ". "
                   "Balance-sheet items: " + (snap["basis"].get("balance_sheet") or "—") + ".")

    st.markdown("##### Valuation history at each fiscal year-end")
    px = repo.get_prices(sym, auto_refresh=False)
    if fd.empty or px.empty:
        st.caption("Needs both statements and price history.")
    else:
        rows = []
        for p in fd.periods:
            before = px[px["date"] <= pd.Timestamp(p)]
            if before.empty or (pd.Timestamp(p) - before["date"].iloc[-1]).days > 10:
                continue
            close = float(before["close"].iloc[-1])
            eps = fd.get("eps_diluted")[p]
            shares = fd.get("shares_outstanding")[p]
            bv = fd.get("total_equity")[p]
            rows.append({"FY": F.fiscal_label(p), "Price at FY end": close,
                         "P/E": close / eps if eps and eps > 0 else np.nan,
                         "P/B": close * shares / bv if shares and bv and bv > 0 else np.nan})
        if not rows:
            st.caption("Price history does not cover the fiscal year-end dates.")
        else:
            hist = pd.DataFrame(rows).set_index("FY")
            c1, c2 = st.columns(2)
            c1.plotly_chart(C.lines(hist[["P/E"]], "P/E at fiscal year-end", ysuffix="x", height=280), width="stretch", config=C.config())
            c2.plotly_chart(C.lines(hist[["P/B"]], "P/B at fiscal year-end", ysuffix="x", height=280), width="stretch", config=C.config())
            st.caption("Uses the closing price on (or just before) each fiscal year-end and that year's reported EPS and book value. "
                       "Note: the price series is not adjusted for later splits/bonus issues unless the provider adjusted it.")
    ui.source_footer([(quote or {}).get("source")] + fd.sources, (quote or {}).get("fetched_at"), basis=fd.basis)

# ------------------------------------------------------------------ DCF
with tabs[1]:
    if fin:
        ui.note("A free-cash-flow (FCFF) DCF is not appropriate for banks and financial companies: debt is an "
                "operating input, not financing, so 'free cash flow to the firm' has no clean meaning. Use the "
                "'Banks: justified P/B' tab (a residual-income style approach) instead.", "warn")
    base, notes = V.default_dcf_inputs(fd, quote)
    if base is None:
        ui.empty_state("DCF cannot be built", notes.get("error", "Insufficient data."))
    elif not fin:
        k = lambda name: f"dcf_{name}_{sym}"  # noqa: E731 - per-company widget keys
        st.markdown("##### 1 · Cost of capital (CAPM / WACC)")
        st.caption("All inputs below are ASSUMPTIONS. Verify the risk-free rate against the current 10-year "
                   "Government of India bond yield (RBI / CCIL) on your valuation date.")
        c1, c2, c3, c4, c5 = st.columns(5)
        rf = c1.number_input("Risk-free rate %", 0.0, 20.0, 7.0, 0.1, key=k("rf"),
                             help="Approx. 10-year G-sec yield. Enter the value as of your valuation date.") / 100
        beta_default = float(quote.get("beta")) if quote and quote.get("beta") and 0.2 < quote["beta"] < 3 else 1.0
        beta = c2.number_input("Beta", 0.0, 3.0, round(beta_default, 2), 0.05, key=k("beta"),
                               help=f"Provider beta: {F.num(quote.get('beta') if quote else None)}. Bounded to a sensible range; "
                                    "you can also use the beta computed on the Technical Analysis page.")
        erp = c3.number_input("Equity risk premium %", 0.0, 15.0, 7.0, 0.25, key=k("erp"),
                              help="Market return above the risk-free rate. Practitioner estimates for India commonly sit around 6-8%.") / 100
        int_exp, debt_now = fd.latest("interest_expense"), fd.latest("total_debt")
        kd_hist = abs(int_exp) / debt_now if int_exp and debt_now and debt_now > 0 else None
        kd_default = float(np.clip(kd_hist, 0.06, 0.14)) * 100 if kd_hist else 9.0
        kd = c4.number_input("Pre-tax cost of debt %", 0.0, 25.0, round(kd_default, 2), 0.25, key=k("kd"),
                             help=f"Default: finance costs / borrowings = {F.pct(kd_hist)} (bounded 6-14%)." if kd_hist else "Default 9%.") / 100
        tax = c5.number_input("Tax rate %", 0.0, 50.0, round(base.tax_rate * 100, 1), 0.5, key=k("tax"),
                              help=notes.get("tax_rate")) / 100
        mcap = snap.get("market_cap") or 0
        w = V.wacc(rf, beta, erp, kd, tax, mcap, debt_now or 0)
        ui.kpis([
            {"label": "Cost of equity (Ke)", "value": F.pct(w["ke"]), "help": "Ke = Rf + β × ERP"},
            {"label": "Post-tax cost of debt", "value": F.pct(w["kd_post_tax"]), "help": "Kd × (1 - tax rate)"},
            {"label": "Weight of equity", "value": F.pct(w["we"]), "help": "Market cap / (Market cap + Borrowings)"},
            {"label": "WACC", "value": F.pct(w["wacc"]), "help": "WACC = We × Ke + Wd × Kd × (1 - t)"},
        ])
        override = st.toggle("Override WACC manually", key=k("ovr"))
        wacc_used = st.slider("WACC used %", 6.0, 20.0, round(w["wacc"] * 100, 2), 0.1, key=k("wacc")) / 100 if override else w["wacc"]

        st.markdown("##### 2 · Operating assumptions")
        c1, c2, c3, c4 = st.columns(4)
        years = c1.slider("Explicit forecast years", 3, 10, 5, key=k("years"))
        g1 = c2.number_input("Revenue growth, year 1 %", -20.0, 60.0, round(base.growth_start * 100, 1), 0.5, key=k("g1"),
                             help=notes.get("growth_start")) / 100
        gN = c3.number_input(f"Revenue growth, year {years} %", -20.0, 60.0, round(base.growth_end * 100, 1), 0.5, key=k("gN"),
                             help=notes.get("growth_end")) / 100
        tg = c4.number_input("Terminal growth %", 0.0, 10.0, 5.0, 0.25, key=k("tg"),
                             help="Long-run nominal growth after the forecast. Should not exceed long-run nominal GDP growth.") / 100
        c1, c2, c3, c4 = st.columns(4)
        margin = c1.number_input("EBIT margin %", -50.0, 80.0, round(base.ebit_margin * 100, 1), 0.5, key=k("m"),
                                 help=notes.get("ebit_margin")) / 100
        da = c2.number_input("D&A % of revenue", 0.0, 40.0, round(base.da_pct * 100, 2), 0.25, key=k("da"), help=notes.get("da_pct")) / 100
        capex = c3.number_input("Capex % of revenue", 0.0, 60.0, round(base.capex_pct * 100, 2), 0.25, key=k("capex"),
                                help=notes.get("capex_to_revenue")) / 100
        nwc = c4.number_input("ΔNWC % of Δrevenue", -50.0, 100.0, round(base.nwc_pct * 100, 1), 1.0, key=k("nwc"),
                              help=notes.get("nwc_pct")) / 100
        inputs = replace(base, years=years, growth_start=g1, growth_end=gN, terminal_growth=tg, ebit_margin=margin,
                         da_pct=da, capex_pct=capex, nwc_pct=nwc, wacc=wacc_used, tax_rate=tax)
        try:
            res = V.run_dcf(inputs)
        except V.DCFError as exc:
            st.error(str(exc))
            res = None
        if res:
            st.session_state[f"dcf_inputs:{sym}"] = inputs
            st.markdown("##### 3 · Result")
            updown = res.per_share / price - 1 if price else None
            ui.kpis([
                {"label": "Intrinsic value / share", "value": F.inr(res.per_share)},
                {"label": "Market price", "value": F.inr(price)},
                {"label": "Model vs market", "value": F.pct(updown, signed=True) if updown is not None else F.MISSING,
                 "sign": 1 if updown and updown > 0 else -1 if updown else 0,
                 "help": "Difference between model value and market price under these assumptions - not a recommendation."},
                {"label": "Enterprise value", "value": F.big_inr(res.enterprise_value)},
                {"label": "Terminal value share", "value": F.pct(res.terminal_share),
                 "help": "Share of EV from the terminal value. Above ~75% means the result is dominated by long-run assumptions."},
            ])
            if res.terminal_share > 0.8:
                ui.note(f"{res.terminal_share:.0%} of the value comes from the terminal value - the result is highly "
                        "sensitive to WACC and terminal growth. See the sensitivity table.", "warn")
            proj = res.projection.copy()
            show = pd.DataFrame({
                f"Y{t}": [F.pct(r["Growth"]), F.crore(r["Revenue"], 0, False), F.crore(r["EBIT"], 0, False),
                          F.crore(r["NOPAT"], 0, False), F.crore(r["D&A"], 0, False), F.crore(-r["Capex"], 0, False),
                          F.crore(-r["ΔNWC"], 0, False), F.crore(r["FCFF"], 0, False), f"{r['Discount factor']:.3f}",
                          F.crore(r["PV of FCFF"], 0, False)] for t, r in proj.iterrows()},
                index=["Revenue growth", "Revenue", "EBIT", "NOPAT = EBIT × (1 - t)", "+ D&A", "- Capex", "- Increase in NWC",
                       "FCFF", "Discount factor", "PV of FCFF"])
            show.index.name = "₹ Cr"
            ui.fin_table(show, bold={"FCFF", "PV of FCFF"})
            bridge = pd.DataFrame({"₹ Cr": [F.crore(res.pv_fcff, 0, False), F.crore(res.terminal_value, 0, False),
                                            F.crore(res.pv_terminal, 0, False), F.crore(res.enterprise_value, 0, False),
                                            F.crore(abs(inputs.net_debt), 0, False), F.crore(inputs.minority_interest, 0, False),
                                            F.crore(res.equity_value, 0, False), f"{inputs.shares / config.CRORE:,.2f} Cr",
                                            F.inr(res.per_share)]},
                                  index=["Sum of PV of FCFF", "Terminal value (Gordon growth)", "PV of terminal value",
                                         "Enterprise value",
                                         "Less: net debt (borrowings - cash)" if inputs.net_debt >= 0 else "Add: net cash (cash - borrowings)",
                                         "Less: minority interest",
                                         "Equity value", "Shares outstanding", "Value per share"])
            bridge.index.name = "EV → equity bridge"
            ui.fin_table(bridge, bold={"Enterprise value", "Equity value", "Value per share"})
            ui.formula("FCFF = EBIT×(1-t) + D&A - Capex - ΔNWC ·  TV = FCFF_N × (1+g) / (WACC - g) ·  "
                       "EV = Σ FCFF_t/(1+WACC)^t + TV/(1+WACC)^N ·  Equity = EV - Net debt - Minority interest")
            if st.button("Save this valuation for the research report", icon=":material/save:"):
                db.set_setting(f"valuation:{sym}", {"inputs": asdict(inputs), "per_share": res.per_share,
                                                    "price": price, "saved": F.ist(db.utcnow()),
                                                    "wacc_detail": {k2: float(v) for k2, v in w.items()},
                                                    "rf": rf, "beta": beta, "erp": erp, "kd": kd})
                db.log_activity("Saved DCF valuation", f"{sym} → ₹{res.per_share:,.0f}")
                st.success("Saved. The PDF report will include these assumptions and results.")
            ui.source_footer(["Calculated by EquityPilot from statements and user assumptions"] + fd.sources,
                             fd.fetched_at, basis=fd.basis, period=f"Base year: {F.fiscal_label(fd.periods[-1])}")

# ------------------------------------------------------------------ scenarios & sensitivity
with tabs[2]:
    inputs = st.session_state.get(f"dcf_inputs:{sym}")
    if fin:
        st.info("Scenario DCF is not applicable to financial companies - see 'Banks: justified P/B'.")
    elif inputs is None:
        ui.empty_state("Build the DCF first", "Open the 'DCF (FCFF)' tab - its assumptions feed the scenarios here.")
    else:
        st.markdown("##### Bear / base / bull")
        st.caption("Each scenario shifts the base-case assumptions by the amounts below (percentage points). Edit to suit your thesis.")
        shifts = pd.DataFrame(V.SCENARIO_SHIFTS, index=["Growth shift", "EBIT margin shift", "WACC shift", "Terminal growth shift"]).T * 100
        edited = st.data_editor(shifts, width="stretch", key=f"scn_{sym}",
                                column_config={c: st.column_config.NumberColumn(format="%+.2f pp") for c in shifts.columns})
        scn = V.scenarios(inputs, {n: tuple(edited.loc[n] / 100) for n in edited.index})
        vals = {n: (r.per_share if isinstance(r, V.DCFResult) else np.nan) for n, r in scn.items()}
        for n, r in scn.items():
            if isinstance(r, str):
                st.warning(f"{n}: {r}")
        c1, c2 = st.columns([3, 2], gap="large")
        c1.plotly_chart(C.scenario_bars(list(vals), list(vals.values()), price, "Value per share by scenario"),
                        width="stretch", config=C.config())
        with c2:
            t = pd.DataFrame({n: {"Value / share": F.inr(r.per_share), "vs market": F.pct(r.per_share / price - 1, signed=True) if price else F.MISSING,
                                  "WACC": F.pct(inputs.wacc + edited.loc[n, "WACC shift"] / 100),
                                  "TV share of EV": F.pct(r.terminal_share)}
                              for n, r in scn.items() if isinstance(r, V.DCFResult)})
            t.index.name = "Scenario"
            ui.fin_table(t)
        st.session_state[f"dcf_scenarios:{sym}"] = vals

        st.markdown("##### Sensitivity: value per share (₹) by WACC and terminal growth")
        waccs = [round(inputs.wacc + d, 4) for d in (-0.02, -0.01, 0, 0.01, 0.02)]
        gs = [round(inputs.terminal_growth + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
        grid = V.sensitivity(inputs, waccs, gs)
        st.session_state[f"dcf_sensitivity:{sym}"] = grid
        if price:
            st.plotly_chart(C.heatmap(grid, diverging=True, fmt=",.0f", zmid=price, xlabel="Terminal growth",
                                      ylabel="WACC", height=320), width="stretch", config=C.config())
            st.caption(f"Colour: blue = above the market price (₹{price:,.0f}), red = below. Cells are values per share in ₹.")
        else:
            st.plotly_chart(C.heatmap(grid, fmt=",.0f", xlabel="Terminal growth", ylabel="WACC", height=320),
                            width="stretch", config=C.config())

        st.markdown("##### Reverse DCF - what growth is the market pricing in?")
        if price:
            implied = V.reverse_dcf(inputs, price)
            if implied is None:
                st.caption("No growth rate between -20% and 60% reproduces the market price with these margins and WACC.")
            else:
                st.metric("Implied constant revenue growth (explicit period)", F.pct(implied),
                          help="The growth rate that makes the DCF value equal the market price, holding all other assumptions fixed.")
                hist = R.cagr(fd.get("revenue"), 3)
                st.caption(f"Compare with the historical 3-year revenue CAGR of {F.pct(hist)}. A large gap means the "
                           "market price assumes a very different future from the past.")

# ------------------------------------------------------------------ relative valuation
with tabs[3]:
    peers = repo.get_peers(sym)
    if not peers:
        ui.empty_state("No peers", "Set a peer group on the Company Research page (Peers tab).")
    else:
        pm = pd.DataFrame([company_metrics(p) for p in peers])
        show = pd.DataFrame({"Company": pm["name"], "P/E": pm["pe"], "P/B": pm["pb"], "EV/EBITDA": pm["ev_ebitda"],
                             "ROE %": pm["roe"] * 100, "Data": pm["data_type"].map(lambda t: config.DATA_TYPES[t][0])})
        st.dataframe(show, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.1f") for c in ["P/E", "P/B", "EV/EBITDA", "ROE %"]})
        rel = V.peer_relative(snap, pm)
        if not rel.empty:
            names = {"pe": "P/E × net profit", "pb": "P/B × book value", "ev_ebitda": "EV/EBITDA × EBITDA - net debt"}
            out = pd.DataFrame({
                "Method": rel["Method"].map(names), "Peer median": rel["Peer median"].map(F.mult),
                "Peers used": rel["Peers used"], "Implied price": rel["Implied price"].map(F.inr),
                "vs market": (rel["Implied price"] / price - 1).map(lambda v: F.pct(v, signed=True)) if price else F.MISSING,
            })
            if fin:
                out = out[out["Method"] != names["ev_ebitda"]]
            st.dataframe(out, hide_index=True, width="stretch")
            st.caption("Peer medians exclude negative multiples. Relative valuation assumes peers are fairly valued "
                       "and comparable in growth, risk and accounting basis - check that before relying on it.")

# ------------------------------------------------------------------ banks
with tabs[4]:
    if not fin:
        st.caption("Designed for banks/NBFCs/insurers, but you can use it for any company with stable ROE.")
    rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
    roe_hist = rt.loc["roe"].dropna().iloc[-3:].mean() if not rt.empty and "roe" in rt.index else None
    bvps = (fd.latest("total_equity") / (snap.get("shares") or fd.latest("shares_outstanding"))) if fd.latest("total_equity") and (snap.get("shares") or fd.latest("shares_outstanding")) else None
    c1, c2, c3 = st.columns(3)
    roe_in = c1.number_input("Sustainable ROE %", -20.0, 50.0, round((roe_hist or 0.14) * 100, 1), 0.25, key=f"jpb_roe_{sym}",
                             help=f"Default: 3-yr average ROE {F.pct(roe_hist)}.") / 100
    ke_in = c2.number_input("Cost of equity %", 5.0, 25.0, 13.5, 0.25, key=f"jpb_ke_{sym}",
                            help="CAPM: Rf + β × ERP (see DCF tab).") / 100
    g_in = c3.number_input("Long-run growth %", 0.0, 15.0, 6.0, 0.25, key=f"jpb_g_{sym}") / 100
    jpb = V.justified_pb(roe_in, ke_in, g_in)
    ui.formula("Justified P/B = (ROE - g) / (Ke - g)  ·  Value per share = Justified P/B × Book value per share")
    if jpb is None:
        st.error("Cost of equity must exceed growth.")
    else:
        val = jpb * bvps if bvps else None
        ui.kpis([{"label": "Justified P/B", "value": F.mult(jpb, 2)},
                 {"label": "Current P/B", "value": F.mult(snap.get("pb"), 2)},
                 {"label": "Book value / share", "value": F.inr(bvps)},
                 {"label": "Implied value / share", "value": F.inr(val)},
                 {"label": "vs market", "value": F.pct(val / price - 1, signed=True) if val and price else F.MISSING}])
        st.caption("A bank earning ROE above its cost of equity deserves P/B above 1x. For banks, also review asset quality "
                   "(GNPA/NNPA), capital adequacy (CRAR) and CASA ratio from the company's quarterly disclosures.")
