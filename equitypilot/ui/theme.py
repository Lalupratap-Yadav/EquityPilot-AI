"""Global CSS for the institutional look. Restrained: no gradients, no animation, one accent."""
from __future__ import annotations

import streamlit as st

NAVY = "#0B1F3A"
BLUE = "#1D4ED8"
CHARCOAL = "#1F2937"
MUTED = "#6B7280"
BORDER = "#E3E8F0"
SURFACE = "#F4F6FA"

CSS = f"""
<style>
:root {{ --ep-navy:{NAVY}; --ep-blue:{BLUE}; --ep-ink:{CHARCOAL}; --ep-muted:{MUTED};
        --ep-border:{BORDER}; --ep-surface:{SURFACE}; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 4.5rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3 {{ color: var(--ep-navy); letter-spacing: -0.01em; }}
h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; margin-top: .6rem; }}
[data-testid="stSidebar"] .ep-brand {{ padding: 2px 4px 10px 4px; }}
.ep-brand-name {{ font-size: 1.15rem; font-weight: 700; color: #FFFFFF; letter-spacing: -.01em; }}
.ep-brand-tag {{ font-size: .72rem; color: #9FB3D1; line-height: 1.3; }}

/* page header */
.ep-header {{ border-bottom: 1px solid var(--ep-border); padding-bottom: .7rem; margin-bottom: 1.1rem; }}
.ep-header h1 {{ font-size: 1.6rem; font-weight: 700; margin: 0; padding: 0; }}
.ep-header .ep-sub {{ color: var(--ep-muted); font-size: .92rem; margin-top: .25rem; }}

/* badges */
.ep-badge {{ display:inline-block; font-size:.68rem; font-weight:600; letter-spacing:.04em;
            padding:2px 7px; border-radius:4px; margin-right:4px; vertical-align: middle;
            border:1px solid transparent; white-space:nowrap; }}
.ep-b-sample {{ background:#FFF4D6; color:#7A4F00; border-color:#F3D68A; }}
.ep-b-delayed {{ background:#E8F0FE; color:#1D4ED8; border-color:#C7D8FB; }}
.ep-b-historical {{ background:#EEF2F7; color:#334155; border-color:#D9E0EA; }}
.ep-b-third_party {{ background:#EEF2F7; color:#334155; border-color:#D9E0EA; }}
.ep-b-official_upload {{ background:#E7F6EC; color:#106B2E; border-color:#BFE5CB; }}
.ep-b-user_entered {{ background:#F1ECFB; color:#5B3BA8; border-color:#DCD0F5; }}
.ep-b-calculated {{ background:#F4F6FA; color:#475569; border-color:#E3E8F0; }}
.ep-b-assumption {{ background:#FDEEE6; color:#9A3D12; border-color:#F6CDB8; }}
.ep-b-neutral {{ background:#F4F6FA; color:#475569; border-color:#E3E8F0; }}

/* KPI grid */
.ep-kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin: .2rem 0 1rem 0; }}
.ep-kpi {{ border:1px solid var(--ep-border); border-radius:8px; padding:11px 13px; background:#fff; min-width:0; }}
.ep-kpi .l {{ font-size:.72rem; color:var(--ep-muted); text-transform:uppercase; letter-spacing:.05em;
             font-weight:600; line-height:1.25; }}
.ep-kpi .v {{ font-size:1.25rem; font-weight:650; color:var(--ep-ink); margin-top:3px;
             font-variant-numeric: tabular-nums; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.ep-kpi .d {{ font-size:.78rem; margin-top:2px; font-variant-numeric: tabular-nums; color:var(--ep-muted); }}
.ep-kpi .d.pos {{ color:#0E7A3B; }} .ep-kpi .d.neg {{ color:#B42318; }}
.ep-kpi .i {{ color:#9AA4B2; cursor:help; font-weight:500; }}

/* company header */
.ep-co {{ display:flex; flex-wrap:wrap; gap:14px 28px; align-items:flex-end; justify-content:space-between;
         border:1px solid var(--ep-border); border-radius:10px; padding:16px 18px; margin-bottom:14px; background:#fff; }}
.ep-co .name {{ font-size:1.35rem; font-weight:700; color:var(--ep-navy); line-height:1.2; }}
.ep-co .meta {{ color:var(--ep-muted); font-size:.85rem; margin-top:4px; }}
.ep-co .px {{ font-size:1.6rem; font-weight:700; color:var(--ep-ink); text-align:right; font-variant-numeric: tabular-nums; }}
.ep-co .chg {{ font-size:.9rem; text-align:right; font-variant-numeric: tabular-nums; }}
.ep-co .chg.pos {{ color:#0E7A3B; }} .ep-co .chg.neg {{ color:#B42318; }}
.ep-co .asof {{ font-size:.72rem; color:var(--ep-muted); text-align:right; }}

/* notices */
.ep-note {{ border-left:3px solid #CBD5E1; background:var(--ep-surface); padding:9px 12px; border-radius:4px;
           font-size:.86rem; color:#334155; margin:.3rem 0 .9rem 0; }}
.ep-note.sample {{ border-left-color:#E0A400; background:#FFF9E8; color:#5C4300; }}
.ep-note.warn {{ border-left-color:#ec835a; background:#FFF4EE; }}
.ep-note.info {{ border-left-color:#2a78d6; background:#F1F6FE; }}

/* source footer */
.ep-source {{ font-size:.76rem; color:var(--ep-muted); border-top:1px dashed var(--ep-border);
             padding-top:6px; margin-top:6px; line-height:1.5; }}
.ep-source a {{ color:var(--ep-muted); text-decoration: underline; }}

/* financial tables */
.ep-table-wrap {{ overflow-x:auto; border:1px solid var(--ep-border); border-radius:8px; margin-bottom:.4rem; }}
table.ep-table {{ border-collapse:collapse; width:100%; font-size:.86rem; font-variant-numeric: tabular-nums; }}
table.ep-table th {{ background:var(--ep-surface); color:#334155; font-weight:600; text-align:right;
                    padding:8px 12px; border-bottom:1px solid var(--ep-border); white-space:nowrap; position:sticky; top:0; }}
table.ep-table th:first-child, table.ep-table td:first-child {{ text-align:left; position:sticky; left:0;
                    background:#fff; z-index:1; min-width:210px; }}
table.ep-table th:first-child {{ background:var(--ep-surface); }}
table.ep-table td {{ padding:7px 12px; text-align:right; border-bottom:1px solid #F0F3F7; white-space:nowrap; color:var(--ep-ink); }}
table.ep-table tr.bold td {{ font-weight:650; background:#FAFBFD; }}
table.ep-table tr.bold td:first-child {{ background:#FAFBFD; }}
table.ep-table tr.section td {{ background:#F7F9FC; color:var(--ep-navy); font-weight:650; font-size:.78rem;
                    text-transform:uppercase; letter-spacing:.05em; }}
table.ep-table td.neg {{ color:#B42318; }}
table.ep-table tr:hover td {{ background:#F5F8FD; }}

/* risk flags */
.ep-flag {{ display:flex; gap:10px; align-items:flex-start; border:1px solid var(--ep-border); border-radius:8px;
           padding:10px 12px; margin-bottom:8px; background:#fff; }}
.ep-flag .ic {{ font-weight:700; font-size:.8rem; padding:2px 7px; border-radius:4px; white-space:nowrap; }}
.ep-flag .ic.good {{ background:#E7F6EC; color:#106B2E; }}
.ep-flag .ic.warning {{ background:#FFF4D6; color:#7A4F00; }}
.ep-flag .ic.serious {{ background:#FDEEE6; color:#9A3D12; }}
.ep-flag .ic.critical {{ background:#FDE8E8; color:#9B1C1C; }}
.ep-flag .ic.na {{ background:#F4F6FA; color:#475569; }}
.ep-flag .t {{ font-weight:600; color:var(--ep-ink); font-size:.9rem; }}
.ep-flag .x {{ color:#475569; font-size:.84rem; margin-top:2px; }}

/* misc */
.ep-empty {{ text-align:center; border:1px dashed #CBD5E1; border-radius:10px; padding:34px 16px; color:var(--ep-muted); }}
.ep-empty .t {{ font-weight:650; color:var(--ep-ink); font-size:1.02rem; margin-bottom:4px; }}
.ep-formula {{ font-family: ui-monospace, Consolas, monospace; font-size:.84rem; background:var(--ep-surface);
              border:1px solid var(--ep-border); border-radius:6px; padding:8px 10px; margin:.3rem 0 .6rem 0; color:#0B1F3A; }}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; font-size: 1.45rem !important; font-weight: 650; }}
[data-testid="stMetricValue"] > div {{ overflow: visible !important; }}
div[data-testid="stExpander"] details {{ border-radius:8px; }}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; padding-top: 4rem; }}
  .ep-header h1 {{ font-size: 1.3rem; }}
  .ep-co .px, .ep-co .chg, .ep-co .asof {{ text-align:left; }}
  .ep-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
</style>
"""


def inject_css() -> None:
    st.html(CSS)
