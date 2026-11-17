import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CheckCircle2, Circle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { CompanyAvatar } from '../components/common'
import { Card, ChangePill, cx, EmptyState, Loading, PageHeader } from '../components/ui'
import { api, type Quote } from '../lib/api'
import { baseSymbol, crore, inr, mult, pct } from '../lib/format'

interface CompanyResp { company: { symbol: string; name: string; description: string | null }; industry: { id: string; name: string } | null; quote: Quote
  metrics: Record<string, number | string | null>; is_financial: boolean; notes: Record<string, string> }

const KEY = 'ep-research-progress'

export default function Research() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const recent = useQuery({ queryKey: ['recent'], queryFn: () => api.get<{ views: { symbol: string; name: string; price: number; change_pct: number }[] }>('/recent') })
  const c = useQuery({ queryKey: ['company', symbol], enabled: !!symbol, queryFn: () => api.get<CompanyResp>(`/companies/${encodeURIComponent(symbol)}`), retry: false })
  const [done, setDone] = useState<Record<string, string[]>>(() => { try { return JSON.parse(localStorage.getItem(KEY) || '{}') } catch { return {} } })
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(done)) } catch { /* ignore */ } }, [done])
  const toggle = (step: string) => setDone((d) => ({ ...d, [symbol]: (d[symbol] ?? []).includes(step) ? d[symbol].filter((s) => s !== step) : [...(d[symbol] ?? []), step] }))

  const s = encodeURIComponent(symbol)
  const m = c.data?.metrics ?? {}
  const steps = c.data ? [
    { id: 'business', title: 'Understand the business', q: 'How does the company make money? What are its products, customers and competitive advantages?',
      facts: [`Industry: ${c.data.industry?.name ?? '—'}`, c.data.notes?.business_model ? 'Your business-model notes are saved' : 'No business notes yet'], to: `/company/${s}?tab=notes`, cta: 'Write business notes' },
    { id: 'industry', title: 'Analyse the industry', q: 'What drives demand? Who are the competitors? What are the industry risks and how is it valued?',
      facts: [c.data.industry ? `Open the ${c.data.industry.name} intelligence page` : 'Industry not classified'], to: c.data.industry ? `/industries/${c.data.industry.id}` : `/company/${s}?tab=peers`, cta: 'Industry analysis' },
    { id: 'financials', title: 'Financial statement analysis', q: 'Is revenue growing? Are margins stable? Is the balance sheet strong?',
      facts: [`Revenue CAGR 3Y ${pct(m.revenue_cagr_3y)}`, `Net margin ${pct(m.net_margin)}`, c.data.is_financial ? 'Financial company - see bank metrics' : `Debt/equity ${mult(m.debt_to_equity, 2)}`], to: `/company/${s}?tab=financials`, cta: 'Statements & ratios' },
    { id: 'earnings', title: 'Earnings analysis', q: 'What happened in the latest quarters? Is growth accelerating or slowing?',
      facts: [`Profit growth (FY) ${pct(m.net_income_growth, 1, true)}`, 'Quarterly QoQ / YoY trends'], to: `/company/${s}?tab=quarterly`, cta: 'Quarterly results' },
    { id: 'cashflow', title: 'Cash flow analysis', q: 'Do profits convert into cash? How much is reinvested?',
      facts: [`CFO / net profit ${mult(m.cfo_to_net_income, 2)}`, `FCF margin ${pct(m.fcf_margin)}`], to: `/company/${s}?tab=financials`, cta: 'Cash flow statement' },
    { id: 'competition', title: 'Competitive positioning', q: 'How does it compare with peers on growth, returns and valuation?',
      facts: [`ROE ${pct(m.roe)} · ROCE ${pct(m.roce)}`], to: `/company/${s}?tab=peers`, cta: 'Peer comparison' },
    { id: 'valuation', title: 'Valuation', q: 'What does the price imply? What is it worth under your assumptions?',
      facts: [`P/E ${mult(m.pe)} · P/B ${mult(m.pb)}`, 'DCF, scenarios, sensitivity, reverse DCF'], to: `/valuation/${s}`, cta: 'Valuation Lab' },
    { id: 'risk', title: 'Risk analysis', q: 'What could go wrong - financially, operationally, in governance or regulation?',
      facts: ['Rule-based checks with thresholds', 'Sector & regulatory considerations'], to: `/company/${s}?tab=risk`, cta: 'Risk analysis' },
    { id: 'report', title: 'Write it up', q: 'Summarise the evidence, the assumptions used and the risks, with sources.',
      facts: ['PDF report with tables, charts and disclosures'], to: `/reports?symbol=${s}`, cta: 'Generate report' },
  ] : []
  const progress = steps.length ? (done[symbol] ?? []).length / steps.length : 0

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Research workspace" title="Equity Research" subtitle="A structured, analyst-style workflow: business → industry → financials → earnings → cash flow → competition → valuation → risk → report. Tick off each step as you go." />
      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Choose a company" className="lg:col-span-1">
          <CompanyPicker value={symbol} onChange={(sym) => setParams({ symbol: sym })} />
          {(recent.data?.views ?? []).length > 0 && (<>
            <div className="mt-4 text-xs font-semibold uppercase muted">Recently viewed</div>
            <ul className="mt-2 space-y-1">{recent.data!.views.slice(0, 8).map((v) => (
              <li key={v.symbol}><button onClick={() => setParams({ symbol: v.symbol })} className={cx('flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-slate-100 dark:hover:bg-ink-700', v.symbol === symbol && 'bg-brand-50 dark:bg-ink-700')}>
                <CompanyAvatar symbol={v.symbol} size="sm" /><span className="min-w-0 flex-1 truncate">{v.name}</span><ChangePill value={v.change_pct} /></button></li>))}</ul>
          </>)}
        </Card>
        <div className="lg:col-span-2">
          {!symbol ? <EmptyState title="Pick a company to start" body="Search any NSE/BSE-listed company. Untracked companies are fetched from the data provider when opened." /> :
            c.isLoading ? <Loading /> : !c.data ? <EmptyState title="Company not tracked yet" action={<Link className="btn-primary" to={`/company/${s}`}>Open company page to fetch data</Link>} /> : (
            <div className="space-y-4">
              <div className="card card-pad flex flex-wrap items-center gap-4">
                <CompanyAvatar symbol={symbol} size="lg" />
                <div className="min-w-0 flex-1"><div className="text-lg font-semibold">{c.data.company.name}</div>
                  <div className="text-sm muted">{baseSymbol(symbol)} · {inr(c.data.quote.price)} · Market cap {crore(m.market_cap)}</div></div>
                <div className="w-48"><div className="mb-1 flex justify-between text-xs"><span className="muted">Research progress</span><span className="font-semibold">{Math.round(progress * 100)}%</span></div>
                  <div className="h-2 rounded-full bg-slate-200 dark:bg-ink-700"><div className="h-2 rounded-full bg-brand-600 transition-all" style={{ width: `${progress * 100}%` }} /></div></div>
              </div>
              <ol className="space-y-3">
                {steps.map((st, i) => {
                  const isDone = (done[symbol] ?? []).includes(st.id)
                  return (
                    <li key={st.id} className={cx('card flex gap-4 p-4', isDone && 'opacity-75')}>
                      <button onClick={() => toggle(st.id)} aria-label={isDone ? 'Mark not done' : 'Mark done'} className="mt-0.5">
                        {isDone ? <CheckCircle2 className="h-6 w-6 text-up" /> : <Circle className="h-6 w-6 text-slate-300" />}
                      </button>
                      <div className="min-w-0 flex-1">
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-300">Step {i + 1}</div>
                        <div className="font-semibold">{st.title}</div><p className="mt-0.5 text-sm muted">{st.q}</p>
                        <div className="mt-2 flex flex-wrap gap-1.5">{st.facts.map((f) => <span key={f} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs dark:bg-ink-700">{f}</span>)}</div>
                      </div>
                      <Link to={st.to} className="btn-outline h-fit self-center whitespace-nowrap">{st.cta}<ArrowRight className="h-4 w-4" /></Link>
                    </li>
                  )
                })}
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
