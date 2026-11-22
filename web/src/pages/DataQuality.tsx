// Data Quality & Source Transparency: where every dataset comes from, how fresh it is and what is missing.
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ExternalLink, Radio } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { CoverageTable, type Coverage } from '../components/coverage'
import { FreshPill, Pill, SourceLabel } from '../components/status'
import { Card, ErrorState, Loading, PageHeader, Stat } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, ist, pct, timeAgo } from '../lib/format'

interface Feed { key: string; source: string; url: string | null; tier: string; refresh_minutes: number | null; last_refreshed: string | null; last_failed: string | null
  state: string; items_stored: number; newest_item: string | null }
interface Quality {
  generated_at: string; offline: boolean; labels: Record<string, string>; feeds: Feed[]; feeds_failing: string[]; feeds_stale: string[]
  market_data: { provider: string; tier: string; realtime: boolean; quotes_stored: number; quotes_within_1d: number; newest_quote: string | null; note: string }
  statements: { companies: number; with_3y_annual: number; with_quarterly: number; no_statements: string[]; eps_warnings: { symbol: string; check: string; detail: string }[]
    eps_warning_count: number; basis_note: string }
  securities: { count: number; as_of: string | null; source: string }
  rules: string[]
}
const LABEL_ORDER = ['OFFICIAL', 'SECONDARY', 'THIRD-PARTY', 'DELAYED', 'HISTORICAL', 'CALCULATED', 'ASSUMPTION', 'USER-ENTERED', 'SAMPLE']

function CompanyCoverage() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const q = useQuery({ queryKey: ['coverage', symbol], enabled: !!symbol, queryFn: () => api.get<Coverage>(`/companies/${encodeURIComponent(symbol)}/coverage`) })
  return (
    <Card title="Company data coverage" subtitle="What EquityPilot holds for one company, where it came from and what is missing">
      <CompanyPicker value={symbol} trackedOnly onChange={(s) => setParams((p) => { p.set('symbol', s); return p }, { replace: true })} className="mb-4 max-w-md" placeholder="Search a tracked company…" />
      {!symbol ? <p className="text-sm muted">Choose a company to see its coverage.</p> : q.isLoading ? <Loading /> : q.data ? <CoverageTable c={q.data} /> : <p className="text-sm muted">Coverage for {baseSymbol(symbol)} is unavailable.</p>}
    </Card>
  )
}

