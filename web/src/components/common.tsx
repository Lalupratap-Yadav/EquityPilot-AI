import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Bell, Building2, CornerDownLeft, Plus, Search, Star } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError, type CompanyCardData, type Quote, type SearchResult } from '../lib/api'
import { baseSymbol, crore, inr, isNum, mult, pct } from '../lib/format'
import { useDebounced, useInvalidate } from '../lib/hooks'
import { ChangePill, cx, DataBadge, Modal, useToast } from './ui'

// ------------------------------------------------------------------ company visuals
export function CompanyAvatar({ symbol, size = 'md' }: { symbol: string; size?: 'sm' | 'md' | 'lg' }) {
  const b = baseSymbol(symbol)
  let h = 0
  for (const ch of b) h = (h * 31 + ch.charCodeAt(0)) % 360
  const dims = size === 'lg' ? 'h-12 w-12 text-base' : size === 'sm' ? 'h-7 w-7 text-[10px]' : 'h-9 w-9 text-xs'
  return (
    <div className={cx('flex shrink-0 items-center justify-center rounded-xl font-bold text-white', dims)}
      style={{ background: `linear-gradient(135deg, hsl(${h} 55% 48%), hsl(${(h + 40) % 360} 60% 38%))` }} aria-hidden>
      {b.replace('SAMPLE-', '').slice(0, 2)}
    </div>
  )
}

export function CompanyCard({ c, className }: { c: CompanyCardData; className?: string }) {
  return (
    <Link to={`/company/${encodeURIComponent(c.symbol)}`}
      className={cx('card group block w-[220px] shrink-0 snap-start p-4 transition-all hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-[var(--shadow-pop)] dark:hover:border-brand-500/60', className)}>
      <div className="flex items-center gap-2.5">
        <CompanyAvatar symbol={c.symbol} />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900 group-hover:text-brand-700 dark:text-white dark:group-hover:text-brand-200">{c.name}</div>
          <div className="text-xs muted">{baseSymbol(c.symbol)}{c.category ? ` · ${c.category}` : ''}</div>
        </div>
      </div>
      <div className="mt-3 flex items-end justify-between">
        <div className="num text-base font-semibold">{inr(c.price)}</div>
        <ChangePill value={c.change_pct} />
      </div>
      <div className="mt-2 flex gap-3 text-[11px] muted">
        {isNum(c.market_cap) && <span>MCap {crore(c.market_cap)}</span>}
        {isNum(c.pe) && <span>P/E {mult(c.pe)}</span>}
        {isNum(c.roe) && <span>ROE {pct(c.roe, 0)}</span>}
      </div>
    </Link>
  )
}

export function CardRow({ title, subtitle, items, empty, action }: { title: ReactNode; subtitle?: ReactNode; items: CompanyCardData[]; empty?: string; action?: ReactNode }) {
  return (
    <section className="min-w-0">
      <div className="mb-2.5 flex items-end justify-between gap-3">
        <div>
          <h2 className="section-title">{title}</h2>
          {subtitle && <p className="text-xs muted">{subtitle}</p>}
        </div>
        {action}
      </div>
      {items.length === 0 ? <p className="text-sm muted">{empty ?? 'Nothing here yet.'}</p> : (
        <div className="scroll-row">{items.map((c) => <CompanyCard key={c.symbol} c={c} />)}</div>
      )}
    </section>
  )
}

export function QuoteLine({ q }: { q?: Quote }) {
  if (!q) return null
  return (
    <span className="inline-flex items-center gap-2">
      <span className="num font-semibold">{inr(q.price)}</span>
      <ChangePill value={q.change_pct} />
      <DataBadge type={q.status} />
    </span>
  )
}

// ------------------------------------------------------------------ sortable table
export interface Column<T> {
  key: string
  label: ReactNode
  render?: (row: T) => ReactNode
  value?: (row: T) => number | string | null | undefined
  align?: 'left' | 'right'
  help?: string
  className?: string
}

