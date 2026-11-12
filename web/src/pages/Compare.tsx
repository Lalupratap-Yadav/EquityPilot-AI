import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { LinesChart } from '../components/charts'
import { CompanyPicker } from '../components/CompanyPicker'
import { CompanyAvatar } from '../components/common'
import { Card, cx, EmptyState, Loading, Notice, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, byKind, isNum } from '../lib/format'

type Row = Record<string, string | number | boolean | null>
interface CompareResp { rows: Row[]; series: Record<string, { revenue_index?: { label: string; value: number }[]; price_index?: { date: string; value: number }[] }>; metrics: Record<string, { label: string; kind: string }> }

const GROUPS: [string, string[]][] = [
  ['Valuation', ['price', 'market_cap', 'pe', 'pb', 'ev_ebitda', 'dividend_yield']],
  ['Growth', ['revenue_growth', 'net_income_growth', 'revenue_cagr_3y', 'profit_cagr_3y']],
  ['Profitability & returns', ['ebitda_margin', 'net_margin', 'roe', 'roce']],
  ['Balance sheet & cash flow', ['debt_to_equity', 'interest_coverage', 'current_ratio', 'cfo_to_net_income', 'fcf_margin']],
  ['Scale & quality', ['revenue', 'net_income', 'piotroski']],
]
const LOWER_BETTER = new Set(['pe', 'pb', 'ev_ebitda', 'debt_to_equity'])
const NO_STAR = new Set(['price', 'market_cap', 'revenue', 'net_income'])

export default function Compare() {
  const [params, setParams] = useSearchParams()
  const symbols = (params.get('symbols') || '').split(',').filter(Boolean).slice(0, 5)
  const q = useQuery({ queryKey: ['compare', symbols.join(',')], enabled: symbols.length >= 1, queryFn: () => api.get<CompareResp>(`/compare?symbols=${symbols.map(encodeURIComponent).join(',')}`) })
  const setSyms = (s: string[]) => setParams({ symbols: s.join(',') })
  const rows = q.data?.rows ?? []
  const revSeries = useMemo(() => {
    const labels = [...new Set(Object.values(q.data?.series ?? {}).flatMap((s) => (s.revenue_index ?? []).map((x) => x.label)))].sort()
    return labels.map((l) => ({ label: l, ...Object.fromEntries(Object.entries(q.data?.series ?? {}).map(([sym, s]) => [baseSymbol(sym), s.revenue_index?.find((x) => x.label === l)?.value ?? null])) }))
  }, [q.data])
  const priceSeries = useMemo(() => {
    const m = new Map<string, Record<string, number | string | null>>()
    Object.entries(q.data?.series ?? {}).forEach(([sym, s]) => (s.price_index ?? []).forEach((p) => { const r = m.get(p.date) ?? { date: p.date }; r[baseSymbol(sym)] = p.value; m.set(p.date, r) }))
    return [...m.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)))
  }, [q.data])

  const best = (k: string) => {
    if (NO_STAR.has(k)) return null
    const vals = rows.map((r) => r[k]).filter(isNum) as number[]
    if (vals.length < 2) return null
    return LOWER_BETTER.has(k) ? Math.min(...vals.filter((v) => v > 0)) : Math.max(...vals)
  }
  const mixed = rows.some((r) => r.is_sample) && rows.some((r) => !r.is_sample)
  const mixedFin = rows.some((r) => r.is_financial) && rows.some((r) => !r.is_financial)
  const usd = rows.filter((r) => r.currency && r.currency !== 'INR')

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Company comparison" title="Compare companies" subtitle="Two to five companies side by side. ★ marks the most favourable value in a row (lowest for valuation multiples and leverage) - a prompt to investigate, not a conclusion." />
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          {symbols.map((s) => <span key={s} className="chip chip-active">{baseSymbol(s)}<button onClick={() => setSyms(symbols.filter((x) => x !== s))} aria-label={`Remove ${s}`}><X className="h-3 w-3" /></button></span>)}
          {symbols.length < 5 && <CompanyPicker className="w-72" placeholder="Add a company…" onChange={(s) => !symbols.includes(s) && setSyms([...symbols, s])} />}
        </div>
      </Card>
      {symbols.length < 2 ? <EmptyState title="Add at least two companies" body="Search above, or select rows in the Screener and choose Compare." /> : q.isLoading ? <Loading /> : (<>
        {mixed && <Notice tone="sample">The selection mixes fictional SAMPLE companies with real ones - sample figures aren't meaningful against real data.</Notice>}
        {mixedFin && <Notice>The selection mixes financial and non-financial companies: leverage, liquidity and EV-based metrics are not comparable (blank for financials).</Notice>}
        {usd.length > 0 && <Notice tone="warn">{usd.map((r) => r.name).join(', ')}: statements reported in {String(usd[0].currency)} by the provider, so rupee amounts and price multiples are not shown.</Notice>}
        <Card pad={false}>
          <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
            <thead><tr><th className="table-head px-4 py-3">Metric</th>{rows.map((r) => (
              <th key={String(r.symbol)} className="table-head px-4 py-3 text-right normal-case tracking-normal"><Link to={`/company/${encodeURIComponent(String(r.symbol))}`} className="inline-flex items-center gap-2 hover:underline">
                <CompanyAvatar symbol={String(r.symbol)} size="sm" /><span className="text-left text-xs font-semibold text-slate-800 dark:text-slate-100">{String(r.name).replace(' Limited', '')}</span></Link></th>))}</tr></thead>
            <tbody>{GROUPS.map(([g, keys]) => [
              <tr key={g}><td colSpan={rows.length + 1} className="bg-slate-50 px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-brand-700 dark:bg-ink-800 dark:text-brand-300">{g}</td></tr>,
              ...keys.map((k) => { const b = best(k); const def = q.data!.metrics[k]
                return (
                  <tr key={k} className="border-t border-slate-100 dark:border-ink-700">
                    <td className="px-4 py-2">{def?.label ?? k}</td>
                    {rows.map((r) => { const v = r[k]; const star = b !== null && v === b
                      return <td key={String(r.symbol)} className={cx('num px-4 py-2 text-right', star && 'font-semibold text-brand-700 dark:text-brand-200')}>{byKind(v, def?.kind ?? 'num')}{star ? ' ★' : ''}</td> })}
                  </tr>)
              })])}</tbody></table></div>
        </Card>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Revenue indexed to 100" subtitle="First available fiscal year = 100; puts different-sized companies on one scale">
            <LinesChart data={revSeries} xKey="label" series={rows.map((r) => ({ key: baseSymbol(String(r.symbol)), label: baseSymbol(String(r.symbol)) }))} fmt={(v) => v.toFixed(0)} />
          </Card>
          <Card title="Price performance, last 12 months" subtitle="Rebased to 100; price return only (dividends excluded)">
            <LinesChart data={priceSeries} xKey="date" series={rows.map((r) => ({ key: baseSymbol(String(r.symbol)), label: baseSymbol(String(r.symbol)) }))} fmt={(v) => v.toFixed(1)} dots={false} />
          </Card>
        </div>
      </>)}
    </div>
  )
}
