import { useQuery } from '@tanstack/react-query'
import { BookOpen, Building2, Clock, CornerDownLeft, ExternalLink, LineChart, Newspaper, Search, Sparkles, Wrench, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { baseSymbol, crore, inr, isNum, num, timeAgo } from '../lib/format'
import { useDebounced } from '../lib/hooks'
import { CompanyAvatar } from './common'
import { ChangePill, cx, DataBadge, TierBadge } from './ui'

interface Co { symbol: string; name: string; exchange: string; sector?: string | null; industry_name?: string | null; category?: string | null; tracked: boolean
  is_sample?: boolean; price?: number | null; change_pct?: number | null; market_cap?: number | null; pe?: number | null; status?: string | null }
interface Idx { symbol: string; name: string; last?: number | null; change_pct?: number | null; as_of?: string | null }
interface SearchResp {
  query: string; did_you_mean?: string | null; order: string[]; ms?: number
  companies: Co[]; indices: Idx[]; industries: { id: string; name: string; companies: number }[]
  concepts: { key: string; name: string; summary: string; to: string }[]; tools: { label: string; description: string; to: string }[]
  news: { title: string; url: string | null; source: string; published: string | null; tier?: string; symbol?: string | null }[]
}
interface Row { key: string; group: string; to: string; external?: boolean; node: ReactNode; preview?: Co }

const GROUP_TITLE: Record<string, [string, ReactNode]> = {
  companies: ['Companies', <Building2 key="c" className="h-3.5 w-3.5" />], indices: ['Indices', <LineChart key="i" className="h-3.5 w-3.5" />],
  industries: ['Sectors & industries', <Building2 key="s" className="h-3.5 w-3.5" />], concepts: ['Financial concepts', <BookOpen key="b" className="h-3.5 w-3.5" />],
  tools: ['Research tools', <Wrench key="w" className="h-3.5 w-3.5" />], news: ['News', <Newspaper key="n" className="h-3.5 w-3.5" />],
  recent: ['Recently viewed', <Clock key="r" className="h-3.5 w-3.5" />], ask: ['Ask the AI', <Sparkles key="a" className="h-3.5 w-3.5" />],
}
const EXAMPLES = ['Reliance', 'HDFC Bank', 'Nifty 50', 'IT industry', 'Companies with high ROE', 'Debt to equity', 'DCF valuation']

function Preview({ c }: { c?: Co }) {
  if (!c) return <div className="flex h-full items-center justify-center p-6 text-center text-sm muted">Move to a company to preview it here.</div>
  return (
    <div className="p-5">
      <div className="flex items-center gap-3"><CompanyAvatar symbol={c.symbol} /><div className="min-w-0"><div className="font-semibold leading-tight">{c.name}</div>
        <div className="text-xs muted">{baseSymbol(c.symbol)} · {c.exchange}{c.category ? ` · ${c.category}` : ''}</div></div></div>
      {isNum(c.price) ? (
        <div className="mt-4"><div className="num text-2xl font-semibold">{inr(c.price)}</div>
          <div className="mt-1 flex items-center gap-2"><ChangePill value={c.change_pct} /><DataBadge type={c.status ?? 'delayed'} /></div></div>
      ) : <p className="mt-4 text-sm muted">{c.tracked ? 'Price not available yet.' : 'Not tracked yet: opening it loads the profile, prices and statements from the data provider (a few seconds).'}</p>}
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-xs muted">Market cap</dt><dd className="num font-medium">{isNum(c.market_cap) ? crore(c.market_cap) : '—'}</dd></div>
        <div><dt className="text-xs muted">P/E</dt><dd className="num font-medium">{isNum(c.pe) && c.pe > 0 ? `${num(c.pe, 1)}x` : '—'}</dd></div>
        <div className="col-span-2"><dt className="text-xs muted">Industry</dt><dd className="font-medium">{c.industry_name || c.sector || '—'}</dd></div>
      </dl>
      <p className="mt-4 text-[11px] muted">Delayed prices · fundamentals from filings data (verify with annual reports).</p>
    </div>
  )
}

/** Global search (Ctrl+K or /): companies, indices, sectors, concepts, tools and news in one place. */
export function SearchPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)
  const dq = useDebounced(q, 120)
  const nav = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const res = useQuery({ queryKey: ['search2', dq.trim().toLowerCase()], enabled: open && dq.trim().length >= 1, placeholderData: (p) => p, staleTime: 60_000,
    queryFn: () => api.get<SearchResp>(`/search?q=${encodeURIComponent(dq.trim())}&limit=7`) })
  const recent = useQuery({ queryKey: ['recent'], queryFn: () => api.get<{ views: { symbol: string; name: string; price?: number; change_pct?: number }[]; searches: string[] }>('/recent'), enabled: open })
  useEffect(() => { if (open) { setQ(''); setIdx(0); window.setTimeout(() => inputRef.current?.focus(), 20) } }, [open])
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])

  const typing = q.trim().length > 0
  const d = typing ? res.data : undefined
  const rows: Row[] = useMemo(() => {
    const out: Row[] = []
    if (!typing) {
      for (const v of recent.data?.views ?? []) out.push({ key: 'r' + v.symbol, group: 'recent', to: `/company/${encodeURIComponent(v.symbol)}`,
        node: <><CompanyAvatar symbol={v.symbol} size="sm" /><Lbl t={v.name} s={baseSymbol(v.symbol)} /><ChangePill value={v.change_pct} /></> })
      return out
    }
    for (const g of d?.order ?? []) {
      if (g === 'companies') for (const c of d!.companies) out.push({ key: 'c' + c.symbol, group: g, to: `/company/${encodeURIComponent(c.symbol)}`, preview: c,
        node: <><CompanyAvatar symbol={c.symbol} size="sm" /><Lbl t={c.name} s={`${baseSymbol(c.symbol)} · ${c.exchange}${c.industry_name ? ' · ' + c.industry_name : c.category ? ' · ' + c.category : ''}`} />
          {c.is_sample ? <DataBadge type="sample" /> : isNum(c.price) ? <span className="text-right"><span className="num block text-sm font-medium">{inr(c.price)}</span><ChangePill value={c.change_pct} /></span>
            : !c.tracked ? <span className="text-[10px] muted">loads on open</span> : null}</> })
      if (g === 'indices') for (const i of d!.indices) out.push({ key: 'i' + i.symbol, group: g, to: `/markets?symbol=${encodeURIComponent(i.symbol)}`,
        node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 dark:bg-ink-700"><LineChart className="h-4 w-4 text-brand-600" /></span><Lbl t={i.name} s="Index · chart and constituents' sector moves" />
          {isNum(i.last) && <span className="text-right"><span className="num block text-sm font-medium">{num(i.last, 2)}</span><ChangePill value={i.change_pct} /></span>}</> })
      if (g === 'industries') for (const s of d!.industries) out.push({ key: 's' + s.id, group: g, to: `/industries/${s.id}`,
        node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 dark:bg-ink-700"><Building2 className="h-4 w-4 text-brand-600" /></span><Lbl t={s.name} s={`Industry page · ${s.companies} listed companies, policies and news`} /></> })
      if (g === 'concepts') for (const c of d!.concepts) out.push({ key: 'k' + c.key, group: g, to: c.to,
        node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-saffron-500/10"><BookOpen className="h-4 w-4 text-saffron-500" /></span><Lbl t={c.name} s={c.summary} /></> })
      if (g === 'tools') for (const t of d!.tools) out.push({ key: 't' + t.to, group: g, to: t.to,
        node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 dark:bg-ink-700"><Wrench className="h-4 w-4 text-slate-500" /></span><Lbl t={t.label} s={t.description} /></> })
      if (g === 'news') for (const n of d!.news) out.push({ key: 'n' + (n.url ?? n.title), group: g, to: n.url ?? '/news', external: !!n.url,
        node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 dark:bg-ink-700"><Newspaper className="h-4 w-4 text-slate-500" /></span>
          <Lbl t={n.title} s={`${n.source.replace(' (RSS)', '')} · ${timeAgo(n.published)}`} /><TierBadge tier={n.tier} /><ExternalLink className="h-3 w-3 shrink-0 muted" /></> })
    }
    out.push({ key: 'ask', group: 'ask', to: `/assistant?q=${encodeURIComponent(q.trim())}`,
      node: <><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white"><Sparkles className="h-4 w-4" /></span><Lbl t={`Ask AI: “${q.trim()}”`} s="Researched answer with sources" /></> })
    return out
  }, [typing, d, recent.data, q])

  useEffect(() => { setIdx(0) }, [d])
  useEffect(() => { listRef.current?.querySelector(`[data-i="${idx}"]`)?.scrollIntoView({ block: 'nearest' }) }, [idx])
  const go = (r: Row) => {
    onClose()
    if (r.external) window.open(r.to, '_blank', 'noopener,noreferrer')
    else nav(r.to)
  }
  const active = rows[idx]
  const preview = active?.preview ?? rows.find((r) => r.preview)?.preview
  if (!open) return null
  let lastGroup = ''

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-ink-950/50 p-0 backdrop-blur-sm sm:p-4 sm:pt-[10vh]" onMouseDown={onClose} role="dialog" aria-modal="true" aria-label="Search">
      <div className="flex h-full w-full max-w-4xl flex-col overflow-hidden bg-white shadow-[var(--shadow-pop)] sm:h-auto sm:max-h-[75vh] sm:rounded-2xl dark:bg-ink-850" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 dark:border-ink-700">
          <Search className="h-5 w-5 shrink-0 text-slate-400" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" autoComplete="off" spellCheck={false}
            placeholder="Search companies, symbols, indices, sectors, concepts…" className="h-14 min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-slate-400"
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(rows.length - 1, i + 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)) }
              if (e.key === 'Enter' && rows[idx]) { e.preventDefault(); go(rows[idx]) }
            }} />
          {res.isFetching && typing && <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" aria-label="Searching" />}
          <button className="btn-ghost p-1.5 sm:hidden" onClick={onClose} aria-label="Close search"><X className="h-5 w-5" /></button>
          <kbd className="hidden rounded-md border border-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400 sm:inline dark:border-ink-600">Esc</kbd>
        </div>
        <div className="flex min-h-0 flex-1">
          <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto p-2 sm:max-h-[60vh]">
            {typing && d?.did_you_mean && <p className="px-3 pb-1 pt-1 text-xs muted">Showing results for <b className="text-slate-700 dark:text-slate-200">{d.did_you_mean}</b></p>}
            {!typing && (
              <div className="px-3 pb-2 pt-1">
                {(recent.data?.searches?.length ?? 0) > 0 && <><div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider muted">Recent searches</div>
                  <div className="mb-3 flex flex-wrap gap-1.5">{recent.data!.searches.map((s) => <button key={s} className="chip" onClick={() => setQ(s)}>{s}</button>)}</div></>}
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider muted">Try</div>
                <div className="flex flex-wrap gap-1.5">{EXAMPLES.map((s) => <button key={s} className="chip" onClick={() => setQ(s)}>{s}</button>)}</div>
              </div>
            )}
            {rows.map((r, i) => {
              const head = r.group !== lastGroup ? GROUP_TITLE[r.group] : null
              lastGroup = r.group
              return (
                <div key={r.key}>
                  {head && <div className="flex items-center gap-1.5 px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider muted">{head[1]}{head[0]}</div>}
                  <button data-i={i} onClick={() => go(r)} onMouseMove={() => setIdx(i)}
                    className={cx('flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left', i === idx ? 'bg-brand-50 dark:bg-ink-700' : '')}>
                    {r.node}{i === idx && <CornerDownLeft className="hidden h-3.5 w-3.5 shrink-0 text-slate-400 sm:block" />}
                  </button>
                </div>
              )
            })}
            {typing && res.isFetched && !res.isFetching && rows.length <= 1 && (
              <div className="px-3 py-6 text-center text-sm">
                <p className="font-medium">No company, index or topic matches “{q.trim()}”.</p>
                <p className="mt-1 muted">Check the spelling, try the NSE symbol (e.g. HDFCBANK), the ISIN, or a shorter name - or ask the AI below.</p>
              </div>
            )}
          </div>
          {typing && (d?.companies.length ?? 0) > 0 && <aside className="hidden w-72 shrink-0 border-l border-slate-200 md:block dark:border-ink-700"><Preview c={preview} /></aside>}
        </div>
        <div className="hidden items-center justify-between border-t border-slate-200 px-4 py-2 text-[11px] muted sm:flex dark:border-ink-700">
          <span>↑↓ move · Enter open · Esc close · Ctrl K or / anywhere</span>
          {typing && d?.ms != null && <span>{d.ms} ms</span>}
        </div>
      </div>
    </div>
  )
}

function Lbl({ t, s }: { t: string; s?: string }) {
  return <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{t}</span>{s && <span className="block truncate text-xs muted">{s}</span>}</span>
}