export function DataTable<T extends object>({ rows, columns, rowKey, onRowClick, initialSort, maxHeight, dense }: {
  rows: T[]; columns: Column<T>[]; rowKey: (r: T) => string; onRowClick?: (r: T) => void
  initialSort?: { key: string; dir: 'asc' | 'desc' }; maxHeight?: number; dense?: boolean
}) {
  const [sort, setSort] = useState(initialSort)
  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    const get = col?.value ?? ((r: T) => (r as Record<string, unknown>)[sort.key] as number | string | null)
    return [...rows].sort((a, b) => {
      const va = get(a), vb = get(b)
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      const c = typeof va === 'number' && typeof vb === 'number' ? va - vb : String(va).localeCompare(String(vb))
      return sort.dir === 'asc' ? c : -c
    })
  }, [rows, sort, columns])
  return (
    <div className="overflow-auto rounded-xl border border-slate-200 dark:border-ink-700" style={maxHeight ? { maxHeight } : undefined}>
      <table className="w-full min-w-max border-collapse text-sm">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} title={c.help} className={cx('table-head cursor-pointer select-none px-3 py-2.5', c.align === 'right' && 'text-right')}
                onClick={() => setSort((s) => ({ key: c.key, dir: s?.key === c.key && s.dir === 'desc' ? 'asc' : 'desc' }))}>
                <span className="inline-flex items-center gap-1">{c.label}
                  {sort?.key === c.key && (sort.dir === 'desc' ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined}
              className={cx('border-t border-slate-100 dark:border-ink-700/70', onRowClick && 'cursor-pointer hover:bg-brand-50/50 dark:hover:bg-ink-800')}>
              {columns.map((c) => (
                <td key={c.key} className={cx('num whitespace-nowrap px-3', dense ? 'py-1.5' : 'py-2.5', c.align === 'right' && 'text-right', c.className)}>
                  {c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ------------------------------------------------------------------ global search palette (Ctrl+K)
export function SearchPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)
  const dq = useDebounced(q, 180)
  const nav = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const res = useQuery({
    queryKey: ['search', dq], enabled: dq.trim().length >= 1,
    queryFn: () => api.get<{ results: SearchResult[]; industries: { id: string; name: string }[] }>(`/search?q=${encodeURIComponent(dq)}`),
  })
  const recent = useQuery({ queryKey: ['recent'], queryFn: () => api.get<{ views: { symbol: string; name: string }[]; searches: string[] }>('/recent'), enabled: open })
  useEffect(() => { if (open) { setQ(''); setIdx(0); window.setTimeout(() => inputRef.current?.focus(), 30) } }, [open])
  const items: { label: string; sub: string; to: string; icon: ReactNode; badge?: ReactNode }[] = q.trim()
    ? [...(res.data?.industries ?? []).map((i) => ({ label: i.name, sub: 'Industry intelligence', to: `/industries/${i.id}`, icon: <Building2 className="h-4 w-4" /> })),
      ...(res.data?.results ?? []).map((r) => ({
        label: r.name, sub: `${baseSymbol(r.symbol)}${r.category ? ' · ' + r.category : ''}${r.industry ? ' · ' + r.industry : ''}`,
        to: `/company/${encodeURIComponent(r.symbol)}`, icon: <CompanyAvatar symbol={r.symbol} size="sm" />,
        badge: r.is_sample ? <DataBadge type="sample" /> : !r.tracked ? <span className="text-[10px] muted">fetch on open</span> : null }))]
    : (recent.data?.views ?? []).map((v) => ({ label: v.name, sub: `${baseSymbol(v.symbol)} · recently viewed`, to: `/company/${encodeURIComponent(v.symbol)}`,
      icon: <CompanyAvatar symbol={v.symbol} size="sm" /> }))
  const go = (to: string) => { onClose(); nav(to) }
  return (
    <Modal open={open} onClose={onClose} title="Search companies, symbols and industries" wide>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input ref={inputRef} className="input pl-9 text-base" placeholder="e.g. Tata, HDFCBANK, INE002A01018, banking" value={q}
          onChange={(e) => { setQ(e.target.value); setIdx(0) }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(items.length - 1, i + 1)) }
            if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)) }
            if (e.key === 'Enter' && items[idx]) go(items[idx].to)
          }} />
      </div>
      {!q.trim() && (recent.data?.searches?.length ?? 0) > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">{recent.data!.searches.map((s) => <button key={s} className="chip" onClick={() => setQ(s)}>{s}</button>)}</div>
      )}
      <ul className="mt-3 max-h-[50vh] overflow-y-auto">
        {items.map((it, i) => (
          <li key={it.to + i}>
            <button onClick={() => go(it.to)} onMouseEnter={() => setIdx(i)}
              className={cx('flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left', i === idx ? 'bg-brand-50 dark:bg-ink-700' : '')}>
              {it.icon}
              <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{it.label}</span><span className="block truncate text-xs muted">{it.sub}</span></span>
              {it.badge}{i === idx && <CornerDownLeft className="h-3.5 w-3.5 text-slate-400" />}
            </button>
          </li>
        ))}
        {q.trim() && res.isFetched && items.length === 0 && <li className="px-3 py-6 text-center text-sm muted">No matches. Try a company name, NSE symbol or ISIN.</li>}
        {!q.trim() && items.length === 0 && <li className="px-3 py-4 text-sm muted">Search 5,500+ NSE/BSE-listed companies by name, symbol or ISIN.</li>}
      </ul>
      <p className="mt-3 text-[11px] muted">↑↓ to move · Enter to open · Esc to close · Ctrl+K anywhere</p>
    </Modal>
  )
}

