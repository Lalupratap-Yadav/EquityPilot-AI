// Company page: Valuation summary, Documents & annual reports, and the company news list (new news engine).
import { useQuery } from '@tanstack/react-query'
import { Calculator, ExternalLink, FileText, UploadCloud } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, cx, EmptyState, Loading, Notice, Stat, TierBadge } from '../../components/ui'
import { api } from '../../lib/api'
import { baseSymbol, inr, isNum, ist, mult, pct, timeAgo } from '../../lib/format'

interface Band { n: number; median: number | null; min: number | null; max: number | null; current: number | null; vs_median: number | null }
interface ValResp {
  snapshot: Record<string, number | null | string | boolean>; bands: Record<string, Band>; implied_from_history: Record<string, number | null>
  is_financial: boolean; peers: { symbol: string; name: string; pe: number | null; pb: number | null; ev_ebitda: number | null; roe: number | null }[]
}

const MULT_LABEL: Record<string, string> = { pe: 'P/E', pb: 'P/B', ev_ebitda: 'EV/EBITDA' }

/** Where the current multiple sits within its own history: 0 = cheapest seen, 1 = most expensive. */
function BandBar({ b }: { b: Band }) {
  if (!isNum(b.min) || !isNum(b.max) || !isNum(b.current) || b.max <= b.min) return <span className="text-xs muted">Not enough history</span>
  const at = Math.min(1, Math.max(0, (b.current - b.min) / (b.max - b.min)))
  const med = isNum(b.median) ? (b.median - b.min) / (b.max - b.min) : null
  return (
    <div className="mt-2">
      <div className="relative h-2 rounded-full bg-gradient-to-r from-up/30 via-slate-200 to-down/30 dark:via-ink-600">
        {med !== null && <span className="absolute top-[-3px] h-[14px] w-px bg-slate-500" style={{ left: `${med * 100}%` }} title={`Median ${mult(b.median)}`} />}
        <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-ink-900 shadow dark:border-ink-850 dark:bg-white" style={{ left: `${at * 100}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[11px] muted"><span>Low {mult(b.min)}</span><span>Median {mult(b.median)}</span><span>High {mult(b.max)}</span></div>
    </div>
  )
}

export function ValuationTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['valuation', symbol], queryFn: () => api.get<ValResp>(`/companies/${encodeURIComponent(symbol)}/valuation`) })
  if (q.isLoading) return <Loading />
  if (!q.data) return <EmptyState title="Valuation data unavailable" body="The provider has not returned enough data to value this company." />
  const d = q.data
  const keys = Object.keys(d.bands).filter((k) => MULT_LABEL[k] && !(d.is_financial && k === 'ev_ebitda'))
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <div className="space-y-5 xl:col-span-2">
        <Card title="Valuation multiples against the company's own history"
          subtitle="Where today's multiple sits between the lowest and highest seen at past fiscal year-ends. Cheaper than history is not automatically good value - growth and risk may have changed.">
          <div className="grid gap-5 sm:grid-cols-2">
            {keys.map((k) => {
              const b = d.bands[k]
              return (
                <div key={k}>
                  <div className="flex items-baseline justify-between"><span className="text-sm font-medium">{MULT_LABEL[k]}</span>
                    <span className="num text-lg font-semibold">{mult(b.current)}</span></div>
                  <div className="text-xs muted">{isNum(b.vs_median) ? `${pct(Math.abs(b.vs_median))} ${b.vs_median > 0 ? 'above' : 'below'} its ${b.n}-year median` : `${b.n} years of history`}</div>
                  <BandBar b={b} />
                </div>
              )
            })}
          </div>
        </Card>
        {Object.values(d.implied_from_history).some(isNum) && (
          <Card title="Price implied by historical multiples" subtitle="Today's earnings or book value × the median multiple of past years. A rough cross-check, not a target price.">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              {Object.entries(d.implied_from_history).filter(([, v]) => isNum(v)).map(([k, v]) => <Stat key={k} label={`At median ${MULT_LABEL[k] ?? k}`} value={inr(v)} />)}
              {isNum(d.snapshot.price as number) && <Stat label="Current price" value={inr(d.snapshot.price as number)} />}
            </div>
          </Card>
        )}
        <Notice><Calculator className="mr-1 inline h-4 w-4" />For a discounted cash flow model (FCFF and FCFE), scenarios, sensitivity tables and margin of safety, open the{' '}
          <Link className="font-medium text-brand-600 underline dark:text-brand-300" to={`/valuation/${encodeURIComponent(symbol)}`}>Valuation Lab</Link>. Model values depend on your assumptions and are estimates, never exact.</Notice>
      </div>
      <Card title="Peer multiples" subtitle="Same industry, latest data">
        {d.peers.length === 0 ? <p className="text-sm muted">No tracked peers.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="table-head"><th className="px-2 py-1.5">Company</th><th className="px-2 py-1.5 text-right">P/E</th><th className="px-2 py-1.5 text-right">P/B</th><th className="px-2 py-1.5 text-right">ROE</th></tr></thead>
            <tbody>{d.peers.map((p) => (
              <tr key={p.symbol} className={cx('border-t border-slate-100 dark:border-ink-700', p.symbol === symbol && 'bg-brand-50/60 font-medium dark:bg-ink-800')}>
                <td className="max-w-[9rem] truncate px-2 py-1.5"><Link to={`/company/${encodeURIComponent(p.symbol)}?tab=valuation`} className="hover:underline">{baseSymbol(p.symbol)}</Link></td>
                <td className="num px-2 py-1.5 text-right">{mult(p.pe)}</td><td className="num px-2 py-1.5 text-right">{mult(p.pb)}</td><td className="num px-2 py-1.5 text-right">{pct(p.roe)}</td></tr>))}</tbody>
          </table></div>
        )}
        <Link to={`/compare?symbols=${encodeURIComponent([symbol, ...d.peers.filter((p) => p.symbol !== symbol).slice(0, 3).map((p) => p.symbol)].join(','))}`} className="mt-3 inline-block text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">Compare in detail →</Link>
      </Card>
    </div>
  )
}

