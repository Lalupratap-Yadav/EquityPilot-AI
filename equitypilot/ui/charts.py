"""Plotly chart helpers with one consistent visual system.

Rules: validated categorical palette in fixed order; one y-axis per chart (no dual axes -
price/volume and indicators use stacked panels); thin marks; hover on every chart; recessive grid.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Validated categorical palette (fixed order - never cycled; fold >8 series into "Other").
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = [[0.0, "#d03b3b"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]
UP, DOWN = "#1baf7a", "#e34948"
INK, INK_2, MUTED, GRID = "#1F2937", "#52514e", "#8A8F98", "#EEF1F5"
FONT = "Inter, -apple-system, Segoe UI, sans-serif"


def _layout(fig: go.Figure, title: str | None = None, height: int = 360, yfmt: str | None = None,
            ysuffix: str = "", legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=14, color=INK)) if title else None,
        height=height, margin=dict(l=8, r=8, t=40 if title else 12, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK_2),
        hovermode="x unified", showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None,
                    font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", bordercolor="#D7DEE8", font=dict(family=FONT, color=INK)),
        bargap=0.25, bargroupgap=0.08,
    )
    fig.update_xaxes(showgrid=False, linecolor="#D7DEE8", tickfont=dict(color=MUTED), ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor="#D7DEE8", tickfont=dict(color=MUTED),
                     tickformat=yfmt, ticksuffix=ysuffix)
    return fig


def config() -> dict:
    """Plotly config passed to st.plotly_chart."""
    return {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "toImageButtonOptions": {"format": "png", "scale": 2}}


def grouped_bars(df: pd.DataFrame, title: str | None = None, ysuffix: str = "", yfmt: str | None = ",.0f",
                 height: int = 340, hover_fmt: str = ",.0f") -> go.Figure:
    """df: index = x categories (e.g. FY labels), columns = series (same unit)."""
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_bar(x=df.index.astype(str), y=df[col], name=str(col), marker_color=SERIES[i % 8],
                    marker_line_width=0, hovertemplate=f"%{{y:{hover_fmt}}}{ysuffix}<extra>{col}</extra>")
    fig.update_traces(marker_cornerradius=4)
    return _layout(fig, title, height, yfmt, ysuffix, legend=len(df.columns) > 1)


def lines(df: pd.DataFrame, title: str | None = None, ysuffix: str = "", yfmt: str | None = None,
          height: int = 340, markers: bool = True, hover_fmt: str = ",.1f") -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_scatter(x=df.index, y=df[col], name=str(col), mode="lines+markers" if markers else "lines",
                        line=dict(width=2, color=SERIES[i % 8]), marker=dict(size=8),
                        connectgaps=False, hovertemplate=f"%{{y:{hover_fmt}}}{ysuffix}<extra>{col}</extra>")
    return _layout(fig, title, height, yfmt, ysuffix, legend=len(df.columns) > 1)


def price_chart(px: pd.DataFrame, overlays: dict[str, pd.Series] | None = None, title: str | None = None,
                candles: bool = True, show_volume: bool = True, height: int = 520) -> go.Figure:
    """Price (candles or line) with optional overlays; volume in its own panel below (no dual axis)."""
    rows = 2 if show_volume else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.78, 0.22] if show_volume else [1.0])
    if candles:
        fig.add_trace(go.Candlestick(x=px["date"], open=px["open"], high=px["high"], low=px["low"],
                                     close=px["close"], name="Price", increasing_line_color=UP,
                                     decreasing_line_color=DOWN, increasing_fillcolor=UP,
                                     decreasing_fillcolor=DOWN, line_width=1), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=px["date"], y=px["close"], name="Close", line=dict(width=2, color=SERIES[0]),
                                 hovertemplate="₹%{y:,.2f}<extra>Close</extra>"), row=1, col=1)
    for i, (name, s) in enumerate((overlays or {}).items()):
        fig.add_trace(go.Scatter(x=px["date"], y=s, name=name, line=dict(width=1.5, color=SERIES[(i + 1) % 8]),
                                 hovertemplate=f"₹%{{y:,.2f}}<extra>{name}</extra>"), row=1, col=1)
    if show_volume:
        colors = np.where(px["close"].diff().fillna(0) >= 0, UP, DOWN)
        fig.add_trace(go.Bar(x=px["date"], y=px["volume"], name="Volume", marker_color=colors,
                             marker_line_width=0, opacity=0.6, showlegend=False,
                             hovertemplate="%{y:,.0f}<extra>Volume</extra>"), row=2, col=1)
    _layout(fig, title, height)
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(tickprefix="₹", row=1, col=1)
    return fig


def indicator_panel(x, series: dict[str, pd.Series], title: str, bands: tuple[float, float] | None = None,
                    bars: str | None = None, height: int = 220) -> go.Figure:
    fig = go.Figure()
    if bars and bars in series:
        s = series[bars]
        fig.add_bar(x=x, y=s, name=bars, marker_color=np.where(s >= 0, UP, DOWN), marker_line_width=0,
                    opacity=0.7, hovertemplate=f"%{{y:.2f}}<extra>{bars}</extra>")
    for i, (name, s) in enumerate(series.items()):
        if name == bars:
            continue
        fig.add_scatter(x=x, y=s, name=name, line=dict(width=1.8, color=SERIES[i % 8]),
                        hovertemplate=f"%{{y:.2f}}<extra>{name}</extra>")
    if bands:
        for b in bands:
            fig.add_hline(y=b, line=dict(color=MUTED, width=1, dash="dot"))
    return _layout(fig, title, height, legend=len(series) > 1)


def donut(labels, values, title: str | None = None, height: int = 320, hover_suffix: str = "") -> go.Figure:
    labels, values = list(labels), list(values)
    if len(labels) > 8:  # fold the tail into "Other" instead of generating hues
        pairs = sorted(zip(values, labels), reverse=True)
        top, rest = pairs[:7], pairs[7:]
        labels = [l for _, l in top] + ["Other"]
        values = [v for v, _ in top] + [sum(v for v, _ in rest)]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, sort=False, direction="clockwise",
                           marker=dict(colors=SERIES[:len(labels)], line=dict(color="white", width=2)),
                           textinfo="percent", textfont=dict(color="white", size=11),
                           hovertemplate=f"%{{label}}: %{{value:,.2f}}{hover_suffix} (%{{percent}})<extra></extra>"))
    fig = _layout(fig, title, height)
    fig.update_layout(hovermode="closest", legend=dict(orientation="v", x=1.02, y=0.5, yanchor="middle",
                                                       xanchor="left"))
    return fig


def heatmap(z: pd.DataFrame, title: str | None = None, diverging: bool = False, fmt: str = ".2f",
            height: int = 380, zmid: float | None = None, xlabel: str = "", ylabel: str = "",
            text_suffix: str = "") -> go.Figure:
    colorscale = DIVERGING if diverging else [[i / (len(SEQ_BLUE) - 1), c] for i, c in enumerate(SEQ_BLUE)]
    text = z.map(lambda v: "—" if pd.isna(v) else f"{v:{fmt}}{text_suffix}").values
    fig = go.Figure(go.Heatmap(z=z.values, x=[str(c) for c in z.columns], y=[str(i) for i in z.index],
                               colorscale=colorscale, zmid=zmid, text=text, texttemplate="%{text}",
                               textfont=dict(size=11), xgap=2, ygap=2, showscale=False,
                               hovertemplate=f"{ylabel} %{{y}} · {xlabel} %{{x}}: %{{text}}<extra></extra>"))
    fig = _layout(fig, title, height, legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title=xlabel, side="bottom", type="category")
    fig.update_yaxes(title=ylabel, type="category", autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def hbar(labels, values, title: str | None = None, suffix: str = "", fmt: str = ",.1f", height: int | None = None,
         color: str | None = None) -> go.Figure:
    fig = go.Figure(go.Bar(y=list(labels), x=list(values), orientation="h",
                           marker_color=color or SERIES[0], marker_line_width=0, marker_cornerradius=4,
                           text=[f"{v:{fmt}}{suffix}" if pd.notna(v) else "—" for v in values],
                           textposition="outside", cliponaxis=False,
                           hovertemplate=f"%{{y}}: %{{x:{fmt}}}{suffix}<extra></extra>"))
    fig = _layout(fig, title, height or max(200, 34 * len(list(labels)) + 60), legend=False)
    fig.update_layout(margin=dict(l=8, r=56, t=40 if title else 12, b=8))
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=True, gridcolor=GRID, ticksuffix=suffix)
    return fig


def sparkline(values, up: bool | None = None, height: int = 46) -> go.Figure:
    vals = list(values)
    if up is None:
        up = len(vals) > 1 and vals[-1] >= vals[0]
    fig = go.Figure(go.Scatter(y=vals, mode="lines", line=dict(width=2, color=UP if up else DOWN),
                               hoverinfo="skip"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def scenario_bars(labels, values, current_price: float | None, title: str | None = None) -> go.Figure:
    """Intrinsic value per share by scenario, with the market price as a reference line."""
    colors = [SERIES[1], SERIES[0], SERIES[2]][:len(labels)]
    fig = go.Figure(go.Bar(x=list(labels), y=list(values), marker_color=colors, marker_line_width=0,
                           marker_cornerradius=4, text=[f"₹{v:,.0f}" if pd.notna(v) else "—" for v in values],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: ₹%{y:,.2f}<extra></extra>"))
    if current_price:
        fig.add_hline(y=current_price, line=dict(color=INK, width=1.5, dash="dash"),
                      annotation_text=f"Market price ₹{current_price:,.0f}", annotation_position="top left",
                      annotation_font=dict(color=INK, size=11))
    fig = _layout(fig, title, 340, legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(tickprefix="₹")
    return fig
