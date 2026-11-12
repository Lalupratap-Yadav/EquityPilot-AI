// Price chart for companies and indices.
//
// Simple mode (default, the look investors know from Groww/Kite): one clean line with no axes or grid, coloured green or
// red by whether the price is above or below the reference (previous close on 1D, start of period otherwise), a faint
// dashed reference line, a floating "value | time" label above the finger/cursor, and range buttons under the chart.
// The header shows the price and change at whatever point you hover or drag over. No page-scroll hijacking.
// Advanced mode: candles / line / area, moving averages, Bollinger bands, volume, RSI and MACD panes with
// an O/H/L/C readout and a colour legend for every line drawn.
//
// Charting library: TradingView Lightweight Charts™ (Apache-2.0).
// Attribution notice: "TradingView Lightweight Charts™ Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/"
// The on-chart logo is turned off; the required link to https://www.tradingview.com/ is shown under every chart.
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Maximize2 } from 'lucide-react'
import {
  AreaSeries, CandlestickSeries, ColorType, createChart, CrosshairMode, HistogramSeries, LineSeries, LineStyle, TickMarkType,
  type IChartApi, type IPriceLine, type ISeriesApi, type MouseEventParams, type SeriesType, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { compactNum, isNum, pct } from '../lib/format'
import { useTheme } from '../lib/hooks'
import { DOWN, UP, useSeriesColors } from './charts'
import { cx, DataBadge, InfoTip, Segmented, Stat } from './ui'

export type Range = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '3Y' | '5Y' | 'MAX'
const RANGES: Range[] = ['1D', '1W', '1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX']
const RANGE_TEXT: Record<Range, string> = { '1D': 'Today', '1W': 'Past week', '1M': 'Past month', '3M': 'Past 3 months', '6M': 'Past 6 months', '1Y': 'Past year', '3Y': 'Past 3 years', '5Y': 'Past 5 years', MAX: 'All time' }
const BAR_TEXT: Record<Range, string> = { '1D': '5 minutes', '1W': '15 minutes', '1M': '1 hour', '3M': '1 day', '6M': '1 day', '1Y': '1 day', '3Y': '1 day', '5Y': '1 day', MAX: '1 week' }

interface ChartBar { time: string; open: number; high: number; low: number; close: number; volume: number | null }
interface ChartResp {
  bars: ChartBar[]; indicators: Record<string, (number | null)[]>; status: string; source: string; intraday: boolean
  has_volume?: boolean; baseline?: { value: number; label: string }; change?: { abs: number; pct: number | null }; session_date?: string
  quote?: { price: number | null; prev_close: number | null; time: string | null; status: string } | null; cleaned?: number
  stats?: { return: number; high: number; low: number; max_drawdown: number; volatility: number | null }
}
/** The latest quote already shown elsewhere on the page (index tile, company header). The chart header uses it
 *  so both numbers are always identical, even between refreshes. */
export interface LiveQuote { price: number | null; prev_close: number | null; time: string | null }
type Style = 'line' | 'candles' | 'area'
type Overlay = 'sma20' | 'sma50' | 'sma200' | 'ema20' | 'bb'
type Pane = 'rsi' | 'macd'
interface Hover { close: number; open: number; high: number; low: number; volume: number | null; time: Time; x?: number; w?: number }

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** Intraday bars arrive as UTC; shift by +5:30 so the axis reads in IST. Daily bars are IST calendar dates. */
const toTime = (t: string, intraday: boolean): Time =>
  (intraday ? (Math.floor(Date.parse(t.endsWith('Z') ? t : t + 'Z') / 1000) + 19800) as UTCTimestamp : t.slice(0, 10)) as Time

function timeParts(t: Time): { y: number; m: number; d: number; hh: number; mm: number; dow: number; hasTime: boolean } {
  if (typeof t === 'number') {
    const dt = new Date(t * 1000)
    return { y: dt.getUTCFullYear(), m: dt.getUTCMonth(), d: dt.getUTCDate(), hh: dt.getUTCHours(), mm: dt.getUTCMinutes(), dow: dt.getUTCDay(), hasTime: true }
  }
  const s = typeof t === 'string' ? t : `${t.year}-${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}`
  const dt = new Date(s + 'T00:00:00Z')
  return { y: dt.getUTCFullYear(), m: dt.getUTCMonth(), d: dt.getUTCDate(), hh: 0, mm: 0, dow: dt.getUTCDay(), hasTime: false }
}
const two = (n: number) => String(n).padStart(2, '0')
/** Short label for the floating hover tag: '11:23 AM' (intraday 1D), '12 Nov, 11:23 AM' (other intraday), '12 Nov 2026' (daily). */
function shortTime(t: Time, range: Range): string {
  const p = timeParts(t)
  if (!p.hasTime) return `${p.d} ${MONTHS[p.m]} ${p.y}`
  const h12 = ((p.hh + 11) % 12) + 1
  const hm = `${h12}:${two(p.mm)} ${p.hh < 12 ? 'AM' : 'PM'}`
  return range === '1D' ? hm : `${p.d} ${MONTHS[p.m]}, ${hm}`
}
function fullTime(t: Time): string {
  const p = timeParts(t)
  return p.hasTime ? `${p.d} ${MONTHS[p.m]} ${p.y}, ${two(p.hh)}:${two(p.mm)} IST` : `${DAYS[p.dow]}, ${p.d} ${MONTHS[p.m]} ${p.y}`
}

function useChartColors() {
  const [theme] = useTheme()
  return theme === 'dark'
    ? { text: '#8a95ad', grid: '#1a2440', cross: '#64748b', ref: '#94a3b8', bg: '#0b1222', theme }
    : { text: '#7b8494', grid: '#f0f2f6', cross: '#94a3b8', ref: '#64748b', bg: '#ffffff', theme }
}

function useStored<T extends string>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => { try { return (localStorage.getItem(key) as T) || initial } catch { return initial } })
  return [v, (x: T) => { setV(x); try { localStorage.setItem(key, x) } catch { /* storage unavailable */ } }]
}

