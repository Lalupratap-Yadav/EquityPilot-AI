"""AI Research Assistant: grounded Q&A over the company's data, documents and notes."""
import pandas as pd
import streamlit as st

from equitypilot import db
from equitypilot.ai import offline
from equitypilot.ai import providers as P
from equitypilot.ai.context import build_context, grounding_check
from equitypilot.data import repository as repo
from equitypilot.data import uploads as U
from equitypilot.ui import components as ui

ui.page_header("AI Research Assistant", "Ask about financials, ratios, valuation, results and risks - answers cite their sources")

settings = db.get_setting("ai_settings", {}) or {}
provider = settings.get("provider", "offline")

# ------------------------------------------------------------------ settings
with st.expander(f"Assistant settings · current engine: {dict(offline='Offline analyst (free)', anthropic='Claude API (paid)', ollama='Ollama (local, free)').get(provider)}",
                 icon=":material/settings:"):
    choice = st.radio("Answer engine", ["offline", "anthropic", "ollama"], index=["offline", "anthropic", "ollama"].index(provider),
                      format_func={"offline": "Offline analyst - free, rule-based, works without internet",
                                   "anthropic": "Claude API - best quality, PAID per use (needs your own API key)",
                                   "ollama": "Ollama - free open-source model running on your own computer"}.get,
                      key="ai_provider")
    new = dict(settings, provider=choice)
    if choice == "anthropic":
        st.warning("The Claude API is billed separately from a Claude Pro subscription - Pro does not include API "
                   "credits. You need an API key from console.anthropic.com with billing set up.")
        model = st.selectbox("Model", list(P.ANTHROPIC_MODELS), index=list(P.ANTHROPIC_MODELS).index(settings.get("model", "claude-opus-5-5")),
                             format_func=lambda m: P.ANTHROPIC_MODELS[m]["label"])
        rows = []
        for m, p in P.ANTHROPIC_MODELS.items():
            c_small, c_big = P.estimate_cost_usd(m, 6000, 900), P.estimate_cost_usd(m, 30000, 1500)
            rows.append({"Model": p["label"], "Input $/M tokens": p["in"], "Output $/M tokens": p["out"],
                         "≈ per question (company data only)": f"${c_small:.4f}",
                         "≈ per question (with a document)": f"${c_big:.4f}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(P.PRICING_NOTE + " Estimates assume ~6k input tokens (company data) or ~30k (with document excerpts).")
        key_found = P.find_api_key()
        if key_found:
            st.success("API key detected from Streamlit secrets / environment variable.")
        else:
            sk = st.text_input("Anthropic API key (kept for this browser session only, never saved)", type="password")
            if sk:
                st.session_state["anthropic_key"] = sk
        consent = st.checkbox("I understand each question is sent to Anthropic and billed to my API account.",
                              value=settings.get("consent", False))
        new.update(model=model, consent=consent)
    elif choice == "ollama":
        host = st.text_input("Ollama host", settings.get("ollama_host", "http://localhost:11434"))
        models = P.ollama_available(host)
        if models is None:
            st.info("Ollama is not running. Install it from ollama.com, then run e.g. `ollama pull llama3.1:8b`. "
                    "Smaller local models are less reliable at following grounding rules than Claude.")
            om = st.text_input("Model name", settings.get("ollama_model", "llama3.1:8b"))
        else:
            om = st.selectbox("Installed model", models or ["(none installed)"])
        new.update(ollama_host=host, ollama_model=om)
    if st.button("Save settings", type="primary"):
        db.set_setting("ai_settings", new)
        st.rerun()

# ------------------------------------------------------------------ context
sym = ui.current_symbol()
company = repo.get_company(sym) if sym else None
c1, c2 = st.columns([3, 2])
with c1:
    if company:
        st.markdown(f"**Company context:** {company['name']} ({sym}) " + (ui.badge("sample") if company.get("is_sample") else ""),
                    unsafe_allow_html=True)
    else:
        st.info("No company selected - you can still ask finance concept questions. Pick a company in the sidebar for company analysis.")
docs = U.list_documents(sym) if sym else pd.DataFrame()
doc_ids = []
with c2:
    if not docs.empty:
        doc_ids = st.multiselect("Include uploaded documents", docs["id"].tolist(),
                                 format_func=lambda i: docs.set_index("id").loc[i, "filename"], key=f"ai_docs_{sym}")
    elif sym:
        st.caption("Upload an annual report in the Data Manager to ask about it.")

hist_key = f"chat:{sym or 'none'}"
history = st.session_state.setdefault(hist_key, [])

SUGGESTIONS = ["Give me an overview of the company", "How has revenue and profit grown?", "Is the balance sheet strong?",
               "How good is the cash conversion?", "How is it valued?", "What are the key risks?", "What is ROCE?"]
if docs is not None and not docs.empty:
    SUGGESTIONS.insert(1, "Summarise the uploaded annual report")
picked = st.pills("Suggested questions", SUGGESTIONS, key=f"sugg_{len(history)}")

for m in history:
    with st.chat_message(m["role"], avatar=":material/person:" if m["role"] == "user" else ":material/insights:"):
        st.markdown(m["content"])
        if m.get("meta"):
            st.caption(m["meta"])
        if m.get("sources") is not None and len(m["sources"]):
            with st.expander("Sources used"):
                st.dataframe(m["sources"], hide_index=True, width="stretch",
                             column_config={"Link": st.column_config.LinkColumn()})

question = st.chat_input("Ask about this company or a finance concept…") or picked
if question:
    history.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(question)
    with st.chat_message("assistant", avatar=":material/insights:"):
        with st.spinner("Gathering sources…"):
            ctx = build_context(sym, question, doc_ids) if company else None
        ctx_text = ctx.render() if ctx else ""
        meta, text = "", ""
        if provider == "offline" or not ctx:
            text = offline.answer(ctx, question)
            meta = "Engine: offline analyst (rule-based, deterministic). Figures come directly from the cited sources."
        else:
            llm_hist = [{"role": h["role"], "content": h["content"]} for h in history[:-1] if h["role"] in ("user", "assistant")]
            try:
                with st.spinner("Asking the AI model…"):
                    if provider == "anthropic":
                        key = P.find_api_key(st.session_state.get("anthropic_key"))
                        if not key:
                            raise P.ProviderError("No API key configured - add one in Assistant settings.")
                        if not settings.get("consent"):
                            raise P.ProviderError("Tick the billing acknowledgement in Assistant settings first.")
                        res = P.ask_anthropic(ctx_text, llm_hist, question, settings.get("model", "claude-opus-5-5"), key)
                    else:
                        res = P.ask_ollama(ctx_text, llm_hist, question, settings.get("ollama_model", "llama3.1:8b"),
                                           settings.get("ollama_host", "http://localhost:11434"))
                text = res.text
                total, untraced = grounding_check(text, ctx_text)
                cost = P.estimate_cost_usd(res.model, res.input_tokens or 0, res.output_tokens or 0) if provider == "anthropic" else None
                meta = (f"Engine: {res.model}" + (f" · tokens in/out {res.input_tokens:,}/{res.output_tokens:,}" if res.input_tokens else "")
                        + (f" · est. cost ${cost:.4f}" if cost else "") + f" · Grounding check: {total - len(untraced)} of {total} "
                        "figures found in the sources")
                if untraced:
                    meta += f" - not found verbatim: {', '.join(untraced[:8])} (may be calculations; verify)"
                if res.note:
                    meta += f" · {res.note}"
            except P.ProviderError as exc:
                st.warning(f"{exc} Falling back to the offline analyst.")
                text = offline.answer(ctx, question)
                meta = "Engine: offline analyst (fallback)."
        st.markdown(text)
        st.caption(meta)
        src = ctx.source_list() if ctx else None
        if src is not None and len(src):
            with st.expander("Sources used"):
                st.dataframe(src, hide_index=True, width="stretch", column_config={"Link": st.column_config.LinkColumn()})
    history.append({"role": "assistant", "content": text, "meta": meta, "sources": src})
    db.log_activity("Asked assistant", f"{sym or '-'}: {question[:60]}")

if history:
    c1, c2, _ = st.columns([1, 1, 3])
    transcript = "\n\n".join(f"## {m['role'].title()}\n{m['content']}" + (f"\n\n_{m['meta']}_" if m.get("meta") else "") for m in history)
    c1.download_button("Download transcript", transcript.encode(), f"equitypilot_chat_{sym or 'general'}.md", mime="text/markdown",
                       icon=":material/download:")
    if c2.button("Clear conversation", icon=":material/delete_sweep:"):
        st.session_state[hist_key] = []
        st.rerun()
st.caption("The assistant uses only EquityPilot's stored data, your notes and selected documents. It does not give "
           "investment recommendations. Always verify important figures against official filings.")
