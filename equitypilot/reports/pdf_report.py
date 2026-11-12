"""Equity research report (PDF) built with ReportLab; charts drawn with matplotlib.

The report contains only data stored in EquityPilot (with its sources), calculations with
formulas, the user's own assumptions and notes (labelled), and standard disclosures.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT, TA_RIGHT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,  # noqa: E402
                                Table, TableStyle)

from .. import config, db  # noqa: E402
from .. import formatting as F  # noqa: E402
from ..analytics import ratios as R  # noqa: E402
from ..analytics import risk as K  # noqa: E402
from ..analytics import technicals as T  # noqa: E402
from ..analytics import valuation as V  # noqa: E402
from ..data import repository as repo  # noqa: E402
from ..data.official import official_links  # noqa: E402

NAVY = colors.HexColor("#0B1F3A")
BLUE = colors.HexColor("#1D4ED8")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E3E8F0")
SURF = colors.HexColor("#F4F6FA")
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(_FONT_DIR / "DejaVuSans.ttf")))          # has the ₹ glyph
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

S = {
    "title": ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=22, leading=27, textColor=NAVY),
    "subtitle": ParagraphStyle("st", fontName="DejaVu", fontSize=11, leading=15, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=13.5, leading=18, textColor=NAVY, spaceBefore=10, spaceAfter=5),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=6, spaceAfter=3),
    "body": ParagraphStyle("b", fontName="DejaVu", fontSize=8.8, leading=12.5, textColor=INK, alignment=TA_LEFT),
    "small": ParagraphStyle("s", fontName="DejaVu", fontSize=7.4, leading=10, textColor=MUTED),
    "cell": ParagraphStyle("c", fontName="DejaVu", fontSize=7.8, leading=10, textColor=INK),
    "cellb": ParagraphStyle("cb", fontName="DejaVu-Bold", fontSize=7.8, leading=10, textColor=INK),
    "cellr": ParagraphStyle("cr", fontName="DejaVu", fontSize=7.8, leading=10, textColor=INK, alignment=TA_RIGHT),
    "cellbr": ParagraphStyle("cbr", fontName="DejaVu-Bold", fontSize=7.8, leading=10, textColor=INK, alignment=TA_RIGHT),
    "box": ParagraphStyle("box", fontName="DejaVu", fontSize=8, leading=11, textColor=INK, backColor=SURF,
                          borderColor=LINE, borderWidth=0.6, borderPadding=6, spaceBefore=4, spaceAfter=8),
}


@dataclass
class ReportOptions:
    analyst: str = "EquityPilot user"
    title: str | None = None
    thesis: str = ""                 # user's own summary / investment thesis
    own_view: str = ""               # optional user's view - clearly labelled, never generated
    sections: list[str] = field(default_factory=lambda: ["overview", "financials", "ratios", "valuation",
                                                         "technicals", "risk", "news", "sources"])


def _esc(x) -> str:
    return (str(x) if x is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(text, style="body"):
    return Paragraph(text, S[style])


def _table(rows: list[list], col_widths=None, header=True, bold_rows: set[int] = frozenset(), align_right_from=None):
    """align_right_from: first column index to right-align (numeric columns); None = left-align all."""
    def style_for(i, j):
        bold = (header and i == 0) or i in bold_rows
        right = align_right_from is not None and j >= align_right_from
        return ("cellbr" if right else "cellb") if bold else ("cellr" if right else "cell")
    data = [[_p(_esc(c), style_for(i, j)) if not isinstance(c, Paragraph) else c for j, c in enumerate(r)]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), SURF))
    for i in bold_rows:
        style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFD")))
    t.setStyle(TableStyle(style))
    return t


def _section(title: str, first, style: str = "h1") -> KeepTogether:
    """Heading kept on the same page as the first block that follows it."""
    return KeepTogether([_p(title, style), first])


def _chart_png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _style_ax(ax, title):
    ax.set_title(title, loc="left", fontsize=9, color="#1F2937", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#D7DEE8")
    ax.tick_params(colors="#6B7280", labelsize=7)
    ax.grid(axis="y", color="#EEF1F5", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_revenue_profit(fd, labels) -> io.BytesIO:
    div, unit = F.amount_unit(fd.currency)
    fig, ax = plt.subplots(figsize=(6.2, 2.5))
    x = range(len(labels))
    w = 0.38
    ax.bar([i - w / 2 for i in x], fd.get("revenue") / div, w, label="Revenue", color=SERIES[0])
    ax.bar([i + w / 2 for i in x], fd.get("net_income") / div, w, label="Net profit", color=SERIES[1])
    ax.set_xticks(list(x), labels)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: F.indian_group(v, 0)))
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    _style_ax(ax, f"Revenue and net profit ({unit})")
    return _chart_png(fig)


def chart_margins(rt, labels) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6.2, 2.3))
    for i, k in enumerate(["ebitda_margin", "net_margin", "roe"]):
        ax.plot(labels, rt.loc[k].values * 100, marker="o", markersize=4, linewidth=1.8, color=SERIES[i],
                label=R.RATIOS[k].label)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(frameon=False, fontsize=7, loc="best")
    _style_ax(ax, "Margins and return on equity (%)")
    return _chart_png(fig)


def chart_price(px: pd.DataFrame) -> io.BytesIO:
    px = px.tail(500)
    fig, ax = plt.subplots(figsize=(6.2, 2.4))
    ax.plot(px["date"], px["close"], color=SERIES[0], linewidth=1.4, label="Close")
    full = T.sma(px["close"], 50)
    ax.plot(px["date"], full, color=SERIES[1], linewidth=1.1, label="50-day SMA")
    ax.plot(px["date"], T.sma(px["close"], 200), color=SERIES[2], linewidth=1.1, label="200-day SMA")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    _style_ax(ax, "Share price (₹), last ~2 years")
    fig.autofmt_xdate(rotation=0, ha="center")
    return _chart_png(fig)


def build_report(symbol: str, opts: ReportOptions | None = None) -> bytes:
    opts = opts or ReportOptions()
    company = repo.get_company(symbol)
    if not company:
        raise ValueError(f"Unknown company {symbol}")
    quote = repo.get_quote(symbol)
    fd = repo.get_financials(symbol, auto_refresh=False)
    fq = repo.get_financials(symbol, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
    snap = V.market_snapshot(quote, fd, fq)
    rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
    px = repo.get_prices(symbol, auto_refresh=False)
    sample = bool(company.get("is_sample"))
    labels = [F.fiscal_label(p).split(" ")[0] for p in fd.periods] if not fd.empty else []
    now = db.utcnow()
    sources: list[tuple[str, str, str]] = []   # (what, source, retrieved/url)

    story = []
    # ------------------------------------------------------------- cover
    story += [Spacer(1, 18 * mm), _p("EQUITY RESEARCH REPORT · EDUCATIONAL", "small"), Spacer(1, 3 * mm),
              _p(_esc(opts.title or company["name"]), "title"), Spacer(1, 2 * mm),
              _p(f"{_esc(symbol)} · {_esc(company.get('exchange'))} · {_esc(company.get('sector'))} · {_esc(company.get('industry'))}", "subtitle"),
              Spacer(1, 6 * mm)]
    if sample:
        story.append(_p("<b>SAMPLE DATA - FICTIONAL COMPANY.</b> Every figure in this report is generated for demonstration "
                        "and does not describe a real business.", "box"))
    kp = [["Price", "Market cap", "P/E", "P/B", "EV/EBITDA", "ROE (latest FY)", "Debt/Equity"],
          [F.inr(snap.get("price")), F.big_inr(snap.get("market_cap")), F.mult(snap.get("pe")), F.mult(snap.get("pb")),
           "n.m." if R.is_financial(company) else F.mult(snap.get("ev_ebitda")),
           F.pct(rt.iloc[:, -1].get("roe")) if not rt.empty else F.MISSING,
           "n.m." if R.is_financial(company) else (F.mult(rt.iloc[:, -1].get("debt_to_equity"), 2) if not rt.empty else F.MISSING)]]
    story.append(_table(kp, col_widths=[24 * mm] * 7, align_right_from=0))
    story.append(_p(f"Price as of {F.ist((quote or {}).get('as_of') or (quote or {}).get('fetched_at'))} "
                    f"({config.DATA_TYPES.get((quote or {}).get('data_type') or 'delayed')[0]}). P/E basis: {_esc(snap['basis'].get('earnings'))}.", "small"))
    story += [Spacer(1, 5 * mm), _p(f"Prepared by: <b>{_esc(opts.analyst)}</b> · Generated {F.ist(now)} with {config.APP_NAME} v{config.APP_VERSION}", "body")]
    if opts.thesis.strip():
        story += [_p("Analyst summary (author's own text)", "h1"), _p(_esc(opts.thesis).replace("\n", "<br/>"))]
    if opts.own_view.strip():
        story += [_p("Author's personal view (not generated by EquityPilot)", "h2"), _p(_esc(opts.own_view).replace("\n", "<br/>"), "box")]
    story.append(_p("<b>Important:</b> This document is an educational research exercise. It is not investment advice or a "
                    "research report under the SEBI (Research Analysts) Regulations, 2014, and contains no buy/sell/hold "
                    "recommendation from EquityPilot. See the disclosures at the end.", "box"))
    if quote:
        sources.append(("Market price & shares", quote.get("source") or "—", F.ist(quote.get("fetched_at"))))

    # ------------------------------------------------------------- overview
    if "overview" in opts.sections:
        desc = company.get("description") or "No description available."
        desc = desc if len(desc) <= 1400 else desc[:1400].rsplit(" ", 1)[0] + "…"
        story += [PageBreak(), _section("1. Company overview", _p(_esc(desc)))]
        sources.append(("Company profile", company.get("source") or "—", F.ist(company.get("fetched_at"))))
        notes = db.get_setting(f"notes:{symbol}") or {}
        for k, lbl in (("business_model", "Business model"), ("products", "Products and services"),
                       ("moat", "Competitive position"), ("management", "Management and governance")):
            if notes.get(k):
                story += [_p(f"{lbl} (analyst notes)", "h2"), _p(_esc(notes[k]).replace("\n", "<br/>"))]
        if notes.get("source"):
            story.append(_p(f"Notes source: {_esc(notes['source'])}", "small"))
        seg = repo.get_segments(symbol)
        if not seg.empty:
            latest = seg[seg["period"] == sorted(seg["period"].unique())[-1]]
            tot = latest["revenue"].sum()
            rows = [["Segment", "Revenue", "Share"]] + [[r["segment"], F.crore(r["revenue"]), F.pct(r["revenue"] / tot)]
                                                        for _, r in latest.iterrows()]
            story += [_section(f"Revenue segments ({_esc(latest['period'].iloc[0])})",
                               _table(rows, [80 * mm, 40 * mm, 30 * mm], align_right_from=1), "h2")]
            sources.append(("Segments", latest["source"].iloc[0] or "—", latest["source_url"].iloc[0] or ""))
        sh = repo.get_shareholding(symbol)
        if not sh.empty:
            latest = sh[sh["period"] == sorted(sh["period"].unique())[-1]]
            rows = [["Category", "Holding", "Pledged"]] + [[r["category"], f"{r['pct']:.2f}%",
                                                           f"{r['pledged_pct']:.2f}%" if pd.notna(r["pledged_pct"]) else "—"]
                                                          for _, r in latest.iterrows()]
            story += [_section(f"Shareholding pattern (quarter ended {_esc(latest['period'].iloc[0])})",
                               _table(rows, [80 * mm, 35 * mm, 35 * mm], align_right_from=1), "h2")]
            sources.append(("Shareholding", latest["source"].iloc[0] or "—", latest["source_url"].iloc[0] or ""))

    # ------------------------------------------------------------- financials
    if "financials" in opts.sections and not fd.empty:
        div, unit = F.amount_unit(fd.currency)
        basis_txt = "not stated by provider (generally consolidated - verify)" if fd.basis == "unspecified" else fd.basis
        story += [_section("2. Financial performance",
                           _p(f"Annual figures in {unit}; basis: {_esc(basis_txt)}; source: {_esc('; '.join(fd.sources))}.", "small"))]
        items = [("revenue", "Revenue"), ("ebitda", "EBITDA"), ("ebit", "EBIT"), ("net_income", "Net profit"),
                 ("eps_diluted", "Diluted EPS"), ("total_equity", "Shareholders' equity"), ("total_debt", "Borrowings"),
                 ("cash", "Cash & ST investments"), ("cfo", "Cash from operations"), ("capex", "Capex")]
        rows = [[unit] + labels]
        for k, lbl in items:
            vals = fd.get(k)
            rows.append([lbl] + [F.num(v) if k == "eps_diluted" else F.amount(v, fd.currency) for v in vals])
        cw = [48 * mm] + [(170 - 48) / max(1, len(labels)) * mm] * len(labels)
        story.append(_table(rows, cw, bold_rows={1, 4}, align_right_from=1))
        story.append(Spacer(1, 3 * mm))
        story.append(Image(chart_revenue_profit(fd, labels), width=170 * mm, height=68 * mm))
        sources.append(("Financial statements", "; ".join(fd.sources) or "—", F.ist(fd.fetched_at)))
        issues = R.quality_checks(fd)
        if issues:
            story.append(_p("Data-quality notes: " + " ".join(f"{_esc(i['check'])}." for i in issues), "small"))

    # ------------------------------------------------------------- ratios
    if "ratios" in opts.sections and not rt.empty:
        keys = ["revenue_growth", "net_income_growth", "ebitda_margin", "net_margin", "roe", "roce", "roa",
                "debt_to_equity", "interest_coverage", "current_ratio", "cfo_to_net_income", "fcf_margin", "dividend_payout"]
        rows = [["Ratio"] + labels] + [[R.RATIOS[k].label] + [F.by_kind(v, R.RATIOS[k].kind) for v in rt.loc[k]] for k in keys]
        cw = [52 * mm] + [(170 - 52) / max(1, len(labels)) * mm] * len(labels)
        story.append(_section("3. Ratio analysis", _table(rows, cw, align_right_from=1)))
        story.append(Image(chart_margins(rt, labels), width=170 * mm, height=63 * mm))
        story.append(_p("Formulas: ROE = net profit / average equity; ROCE = EBIT / average (total assets - current liabilities); "
                        "CFO/net profit = cash from operations / net profit; FCF margin = (CFO - capex) / revenue.", "small"))

    # ------------------------------------------------------------- valuation
    if "valuation" in opts.sections:
        story += [PageBreak(), _p("4. Valuation", "h1")]
        rows = [["Metric", "Value", "Formula / basis"],
                ["Market capitalisation", F.big_inr(snap.get("market_cap")), "Price × shares outstanding"],
                ["Enterprise value", F.big_inr(snap.get("ev")), "Market cap + borrowings - cash"],
                ["P/E", F.mult(snap.get("pe")), _esc(snap["basis"].get("earnings"))],
                ["P/B", F.mult(snap.get("pb")), _esc(snap["basis"].get("balance_sheet"))],
                ["EV/EBITDA", F.mult(snap.get("ev_ebitda")), _esc(snap["basis"].get("ebitda"))],
                ["Dividend yield", F.pct(snap.get("dividend_yield")), "Dividend per share / price"]]
        story.append(_table(rows, [45 * mm, 35 * mm, 90 * mm]))
        val = db.get_setting(f"valuation:{symbol}")
        if val and not snap.get("currency_mismatch"):
            i = V.DCFInputs(**val["inputs"])
            try:
                res = V.run_dcf(i)
            except V.DCFError as exc:
                res = None
                story.append(_p(f"Saved DCF could not be recomputed: {_esc(exc)}", "small"))
            if res:
                story += [_p("Discounted cash flow (FCFF) - author's assumptions", "h2")]
                arows = [["Assumption", "Value"], ["WACC", F.pct(i.wacc)], ["Terminal growth", F.pct(i.terminal_growth)],
                         ["Revenue growth (yr 1 → final yr)", f"{F.pct(i.growth_start)} → {F.pct(i.growth_end)}"],
                         ["Explicit forecast", f"{i.years} years"], ["EBIT margin", F.pct(i.ebit_margin)], ["Tax rate", F.pct(i.tax_rate)],
                         ["D&A / Capex (% revenue)", f"{F.pct(i.da_pct)} / {F.pct(i.capex_pct)}"],
                         ["ΔNWC (% of Δrevenue)", F.pct(i.nwc_pct)]]
                if val.get("rf") is not None:
                    arows += [["Risk-free / beta / ERP", f"{F.pct(val['rf'])} / {val['beta']:.2f} / {F.pct(val['erp'])}"]]
                rrows = [["Result", "Value"], ["Enterprise value", F.big_inr(res.enterprise_value)],
                         ["Less: net debt" if i.net_debt >= 0 else "Add: net cash", F.big_inr(abs(i.net_debt))],
                         ["Equity value", F.big_inr(res.equity_value)],
                         ["Estimated value per share (model)", F.inr(res.per_share)], ["Market price (report date)", F.inr(snap.get("price"))],
                         ["Margin of safety", F.pct(V.margin_of_safety(res.per_share, snap.get("price")), signed=True)],
                         ["Terminal value share of EV", F.pct(res.terminal_share)]]
                story.append(Table([[_table(arows, [55 * mm, 30 * mm], align_right_from=1),
                                     _table(rrows, [50 * mm, 32 * mm], align_right_from=1)]],
                                   colWidths=[88 * mm, 85 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]))
                scn = V.scenarios(i)
                srows = [["Scenario", "Value / share", "vs market"]]
                for n, r in scn.items():
                    if isinstance(r, V.DCFResult):
                        srows.append([n, F.inr(r.per_share), F.pct(r.per_share / snap["price"] - 1, signed=True) if snap.get("price") else "—"])
                story += [_p("Scenarios (default shifts: bear -4pp growth, -3pp margin, +1pp WACC, -1pp g; bull +3pp, +2pp, -1pp, +0.5pp)", "h2"),
                          _table(srows, [40 * mm, 40 * mm, 40 * mm], align_right_from=1)]
                waccs = [round(i.wacc + d, 4) for d in (-0.01, 0, 0.01)]
                gs = [round(i.terminal_growth + d, 4) for d in (-0.01, 0, 0.01)]
                grid = V.sensitivity(i, waccs, gs)
                grows = [["WACC \\ g"] + list(grid.columns)] + [[idx] + [F.inr(v, 0) for v in row] for idx, row in grid.iterrows()]
                story += [_section("Sensitivity: value per share (rows WACC, columns terminal growth)",
                                   _table(grows, [30 * mm] + [35 * mm] * len(grid.columns), align_right_from=1), "h2")]
                story.append(_p("FCFF = EBIT×(1-t) + D&A - capex - ΔNWC; TV = FCFF_N×(1+g)/(WACC-g). Margin of safety = "
                                "(estimated value - price) / estimated value. Model values are estimates that depend entirely "
                                f"on these assumptions (saved {_esc(val.get('saved'))}); they are not a price target or a "
                                "statement of the stock's true value.", "small"))
        else:
            story.append(_p("No DCF saved for this company (or statements are not in INR). Build and save one on the "
                            "Valuation page to include it.", "small"))

    # ------------------------------------------------------------- technicals
    if "technicals" in opts.sections and len(px) > 60:
        c, d = px["close"], px["date"]
        ly = px[px["date"] >= d.max() - pd.Timedelta(days=365)]
        ind = T.indicator_frame(px).iloc[-1]
        story += [_section("5. Price and technical snapshot", Image(chart_price(px), width=170 * mm, height=66 * mm))]
        rows = [["1M", "1Y", "3Y", "Volatility (1Y)", "Max drawdown (1Y)", "RSI (14)", "vs 200-day SMA"],
                [F.pct(T.period_return(c, d, 30), signed=True), F.pct(T.period_return(c, d, 365), signed=True),
                 F.pct(T.period_return(c, d, 1095), signed=True), F.pct(T.annualised_volatility(ly["close"])),
                 F.pct(T.max_drawdown(ly["close"])), F.num(ind["RSI 14"], 1),
                 F.pct(ind["close"] / ind["SMA 200"] - 1, signed=True) if pd.notna(ind["SMA 200"]) else "—"]]
        story.append(_table(rows, [24 * mm] * 7, align_right_from=0))
        story.append(_p(f"Price returns exclude dividends. Data: {_esc('; '.join(px['source'].dropna().unique()))}, "
                        f"{F.fdate(d.min())} to {F.fdate(d.max())}.", "small"))
        sources.append(("Price history", "; ".join(px["source"].dropna().unique()), F.ist(pd.to_datetime(px["fetched_at"]).max())))

    # ------------------------------------------------------------- risk
    if "risk" in opts.sections:
        flags = K.assess(company, fd, px, repo.get_shareholding(symbol), repo.get_segments(symbol),
                     repo.get_bank_metrics(symbol))
        rows = [["Category", "Check", "Value", "Level", "Thresholds"]] + [
            [f["category"], f["title"], f["value"], K.LEVEL_LABEL[f["level"]], f["rule"]] for f in flags]
        story.append(_section("6. Risk assessment", _table(rows, [24 * mm, 45 * mm, 22 * mm, 20 * mm, 59 * mm])))
        rn = db.get_setting(f"risk_notes:{symbol}") or {}
        if rn.get("text"):
            story += [_p("Company-specific risks (analyst notes)", "h2"), _p(_esc(rn["text"]).replace("\n", "<br/>")),
                      _p(f"Source: {_esc(rn.get('source'))}", "small")]
        sector_items = K.SECTOR_CONSIDERATIONS.get(company.get("sector"), [])
        if sector_items:
            story += [_p("General sector considerations (not company-specific findings)", "h2")] + \
                     [_p("• " + _esc(x)) for x in sector_items]

    # ------------------------------------------------------------- news
    if "news" in opts.sections:
        dd = repo.get_disclosures(symbol, limit=12)
        if not dd.empty:
            rows = [["Date", "Category", "Title", "Publisher / source"]] + [
                [F.fdate(r["date"]), r["category"], r["title"][:140], r["publisher"] or r["source"]] for _, r in dd.iterrows()]
            story.append(_section("7. Recent disclosures and headlines", _table(rows, [22 * mm, 26 * mm, 88 * mm, 34 * mm])))
            story.append(_p("Headlines are from third-party publishers via the Yahoo Finance aggregator, or logged by the user from exchange filings.", "small"))

    # ------------------------------------------------------------- sources & disclosures
    story += [PageBreak(), _p("Sources and references", "h1")]
    seen, rows = set(), [["Content", "Source", "Retrieved / reference"]]
    for what, src, ref in sources:
        if (what, src) not in seen:
            seen.add((what, src))
            rows.append([what, src, ref])
    story.append(_table(rows, [40 * mm, 80 * mm, 50 * mm]))
    links = official_links(symbol)
    if links:
        story.append(_p("Official sources for verification: " + "; ".join(f"{_esc(k)}: {_esc(v)}" for k, v in list(links.items())[:5]), "small"))
    story += [_p("Disclosures", "h1"), *[_p(t, "small") for t in [
        "1. Purpose. Prepared with EquityPilot AI, an educational equity research tool, for learning and analysis. It is not "
        "investment advice, an offer, or a solicitation to buy or sell any security.",
        "2. Regulatory status. EquityPilot is not registered with SEBI as a Research Analyst or Investment Adviser. Unless the "
        "author states otherwise, the author is not acting as a SEBI-registered research analyst and this document is not a "
        "research report under the SEBI (Research Analysts) Regulations, 2014.",
        "3. Data. Market data and summarised statements come from third-party sources (e.g. Yahoo Finance via yfinance) that "
        "may be delayed, incomplete or differ from audited filings; uploaded figures are as entered by the user. Verify "
        "material figures against the company's annual report and exchange filings (NSE/BSE).",
        "4. Models. Valuation outputs are sensitive to assumptions chosen by the author and are illustrative estimates, not "
        "price targets. Past performance does not indicate future results.",
        "5. Conflicts. The author should disclose any holding in, or relationship with, the company covered.",
    ]]]

    buf = io.BytesIO()

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 9 * mm, A4[0], 9 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("DejaVu-Bold", 8)
        canvas.drawString(15 * mm, A4[1] - 6 * mm, f"{config.APP_NAME}  ·  {company['name']}")
        canvas.setFont("DejaVu", 7)
        canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 6 * mm, f"Generated {F.fdate(datetime.now())}")
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 8 * mm, "Educational research - not investment advice. See disclosures.")
        canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
        if sample:
            canvas.setFillColor(colors.Color(0.85, 0.6, 0, alpha=0.12))
            canvas.setFont("DejaVu-Bold", 46)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "SAMPLE - FICTIONAL DATA")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=15 * mm,
                            title=f"{company['name']} - Equity Research ({config.APP_NAME})", author=opts.analyst,
                            subject="Educational equity research report")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    db.log_activity("Generated PDF report", symbol)
    return buf.getvalue()