// ------------------------------------------------------------------ watchlist / alert / trade dialogs
interface WatchlistLite { id: number; name: string; items: { symbol: string }[] }

export function WatchlistButton({ symbol, compact }: { symbol: string; compact?: boolean }) {
  const [open, setOpen] = useState(false)
  const toast = useToast()
  const inv = useInvalidate()
  const wls = useQuery({ queryKey: ['watchlists'], queryFn: () => api.get<WatchlistLite[]>('/watchlists') })
  const inAny = (wls.data ?? []).some((w) => w.items.some((i) => i.symbol === symbol))
  const toggle = async (w: WatchlistLite) => {
    const has = w.items.some((i) => i.symbol === symbol)
    try {
      if (has) await api.del(`/watchlists/${w.id}/items/${encodeURIComponent(symbol)}`)
      else await api.post(`/watchlists/${w.id}/items`, { symbol })
      toast(has ? `Removed from ${w.name}` : `Added to ${w.name}`)
      inv('watchlists')
    } catch (e) { toast((e as Error).message, 'error') }
  }
  return (
    <>
      <button className={compact ? 'btn-ghost p-2' : 'btn-outline'} onClick={() => setOpen(true)} aria-label="Watchlist">
        <Star className={cx('h-4 w-4', inAny && 'fill-saffron-400 text-saffron-500')} />{!compact && (inAny ? 'Watching' : 'Watchlist')}
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Add to watchlist">
        <ul className="space-y-1">
          {(wls.data ?? []).map((w) => {
            const has = w.items.some((i) => i.symbol === symbol)
            return (
              <li key={w.id}><button onClick={() => toggle(w)} className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 hover:bg-slate-100 dark:hover:bg-ink-700">
                <span className="font-medium">{w.name}</span><span className="text-xs muted">{w.items.length} stocks</span>
                <Star className={cx('h-4 w-4', has ? 'fill-saffron-400 text-saffron-500' : 'text-slate-400')} />
              </button></li>
            )
          })}
        </ul>
        <Link to="/watchlists" className="btn-ghost mt-3 w-full" onClick={() => setOpen(false)}><Plus className="h-4 w-4" />Manage watchlists</Link>
      </Modal>
    </>
  )
}

export function AlertButton({ symbol, price }: { symbol: string; price?: number | null }) {
  const [open, setOpen] = useState(false)
  const [dir, setDir] = useState<'above' | 'below'>('above')
  const [val, setVal] = useState('')
  const toast = useToast()
  const inv = useInvalidate()
  useEffect(() => { if (open && isNum(price)) setVal(String(Math.round(price * (dir === 'above' ? 1.05 : 0.95)))) }, [open, dir, price])
  const save = useMutation({
    mutationFn: () => api.post('/alerts', { symbol, direction: dir, price: Number(val) }),
    onSuccess: () => { toast('Price alert created'); setOpen(false); inv('alerts') },
    onError: (e) => toast((e as Error).message, 'error'),
  })
  return (
    <>
      <button className="btn-outline" onClick={() => setOpen(true)}><Bell className="h-4 w-4" />Alert</button>
      <Modal open={open} onClose={() => setOpen(false)} title={`Price alert · ${baseSymbol(symbol)}`}>
        <p className="mb-3 text-sm muted">You'll get an in-app notification when the latest available (delayed) price crosses your level. Current: {inr(price)}</p>
        <div className="flex gap-2">
          <select className="input w-32" value={dir} onChange={(e) => setDir(e.target.value as 'above' | 'below')}>
            <option value="above">Above</option><option value="below">Below</option>
          </select>
          <input className="input" type="number" min="0" step="0.05" value={val} onChange={(e) => setVal(e.target.value)} aria-label="Alert price" />
        </div>
        <button className="btn-primary mt-4 w-full" disabled={!Number(val) || save.isPending} onClick={() => save.mutate()}>Create alert</button>
      </Modal>
    </>
  )
}

