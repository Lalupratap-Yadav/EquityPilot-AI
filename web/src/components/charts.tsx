import { useMemo } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useTheme } from '../lib/hooks'

// Validated categorical palette (fixed order); dark-mode steps chosen for the dark surface.
export const SERIES_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
export const SERIES_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
export const UP = '#12a150'
export const DOWN = '#dc3545'

export function useSeriesColors() {
  const [theme] = useTheme()
  return theme === 'dark' ? SERIES_DARK : SERIES_LIGHT
}

function useAxisColors() {
  const [theme] = useTheme()
  return theme === 'dark'
    ? { grid: '#1e2a45', text: '#8a95ad', tooltipBg: '#0f172b', border: '#2c3a5a' }
    : { grid: '#eef1f5', text: '#8a8f98', tooltipBg: '#ffffff', border: '#e3e8f0' }
}

// ------------------------------------------------------------------ sparkline (pure SVG)
export function Sparkline({ data, width = 120, height = 36, positive }: { data: number[]; width?: number; height?: number; positive?: boolean }) {
  if (!data || data.length < 2) return <svg width={width} height={height} />
  const min = Math.min(...data), max = Math.max(...data), span = max - min || 1
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - 3 - ((v - min) / span) * (height - 6)}`).join(' ')
  const up = positive ?? data[data.length - 1] >= data[0]
  const color = up ? UP : DOWN
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className="overflow-visible">
      <defs>
        <linearGradient id={`sg-${up}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" /><stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${pts} ${width},${height}`} fill={`url(#sg-${up})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

// ------------------------------------------------------------------ recharts wrappers
type Row = Record<string, string | number | null>

function ChartTooltip({ fmt }: { fmt?: (v: number) => string }) {
  const ax = useAxisColors()
  return <Tooltip formatter={(v) => (typeof v === 'number' && fmt ? fmt(v) : String(v))}
    contentStyle={{ background: ax.tooltipBg, border: `1px solid ${ax.border}`, borderRadius: 10, fontSize: 12 }}
    labelStyle={{ fontWeight: 600 }} cursor={{ fill: 'rgba(120,130,150,0.08)' }} />
}

export function BarsChart({ data, xKey, series, height = 260, fmt, yFmt }: { data: Row[]; xKey: string; series: { key: string; label: string }[]; height?: number; fmt?: (v: number) => string; yFmt?: (v: number) => string }) {
  const colors = useSeriesColors(), ax = useAxisColors()
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barGap={2}>
        <CartesianGrid vertical={false} stroke={ax.grid} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} width={56} tickFormatter={yFmt} />
        <ChartTooltip fmt={fmt} />
        {series.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        {series.map((s, i) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={colors[i]} radius={[4, 4, 0, 0]} maxBarSize={36} />)}
      </BarChart>
    </ResponsiveContainer>
  )
}

export function LinesChart({ data, xKey, series, height = 260, fmt, yFmt, dots = true }: { data: Row[]; xKey: string; series: { key: string; label: string }[]; height?: number; fmt?: (v: number) => string; yFmt?: (v: number) => string; dots?: boolean }) {
  const colors = useSeriesColors(), ax = useAxisColors()
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={ax.grid} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} minTickGap={24} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} width={56} tickFormatter={yFmt} domain={['auto', 'auto']} />
        <ChartTooltip fmt={fmt} />
        {series.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        {series.map((s, i) => <Line key={s.key} dataKey={s.key} name={s.label} stroke={colors[i]} strokeWidth={2} dot={dots ? { r: 3 } : false} connectNulls={false} />)}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function AreaGrowth({ data, xKey, series, height = 260, fmt }: { data: Row[]; xKey: string; series: { key: string; label: string }[]; height?: number; fmt?: (v: number) => string }) {
  const colors = useSeriesColors(), ax = useAxisColors()
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>{series.map((s, i) => (
          <linearGradient key={s.key} id={`ag-${s.key}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={colors[i]} stopOpacity={i === 0 ? 0.25 : 0} /><stop offset="100%" stopColor={colors[i]} stopOpacity={0} />
          </linearGradient>))}
        </defs>
        <CartesianGrid vertical={false} stroke={ax.grid} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} minTickGap={30} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: ax.text, fontSize: 11 }} width={48} domain={['auto', 'auto']} />
        <ChartTooltip fmt={fmt} />
        {series.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        {series.map((s, i) => <Area key={s.key} dataKey={s.key} name={s.label} stroke={colors[i]} strokeWidth={2} fill={`url(#ag-${s.key})`} connectNulls />)}
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function Donut({ data, height = 240, fmt }: { data: { name: string; value: number }[]; height?: number; fmt?: (v: number) => string }) {
  const colors = useSeriesColors()
  const rows = useMemo(() => {
    const sorted = [...data].filter((d) => d.value > 0).sort((a, b) => b.value - a.value)
    if (sorted.length <= 8) return sorted
    const rest = sorted.slice(7).reduce((s, d) => s + d.value, 0)
    return [...sorted.slice(0, 7), { name: 'Other', value: rest }]
  }, [data])
  const total = rows.reduce((s, d) => s + d.value, 0)
  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row">
      <ResponsiveContainer width={180} height={height > 180 ? 180 : height}>
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="95%" stroke="none" paddingAngle={1.5}>
            {rows.map((_, i) => <Cell key={i} fill={colors[i]} />)}
          </Pie>
          <ChartTooltip fmt={fmt} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="w-full space-y-1.5 text-sm">
        {rows.map((r, i) => (
          <li key={r.name} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colors[i] }} />
            <span className="min-w-0 flex-1 truncate">{r.name}</span>
            <span className="num muted">{total ? ((r.value / total) * 100).toFixed(1) : '0'}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
