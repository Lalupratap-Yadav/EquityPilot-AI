import { useMutation, useQuery } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AreaGrowth, BarsChart, Donut } from '../components/charts'
import { CompanyPicker } from '../components/CompanyPicker'
import { CompanyAvatar } from '../components/common'
import { Card, ChangePill, EmptyState, Loading, Notice, PageHeader, Stat, useToast } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, inr, isNum, num, pct } from '../lib/format'
import { useInvalidate } from '../lib/hooks'

interface PortResp {
  empty?: boolean
  lots: { id: number; symbol: string; quantity: number; avg_cost: number; buy_date: string | null; notes: string | null }[]
  holdings: { symbol: string; name: string; sector: string; quantity: number; invested: number; value: number | null; price: number | null; weight: number | null }[]
  invested: number; value: number; pnl: number; return: number | null; xirr: number | null
  concentration: { hhi: number | null; effective_n: number | null; top_weight: number | null }
  sectors: Record<string, number>
  risk: { volatility?: number; annual_return?: number; sharpe?: number | null; max_drawdown?: number; beta?: number | null; diversification_ratio?: number | null; observations?: number }
  risk_contribution: Record<string, number>; correlation: { symbols: string[]; values: number[][] } | null; growth: { date: string; value: number }[]
}

export default function Portfolio() {
  const q = useQuery({ queryKey: ['portfolio'], queryFn: () => api.get<PortResp>('/portfolio') })
  const [lot, setLot] = useState({ symbol: '', quantity: '', avg_cost: '', buy_date: '', notes: '' })
  const toast = useToast()
  const inv = useInvalidate()
  const add = useMutation({
    mutationFn: () => api.post('/portfolio/lots', { symbol: lot.symbol, quantity: Number(lot.quantity), avg_cost: Number(lot.avg_cost), buy_date: lot.buy_date || null, notes: lot.notes || null }),
    onSuccess: () => { toast('Holding added'); setLot({ symbol: '', quantity: '', avg_cost: '', buy_date: '', notes: '' }); inv('portfolio') }, onError: (e) => toast((e as Error).message, 'error'),
  })
  const del = useMutation({ mutationFn: (id: number) => api.del(`/portfolio/lots/${id}`), onSuccess: () => inv('portfolio') })
  const d = q.data
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="My space" title="Portfolio analysis" subtitle="Record your real holdings manually (EquityPilot never connects to your demat account) and analyse value, returns, allocation, diversification and risk. For practice with virtual money, use Virtual Invest." />
      <Card title="Add a holding (purchase lot)">
        <div className="grid gap-3 md:grid-cols-6">
          <div className="md:col-span-2"><label className="label">Company</label><CompanyPicker value={lot.symbol} trackedOnly onChange={(s) => setLot({ ...lot, symbol: s })} />{lot.symbol && <div className="mt-1 text-xs muted">Selected: {baseSymbol(lot.symbol)}</div>}</div>
          <div><label className="label">Quantity</label><input className="input num" type="number" min="0" value={lot.quantity} onChange={(e) => setLot({ ...lot, quantity: e.target.value })} /></div>
          <div><label className="label">Average cost (₹)</label><input className="input num" type="number" min="0" step="0.05" value={lot.avg_cost} onChange={(e) => setLot({ ...lot, avg_cost: e.target.value })} /></div>
          <div><label className="label">Buy date (for XIRR)</label><input className="input" type="date" value={lot.buy_date} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setLot({ ...lot, buy_date: e.target.value })} /></div>
          <div className="flex items-end"><button className="btn-primary w-full" disabled={!lot.symbol || !Number(lot.quantity) || !Number(lot.avg_cost) || add.isPending} onClick={() => add.mutate()}><Plus className="h-4 w-4" />Add</button></div>
        </div>
      </Card>
      {q.isLoading ? <Loading /> : !d || d.empty ? <EmptyState title="No holdings yet" body="Add purchase lots above to see value, returns and risk." /> : (<>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Stat label="Current value" value={inr(d.value, 0)} /><Stat label="Invested" value={inr(d.invested, 0)} />
          <Stat label="Unrealised P&L" value={inr(d.pnl, 0)} sub={pct(d.return, 2, true)} tone={d.pnl >= 0 ? 'up' : 'down'} />
          <Stat label="XIRR (annualised)" value={pct(d.xirr)} help="Money-weighted annual return using each lot's buy date; needs a buy date for every lot" />
          <Stat label="Holdings" value={String(d.holdings.length)} /><Stat label="Effective no. of stocks" value={num(d.concentration.effective_n, 1)} help="1 / Σ(weight²). Lower = more concentrated" />
        </div>
        {(d.concentration.top_weight ?? 0) > 0.25 && <Notice tone="warn">Largest holding is {pct(d.concentration.top_weight, 0)} of the portfolio - concentration means one company's results can move the whole portfolio.</Notice>}
        <Card title="Holdings" pad={false}>
          <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
            <thead><tr>{['Company', 'Qty', 'Invested', 'Price', 'Value', 'P&L', 'Weight'].map((h, i) => <th key={h} className={`table-head px-4 py-2.5 ${i ? 'text-right' : ''}`}>{h}</th>)}</tr></thead>
            <tbody>{d.holdings.map((h) => (
              <tr key={h.symbol} className="border-t border-slate-100 dark:border-ink-700">
                <td className="px-4 py-2.5"><Link to={`/company/${encodeURIComponent(h.symbol)}`} className="flex items-center gap-2 hover:underline"><CompanyAvatar symbol={h.symbol} size="sm" /><span className="font-medium">{h.name}</span></Link></td>
                <td className="num px-4 text-right">{num(h.quantity, 0)}</td><td className="num px-4 text-right">{inr(h.invested, 0)}</td><td className="num px-4 text-right">{inr(h.price)}</td>
                <td className="num px-4 text-right">{inr(h.value, 0)}</td><td className="px-4 text-right">{isNum(h.value) && <ChangePill value={h.value / h.invested - 1} />}</td><td className="num px-4 text-right">{pct(h.weight)}</td>
              </tr>))}</tbody></table></div>
        </Card>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Allocation by holding"><Donut data={d.holdings.map((h) => ({ name: h.name.replace(' Limited', ''), value: h.value ?? 0 }))} fmt={(v) => inr(v, 0)} /></Card>
          <Card title="Sector exposure"><Donut data={Object.entries(d.sectors).map(([name, value]) => ({ name, value }))} fmt={(v) => inr(v, 0)} /></Card>
        </div>
        {d.risk.volatility !== undefined && (<>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Stat label="1Y return (current weights)" value={pct(d.risk.annual_return, 1, true)} /><Stat label="Volatility" value={pct(d.risk.volatility)} />
            <Stat label="Sharpe ratio" value={num(d.risk.sharpe)} help="(Return − 6.5% risk-free) / volatility" /><Stat label="Max drawdown" value={pct(d.risk.max_drawdown)} />
            <Stat label="Beta vs NIFTY" value={num(d.risk.beta)} /><Stat label="Diversification ratio" value={num(d.risk.diversification_ratio)} help="Weighted average stock volatility / portfolio volatility" />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Growth of ₹100 at current weights" subtitle={`${d.risk.observations} daily returns - today's weights applied to past prices`}><AreaGrowth data={d.growth} xKey="date" series={[{ key: 'value', label: 'Portfolio' }]} fmt={(v) => v.toFixed(1)} /></Card>
            <Card title="Share of portfolio risk" subtitle="Each holding's contribution to total variance"><BarsChart data={Object.entries(d.risk_contribution).map(([s, v]) => ({ name: baseSymbol(s), value: v * 100 }))} xKey="name" series={[{ key: 'value', label: 'Risk share (%)' }]} fmt={(v) => `${v.toFixed(1)}%`} /></Card>
          </div>
          {d.correlation && d.correlation.symbols.length > 1 && (
            <Card title="Correlation of daily returns" subtitle="Lower correlation between holdings improves diversification">
              <div className="overflow-x-auto"><table className="text-xs"><thead><tr><th />{d.correlation.symbols.map((s) => <th key={s} className="p-1 font-semibold muted">{baseSymbol(s)}</th>)}</tr></thead>
                <tbody>{d.correlation.symbols.map((s, i) => (<tr key={s}><td className="p-1 pr-2 font-semibold muted">{baseSymbol(s)}</td>{d.correlation!.values[i].map((v, j) => (
                  <td key={j} className="num h-9 w-16 rounded text-center" style={{ background: v >= 0 ? `rgba(42,120,214,${Math.abs(v) * 0.55})` : `rgba(220,53,69,${Math.abs(v) * 0.55})` }}>{v.toFixed(2)}</td>))}</tr>))}</tbody></table></div>
            </Card>
          )}
        </>)}
        <Card title="Purchase lots">
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">{d.lots.map((l) => (
            <li key={l.id} className="flex items-center justify-between gap-3 py-2 text-sm"><span className="font-medium">{baseSymbol(l.symbol)}</span><span className="num">{num(l.quantity, 0)} @ {inr(l.avg_cost)}</span><span className="muted">{l.buy_date ?? 'no date'}</span>
              <button className="btn-ghost p-1.5" onClick={() => del.mutate(l.id)} aria-label="Delete lot"><Trash2 className="h-4 w-4" /></button></li>))}</ul>
        </Card>
      </>)}
    </div>
  )
}