export default function DataQuality() {
  const q = useQuery({ queryKey: ['data-quality'], queryFn: () => api.get<Quality>('/data/quality'), refetchInterval: 120_000 })
  const d = q.data
  return (
    <div className="page-enter space-y-5">
      <PageHeader eyebrow="Trust" title="Data Quality & Sources"
        subtitle="Where every dataset comes from, how recent it is, and what is missing. Missing values are shown as missing, never as zero." />
      {q.error ? <ErrorState error={q.error} retry={() => q.refetch()} /> : !d ? <Loading /> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Feeds healthy" value={`${d.feeds.length - d.feeds_failing.length - d.feeds_stale.length} / ${d.feeds.length}`}
              sub={d.feeds_failing.length ? `${d.feeds_failing.length} failing` : d.feeds_stale.length ? `${d.feeds_stale.length} stale` : 'all refreshing'} />
            <Stat label="Prices" value={d.market_data.realtime ? 'Real-time' : 'Delayed'} sub={d.market_data.provider} />
            <Stat label="Companies with 3+ years" value={`${d.statements.with_3y_annual} / ${d.statements.companies}`} sub="of annual statements" />
            <Stat label="EPS warnings" value={d.statements.eps_warning_count} sub="flagged for verification" />
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2" pad={false} title="Feeds and providers" subtitle="Each source, its label, how often EquityPilot asks it for updates and when it last succeeded">
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead><tr className="table-head"><th className="px-4 py-2 text-left">Source</th><th className="px-4 py-2 text-left">Label</th><th className="px-4 py-2 text-right">Every</th><th className="px-4 py-2 text-left">Last refreshed</th><th className="px-4 py-2 text-left">State</th><th className="px-4 py-2 text-right">Items kept</th></tr></thead>
                  <tbody>{d.feeds.map((f) => (
                    <tr key={f.key} className="border-t border-slate-100 dark:border-ink-700">
                      <td className="px-4 py-2">{f.url ? <a href={f.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">{f.source}<ExternalLink className="h-3 w-3 opacity-50" /></a> : f.source}</td>
                      <td className="px-4 py-2"><SourceLabel tier={f.tier} /></td>
                      <td className="num px-4 py-2 text-right muted">{f.refresh_minutes ? `${f.refresh_minutes} min` : '—'}</td>
                      <td className="px-4 py-2" title={f.last_refreshed ? `${ist(f.last_refreshed)} IST` : undefined}>{f.last_refreshed ? timeAgo(f.last_refreshed) : 'Never'}
                        {f.state === 'failing' && f.last_failed && <div className="text-[11px] text-down">Failed {timeAgo(f.last_failed)}; cached items shown</div>}</td>
                      <td className="px-4 py-2"><FreshPill state={f.state} /></td>
                      <td className="num px-4 py-2 text-right">{f.items_stored.toLocaleString('en-IN')}</td>
                    </tr>))}</tbody>
                </table>
              </div>
              <p className="px-4 pb-4 pt-2 text-xs muted">Feeds that fail are retried after 10 minutes; their previously collected items stay visible. {d.offline && 'Offline mode: no feed is contacted.'}</p>
            </Card>
            <div className="space-y-5">
              <Card title={<span className="inline-flex items-center gap-1.5"><Radio className="h-4 w-4 text-brand-600" />Market prices</span>}>
                <div className="flex items-center gap-2"><SourceLabel tier={d.market_data.tier} /><span className="text-sm font-medium">{d.market_data.provider}</span></div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{d.market_data.note}</p>
                <p className="mt-2 text-xs muted">{d.market_data.quotes_within_1d} of {d.market_data.quotes_stored} stored quotes updated in the last 24 hours{d.market_data.newest_quote ? ` · newest ${timeAgo(d.market_data.newest_quote)}` : ''}.</p>
              </Card>
              <Card title="Securities master">
                <p className="text-sm"><b className="num">{d.securities.count.toLocaleString('en-IN')}</b> listed securities · <SourceLabel tier="OFFICIAL" /></p>
                <p className="mt-1 text-xs muted">{d.securities.source}{d.securities.as_of ? ` · ${d.securities.as_of}` : ''}</p>
              </Card>
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card title="Financial statements" subtitle="Annual and quarterly statements from Yahoo Finance (THIRD-PARTY)">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div><div className="num text-xl font-semibold">{d.statements.companies}</div><div className="text-xs muted">tracked companies</div></div>
                <div><div className="num text-xl font-semibold">{pct(d.statements.companies ? d.statements.with_3y_annual / d.statements.companies : null, 0)}</div><div className="text-xs muted">with 3+ years</div></div>
                <div><div className="num text-xl font-semibold">{pct(d.statements.companies ? d.statements.with_quarterly / d.statements.companies : null, 0)}</div><div className="text-xs muted">with quarterly data</div></div>
              </div>
              <p className="mt-4 text-xs muted">{d.statements.basis_note}</p>
              {d.statements.no_statements.length > 0 && <p className="mt-2 text-xs muted">No statements yet: {d.statements.no_statements.map(baseSymbol).join(', ')}.</p>}
              <div className="mt-4">
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide muted">EPS consistency</div>
                {d.statements.eps_warnings.length === 0 ? <p className="text-sm muted">No EPS inconsistencies detected.</p> : (
                  <ul className="space-y-2">{d.statements.eps_warnings.map((w) => (
                    <li key={w.symbol + w.check} className="flex gap-2 text-sm"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                      <span><b className="font-medium">{baseSymbol(w.symbol)}: {w.check}.</b> <span className="text-slate-600 dark:text-slate-300">{w.detail}</span></span></li>))}</ul>)}
              </div>
            </Card>
            <Card title="Labels used across EquityPilot" subtitle="Every figure carries one of these">
              <dl className="grid gap-x-4 gap-y-2.5 text-sm sm:grid-cols-[auto_1fr]">
                {LABEL_ORDER.filter((k) => d.labels[k]).map((k) => (
                  <div key={k} className="contents"><dt><SourceLabel tier={k} /></dt><dd className="text-slate-600 dark:text-slate-300">{d.labels[k]}</dd></div>))}
              </dl>
            </Card>
          </div>

          <CompanyCoverage />

          <Card title="Rules EquityPilot follows">
            <ul className="space-y-1.5 text-sm">{d.rules.map((r) => <li key={r} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-up" />{r}</li>)}</ul>
            <p className="mt-3 text-xs muted">Report generated {ist(d.generated_at)} IST. <Pill tone="neutral">Educational use</Pill></p>
          </Card>
        </>
      )}
    </div>
  )
}
