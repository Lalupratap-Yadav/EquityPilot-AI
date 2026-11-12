import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Calculator, ExternalLink, FileText, PiggyBank, RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { AlertButton, CompanyAvatar, TradeTicket, WatchlistButton } from '../components/common'
import { ExplainLabel } from '../components/Explain'
import { Card, ChangePill, cx, DataBadge, EmptyState, ErrorState, Loading, Modal, Notice, SourceNote, Stat, Tabs, useToast } from '../components/ui'
import { api, ApiError, type Quote } from '../lib/api'
import { baseSymbol, crore, inr, isNum, ist, mult, num, pct } from '../lib/format'
import { useInvalidate, useQuoteStream } from '../lib/hooks'
import FinancialsTab from './company/Financials'
import { BankTab, ChartTab, NewsTab, NotesTab, OwnershipTab, PeersTab, QuarterlyTab, RiskTab, TechnicalsTab } from './company/Sections'

export interface CompanyResponse {
  company: { symbol: string; name: string; exchange: string; isin: string | null; sector: string | null; industry: string | null; description: string | null
    website: string | null; employees: number | null; is_sample: boolean; source: string; source_url: string | null; fetched_at: string }
  industry: { id: string; name: string } | null
  category: string | null
  is_financial: boolean
  quote: Quote
  fundamentals_quote: { market_cap: number | null; week52_high: number | null; week52_low: number | null; beta: number | null; fetched_at: string }
  metrics: Record<string, number | string | boolean | null>
  statement_basis: string
  statement_currency: string
  official_links: Record<string, string>
  notes: Record<string, string>
}

type TabId = 'overview' | 'chart' | 'financials' | 'quarterly' | 'technicals' | 'risk' | 'peers' | 'ownership' | 'bank' | 'news' | 'notes'

function Insights({ m, isFin }: { m: CompanyResponse['metrics']; isFin: boolean }) {
  const items: { text: string; tone: 'up' | 'down' | 'neutral' }[] = []
  const n = (k: string) => (isNum(m[k]) ? (m[k] as number) : null)
  const rc = n('revenue_cagr_3y'), rg = n('revenue_growth'), roe = n('roe'), de = n('debt_to_equity'), cfo = n('cfo_to_net_income'), pe = n('pe')
  if (rc !== null) items.push({ text: `Revenue has compounded at ${pct(rc)} a year over 3 years${rg !== null ? `; latest year ${pct(rg, 1, true)}` : ''}.`, tone: rc > 0.1 ? 'up' : rc < 0 ? 'down' : 'neutral' })
  if (roe !== null) items.push({ text: `Return on equity of ${pct(roe)} is ${roe > 0.14 ? 'above' : 'at or below'} a typical Indian cost of equity (~12-14%).`, tone: roe > 0.14 ? 'up' : roe < 0.08 ? 'down' : 'neutral' })
  if (!isFin && de !== null) items.push({ text: de < 0.3 ? `Low leverage: debt is ${mult(de, 2)} equity.` : de > 1 ? `High leverage: debt is ${mult(de, 2)} equity.` : `Moderate leverage: debt is ${mult(de, 2)} equity.`, tone: de < 0.5 ? 'up' : de > 1 ? 'down' : 'neutral' })
  if (!isFin && cfo !== null) items.push({ text: `Operating cash flow was ${mult(cfo, 2)} net profit in the latest year${cfo < 0.8 ? ' - weaker cash conversion' : ''}.`, tone: cfo >= 0.9 ? 'up' : cfo < 0.7 ? 'down' : 'neutral' })
  if (pe !== null) items.push({ text: `Trades at ${mult(pe)} earnings (P/E). Compare with history and peers on the Valuation Lab.`, tone: 'neutral' })
  if (!items.length) return null
  return (
    <Card title="At a glance" subtitle="Automated observations calculated from the data on this page - not a recommendation">
      <ul className="space-y-2.5">
        {items.map((i, k) => (
          <li key={k} className="flex gap-2.5 text-sm"><span className={cx('mt-1.5 h-2 w-2 shrink-0 rounded-full', i.tone === 'up' ? 'bg-up' : i.tone === 'down' ? 'bg-down' : 'bg-slate-400')} />{i.text}</li>
        ))}
      </ul>
    </Card>
  )
}

