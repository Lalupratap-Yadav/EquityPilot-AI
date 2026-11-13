import { useQuery } from '@tanstack/react-query'
import { Bot, Compass, Home, LineChart, PiggyBank } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { api, type IndexRow, type MarketStatus } from '../lib/api'
import { isNum, num, pct } from '../lib/format'
import { cx } from './ui'

/** Shared market clock (one request for the whole app). */
export function useMarketStatus() {
  return useQuery({ queryKey: ['market-status'], queryFn: () => api.get<MarketStatus>('/market/status'), refetchInterval: 30_000 })
}

/** Index tiles shared by the ticker, Home and Market Tracker. Refreshes every 15 s while the market is in session. */
export function useIndexOverview() {
  const st = useMarketStatus()
  const live = st.data?.phase === 'open' || st.data?.phase === 'pre-open'
  return useQuery({
    queryKey: ['market-overview'],
    queryFn: () => api.get<{ status: MarketStatus; indices: IndexRow[]; source: string }>('/market/overview'),
    refetchInterval: live ? 15_000 : 120_000,
  })
}

/** 'flash-up' / 'flash-down' for one second after a value changes - the brief green/red tick traders expect. */
export function useFlash(value: number | null | undefined): string {
  const prev = useRef(value)
  const [state, setState] = useState<{ cls: string; n: number }>({ cls: '', n: 0 })
  useEffect(() => {
    const p = prev.current
    prev.current = value
    if (!isNum(p) || !isNum(value) || p === value) return
    setState((s) => ({ cls: value > p ? 'flash-up' : 'flash-down', n: s.n + 1 }))
    const t = window.setTimeout(() => setState((s) => ({ ...s, cls: '' })), 1100)
    return () => window.clearTimeout(t)
  }, [value])
  return state.cls
}

/** A number that flashes green/red when it changes. */
export function LivePrice({ value, digits = 2, prefix = '', className }: { value: number | null | undefined; digits?: number; prefix?: string; className?: string }) {
  const flash = useFlash(value)
  return <span className={cx('num rounded px-0.5 -mx-0.5 transition-colors', flash, className)}>{isNum(value) ? prefix + num(value, digits) : '—'}</span>
}

function countdown(toIso: string | null | undefined, nowMs: number): string | null {
  if (!toIso) return null
  const s = Math.max(0, Math.round((new Date(toIso).getTime() - nowMs) / 1000))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d >= 1) return `${d}d ${h}h`
  if (h >= 1) return `${h}h ${m}m`
  return `${Math.max(1, m)}m`
}

function useNow(ms = 30_000) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), ms); return () => window.clearInterval(t) }, [ms])
  return now
}

/** "Market open · closes in 2h 10m" / "Pre-open" / "Closed · opens in 7h 15m" (holidays detected from data). */
export function MarketClock({ compact = false }: { compact?: boolean }) {
  const q = useMarketStatus()
  const now = useNow()
  const s = q.data
  if (!s) return null
  const open = s.phase === 'open', pre = s.phase === 'pre-open'
  const label = open ? 'Market open' : pre ? 'Pre-open' : s.holiday ? 'Holiday' : 'Market closed'
  const sub = open ? (countdown(s.closes_at, now) ? `closes in ${countdown(s.closes_at, now)}` : '')
    : s.next_open ? `opens in ${countdown(s.next_open, now)}` : ''
  return (
    <span title={`${s.note}\n${s.realtime ? 'Real-time quotes: ' + s.provider : 'Prices are delayed (free data source).'}`}
      className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium',
        open ? 'bg-up/10 text-up' : pre ? 'bg-saffron-500/15 text-saffron-500' : 'bg-slate-500/10 text-slate-500 dark:text-slate-400')}>
      <span className="relative flex h-2 w-2">
        {(open || pre) && <span className={cx('absolute inline-flex h-full w-full animate-ping rounded-full opacity-60', open ? 'bg-up' : 'bg-saffron-500')} />}
        <span className={cx('relative inline-flex h-2 w-2 rounded-full', open ? 'bg-up' : pre ? 'bg-saffron-500' : 'bg-slate-400')} />
      </span>
      {label}{!compact && sub && <span className="font-normal opacity-80">· {sub}</span>}
    </span>
  )
}

