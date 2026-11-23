import { useMutation, useQuery } from '@tanstack/react-query'
import { Award, GraduationCap, Lightbulb, Lock, RotateCcw, Trophy } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AreaGrowth, Donut } from '../components/charts'
import { CompanyPicker } from '../components/CompanyPicker'
import { CompanyAvatar, TradeTicket } from '../components/common'
import { Card, ChangePill, cx, DataBadge, EmptyState, Loading, Modal, Notice, Segmented, Stat, useToast } from '../components/ui'
import { api, type Quote } from '../lib/api'
import { baseSymbol, inr, ist, num, pct } from '../lib/format'
import { useInvalidate, useMe, useQuoteStream } from '../lib/hooks'

interface Holding { symbol: string; name: string; sector: string; qty: number; avg_price: number; invested: number; price: number | null; value: number | null; pnl: number | null; pnl_pct: number | null; day_change_pct: number | null; price_status: Quote['status']; weight: number | null; dividends: number }
interface Summary { cash: number; initial: number; invested: number; holdings_value: number; total_value: number; total_return: number; unrealised: number; realised: number; dividends: number; started_at: string; resets: number; holdings: Holding[]; trade_count: number
  sectors: Record<string, number>; concentration: { effective_n?: number; top_weight?: number }; risk: { volatility?: number; max_drawdown?: number; beta?: number | null; diversification_ratio?: number | null }
  achievements: { id: string; title: string; description: string; earned: boolean }[]; tips: string[]; disclaimer: string }
interface Trade { id: number; ts: string; kind: string; symbol: string; name: string; qty: number; price: number | null; amount: number; cash_after: number; price_type: string; note: string }