// ------------------------------------------------------------------ the chart canvas
function ChartCanvas({ data, range, mode, style, overlays, panes, showVolume, height, onHover, money }: {
  data: ChartResp; range: Range; mode: 'simple' | 'advanced'; style: Style; overlays: Overlay[]; panes: Pane[]; showVolume: boolean
  height: number; onHover: (h: Hover | null) => void; money: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const main = useRef<ISeriesApi<SeriesType> | null>(null)
  const extra = useRef<Record<string, ISeriesApi<SeriesType>>>({})
  const refLine = useRef<IPriceLine | null>(null)
  const c = useChartColors()
  const palette = useSeriesColors()
  const paneH = Math.round(height * 0.24)
  const structure = `${mode}|${style}|${overlays.join(',')}|${panes.join(',')}|${showVolume}|${c.theme}|${height}|${data.intraday}`

  // create the chart and its series when the *structure* changes (style, indicators, theme)
  useEffect(() => {
    if (!ref.current) return
    const simple = mode === 'simple'
    const fmtPrice = (p: number) => p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: c.text, fontFamily: 'Inter Variable, system-ui', fontSize: 11,
        attributionLogo: false, panes: { separatorColor: c.grid, enableResize: false } },
      grid: { vertLines: { visible: false }, horzLines: { visible: !simple, color: c.grid } },
      rightPriceScale: { visible: !simple, borderVisible: false, scaleMargins: { top: simple ? 0.1 : 0.12, bottom: showVolume ? 0.22 : 0.08 } },
      timeScale: {
        visible: !simple, borderVisible: false, timeVisible: data.intraday, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: (t: Time, type: TickMarkType) => {
          const p = timeParts(t)
          if (type === TickMarkType.Year) return String(p.y)
          if (type === TickMarkType.Month) return `${MONTHS[p.m]}${p.m === 0 ? ` ${p.y}` : ''}`
          if (type === TickMarkType.DayOfMonth) return `${p.d} ${MONTHS[p.m]}`
          return `${two(p.hh)}:${two(p.mm)}`
        },
      },
      localization: { priceFormatter: fmtPrice, timeFormatter: (t: Time) => fullTime(t) },
      crosshair: {
        mode: simple ? CrosshairMode.Magnet : CrosshairMode.Normal,
        vertLine: { color: simple ? (c.theme === 'dark' ? '#475569' : '#cbd5e1') : c.cross, style: simple ? LineStyle.Solid : LineStyle.Dashed, width: 1,
          labelVisible: !simple, labelBackgroundColor: c.theme === 'dark' ? '#334155' : '#475569' },
        horzLine: { visible: !simple, labelVisible: !simple, color: c.cross, style: LineStyle.Dashed, labelBackgroundColor: c.theme === 'dark' ? '#334155' : '#475569' },
      },
      // never hijack the page's scroll wheel; drag to pan and pinch to zoom in advanced mode only
      handleScroll: simple ? false : { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: simple ? false : { mouseWheel: false, pinch: true, axisPressedMouseMove: true, axisDoubleClickReset: true },
    })
    chartRef.current = chart
    extra.current = {}
    refLine.current = null
    const common = { priceLineVisible: false, lastValueVisible: true }
    if (simple) {
      main.current = chart.addSeries(LineSeries, { priceLineVisible: false, lastValueVisible: false, lineWidth: 2, crosshairMarkerRadius: 5,
        crosshairMarkerBorderWidth: 2, crosshairMarkerBorderColor: c.bg, lineType: 0 })
    } else if (style === 'area') {
      main.current = chart.addSeries(AreaSeries, { ...common, lineWidth: 2, crosshairMarkerRadius: 5, crosshairMarkerBorderWidth: 2, crosshairMarkerBorderColor: c.bg })
    } else if (style === 'line') {
      main.current = chart.addSeries(LineSeries, { ...common, color: palette[0], lineWidth: 2, crosshairMarkerRadius: 4 })
    } else {
      main.current = chart.addSeries(CandlestickSeries, { ...common, upColor: UP, downColor: DOWN, borderVisible: false, wickUpColor: UP, wickDownColor: DOWN })
    }
    if (!simple) {
      const ov: Record<string, string> = { sma20: palette[3], sma50: palette[1], sma200: palette[2], ema20: palette[6], bb: palette[4] }
      const add = (key: string, color: string, pane = 0, opts: Record<string, unknown> = {}) => {
        extra.current[key] = chart.addSeries(LineSeries, { color, lineWidth: 1.5 as 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, ...opts }, pane)
      }
      overlays.forEach((o) => (o === 'bb' ? (add('bb_upper', ov.bb, 0, { lineStyle: LineStyle.Dotted }), add('bb_lower', ov.bb, 0, { lineStyle: LineStyle.Dotted })) : add(o, ov[o])))
      let pane = 1
      if (panes.includes('rsi')) {
        add('rsi14', palette[6], pane, { lastValueVisible: true, title: 'RSI' })
        const s = extra.current.rsi14
        s.createPriceLine({ price: 70, color: DOWN + '99', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: '70' })
        s.createPriceLine({ price: 30, color: UP + '99', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: '30' })
        pane++
      }
      if (panes.includes('macd')) {
        extra.current.macd_hist = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane)
        add('macd', palette[0], pane, { title: 'MACD' })
        add('macd_signal', palette[1], pane, { title: 'Signal' })
      }
      chart.panes().forEach((p, i) => i > 0 && p.setHeight(paneH))
    }
    if (showVolume) {
      extra.current.volume = chart.addSeries(HistogramSeries, { priceScaleId: 'vol', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
      chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
    }
    const onMove = (param: MouseEventParams) => {
      const d = param.time !== undefined && main.current ? param.seriesData.get(main.current) as Record<string, number> | undefined : undefined
      if (!d) return onHover(null)
      const v = extra.current.volume ? (param.seriesData.get(extra.current.volume) as { value?: number } | undefined)?.value ?? null : null
      const close = d.close ?? d.value
      onHover({ close, open: d.open ?? close, high: d.high ?? close, low: d.low ?? close, volume: v, time: param.time!,
        x: param.point?.x, w: ref.current?.clientWidth })
    }
    chart.subscribeCrosshairMove(onMove)
    return () => {
      chart.unsubscribeCrosshairMove(onMove)
      chart.remove()
      chartRef.current = null
      main.current = null
    }
  }, [structure]) // eslint-disable-line react-hooks/exhaustive-deps

  // push data into the existing series (range switches don't rebuild the chart, so there is no flicker)
  useEffect(() => {
    const chart = chartRef.current, s = main.current
    if (!chart || !s || !data.bars.length) return
    const t = (b: ChartBar) => toTime(b.time, data.intraday)
    const base = data.baseline?.value ?? data.bars[0].close
    const last = data.bars[data.bars.length - 1].close
    const color = last >= base ? UP : DOWN
    if (mode === 'simple') {
      s.applyOptions({ color })
    } else if (style === 'area') {
      s.applyOptions({ lineColor: color, topColor: color + '38', bottomColor: color + '03' })
    }
    const pad: { time: Time }[] = []
    if (range === '1D' && data.intraday) {
      const lastT = t(data.bars[data.bars.length - 1]) as number
      const day = new Date(lastT * 1000)
      const close = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), 15, 30) / 1000   // 15:30 IST on the shifted axis
      for (let x = lastT + 300; x <= close; x += 300) pad.push({ time: x as UTCTimestamp })
    }
    if (mode === 'advanced' && style === 'candles') {
      s.setData([...data.bars.map((b) => ({ time: t(b), open: b.open, high: b.high, low: b.low, close: b.close })), ...pad])
    } else {
      s.setData([...data.bars.map((b) => ({ time: t(b), value: b.close })), ...pad])
    }
    if (refLine.current) s.removePriceLine(refLine.current)
    refLine.current = mode === 'simple'
      ? s.createPriceLine({ price: base, color: c.theme === 'dark' ? '#475569' : '#cbd5e1', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })
      : s.createPriceLine({ price: base, color: c.ref, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true,
        title: data.baseline?.label === 'Previous close' ? 'Prev close' : 'Start' })
    const ind = data.indicators ?? {}
    const series = (key: string, vals?: (number | null)[]) => {
      const x = extra.current[key]
      if (!x) return
      x.setData(vals ? data.bars.flatMap((b, i) => (vals[i] == null ? [] : [{ time: t(b), value: vals[i] as number }])) : [])
    }
    ;['sma20', 'sma50', 'sma200', 'ema20', 'bb_upper', 'bb_lower', 'rsi14', 'macd', 'macd_signal'].forEach((k) => series(k, ind[k]))
    if (extra.current.macd_hist) {
      const h = ind.macd_hist ?? []
      extra.current.macd_hist.setData(data.bars.flatMap((b, i) => (h[i] == null ? [] : [{ time: t(b), value: h[i] as number, color: (h[i] as number) >= 0 ? UP + '80' : DOWN + '80' }])))
    }
    if (extra.current.volume) {
      extra.current.volume.setData(data.bars.map((b, i) => ({ time: t(b), value: b.volume ?? 0,
        color: (i === 0 || b.close >= data.bars[i - 1].close ? UP : DOWN) + (c.theme === 'dark' ? '70' : '55') })))
    }
    chart.timeScale().fitContent()
  }, [data, structure]) // eslint-disable-line react-hooks/exhaustive-deps

  const totalH = height + (mode === 'advanced' ? panes.length * paneH : 0)
  return <div ref={ref} style={{ height: totalH }} className="w-full touch-pan-y" role="img"
    aria-label={`Price chart, ${RANGE_TEXT[range].toLowerCase()}${money ? ' in rupees' : ''}`} />
}