export default function Company() {
  const { symbol = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as TabId) || 'overview'
  const setTab = (t: TabId) => setParams((p) => { p.set('tab', t); return p }, { replace: true })
  const [trade, setTrade] = useState(false)
  const toast = useToast()
  const inv = useInvalidate()
  const nav = useNavigate()
  const q = useQuery({ queryKey: ['company', symbol], queryFn: () => api.get<CompanyResponse>(`/companies/${encodeURIComponent(symbol)}`), retry: false })
  const stream = useQuoteStream(q.data ? [symbol] : [])
  const quote = stream.quotes[symbol] ?? q.data?.quote
  const track = useMutation({
    mutationFn: () => api.post<{ symbol: string; message: string }>(`/companies/${encodeURIComponent(symbol)}/track`),
    onSuccess: (r) => { toast('Company data fetched'); if (r.symbol !== symbol) nav(`/company/${encodeURIComponent(r.symbol)}`); else q.refetch() },
    onError: (e) => toast((e as Error).message, 'error'),
  })
  const refresh = useMutation({
    mutationFn: () => api.post<{ messages: string[] }>(`/companies/${encodeURIComponent(symbol)}/refresh`),
    onSuccess: (r) => { toast(r.messages.join(' '), 'info'); inv('company') },
    onError: (e) => toast((e as Error).message, 'error'),
  })

  const tabs = useMemo(() => {
    const t: { id: TabId; label: string }[] = [
      { id: 'overview', label: 'Overview' }, { id: 'chart', label: 'Chart' }, { id: 'financials', label: 'Financials' },
      { id: 'quarterly', label: 'Quarterly' }, { id: 'technicals', label: 'Technicals' }, { id: 'risk', label: 'Risk' },
      { id: 'peers', label: 'Peers' }, { id: 'ownership', label: 'Ownership' }, { id: 'news', label: 'News' }, { id: 'notes', label: 'My notes' }]
    if (q.data?.is_financial) t.splice(3, 0, { id: 'bank', label: 'Bank metrics' })
    return t
  }, [q.data?.is_financial])

  if (q.isLoading) return <Loading label="Loading company…" />
  if (q.error instanceof ApiError && q.error.status === 404) {
    return (
      <EmptyState title={`${baseSymbol(symbol)} isn't tracked yet`}
        body="EquityPilot can fetch its profile, delayed quote, financial statements and price history from the data provider (Yahoo Finance). This takes a few seconds."
        action={<button className="btn-primary" disabled={track.isPending} onClick={() => track.mutate()}>{track.isPending ? 'Fetching data…' : 'Fetch company data'}</button>} />
    )
  }
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  const d = q.data!
  const c = d.company, m = d.metrics
  const fq = d.fundamentals_quote

  return (
    <div className="space-y-5">
      {/* ---------------------------------------------- header */}
      <section className="card card-pad">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3.5">
            <CompanyAvatar symbol={c.symbol} size="lg" />
            <div className="min-w-0">
              <h1 className="text-xl font-semibold sm:text-2xl">{c.name}</h1>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
                <span className="chip">{baseSymbol(c.symbol)} · {c.exchange}</span>
                {d.category && <span className="chip">{d.category}</span>}
                {d.industry && <Link to={`/industries/${d.industry.id}`} className="chip">{d.industry.name}</Link>}
                {c.industry && <span className="muted">{c.industry}</span>}
                {c.is_sample && <DataBadge type="sample" />}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="num text-3xl font-semibold tracking-tight">{inr(quote?.price)}</div>
            <div className="mt-1 flex items-center justify-end gap-2">
              <span className={cx('num text-sm font-medium', isNum(quote?.change) && quote!.change! >= 0 ? 'text-up' : 'text-down')}>{isNum(quote?.change) ? `${quote!.change! >= 0 ? '+' : ''}${num(quote!.change)}` : ''}</span>
              <ChangePill value={quote?.change_pct} size="md" />
            </div>
            <div className="mt-1 flex items-center justify-end gap-1.5 text-[11px] muted">
              <DataBadge type={quote?.status} />{quote?.time ? ist(quote.time) : ''}{stream.connected && <span title="Streaming updates via WebSocket">· auto-updating</span>}
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <WatchlistButton symbol={symbol} />
          <AlertButton symbol={symbol} price={quote?.price} />
          <button className="btn-primary" onClick={() => setTrade(true)}><PiggyBank className="h-4 w-4" />Virtual trade</button>
          <Link to={`/valuation/${encodeURIComponent(symbol)}`} className="btn-outline"><Calculator className="h-4 w-4" />Valuation Lab</Link>
          <Link to={`/assistant?symbol=${encodeURIComponent(symbol)}`} className="btn-outline"><Bot className="h-4 w-4" />Ask AI</Link>
          <Link to={`/reports?symbol=${encodeURIComponent(symbol)}`} className="btn-outline"><FileText className="h-4 w-4" />Report</Link>
          {!c.is_sample && <button className="btn-ghost" disabled={refresh.isPending} onClick={() => refresh.mutate()}><RefreshCw className={cx('h-4 w-4', refresh.isPending && 'animate-spin')} />Refresh data</button>}
        </div>
        {c.is_sample && <Notice tone="sample" className="mt-4"><b>Sample data.</b> This is a fictional company created for demonstration and testing; its figures do not describe a real business.</Notice>}
      </section>

      <Tabs tabs={tabs} value={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div className="grid gap-5 xl:grid-cols-3">
          <div className="space-y-5 xl:col-span-2">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label={<ExplainLabel metric="market_cap" label="Market cap" value={crore(m.market_cap)} formula="Price × shares outstanding" />} value={crore(m.market_cap)} />
              <Stat label={<ExplainLabel metric="pe" label="P/E" value={mult(m.pe)} formula="Market cap / net profit (TTM where available)" />} value={mult(m.pe)} />
              <Stat label={<ExplainLabel metric="pb" label="P/B" value={mult(m.pb)} formula="Market cap / shareholders' equity" />} value={mult(m.pb)} />
              {d.is_financial
                ? <Stat label={<ExplainLabel metric="dividend_yield" label="Dividend yield" value={pct(m.dividend_yield)} formula="Annual dividend per share / price" />} value={pct(m.dividend_yield)} />
                : <Stat label={<ExplainLabel metric="ev_ebitda" label="EV/EBITDA" value={mult(m.ev_ebitda)} formula="Enterprise value / EBITDA" />} value={mult(m.ev_ebitda)} />}
              <Stat label={<ExplainLabel metric="roe" label="ROE" value={pct(m.roe)} formula="Net profit / average shareholders' equity (latest FY)" />} value={pct(m.roe)} />
              {d.is_financial
                ? <Stat label={<ExplainLabel metric="net_margin" label="Net margin" value={pct(m.net_margin)} formula="Net profit / revenue" />} value={pct(m.net_margin)} />
                : <Stat label={<ExplainLabel metric="roce" label="ROCE" value={pct(m.roce)} formula="EBIT / average capital employed" />} value={pct(m.roce)} />}
              {d.is_financial
                ? <Stat label={<ExplainLabel metric="net_income_growth" label="Profit growth" value={pct(m.net_income_growth, 1, true)} />} value={pct(m.net_income_growth, 1, true)} />
                : <Stat label={<ExplainLabel metric="debt_to_equity" label="Debt / equity" value={mult(m.debt_to_equity, 2)} formula="Total borrowings / shareholders' equity" />} value={mult(m.debt_to_equity, 2)} />}
              <Stat label="52-week range" value={<span className="text-sm">{inr(fq.week52_low, 0)} – {inr(fq.week52_high, 0)}</span>} />
            </div>
            <Insights m={m} isFin={d.is_financial} />
            <ChartTab symbol={symbol} compact live={quote} />
          </div>
          <div className="space-y-5">
            <Card title="Business">
              <p className="line-clamp-[10] text-sm leading-relaxed text-slate-600 dark:text-slate-300">{c.description || 'No description available from the provider.'}</p>
              <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                <dt className="muted">Sector</dt><dd>{c.sector ?? '—'}</dd>
                <dt className="muted">Industry</dt><dd>{c.industry ?? '—'}</dd>
                <dt className="muted">ISIN</dt><dd className="num">{c.isin ?? '—'}</dd>
                <dt className="muted">Employees</dt><dd className="num">{isNum(c.employees) ? c.employees.toLocaleString('en-IN') : '—'}</dd>
                {c.website && <><dt className="muted">Website</dt><dd className="truncate"><a className="text-brand-600 hover:underline dark:text-brand-300" href={c.website} target="_blank" rel="noopener noreferrer">{c.website.replace(/^https?:\/\//, '')}</a></dd></>}
              </dl>
              <SourceNote sources={[c.source]} time={c.fetched_at} />
            </Card>
            {Object.keys(d.official_links).length > 0 && (
              <Card title="Verify at the source" subtitle="Official exchange and regulator pages (open in a new tab)">
                <ul className="space-y-1.5 text-sm">
                  {Object.entries(d.official_links).slice(0, 6).map(([k, v]) => (
                    <li key={k}><a href={v} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-brand-600 hover:underline dark:text-brand-300">{k}<ExternalLink className="h-3 w-3" /></a></li>
                  ))}
                </ul>
              </Card>
            )}
            <NewsTab symbol={symbol} compact />
          </div>
        </div>
      )}
      {tab === 'chart' && <ChartTab symbol={symbol} live={quote} />}
      {tab === 'financials' && <FinancialsTab symbol={symbol} isFinancial={d.is_financial} />}
      {tab === 'quarterly' && <QuarterlyTab symbol={symbol} />}
      {tab === 'bank' && <BankTab symbol={symbol} sample={c.is_sample} />}
      {tab === 'technicals' && <TechnicalsTab symbol={symbol} />}
      {tab === 'risk' && <RiskTab symbol={symbol} />}
      {tab === 'peers' && <PeersTab symbol={symbol} />}
      {tab === 'ownership' && <OwnershipTab symbol={symbol} sample={c.is_sample} />}
      {tab === 'news' && <NewsTab symbol={symbol} />}
      {tab === 'notes' && <NotesTab symbol={symbol} initial={d.notes} />}

      <Modal open={trade} onClose={() => setTrade(false)} title="Virtual Invest · paper trade">
        <TradeTicket symbol={symbol} name={c.name} quote={quote} onDone={() => setTrade(false)} />
      </Modal>
    </div>
  )
}