export default function Invest() {
  const s = useQuery({ queryKey: ['invest-summary'], queryFn: () => api.get<Summary>('/invest/summary') })
  const trades = useQuery({ queryKey: ['invest-trades'], queryFn: () => api.get<Trade[]>('/invest/trades') })
  const perf = useQuery({ queryKey: ['invest-perf'], queryFn: () => api.get<{ series: { date: string; portfolio: number; nifty50?: number }[]; note: string }>('/invest/performance') })
  const lb = useQuery({ queryKey: ['leaderboard'], queryFn: () => api.get<{ rows: { display_name: string; total_return: number }[]; note: string }>('/invest/leaderboard') })
  const me = useMe()
  const [pick, setPick] = useState<{ symbol: string; name: string } | null>(null)
  const [ticket, setTicket] = useState<{ symbol: string; name: string; side: 'BUY' | 'SELL' } | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const [alloc, setAlloc] = useState<'company' | 'sector'>('company')
  const stream = useQuoteStream([...(s.data?.holdings ?? []).map((h) => h.symbol), ...(pick ? [pick.symbol] : []), ...(ticket ? [ticket.symbol] : [])])
  const inv = useInvalidate()
  const toast = useToast()
  const reset = useMutation({ mutationFn: () => api.post('/invest/reset'), onSuccess: () => { inv('invest-summary', 'invest-trades', 'invest-perf'); setConfirmReset(false); toast('Started a fresh ₹10 lakh virtual portfolio') } })
  if (s.isLoading) return <Loading />
  const d = s.data!
  const quoteFor = (sym: string, fallback?: Holding): Quote | undefined => stream.quotes[sym] ?? (fallback ? { symbol: sym, price: fallback.price, prev_close: null, change: null, change_pct: fallback.day_change_pct, volume: null, time: null, status: fallback.price_status, source: '' } : undefined)

  return (
    <div className="space-y-5">
      <section className="hero-surface-brand rounded-3xl p-6 text-white">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-sm text-brand-100"><GraduationCap className="h-4 w-4" />EquityPilot Virtual Invest · practice with virtual money</div>
            <div className="num mt-2 text-4xl font-semibold">{inr(d.total_value, 0)}</div>
            <div className="mt-1 flex items-center gap-2 text-sm"><span className={cx('rounded-md px-2 py-0.5 font-semibold', d.total_return >= 0 ? 'bg-emerald-400/20 text-emerald-200' : 'bg-rose-400/20 text-rose-200')}>{pct(d.total_return, 2, true)}</span>
              <span className="text-brand-100">since {ist(d.started_at, false)} · started with {inr(d.initial, 0)}</span></div>
          </div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-3">
            {[['Available cash', inr(d.cash, 0)], ['Invested (cost)', inr(d.invested, 0)], ['Holdings value', inr(d.holdings_value, 0)],
              ['Unrealised P&L', inr(d.unrealised, 0)], ['Realised P&L', inr(d.realised, 0)], ['Dividends', inr(d.dividends, 0)]].map(([k, v]) => (
              <div key={k}><div className="text-xs text-brand-200">{k}</div><div className="num font-semibold">{v}</div></div>))}
          </div>
        </div>
      </section>
      <Notice tone="sample"><Lock className="mr-1 inline h-4 w-4" />{d.disclaimer}</Notice>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card title="Holdings" subtitle={`${d.holdings.length} positions · ${d.trade_count} trades`}>
            {d.holdings.length === 0 ? <EmptyState title="No positions yet" body="Search a company in the trade panel. Tip: research it first - read its financials, valuation and risk pages." /> : (
              <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
                <thead><tr>{['Company', 'Qty', 'Avg price', 'LTP', 'Value', 'P&L', 'Day', ''].map((h, i) => <th key={i} className={`table-head px-3 py-2.5 ${i && i < 7 ? 'text-right' : ''}`}>{h}</th>)}</tr></thead>
                <tbody>{d.holdings.map((h) => { const q = quoteFor(h.symbol, h); const val = (q?.price ?? 0) * h.qty; const pnl = val - h.invested
                  return (
                    <tr key={h.symbol} className="border-t border-slate-100 dark:border-ink-700">
                      <td className="px-3 py-2.5"><Link to={`/company/${encodeURIComponent(h.symbol)}`} className="flex items-center gap-2 hover:underline"><CompanyAvatar symbol={h.symbol} size="sm" /><span><span className="block font-medium">{h.name}</span><span className="text-[11px] muted">{h.sector}</span></span></Link></td>
                      <td className="num px-3 text-right">{num(h.qty, 0)}</td><td className="num px-3 text-right">{inr(h.avg_price)}</td>
                      <td className="num px-3 text-right">{inr(q?.price)} <DataBadge type={q?.status} /></td><td className="num px-3 text-right">{inr(val, 0)}</td>
                      <td className={cx('num px-3 text-right font-semibold', pnl >= 0 ? 'text-up' : 'text-down')}>{inr(pnl, 0)}<div className="text-[11px] font-normal">{pct(h.invested ? pnl / h.invested : null, 2, true)}</div></td>
                      <td className="px-3 text-right"><ChangePill value={q?.change_pct} /></td>
                      <td className="px-3 text-right"><span className="inline-flex gap-1"><button className="btn bg-up/10 px-2.5 py-1 text-xs text-up" onClick={() => setTicket({ symbol: h.symbol, name: h.name, side: 'BUY' })}>Buy</button>
                        <button className="btn bg-down/10 px-2.5 py-1 text-xs text-down" onClick={() => setTicket({ symbol: h.symbol, name: h.name, side: 'SELL' })}>Sell</button></span></td>
                    </tr>) })}</tbody></table></div>
            )}
          </Card>
          <Card title="Performance vs NIFTY 50" subtitle={perf.data?.note}>
            {(perf.data?.series.length ?? 0) < 2 ? <p className="text-sm muted">The chart builds up day by day from when you started (closing prices).</p> :
              <AreaGrowth data={perf.data!.series} xKey="date" series={[{ key: 'portfolio', label: 'My virtual portfolio' }, { key: 'nifty50', label: 'NIFTY 50' }]} fmt={(v) => v.toFixed(2)} />}
          </Card>
          <div className="grid gap-5 md:grid-cols-2">
            <Card title="Allocation" action={<Segmented size="xs" value={alloc} onChange={setAlloc} options={[{ id: 'company', label: 'Company' }, { id: 'sector', label: 'Sector' }]} />}>
              {d.holdings.length === 0 ? <p className="text-sm muted">—</p> : <Donut data={alloc === 'company' ? d.holdings.map((h) => ({ name: baseSymbol(h.symbol), value: h.value ?? 0 })) : Object.entries(d.sectors).map(([name, value]) => ({ name, value }))} fmt={(v) => inr(v, 0)} />}
            </Card>
            <Card title="Risk & diversification">
              <div className="grid grid-cols-2 gap-2">
                <Stat label="Effective no. of stocks" value={num(d.concentration.effective_n, 1)} help="1 / Σ(weight²)" /><Stat label="Largest position" value={pct(d.concentration.top_weight)} />
                <Stat label="Volatility (ann.)" value={pct(d.risk.volatility)} help="Current weights on last year's daily returns" /><Stat label="Beta vs NIFTY" value={num(d.risk.beta)} />
              </div>
            </Card>
          </div>
          <Card title="Transaction history">
            {(trades.data ?? []).length === 0 ? <p className="text-sm muted">No transactions yet.</p> : (
              <div className="max-h-96 overflow-y-auto"><table className="w-full text-sm"><thead><tr>{['Time', 'Type', 'Company', 'Qty', 'Price', 'Amount', 'Cash after'].map((h, i) => <th key={h} className={`table-head px-3 py-2 ${i > 2 ? 'text-right' : ''}`}>{h}</th>)}</tr></thead>
                <tbody>{trades.data!.map((t) => (
                  <tr key={t.id} className="border-t border-slate-100 dark:border-ink-700" title={t.note}>
                    <td className="px-3 py-2 text-xs muted">{ist(t.ts)}</td>
                    <td className="px-3"><span className={cx('rounded px-1.5 py-0.5 text-[10px] font-bold', t.kind === 'BUY' ? 'bg-up/10 text-up' : t.kind === 'SELL' ? 'bg-down/10 text-down' : 'bg-brand-500/10 text-brand-700 dark:text-brand-200')}>{t.kind}</span></td>
                    <td className="px-3">{baseSymbol(t.symbol)}</td><td className="num px-3 text-right">{num(t.qty, 0)}</td><td className="num px-3 text-right">{inr(t.price)}</td>
                    <td className={cx('num px-3 text-right', t.amount >= 0 ? 'text-up' : 'text-down')}>{inr(t.amount, 0)}</td><td className="num px-3 text-right">{inr(t.cash_after, 0)}</td></tr>))}</tbody></table></div>
            )}
          </Card>
        </div>
        <div className="space-y-5">
          <Card title="Trade">
            <CompanyPicker trackedOnly placeholder="Search a company to trade…" onChange={(sym, name) => setPick({ symbol: sym, name })} />
            {pick ? <div className="mt-4"><TradeTicket key={pick.symbol} symbol={pick.symbol} name={pick.name} quote={stream.quotes[pick.symbol]} /></div>
              : <p className="mt-3 text-xs muted">Only tracked companies can be traded. Open any company's page first to fetch its data.</p>}
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5"><Lightbulb className="h-4 w-4 text-saffron-500" />Learning tips</span>} subtitle="Educational observations, not investment advice">
            <ul className="space-y-2 text-sm">{d.tips.map((t) => <li key={t} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-saffron-500" />{t}</li>)}</ul>
            <Link to="/learn?lesson=portfolio-diversification" className="mt-3 inline-block text-sm font-medium text-brand-600 hover:underline">Learn about diversification →</Link>
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5"><Award className="h-4 w-4 text-brand-600" />Achievements</span>}>
            <div className="grid grid-cols-2 gap-2">{d.achievements.map((a) => (
              <div key={a.id} title={a.description} className={cx('rounded-xl border p-2.5 text-xs', a.earned ? 'border-saffron-400/60 bg-saffron-400/10' : 'border-slate-200 opacity-60 dark:border-ink-700')}>
                <div className="font-semibold">{a.earned ? '🏅 ' : ''}{a.title}</div><div className="mt-0.5 muted">{a.description}</div></div>))}</div>
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5"><Trophy className="h-4 w-4 text-saffron-500" />Leaderboard</span>} subtitle={lb.data?.note}>
            {(lb.data?.rows ?? []).length === 0 ? <p className="text-sm muted">No one has opted in yet.{me.data?.user && !me.data.user.show_on_leaderboard ? <> <Link className="text-brand-600 underline" to="/settings">Join from Settings</Link>.</> : null}</p> : (
              <ol className="space-y-1.5 text-sm">{lb.data!.rows.map((r, i) => <li key={i} className="flex justify-between"><span><span className="mr-2 font-bold muted">{i + 1}</span>{r.display_name}</span><ChangePill value={r.total_return} /></li>)}</ol>
            )}
          </Card>
          <button className="btn-outline w-full" onClick={() => setConfirmReset(true)}><RotateCcw className="h-4 w-4" />Reset virtual portfolio</button>
        </div>
      </div>
      <Modal open={!!ticket} onClose={() => setTicket(null)} title="Virtual trade">
        {ticket && <TradeTicket key={ticket.symbol + ticket.side} symbol={ticket.symbol} name={ticket.name} side={ticket.side} quote={stream.quotes[ticket.symbol] ?? quoteFor(ticket.symbol, d.holdings.find((h) => h.symbol === ticket.symbol))} onDone={() => setTicket(null)} />}
      </Modal>
      <Modal open={confirmReset} onClose={() => setConfirmReset(false)} title="Reset virtual portfolio?">
        <p className="text-sm">This deletes all virtual holdings and transactions and starts again with ₹10,00,000 virtual cash. It cannot be undone.</p>
        <div className="mt-4 flex gap-2"><button className="btn-danger flex-1" onClick={() => reset.mutate()}>Reset</button><button className="btn-outline flex-1" onClick={() => setConfirmReset(false)}>Cancel</button></div>
      </Modal>
    </div>
  )
}