export function DocumentsTab({ symbol, links, sample }: { symbol: string; links: Record<string, string>; sample: boolean }) {
  const q = useQuery({ queryKey: ['documents', symbol], queryFn: () => api.get<{ id: number; filename: string; doc_type: string; period: string; pages: number; uploaded_at?: string }[]>(`/documents?symbol=${encodeURIComponent(symbol)}`) })
  const official = Object.entries(links).filter(([k]) => /annual|result|shareholding|announcement|corporate/i.test(k))
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Your documents" subtitle="Annual reports, results and presentations you uploaded for this company"
        action={<Link to={`/documents?symbol=${encodeURIComponent(symbol)}`} className="btn-outline px-3 py-1.5 text-xs"><UploadCloud className="h-3.5 w-3.5" />Upload</Link>}>
        {q.isLoading ? <Loading /> : (q.data?.length ?? 0) === 0 ? (
          <EmptyState icon={<FileText className="h-6 w-6" />} title="No documents yet" body="Upload the annual report PDF to search it, quote it in reports and ask the AI about it." />
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">{q.data!.map((d) => (
            <li key={d.id} className="flex items-center gap-3 py-2.5 text-sm"><FileText className="h-4 w-4 shrink-0 text-brand-600" />
              <span className="min-w-0 flex-1"><span className="block truncate font-medium">{d.filename}</span><span className="text-xs muted">{d.doc_type} · {d.period} · {d.pages} pages</span></span>
              <Link to={`/assistant?symbol=${encodeURIComponent(symbol)}`} className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-300">Ask AI</Link></li>))}</ul>
        )}
      </Card>
      <Card title="Official filings" subtitle="The primary record - open on the exchange website">
        {sample ? <p className="text-sm muted">Sample companies have no official filings.</p> : official.length === 0 ? <p className="text-sm muted">No official links available.</p> : (
          <ul className="space-y-2 text-sm">{official.map(([k, v]) => (
            <li key={k}><a href={v} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-brand-600 hover:underline dark:text-brand-300">{k}<ExternalLink className="h-3 w-3" /></a></li>))}</ul>
        )}
        <p className="mt-3 text-xs muted">EquityPilot does not download from exchange websites automatically. Download the PDF there and upload it here to analyse it.</p>
      </Card>
    </div>
  )
}

interface FeedItem { id: string; title: string; summary: string | null; url: string | null; source: string; publisher: string | null; tier: string; category: string
  company: string | null; published: string | null; important: boolean; match: string | null }

export function CompanyNews({ symbol, compact }: { symbol: string; compact?: boolean }) {
  const q = useQuery({ queryKey: ['newsfeed', 'company', symbol, compact],
    queryFn: () => api.get<{ items: FeedItem[]; total: number }>(`/news/feed?section=company&symbol=${encodeURIComponent(symbol)}&days=90&limit=${compact ? 6 : 40}`) })
  const all = `/news?section=company&symbol=${encodeURIComponent(symbol)}`
  return (
    <Card title={compact ? 'Latest news & filings' : 'News, filings & announcements'} subtitle={compact ? undefined : 'Official filings first; headlines link to the original publisher'}
      action={<Link to={all} className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">{compact ? 'All' : 'Open in News'}</Link>}>
      {q.isLoading ? <Loading /> : (q.data?.items.length ?? 0) === 0 ? <p className="text-sm muted">No news or filings for {baseSymbol(symbol)} in the last 90 days. Headlines appear here only when they name the company.</p> : (
        <ul className="space-y-3">{q.data!.items.map((n) => {
          const filing = n.tier === 'primary' && !!n.company
          return (
            <li key={n.id} className="text-sm">
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] muted"><TierBadge tier={n.tier} />{n.category} · {(n.publisher || n.source).replace(' (RSS)', '')} ·
                <span title={n.published ? `${ist(n.published)} IST` : undefined}>{timeAgo(n.published)}</span>{n.important && <b className="text-amber-700 dark:text-saffron-400">· Important</b>}
                {n.match && !filing && <span title="How EquityPilot linked this headline to the company">· {n.match.toLowerCase()}</span>}</div>
              <a href={n.url ?? '#'} target="_blank" rel="noopener noreferrer" className="hover:underline">{filing ? (n.summary ?? n.title) : n.title} <ExternalLink className="inline h-3 w-3 opacity-60" /></a>
            </li>)
        })}</ul>
      )}
    </Card>
  )
}