export function TradeTicket({ symbol, name, quote, side: initialSide = 'BUY', onDone, holdingQty }: {
  symbol: string; name?: string; quote?: Quote; side?: 'BUY' | 'SELL'; onDone?: () => void; holdingQty?: number
}) {
  const [side, setSide] = useState<'BUY' | 'SELL'>(initialSide)
  const [qty, setQty] = useState('1')
  const toast = useToast()
  const inv = useInvalidate()
  const acct = useQuery({ queryKey: ['invest-summary'], queryFn: () => api.get<{ cash: number; holdings: { symbol: string; qty: number }[] }>('/invest/summary') })
  const held = holdingQty ?? acct.data?.holdings.find((h) => h.symbol === symbol)?.qty ?? 0
  const n = Math.floor(Number(qty) || 0)
  const value = isNum(quote?.price) ? n * quote!.price! : null
  const cash = acct.data?.cash
  const problem = n <= 0 ? 'Enter a whole number of shares.' : side === 'BUY' && isNum(value) && isNum(cash) && value > cash ? 'Order value exceeds available virtual cash.'
    : side === 'SELL' && n > held ? `You hold ${held} shares.` : null
  const place = useMutation({
    mutationFn: () => api.post<{ price: number; qty: number; price_status: string }>('/invest/orders', { symbol, side, qty: n }),
    onSuccess: (r) => { toast(`Virtual ${side.toLowerCase()} of ${r.qty} ${baseSymbol(symbol)} at ${inr(r.price)} (${r.price_status} price)`); inv('invest-summary', 'invest-trades', 'invest-perf'); onDone?.() },
    onError: (e) => toast(e instanceof ApiError ? e.message : 'Order failed', 'error'),
  })
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div><div className="font-semibold">{name ?? baseSymbol(symbol)}</div><QuoteLine q={quote} /></div>
        <div className="inline-flex rounded-xl bg-slate-100 p-0.5 dark:bg-ink-800">
          {(['BUY', 'SELL'] as const).map((s) => (
            <button key={s} onClick={() => setSide(s)} className={cx('rounded-[10px] px-4 py-1.5 text-sm font-semibold',
              side === s ? (s === 'BUY' ? 'bg-up text-white' : 'bg-down text-white') : 'text-slate-500')}>{s === 'BUY' ? 'Buy' : 'Sell'}</button>
          ))}
        </div>
      </div>
      <label className="label" htmlFor="qty">Quantity (shares)</label>
      <input id="qty" className="input num" type="number" min="1" step="1" value={qty} onChange={(e) => setQty(e.target.value)} />
      <dl className="mt-3 space-y-1.5 text-sm">
        <div className="flex justify-between"><dt className="muted">Estimated value</dt><dd className="num font-semibold">{inr(value)}</dd></div>
        <div className="flex justify-between"><dt className="muted">Available virtual cash</dt><dd className="num">{inr(cash)}</dd></div>
        <div className="flex justify-between"><dt className="muted">Shares held</dt><dd className="num">{held}</dd></div>
      </dl>
      {problem && n > 0 && <p className="mt-2 text-sm text-down">{problem}</p>}
      <button className={cx('btn mt-4 w-full text-white', side === 'BUY' ? 'bg-up hover:bg-up/90' : 'bg-down hover:bg-down/90')}
        disabled={!!problem || place.isPending || !isNum(quote?.price)} onClick={() => place.mutate()}>
        {place.isPending ? 'Placing…' : `${side === 'BUY' ? 'Buy' : 'Sell'} with virtual money`}
      </button>
      <p className="mt-2 text-[11px] leading-snug muted">Virtual trade only - no real order is placed. Fills at the latest {quote?.status ?? ''} price; charges and taxes are not simulated.</p>
    </div>
  )
}
