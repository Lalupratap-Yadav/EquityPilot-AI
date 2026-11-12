import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { BarsChart, LinesChart } from '../../components/charts'
import { AssessChip, ExplainLabel, type Assessment, type GuideEntry } from '../../components/Explain'
import { Card, cx, DataBadge, EmptyState, Loading, Notice, Segmented, SourceNote } from '../../components/ui'
import { api } from '../../lib/api'
import { byKind, isNum, num, pct } from '../../lib/format'

interface Row { key: string; label: string; values: (number | null)[] }
interface Ratio { key: string; label: string; category: string; formula: string; kind: string; help: string; values: (number | null)[]; guide?: GuideEntry | null; assessment?: Assessment | null }
interface Fin {
  empty?: boolean; bases?: string[]
  periods: string[]; labels: string[]; basis: string; currency: string; unit: string; divisor: number
  statements: Record<string, { title: string; rows: Row[] }>; ratios: Ratio[]
  dupont: Record<string, Record<string, number | null>>; piotroski: { score: number | null; tests: [string, boolean | null][] }
  cagr: Record<string, { '3y': number | null; all: number | null }>
  quality: { level: string; check: string; detail: string }[]; sources: string[]; data_types: string[]; fetched_at: string
  benchmark_note?: string; is_financial?: boolean
}

const HEALTH = ['roe', 'roce', 'revenue_growth', 'net_income_growth', 'debt_to_equity', 'interest_coverage', 'cfo_to_net_income', 'current_ratio']
const HEALTH_FIN = ['roe', 'roa', 'revenue_growth', 'net_income_growth']
const latest = (vals: (number | null)[]) => [...vals].reverse().find(isNum) ?? null
/** Chart-friendly series in display units (percentages as %, not fractions). */
function ratioHistory(r: Ratio, labels: string[]) {
  const scale = r.kind === 'pct' ? 100 : 1
  return labels.map((l, i) => ({ label: l, value: isNum(r.values[i]) ? r.values[i]! * scale : null }))
}
function ratioFmt(kind: string) {
  return (v: number) => kind === 'pct' ? `${v.toFixed(1)}%` : kind === 'x' ? `${v.toFixed(1)}x` : kind === 'days' ? `${v.toFixed(0)} d` : kind === 'inr' ? `₹${v.toFixed(1)}` : v.toFixed(2)
}

function RatioLabel({ r, labels }: { r: Ratio; labels: string[] }) {
  return <ExplainLabel metric={r.key} label={r.label} value={byKind(latest(r.values), r.kind)} assessment={r.assessment} formula={r.formula}
    history={ratioHistory(r, labels)} fmt={ratioFmt(r.kind)} />
}

function HealthSummary({ d }: { d: Fin }) {
  const keys = d.is_financial ? HEALTH_FIN : HEALTH
  const rows = keys.map((k) => d.ratios.find((r) => r.key === k)).filter((r): r is Ratio => !!r)
  if (!rows.length) return null
  return (
    <Card title="Financial health at a glance" subtitle="Latest fiscal year. Click any metric for a plain-English explanation and its history.">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {rows.map((r) => (
          <div key={r.key} className="rounded-xl border border-slate-200 p-3 dark:border-ink-700">
            <div className="flex items-start justify-between gap-2 text-xs font-medium muted"><RatioLabel r={r} labels={d.labels} /><AssessChip a={r.assessment} /></div>
            <div className="num mt-1 text-lg font-semibold">{byKind(latest(r.values), r.kind)}</div>
            <p className="mt-0.5 text-xs leading-snug text-slate-600 dark:text-slate-300">{r.assessment?.text ?? (isNum(latest(r.values)) ? 'No single benchmark applies - compare with peers and history.' : 'Data not available.')}</p>
          </div>
        ))}
      </div>
      {d.benchmark_note && <p className="mt-3 text-xs muted">{d.benchmark_note}</p>}
    </Card>
  )
}

const BOLD = new Set(['revenue', 'ebitda', 'ebit', 'net_income', 'total_assets', 'total_equity', 'cfo', 'fcf'])
const PER_SHARE = new Set(['eps_basic', 'eps_diluted'])
const COUNTS = new Set(['shares_diluted', 'shares_outstanding'])
const BASIS: Record<string, string> = { consolidated: 'Consolidated', standalone: 'Standalone', unspecified: 'Provider basis (not stated)' }

