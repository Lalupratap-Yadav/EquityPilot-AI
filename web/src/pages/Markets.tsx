import { useQuery } from '@tanstack/react-query'
import { Radio, Wifi, WifiOff } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Sparkline } from '../components/charts'
import { StockChart } from '../components/StockChart'
import { Card, ChangePill, cx, DataBadge, EmptyState, Notice, PageHeader, Segmented, Skeleton } from '../components/ui'
import { api, type IndexRow, type MarketStatus } from '../lib/api'
import { baseSymbol, inr, num, timeAgo } from '../lib/format'
import { useQuoteStream } from '../lib/hooks'


const INDEX_NAMES: Record<string, string> = { '^NSEI': 'NIFTY 50', '^BSESN': 'SENSEX', '^NSEBANK': 'NIFTY BANK', '^CNX100': 'NIFTY 100',
  '^NSEMDCP50': 'NIFTY MIDCAP 50', '^INDIAVIX': 'INDIA VIX', '^CNXIT': 'NIFTY IT' }

export default function Markets() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || '^NSEI'
  const [board, setBoard] = useState<'watchlist' | 'universe'>('universe')
  const ov = useQuery({ queryKey: ['market-overview'], queryFn: () => api.get<{ status: MarketStatus; indices: IndexRow[] }>('/market/overview'), refetchInterval: 120_000 })
  const wl = useQuery({ queryKey: ['watchlists'], queryFn: () => api.get<{ items: { symbol: string; name: string }[] }[]>('/watchlists') })
  const mv = useQuery({ queryKey: ['movers-20'], queryFn: () => api.get<{ active: { symbol: string; name: string }[] }>('/market/movers?n=20') })
  const boardSymbols = useMemo(() => (board === 'watchlist' ? (wl.data ?? []).flatMap((w) => w.items.map((i) => i.symbol)) : (mv.data?.active ?? []).map((m) => m.symbol)).slice(0, 25), [board, wl.data, mv.data])
  const names = useMemo(() => Object.fromEntries([...(wl.data ?? []).flatMap((w) => w.items), ...(mv.data?.active ?? [])].map((x) => [x.symbol, x.name])), [wl.data, mv.data])
  const stream = useQuoteStream(boardSymbols)
  const idx = ov.data?.indices ?? []
  const current = idx.find((i) => i.symbol === symbol)

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Market tracking" title="Market Tracker" subtitle="Charts from 1 day to the full history, with streaming quote updates. All prices are labelled LIVE, DELAYED, LAST CLOSE or HISTORICAL - EquityPilot never shows an unlabelled price."
        actions={<span className={cx('inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold', stream.connected ? 'bg-up/10 text-up' : 'bg-slate-500/10 text-slate-500')}>
          {stream.connected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}{stream.connected ? 'Stream connected' : 'Connecting…'}</span>} />
      <div className="scroll-row">
        {ov.isLoading && Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[84px] w-[170px] shrink-0 rounded-2xl" />)}
        {idx.map((i) => (
          <button key={i.symbol} onClick={() => setParams({ symbol: i.symbol })}
            className={cx('card w-[170px] shrink-0 p-3 text-left transition-colors', symbol === i.symbol ? 'border-brand-500 ring-2 ring-brand-500/20' : 'hover:border-brand-300')}>
            <div className="truncate text-[11px] font-semibold muted">{i.name}</div>
            <div className="num text-sm font-semibold">{num(i.last, 2)}</div>
            <div className="flex items-center justify-between"><ChangePill value={i.change_pct} /><Sparkline data={i.spark} width={56} height={22} /></div>
          </button>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2" title={current?.name ?? INDEX_NAMES[symbol] ?? baseSymbol(symbol)}>
          <StockChart symbol={symbol} isIndex={symbol.startsWith('^')} defaultRange="1D"
            live={current ? { price: current.last, prev_close: current.prev ?? null, time: current.time ?? null } : null} />
        </Card>

        <Card title={<span className="inline-flex items-center gap-1.5"><Radio className="h-4 w-4 text-brand-600" />Quote board</span>}
          subtitle={stream.updatedAt ? `Updated ${timeAgo(new Date(stream.updatedAt).toISOString())} · pushes every ~30 s` : 'Waiting for the first update…'}
          action={<Segmented size="xs" value={board} onChange={setBoard} options={[{ id: 'universe', label: 'Most active' }, { id: 'watchlist', label: 'Watchlist' }]} />}>
          {boardSymbols.length === 0 ? <EmptyState title="Nothing to track" body={board === 'watchlist' ? 'Add companies to a watchlist first.' : 'Loading…'} /> : (
            <ul className="divide-y divide-slate-100 dark:divide-ink-700">
              {boardSymbols.map((s) => {
                const q = stream.quotes[s]
                return (
                  <li key={s} className="flex items-center justify-between gap-2 py-2">
                    <Link to={`/company/${encodeURIComponent(s)}`} className="min-w-0"><div className="truncate text-sm font-medium hover:underline">{names[s] ?? baseSymbol(s)}</div><div className="text-[11px] muted">{baseSymbol(s)}</div></Link>
                    <div className="text-right"><div className="num text-sm font-semibold">{inr(q?.price)}</div><div className="flex items-center justify-end gap-1"><ChangePill value={q?.change_pct} /><DataBadge type={q?.status} /></div></div>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>

      <Notice><b>About real-time data and market depth.</b> Prices come from Yahoo Finance and are typically delayed by about 15 minutes for NSE. Market depth (the order book) and true tick-by-tick prices require a licensed exchange data feed or a broker API connected to your own trading account, so EquityPilot does not display them. See Settings → Data sources for the options.</Notice>
    </div>
  )
}
