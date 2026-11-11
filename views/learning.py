"""Learning Centre: NISM Series XV and MBA Finance concepts, formulas, live examples and quizzes."""
import pandas as pd
import streamlit as st

from equitypilot import db
from equitypilot import formatting as F
from equitypilot.analytics import ratios as R
from equitypilot.content.glossary import GLOSSARY
from equitypilot.content.learning import MODULES, total_questions
from equitypilot.data import repository as repo
from equitypilot.ui import components as ui

ui.page_header("Learning Centre", "Equity research concepts for NISM Series XV and MBA Finance - with formulas, live examples and quizzes")

progress = db.get_setting("learning_progress", {}) or {}
done = sum(1 for m in MODULES if m["id"] in progress)
best = sum(progress.get(m["id"], {}).get("best", 0) for m in MODULES)
ui.kpis([{"label": "Modules completed", "value": f"{done} / {len(MODULES)}"},
         {"label": "Best quiz score", "value": f"{best} / {total_questions()}"},
         {"label": "Glossary terms", "value": str(len(GLOSSARY))}])

tab_learn, tab_gloss, tab_prog = st.tabs(["Modules", "Glossary", "My progress"])

with tab_learn:
    titles = {m["id"]: f"{i + 1}. {m['title']}" + (" ✓" if m["id"] in progress else "") for i, m in enumerate(MODULES)}
    mid = st.selectbox("Module", list(titles), format_func=titles.get, key="learn_mod")
    m = next(x for x in MODULES if x["id"] == mid)
    st.markdown(f"### {m['title']}")
    st.caption(m["summary"])
    for heading, body in m["sections"]:
        st.markdown(f"##### {heading}")
        st.markdown(body)
    if m["formulas"]:
        st.markdown("##### Key formulas")
        for f in m["formulas"]:
            ui.formula(f)

    # ---- live worked example on a sample company
    if mid in ("ratios", "statements", "valuation"):
        st.markdown("##### Worked example (fictional SAMPLE company)")
        fd = repo.get_financials("SAMPLE-ALPHA", auto_refresh=False)
        if not fd.empty:
            last = fd.periods[-1]
            ni, rev = fd.get("net_income")[last], fd.get("revenue")[last]
            eq_avg = (fd.get("total_equity").iloc[-1] + fd.get("total_equity").iloc[-2]) / 2
            if mid == "ratios":
                dp = R.dupont(fd).iloc[:, -1]
                st.markdown(f"""Alpha Consumer Products Ltd (Sample), {F.fiscal_label(last)}:
- Net profit {F.crore(ni)}, revenue {F.crore(rev)} → **net margin = {F.pct(ni / rev)}**
- Average equity {F.crore(eq_avg)} → **ROE = {F.crore(ni)} / {F.crore(eq_avg)} = {F.pct(ni / eq_avg)}**
- DuPont: {F.pct(dp['Net margin'])} × {dp['Asset turnover']:.2f} × {dp['Equity multiplier']:.2f} = **{F.pct(dp['ROE (product)'])}**""")
            elif mid == "statements":
                cfo, capex = fd.get("cfo")[last], fd.get("capex")[last]
                st.markdown(f"""Alpha Consumer Products Ltd (Sample), {F.fiscal_label(last)}:
- Cash from operations {F.crore(cfo)}, capex {F.crore(capex)} → **free cash flow = {F.crore(cfo + capex)}**
- Net profit {F.crore(ni)} → cash conversion (CFO / net profit) = **{cfo / ni:.2f}x**""")
            else:
                st.markdown("""With Rf = 7.0%, β = 0.70, ERP = 7.0%: **Ke = 7.0% + 0.70 × 7.0% = 11.9%**.
If debt is 5% of capital at a post-tax cost of 6.4%: **WACC = 0.95 × 11.9% + 0.05 × 6.4% ≈ 11.6%**.
Open the Valuation page with a sample company to see the full DCF.""")
    st.page_link(m["page"], label="Try it in the app →", icon=":material/arrow_forward:")

    # ---- quiz
    st.markdown("##### Quiz")
    with st.form(f"quiz_{mid}"):
        answers = []
        for i, (q, opts, _, _) in enumerate(m["quiz"]):
            answers.append(st.radio(f"Q{i + 1}. {q}", range(len(opts)), format_func=lambda j, o=opts: o[j], index=None,
                                    key=f"q_{mid}_{i}"))
        submitted = st.form_submit_button("Check answers", type="primary")
    if submitted:
        score = 0
        for i, ((q, opts, correct, why), a) in enumerate(zip(m["quiz"], answers)):
            ok = a == correct
            score += ok
            (st.success if ok else st.error)(f"Q{i + 1}: {'Correct' if ok else 'Not quite'} - answer: **{opts[correct]}**. {why}")
        st.metric("Your score", f"{score} / {len(m['quiz'])}")
        prev = progress.get(mid, {})
        progress[mid] = {"best": max(score, prev.get("best", 0)), "last": score, "attempts": prev.get("attempts", 0) + 1,
                         "updated": F.ist(db.utcnow())}
        db.set_setting("learning_progress", progress)
        db.log_activity("Completed quiz", f"{m['title']}: {score}/{len(m['quiz'])}")

with tab_gloss:
    q = st.text_input("Search terms", placeholder="e.g. ROCE, WACC, beta, consolidated")
    for name, e in GLOSSARY.items():
        hay = (name + " " + " ".join(e["aliases"]) + " " + e["definition"]).lower()
        if q and q.lower() not in hay:
            continue
        with st.expander(name):
            st.write(e["definition"])
            if e.get("formula") and e["formula"] != "—":
                ui.formula(e["formula"])
            st.caption(e["interpretation"])

with tab_prog:
    rows = [{"Module": m["title"], "Best score": f"{progress[m['id']]['best']} / {len(m['quiz'])}" if m["id"] in progress else "—",
             "Attempts": progress.get(m["id"], {}).get("attempts", 0), "Last attempt": progress.get(m["id"], {}).get("updated", "—")}
            for m in MODULES]
    st.dataframe(pd.DataFrame(rows), hide_index=True, placeholder="—", width="stretch")
    if progress and st.button("Reset progress"):
        db.set_setting("learning_progress", {})
        st.rerun()
    st.caption("Content is a simplified educational overview. For exam preparation, use the official NISM Series XV "
               "workbook and the current SEBI regulations.")