// ------------------------------------------------------------------ legend & explainer
function Swatch({ color, dashed, bar }: { color: string; dashed?: boolean; bar?: boolean }) {
  if (bar) return <span className="inline-block h-3 w-1.5 rounded-sm" style={{ background: color }} />
  return <span className="inline-block w-5 border-t-2" style={{ borderColor: color, borderStyle: dashed ? 'dashed' : 'solid' }} />
}

function LegendItem({ swatch, label, help }: { swatch: ReactNode; label: string; help: string }) {
  return <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">{swatch}{label}<InfoTip text={help} /></span>
}

function Explainer({ mode, range, isIndex }: { mode: 'simple' | 'advanced'; range: Range; isIndex: boolean }) {
  const [open, setOpen] = useStored<'open' | 'closed'>('ep-chart-help', 'closed')
  const unit = BAR_TEXT[range]
  const simple = [
    ['The line', `The ${isIndex ? 'index value' : 'share price'} at the close of each ${unit} in the selected period.`],
    ['Green or red', `Green when the latest ${isIndex ? 'value' : 'price'} is above the dashed reference line, red when it is below. It describes the past, not a forecast.`],
    ['Dashed grey line', range === '1D' ? "Yesterday's closing price (\"Prev close\"). Today's gain or loss is measured from it, as exchanges do." : 'The price at the start of the selected period ("Start"). The change shown at the top is measured from it.'],
    ['Big number at the top', 'The most recent value, and how much it has changed in the selected period. Prices are delayed or end-of-day, as labelled below the chart.'],
    ['Hover or drag', 'Move along the chart: a small tag shows the value and time at that point, and the big number shows the change up to then.'],
    ...(isIndex ? [] : [['Volume bars (optional)', 'How many shares changed hands in each bar. Green when the price closed higher than the bar before, red when lower. Unusually tall bars mean unusual interest.']]),
  ]
  const advanced = [
    ['Candles', `Each candle is one ${unit}. The thick body runs from the opening to the closing price, and the thin wicks show the highest and lowest prices. Green = closed higher than it opened; red = closed lower.`],
    ['SMA 20 / 50 / 200', 'Simple moving average: the average closing price of the last 20, 50 or 200 bars. It smooths out day-to-day noise. A price above its 200-day average is often read as a long-term uptrend.'],
    ['EMA 20', 'Exponential moving average: like the SMA but gives more weight to recent prices, so it reacts faster.'],
    ['Bollinger bands', 'Dotted lines two standard deviations above and below the 20-bar average. Wider bands mean the price has been more volatile.'],
    ['RSI (14)', 'Relative Strength Index, a 0-100 momentum gauge in its own panel. Above 70 is often called "overbought" and below 30 "oversold". These are descriptions, not buy or sell signals.'],
    ['MACD', 'The gap between the 12- and 26-bar exponential averages (blue) and its 9-bar average (orange). The bars show the distance between the two lines.'],
    ['Pan and zoom', 'Drag the chart to move through time, pinch or drag the axis to zoom, and double-click the time axis to reset. The mouse wheel scrolls the page, not the chart.'],
  ]
  const items = mode === 'simple' ? simple : [...simple.slice(0, 5), ...advanced]
  return (
    <div className="mt-3 rounded-xl border border-slate-200 dark:border-ink-700">
      <button className="flex w-full items-center justify-between px-3.5 py-2.5 text-left text-sm font-medium" onClick={() => setOpen(open === 'open' ? 'closed' : 'open')} aria-expanded={open === 'open'}>
        How to read this chart<ChevronDown className={cx('h-4 w-4 transition-transform', open === 'open' && 'rotate-180')} />
      </button>
      {open === 'open' && (
        <dl className="grid gap-x-6 gap-y-2.5 border-t border-slate-200 px-3.5 py-3 text-sm sm:grid-cols-2 dark:border-ink-700">
          {items.map(([k, v]) => <div key={k}><dt className="font-medium">{k}</dt><dd className="text-slate-600 dark:text-slate-300">{v}</dd></div>)}
          {mode === 'advanced' && range !== '1D' && <p className="text-xs muted sm:col-span-2">On intraday ranges, "20" means 20 bars of {unit}, not 20 days. Technical indicators summarise past prices; they do not predict future ones.</p>}
        </dl>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ public component
export function StockChart({ symbol, isIndex = false, compact = false, defaultRange = '1D', height, fullLink, live }: {
  symbol: string; isIndex?: boolean; compact?: boolean; defaultRange?: Range; height?: number; fullLink?: string; live?: LiveQuote | null
}) {
  const [range, setRange] = useState<Range>(defaultRange)
  const [mode, setMode] = useStored<'simple' | 'advanced'>('ep-chart-mode-v2', 'simple')
  const effMode = compact ? 'simple' : mode
  const [style, setStyle] = useStored<Style>('ep-chart-style', 'candles')
  const [overlays, setOverlays] = useState<Overlay[]>(['sma50', 'sma200'])
  const [panes, setPanes] = useState<Pane[]>(['rsi'])
  const [simpleVolume, setSimpleVolume] = useState(false)       // Groww-style: off in the simple view
  const [advVolume, setAdvVolume] = useState(true)              // Kite-style: on in the advanced view
  const [hover, setHover] = useState<Hover | null>(null)
  const palette = useSeriesColors()
  const q = useQuery({
    queryKey: ['chart', symbol, range], placeholderData: (p) => p, staleTime: range === '1D' ? 60_000 : 300_000,
    refetchInterval: range === '1D' ? 120_000 : false,
    queryFn: () => api.get<ChartResp>(`/chart/${encodeURIComponent(symbol)}?range=${range}`),
  })
  const raw = q.data
  // if the page holds a newer quote than the chart response, end the chart on it (same number as the tile/header)
  const d = useMemo(() => {
    if (!raw?.bars.length || !live || live.price == null || !live.time) return raw
    if (raw.quote?.time && live.time <= raw.quote.time) return raw
    const bars = raw.bars.slice()
    const lb = bars[bars.length - 1]
    bars[bars.length - 1] = { ...lb, close: live.price, high: Math.max(lb.high, live.price), low: Math.min(lb.low, live.price) }
    const baseline = range === '1D' && raw.intraday && live.prev_close ? { value: live.prev_close, label: 'Previous close' } : raw.baseline
    return { ...raw, bars, baseline }
  }, [raw, live?.price, live?.prev_close, live?.time, range]) // eslint-disable-line react-hooks/exhaustive-deps
  const showVolume = !!d?.has_volume && !isIndex && (effMode === 'advanced' ? advVolume : simpleVolume && !compact)
  const h = height ?? (compact ? 260 : 380)
  const onHover = useCallback((x: Hover | null) => setHover(x), [])
  const money = !isIndex
  const fmt = (v: number | null | undefined) => (isNum(v) ? `${money ? '₹' : ''}${v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—')

  const head = useMemo(() => {
    if (!d?.bars.length) return null
    const base = d.baseline?.value ?? d.bars[0].close
    const value = hover?.close ?? d.bars[d.bars.length - 1].close
    const abs = value - base
    return { value, abs, pct: base ? abs / base : null, base }
  }, [d, hover])
  const todayIST = new Date(Date.now() + 19800_000).toISOString().slice(0, 10)
  const caption = hover ? fullTime(hover.time)
    : range === '1D' && d?.session_date && d.session_date !== todayIST ? `Last trading session · ${fullTime(d.session_date as Time)}`
      : range === '1D' ? 'Today' : RANGE_TEXT[range]
  const toggle = <T,>(arr: T[], v: T) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v])
  const up = (head?.abs ?? 0) >= 0
  const loadingFirst = q.isLoading && !d
  const rangeBar = (
    <div className={cx('flex items-center gap-0.5 overflow-x-auto pb-1 sm:gap-1', effMode === 'simple' ? 'mt-2 border-t border-slate-100 pt-3 dark:border-ink-700' : 'mt-3')} role="tablist" aria-label="Time range">
      {(compact ? RANGES.filter((r) => r !== '3Y') : RANGES).map((r) => (
        <button key={r} role="tab" aria-selected={range === r} onClick={() => { setRange(r); setHover(null) }}
          className={cx('shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold transition-colors sm:px-3',
            range === r ? (up ? 'bg-up/10 text-up ring-1 ring-up/30' : 'bg-down/10 text-down ring-1 ring-down/30') : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-ink-800 dark:hover:text-slate-100')}>
          {r === 'MAX' ? 'All' : r}
        </button>
      ))}
      {compact && fullLink && <Link to={fullLink} className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-300"><Maximize2 className="h-3 w-3" />Full chart</Link>}
    </div>
  )
  const tagLeft = hover?.x != null && hover.w ? Math.min(Math.max(hover.x, 70), hover.w - 70) : null

  return (
    <div className="min-w-0">
      {/* header: price and change at the hovered point (or latest) */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="num text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl dark:text-white">{head ? fmt(head.value) : '—'}</div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm">
            {head && <span className={cx('num font-semibold', up ? 'text-up' : 'text-down')}>{up ? '+' : '−'}{fmt(Math.abs(head.abs))} ({pct(head.pct, 2, true)})</span>}
            <span className="muted">{caption}</span>
          </div>
        </div>
        {!compact && <Segmented size="xs" value={mode} onChange={setMode} options={[{ id: 'simple', label: 'Simple' }, { id: 'advanced', label: 'Advanced' }]} />}
      </div>

      {effMode === 'advanced' && rangeBar}

      {/* advanced toolbar */}
      {effMode === 'advanced' && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Segmented size="xs" value={style} onChange={setStyle} options={[{ id: 'candles', label: 'Candles' }, { id: 'line', label: 'Line' }, { id: 'area', label: 'Area' }]} />
          {([['sma20', 'SMA 20'], ['sma50', 'SMA 50'], ['sma200', 'SMA 200'], ['ema20', 'EMA 20'], ['bb', 'Bollinger']] as [Overlay, string][]).map(([k, l]) => (
            <button key={k} className={cx('chip', overlays.includes(k) && 'chip-active')} onClick={() => setOverlays(toggle(overlays, k))}>{l}</button>))}
          {d?.has_volume && !isIndex && <button className={cx('chip', advVolume && 'chip-active')} aria-pressed={advVolume} onClick={() => setAdvVolume(!advVolume)}>Volume</button>}
          <button className={cx('chip', panes.includes('rsi') && 'chip-active')} onClick={() => setPanes(toggle(panes, 'rsi'))}>RSI</button>
          <button className={cx('chip', panes.includes('macd') && 'chip-active')} onClick={() => setPanes(toggle(panes, 'macd'))}>MACD</button>
        </div>
      )}

      {/* O/H/L/C readout in advanced mode */}
      {effMode === 'advanced' && d?.bars.length ? (() => {
        const b = hover ?? (() => { const x = d.bars[d.bars.length - 1]; return { open: x.open, high: x.high, low: x.low, close: x.close, volume: x.volume } })()
        return (
          <div className="num mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-600 dark:text-slate-300">
            <span>O <b>{fmt(b.open)}</b></span><span>H <b>{fmt(b.high)}</b></span><span>L <b>{fmt(b.low)}</b></span><span>C <b>{fmt(b.close)}</b></span>
            {isNum(b.volume) && b.volume > 0 && <span>Vol <b>{compactNum(b.volume)}</b></span>}
          </div>
        )
      })() : null}

      {/* chart */}
      <div className={cx('relative', effMode === 'simple' ? 'mt-1 pt-6' : 'mt-2')} onMouseLeave={() => setHover(null)}>
        {effMode === 'simple' && hover && tagLeft != null && (
          <div className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 whitespace-nowrap text-xs" style={{ left: tagLeft }}>
            <span className="num font-semibold text-slate-800 dark:text-slate-100">{fmt(hover.close)}</span>
            <span className="mx-1 text-slate-300 dark:text-ink-600">|</span>
            <span className="text-slate-500 dark:text-slate-400">{shortTime(hover.time, range)}</span>
          </div>
        )}
        {loadingFirst ? <div className="animate-pulse rounded-xl bg-slate-100 dark:bg-ink-800" style={{ height: h }} />
          : !d?.bars.length ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 text-center dark:border-ink-700" style={{ height: h }}>
              <p className="font-medium">No price data for this range</p>
              <p className="mt-1 max-w-sm text-sm muted">{q.isError ? 'The price provider did not respond. Try another range or again in a minute.' : 'The provider has no bars for this period (for example, intraday data for some instruments outside market hours).'}</p>
            </div>
          ) : (
            <div className={cx('transition-opacity duration-300', q.isFetching && q.isPlaceholderData ? 'opacity-50' : 'opacity-100')}>
              <ChartCanvas data={d} range={range} mode={effMode} style={style} overlays={overlays} panes={panes} showVolume={showVolume} height={h} onHover={onHover} money={money} />
            </div>
          )}
        {q.isFetching && q.isPlaceholderData && <div className="absolute right-2 top-2 h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" aria-label="Loading" />}
      </div>
      {effMode === 'simple' && rangeBar}

      {/* legend: every line on the chart is named */}
      {d?.bars.length ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
          <LegendItem swatch={effMode === 'advanced' && style === 'candles' ? <span className="inline-flex gap-0.5"><Swatch color={UP} bar /><Swatch color={DOWN} bar /></span> : <Swatch color={up ? UP : DOWN} />}
            label={effMode === 'advanced' && style === 'candles' ? 'Candles' : isIndex ? 'Index value' : 'Price'} help={`Closing value of each ${BAR_TEXT[range]} bar.`} />
          <LegendItem swatch={<Swatch color="#94a3b8" dashed />} label={`${d.baseline?.label === 'Previous close' ? 'Previous close' : 'Start of period'} ${fmt(d.baseline?.value ?? d.bars[0].close)}`}
            help="The reference the change at the top is measured from. Above it = gain, below it = loss." />
          {showVolume && <LegendItem swatch={<span className="inline-flex gap-0.5"><Swatch color={UP + '88'} bar /><Swatch color={DOWN + '88'} bar /></span>} label="Volume" help="Shares traded in each bar." />}
          {effMode === 'simple' && !compact && d.has_volume && !isIndex && (
            <button className={cx('chip ml-auto', simpleVolume && 'chip-active')} aria-pressed={simpleVolume} onClick={() => setSimpleVolume(!simpleVolume)}>{simpleVolume ? '✓ Volume shown' : '+ Show volume'}</button>)}
          {effMode === 'advanced' && overlays.map((o) => {
            const meta: Record<Overlay, [string, string, string]> = { sma20: ['SMA 20', palette[3], 'Average close of the last 20 bars'], sma50: ['SMA 50', palette[1], 'Average close of the last 50 bars'],
              sma200: ['SMA 200', palette[2], 'Average close of the last 200 bars'], ema20: ['EMA 20', palette[6], 'Exponential average weighting recent bars more'], bb: ['Bollinger bands', palette[4], '20-bar average ± 2 standard deviations'] }
            const [l, col, help] = meta[o]
            return <LegendItem key={o} swatch={<Swatch color={col} dashed={o === 'bb'} />} label={l} help={help} />
          })}
          {effMode === 'advanced' && panes.includes('rsi') && <LegendItem swatch={<Swatch color={palette[6]} />} label="RSI (lower panel)" help="0-100 momentum gauge; dashed lines at 70 and 30." />}
          {effMode === 'advanced' && panes.includes('macd') && <LegendItem swatch={<span className="inline-flex gap-1"><Swatch color={palette[0]} /><Swatch color={palette[1]} /></span>} label="MACD / signal (lower panel)" help="Blue: 12-bar EMA minus 26-bar EMA. Orange: 9-bar average of the blue line." />}
        </div>
      ) : null}

      {/* period statistics */}
      {!compact && d?.stats && (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {range === '1D' && d.intraday ? (<>
            <Stat label="Open" value={fmt(d.bars[0].open)} help="First traded value of the session (09:15 IST)" />
            <Stat label="Previous close" value={fmt(d.baseline?.value)} help="Closing value of the previous trading day - today's change is measured from it" />
            <Stat label="Day high" value={fmt(d.stats.high)} help="Highest value traded today (from 5-minute bars)" />
            <Stat label="Day low" value={fmt(d.stats.low)} help="Lowest value traded today (from 5-minute bars)" />
          </>) : (<>
            <Stat label="Period high" value={fmt(d.stats.high)} help="Highest traded value in the selected period" />
            <Stat label="Period low" value={fmt(d.stats.low)} help="Lowest traded value in the selected period" />
            <Stat label="Largest fall" value={pct(d.stats.max_drawdown)} help="Biggest drop from a peak to a later low within the period (maximum drawdown)" />
            {isNum(d.stats.volatility)
              ? <Stat label="Volatility (yearly)" value={pct(d.stats.volatility)} help="How much returns swing, scaled to a year (standard deviation of daily returns × √252, or weekly × √52 on 'All')." />
              : <Stat label="Start of period" value={fmt(d.baseline?.value ?? d.bars[0].close)} help="Value at the start of the selected period - the change at the top is measured from it" />}
          </>)}
        </div>
      )}

      {!compact && <Explainer mode={effMode} range={range} isIndex={isIndex} />}

      {d && (
        <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs muted">
          <span><b className="font-medium">Source:</b> {d.source}</span><DataBadge type={d.status} />
          <span>{d.intraday ? `${BAR_TEXT[range]} bars, delayed.` : `${BAR_TEXT[range] === '1 week' ? 'Weekly' : 'Daily'} closing prices${isIndex ? '' : ', not adjusted for dividends'}.`}</span>
          {d.cleaned ? <span title="A bar whose price jumped away and straight back far beyond normal moves (typically a closing-session artefact in the provider's data) was removed or its wick capped. Nothing else is altered.">{d.cleaned} bad tick{d.cleaned === 1 ? '' : 's'} from the provider filtered.</span> : null}
          <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer" className="hover:underline">Charts by TradingView</a>
        </p>
      )}
    </div>
  )
}
