"""EquityPilot AI - entry point.  Run with:  streamlit run app.py"""
import streamlit as st

from equitypilot import config, db
from equitypilot.data import sample
from equitypilot.ui import components as ui
from equitypilot.ui import theme

st.set_page_config(page_title=config.APP_NAME, page_icon="assets/icon.svg", layout="wide",
                   initial_sidebar_state="expanded",
                   menu_items={"About": f"{config.APP_NAME} v{config.APP_VERSION} - {config.APP_TAGLINE}. "
                                        "Educational research tool; not investment advice."})
theme.inject_css()
st.logo("assets/logo.svg", size="large", icon_image="assets/icon.svg")


@st.cache_resource(show_spinner=False)
def bootstrap() -> bool:
    """Create the database and load the fictional sample companies once per server process."""
    db.get_engine()
    sample.load_sample_data()
    return True


bootstrap()


def page(path: str, title: str, icon: str, default: bool = False) -> st.Page:
    return st.Page(path, title=title, icon=f":material/{icon}:", default=default)


PAGES = {
    "Overview": [
        page("views/dashboard.py", "Dashboard", "dashboard", default=True),
    ],
    "Company research": [
        page("views/company.py", "Company Research", "apartment"),
        page("views/financials.py", "Financial Analysis", "table_chart"),
        page("views/valuation.py", "Valuation", "calculate"),
        page("views/technicals.py", "Technical Analysis", "candlestick_chart"),
        page("views/risk.py", "Risk Analysis", "shield"),
    ],
    "Tools": [
        page("views/screener.py", "Stock Screener", "filter_alt"),
        page("views/compare.py", "Company Comparison", "compare_arrows"),
    ],
}

nav = st.navigation(PAGES)
ui.sidebar_company_picker()
with st.sidebar:
    st.divider()
    mode = "Offline mode (sample data only)" if config.OFFLINE else "Online · Yahoo Finance (delayed) + your uploads"
    st.caption(f"{mode}\n\nEducational research tool. Not investment advice.")
nav.run()