export default function FinancialsTab({ symbol, isFinancial }: { symbol: string; isFinancial: boolean }) {
  const [period, setPeriod] = useState<'annual' | 'quarterly'>('annual')
  const [basis, setBasis] = useState<string>('')
  const [view, setView] = useState<'income' | 'balance' | 'cashflow' | 'ratios'>('income')
  const q = useQuery({
    queryKey: ['fin', symbol, period, basis],
    queryFn: () => api.get<Fin>(`/companies/${encodeURIComponent(symbol)}/financials?period=${period}${basis ? `&basis=${basis}` : ''}`),
  })
  const d = q.data
  const fmt = (key: string, v: number | null) => {
    if (!isNum(v)) return '—'
    if (PER_SHARE.has(key)) return num(v)
    if (COUNTS.has(key)) return `${num(v / 1e7)} Cr`
    return num(v / (d?.divisor ?? 1e7), 0)
  }
  const chart = useMemo(() => {
    if (!d || d.empty) return []
    const get = (k: string) => d.statements.income.rows.find((r) => r.key === k)?.values ?? []
    const rev = get('revenue'), ebitda = get('ebitda'), ni = get('net_income')
    return d.labels.map((l, i) => ({ label: l, Revenue: isNum(rev[i]) ? rev[i]! / d.divisor : null, EBITDA: isNum(ebitda[i]) ? ebitda[i]! / d.divisor : null, 'Net profit': isNum(ni[i]) ? ni[i]! / d.divisor : null }))
  }, [d])
  const margins = useMemo(() => {
    if (!d || d.empty) return []
    const r = (k: string) => d.ratios.find((x) => x.key === k)?.values ?? []
    return d.labels.map((l, i) => ({ label: l, 'EBITDA margin': r('ebitda_margin')[i] != null ? r('ebitda_margin')[i]! * 100 : null,
      'Net margin': r('net_margin')[i] != null ? r('net_margin')[i]! * 100 : null, ROE: r('roe')[i] != null ? r('roe')[i]! * 100 : null }))
  }, [d])

  if (q.isLoading) return <Loading />
  if (!d || d.empty) return <EmptyState title={`No ${period} statements stored`} body="Upload statements from the annual report in Documents, or refresh the company from the provider." />

  const categories = [...new Set(d.ratios.map((r) => r.category))]
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Segmented value={period} onChange={(v) => { setPeriod(v); setBasis('') }} options={[{ id: 'annual', label: 'Annual' }, { id: 'quarterly', label: 'Quarterly' }]} />
        <Segmented value={view} onChange={setView} options={[{ id: 'income', label: 'P&L' }, { id: 'balance', label: 'Balance sheet' }, { id: 'cashflow', label: 'Cash flow' }, { id: 'ratios', label: 'Ratios' }]} />
        {(d.bases?.length ?? 0) > 1 && (
          <select className="input w-auto" value={basis || d.basis} onChange={(e) => setBasis(e.target.value)} aria-label="Statement basis">
            {d.bases!.map((b) => <option key={b} value={b}>{BASIS[b] ?? b}</option>)}
          </select>
        )}
        <span className="ml-auto flex items-center gap-1.5">{d.data_types.map((t) => <DataBadge key={t} type={t} />)}</span>
      </div>
      {d.basis === 'unspecified' && <Notice>Basis not stated by the provider - Yahoo Finance generally shows consolidated figures for Indian listings; verify material numbers against the filing.</Notice>}
      {d.currency !== 'INR' && <Notice tone="warn">Statements are reported by the provider in {d.currency}. Ratios are valid; price multiples are not computed.</Notice>}

      {view !== 'ratios' ? (
        <Card pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-max text-sm">
              <thead><tr><th className="table-head sticky left-0 px-4 py-2.5">{d.unit}</th>{d.labels.map((l) => <th key={l} className="table-head px-4 py-2.5 text-right">{l}</th>)}</tr></thead>
              <tbody>
                {d.statements[view].rows.map((r) => (
                  <tr key={r.key} className={cx('border-t border-slate-100 dark:border-ink-700/70', BOLD.has(r.key) && 'bg-slate-50/70 font-semibold dark:bg-ink-800/50')}>
                    <td className="sticky left-0 bg-inherit px-4 py-2">{r.label}</td>
                    {r.values.map((v, i) => <td key={i} className={cx('num px-4 py-2 text-right', isNum(v) && v < 0 && 'text-down')}>{fmt(r.key, v)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 pb-3"><SourceNote sources={d.sources} time={d.fetched_at} extra={`Basis: ${BASIS[d.basis] ?? d.basis}. EPS in ₹; share counts in crore; '—' = not reported.`} /></div>
        </Card>
      ) : (
        <div className="space-y-4">
          {period === 'quarterly' ? <Notice tone="warn">Quarterly ratios use quarterly flows against period-end balances (not annualised), so they are not rated against benchmarks.</Notice> : <HealthSummary d={d} />}
          {categories.map((cat) => (
            <Card key={cat} title={cat} pad={false}>
              <div className="overflow-x-auto">
                <table className="w-full min-w-max text-sm">
                  <thead><tr><th className="table-head px-4 py-2">Ratio</th>{d.labels.map((l) => <th key={l} className="table-head px-4 py-2 text-right">{l}</th>)}{period === 'annual' && <th className="table-head px-4 py-2 text-right">Rating</th>}</tr></thead>
                  <tbody>
                    {d.ratios.filter((r) => r.category === cat).map((r) => (
                      <tr key={r.key} className="border-t border-slate-100 dark:border-ink-700/70">
                        <td className="px-4 py-2"><RatioLabel r={r} labels={d.labels} /></td>
                        {r.values.map((v, i) => <td key={i} className={cx('num px-4 py-2 text-right', isNum(v) && v < 0 && 'text-down')}>{byKind(v, r.kind)}</td>)}
                        {period === 'annual' && <td className="px-4 py-2 text-right">{r.assessment ? <AssessChip a={r.assessment} /> : <span className="text-xs muted">—</span>}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
          {isFinancial && <Notice>Liquidity and leverage ratios are not meaningful for banks and NBFCs - see the Bank metrics tab.</Notice>}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title={`Revenue, EBITDA & net profit (${d.unit})`}><BarsChart data={chart} xKey="label" series={[{ key: 'Revenue', label: 'Revenue' }, { key: 'EBITDA', label: 'EBITDA' }, { key: 'Net profit', label: 'Net profit' }]} fmt={(v) => num(v, 0)} yFmt={(v) => num(v, 0)} /></Card>
        <Card title="Margins & ROE (%)"><LinesChart data={margins} xKey="label" series={[{ key: 'EBITDA margin', label: 'EBITDA margin' }, { key: 'Net margin', label: 'Net margin' }, { key: 'ROE', label: 'ROE' }]} fmt={(v) => `${v.toFixed(1)}%`} yFmt={(v) => `${v}%`} /></Card>
      </div>

      {period === 'annual' && (
        <div className="grid gap-5 lg:grid-cols-3">
          <Card title="DuPont analysis" subtitle="ROE = Net margin × Asset turnover × Equity multiplier">
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(d.dupont).map(([k, row]) => (
                  <tr key={k} className="border-t border-slate-100 first:border-0 dark:border-ink-700">
                    <td className="py-1.5">{k}</td>
                    <td className="num py-1.5 text-right font-medium">{(() => { const v = Object.values(row).at(-1); return k.includes('margin') || k.includes('ROE') ? pct(v) : isNum(v) ? `${v.toFixed(2)}x` : '—' })()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs muted">Latest year. ROE driven by margins or turnover is higher quality than ROE driven by leverage.</p>
          </Card>
          <Card title="Piotroski F-score" subtitle="Nine tests of profitability, leverage and efficiency (latest vs prior year)">
            {d.piotroski.score === null ? <p className="text-sm muted">Not enough data{isFinancial ? ' (and not designed for financial companies)' : ''}.</p> : (<>
              <div className="num text-3xl font-semibold">{d.piotroski.score}<span className="text-base muted"> / 9</span></div>
              <ul className="mt-2 space-y-1 text-xs">{d.piotroski.tests.map(([t, v]) => <li key={t} className="flex justify-between"><span>{t}</span><span className={v ? 'text-up' : v === false ? 'text-down' : 'muted'}>{v ? 'Pass' : v === false ? 'Fail' : 'n/a'}</span></li>)}</ul>
            </>)}
          </Card>
          <Card title="Growth (CAGR)">
            <table className="w-full text-sm"><thead><tr className="text-xs muted"><th className="text-left font-medium">Metric</th><th className="text-right font-medium">3-year</th><th className="text-right font-medium">Full period</th></tr></thead>
              <tbody>{Object.entries(d.cagr).map(([k, v]) => <tr key={k} className="border-t border-slate-100 dark:border-ink-700"><td className="py-1.5 capitalize">{k.replace('_', ' ').replace('eps diluted', 'EPS')}</td><td className="num text-right">{pct(v['3y'])}</td><td className="num text-right">{pct(v.all)}</td></tr>)}</tbody></table>
            <p className="mt-2 text-xs muted">CAGR = (end / start)^(1/years) − 1; blank if either value ≤ 0.</p>
          </Card>
        </div>
      )}

      <Card title={`Data quality checks (${d.quality.length})`} subtitle="EquityPilot never fills missing figures with estimates">
        {d.quality.length === 0 ? <p className="text-sm text-up">No consistency issues detected.</p> : (
          <ul className="space-y-2">{d.quality.map((i, k) => (
            <li key={k} className="flex gap-3 text-sm"><span className={cx('mt-0.5 h-fit rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase', i.level === 'warning' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-300' : i.level === 'critical' ? 'bg-down/10 text-down' : 'bg-slate-500/10 muted')}>{i.level}</span>
              <span><b className="font-medium">{i.check}.</b> <span className="muted">{i.detail}</span></span></li>))}
          </ul>
        )}
      </Card>
    </div>
  )
}