function TickerItem({ i }: { i: IndexRow }) {
  const flash = useFlash(i.last)
  const vix = i.symbol === '^INDIAVIX'
  const up = (i.change_pct ?? 0) >= 0
  return (
    <Link to={`/markets?symbol=${encodeURIComponent(i.symbol)}`}
      className="flex h-9 shrink-0 items-center gap-2 rounded-lg px-2.5 text-xs transition-colors hover:bg-slate-100 dark:hover:bg-ink-800">
      <span className="font-semibold text-slate-700 dark:text-slate-200">{i.name}</span>
      <span className={cx('num rounded px-0.5 font-medium text-slate-900 dark:text-white', flash)}>{num(i.last, 2)}</span>
      {isNum(i.change_pct) && (
        <span className={cx('num font-semibold', vix ? 'muted' : up ? 'text-up' : 'text-down')}>
          {up ? '▲' : '▼'} {num(Math.abs(i.change ?? 0), 2)} ({pct(Math.abs(i.change_pct), 2)})
        </span>
      )}
    </Link>
  )
}

/** Index strip under the header: NIFTY, SENSEX, BANK NIFTY ... with the same values as every tile and chart. */
export function LiveTicker() {
  const ov = useIndexOverview()
  const broad = (ov.data?.indices ?? []).filter((i) => i.kind === 'broad')
  return (
    <div className="border-t border-slate-200/70 dark:border-ink-800">
      <div className="mx-auto flex h-9 max-w-[1400px] items-center gap-1 px-2 sm:px-4">
        {/* items that do not fit wrap onto a second line, which is clipped: an index is shown whole or not at all */}
        <div className="flex h-9 min-w-0 flex-1 flex-wrap items-center gap-x-1 overflow-hidden">
          {broad.length === 0 && Array.from({ length: 3 }).map((_, k) => <span key={k} className="skeleton my-2.5 h-4 w-36 shrink-0" />)}
          {broad.slice(0, 6).map((i) => <TickerItem key={i.symbol} i={i} />)}
        </div>
        <Link to="/markets" className="hidden shrink-0 pl-2 text-[10px] uppercase tracking-wider muted hover:text-brand-600 xl:inline"
          title={ov.data?.indices[0]?.time ? `Last value at ${new Date(ov.data.indices[0].time + 'Z').toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })} IST` : undefined}>
          {ov.data?.status.realtime ? 'Live' : 'Delayed'} · {ov.data?.status.phase === 'open' ? 'auto-updating' : 'last close'}{ov.data?.indices[0]?.as_of ? ` · ${ov.data.indices[0].as_of}` : ''}
        </Link>
      </div>
    </div>
  )
}

const TABS: { to: string; label: string; icon: ReactNode }[] = [
  { to: '/', label: 'Home', icon: <Home /> }, { to: '/markets', label: 'Markets', icon: <LineChart /> },
  { to: '/explore', label: 'Explore', icon: <Compass /> }, { to: '/invest', label: 'Invest', icon: <PiggyBank /> },
  { to: '/assistant', label: 'Ask AI', icon: <Bot /> },
]

/** Phone navigation: the five most-used destinations one thumb-tap away. */
export function MobileTabBar() {
  return (
    <nav aria-label="Quick navigation" className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 backdrop-blur-md lg:hidden dark:border-ink-700 dark:bg-ink-900/95">
      <ul className="mx-auto grid max-w-lg grid-cols-5">
        {TABS.map((t) => (
          <li key={t.to}>
            <NavLink to={t.to} end={t.to === '/'} className={({ isActive }) => cx('flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium [&>svg]:h-5 [&>svg]:w-5',
              isActive ? 'text-brand-600 dark:text-brand-300' : 'text-slate-500 dark:text-slate-400')}>
              {t.icon}{t.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
