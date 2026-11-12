import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Search } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Card, cx, EmptyState, Loading, PageHeader, SourceNote, Tabs, TierBadge } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, ist, timeAgo } from '../lib/format'
import { useDebounced } from '../lib/hooks'

type Section = 'disclosures' | 'results' | 'corporate' | 'company' | 'economy' | 'regulation' | 'global'
interface Item { title: string; url: string | null; published: string | null; source: string; category: string; symbol: string | null; summary: string | null; tier?: string }

const OFFICIAL = [
  ['NSE corporate announcements', 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'],
  ['BSE corporate announcements', 'https://www.bseindia.com/corporates/ann.html'],
  ['SEBI', 'https://www.sebi.gov.in/'],
  ['RBI press releases', 'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx'],
  ['MOSPI (GDP, inflation, IIP)', 'https://mospi.gov.in/'],
  ['Press Information Bureau', 'https://pib.gov.in/'],
]

const INDUSTRIES = [['', 'All tracked companies'], ['banking', 'Banking'], ['financial-services', 'Financial services'], ['it', 'IT'], ['pharma', 'Pharma'], ['healthcare', 'Healthcare'],
  ['automobiles', 'Automobiles'], ['fmcg', 'FMCG'], ['agriculture', 'Agriculture'], ['energy', 'Energy'], ['infrastructure', 'Infrastructure'], ['metals', 'Metals'],
  ['real-estate', 'Real estate'], ['telecom', 'Telecom'], ['consumer-durables', 'Consumer durables'], ['chemicals', 'Chemicals']]

export default function News() {
  const [section, setSection] = useState<Section>('disclosures')
  const [query, setQuery] = useState('')
  const [tracked, setTracked] = useState(true)
  const [symbol, setSymbol] = useState('')
  const [industry, setIndustry] = useState('')
  const [unrated, setUnrated] = useState(false)
  const dq = useDebounced(query, 300)
  const url = (section === 'company'
    ? `/news?section=company${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}${industry ? `&industry=${industry}` : ''}&q=${encodeURIComponent(dq)}&limit=80`
    : `/news?section=${section}&q=${encodeURIComponent(dq)}&tracked_only=${tracked && ['disclosures', 'results', 'corporate'].includes(section)}&limit=80`) + `&include_unrated=${unrated}`
  const q = useQuery({ queryKey: ['news', url], queryFn: () => api.get<{ items: Item[]; sources?: string[]; hidden_unrated?: number; unrated_note?: string }>(url), refetchInterval: 300_000 })
  const hidden = q.data?.hidden_unrated ?? 0
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="News & market intelligence" title="What's new - with the original source" subtitle="Exchange filings and results come from NSE's official RSS feeds (linking to the filing PDF); economic and regulatory updates from RBI and SEBI feeds; market headlines from third-party publishers via Yahoo Finance. EquityPilot never writes or alters news." />
      <Tabs value={section} onChange={setSection} tabs={[
        { id: 'disclosures', label: 'Exchange disclosures' }, { id: 'results', label: 'Quarterly results' }, { id: 'corporate', label: 'Corporate actions' },
        { id: 'company', label: 'Company & sector news' }, { id: 'economy', label: 'Economy & RBI' }, { id: 'regulation', label: 'SEBI & regulation' }, { id: 'global', label: 'Markets & global' }]} />
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Filter by keyword…" value={query} onChange={(e) => setQuery(e.target.value)} /></div>
        {['disclosures', 'results', 'corporate'].includes(section) && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={tracked} onChange={(e) => setTracked(e.target.checked)} />Only companies tracked in EquityPilot</label>}
        {section === 'company' && (<>
          <select className="input w-auto" value={industry} onChange={(e) => { setIndustry(e.target.value); setSymbol('') }} aria-label="Industry">{INDUSTRIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <CompanyPicker className="w-64" value={symbol} placeholder="Or pick a company…" onChange={(s) => { setSymbol(s); setIndustry('') }} />
          {symbol && <button className="chip chip-active" onClick={() => setSymbol('')}>{baseSymbol(symbol)} ✕</button>}
        </>)}
      </div>
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_18rem]">
      <Card pad={false}>
        {(hidden > 0 || unrated) && (
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-2.5 text-xs dark:border-ink-700">
            <span className="muted">{unrated ? 'Showing headlines from unrated publishers too (marked UNRATED).' : `${hidden} headline${hidden === 1 ? '' : 's'} from unrated publishers hidden.`}</span>
            <button className="font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => setUnrated(!unrated)}>{unrated ? 'Hide them' : 'Show them'}</button>
          </div>
        )}
        {q.isLoading ? <Loading /> : (q.data?.items.length ?? 0) === 0 ? <div className="p-5"><EmptyState title="No items" body="Nothing matches these filters right now. Feeds refresh automatically every few minutes." /></div> : (
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">
            {q.data!.items.map((n, i) => (
              <li key={i} className="flex gap-4 px-5 py-3.5">
                <div className="w-24 shrink-0 text-xs muted" title={ist(n.published)}>{timeAgo(n.published)}</div>
                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 flex flex-wrap items-center gap-1.5 text-[11px]">
                    {n.symbol && <Link to={`/company/${encodeURIComponent(n.symbol)}`} className="rounded bg-brand-50 px-1.5 py-0.5 font-semibold text-brand-700 hover:underline dark:bg-brand-500/15 dark:text-brand-200">{baseSymbol(n.symbol)}</Link>}
                    <span className={cx('rounded px-1.5 py-0.5 font-medium', n.category === 'Quarterly results' ? 'bg-up/10 text-up' : 'bg-slate-500/10 muted')}>{n.category}</span>
                    <TierBadge tier={n.tier} />
                    <span className="muted">{n.source}</span>
                  </div>
                  <a href={n.url ?? '#'} target="_blank" rel="noopener noreferrer" className="text-sm font-medium hover:text-brand-600 hover:underline">
                    {section === 'disclosures' || section === 'results' || section === 'corporate' ? <>{n.title}{n.summary ? <span className="font-normal muted"> - {n.summary.replace(`${n.title} has informed the Exchange about `, '')}</span> : null}</> : n.title}
                    <ExternalLink className="ml-1 inline h-3 w-3 opacity-60" />
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="px-5 pb-4"><SourceNote sources={q.data?.sources ?? ['NSE (RSS)', 'Yahoo Finance headlines']} extra="Times shown relative to now (hover for IST)." /></div>
      </Card>
      <div className="space-y-5">
        <Card title="How sources are labelled">
          <ul className="space-y-2.5 text-sm">
            <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="primary" /></span><span className="text-slate-600 dark:text-slate-300">Exchange, regulator or government publication. The authoritative record.</span></li>
            <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="established" /></span><span className="text-slate-600 dark:text-slate-300">Reporting by an established news organisation. Check material facts against the filing.</span></li>
            <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="unrated" /></span><span className="text-slate-600 dark:text-slate-300">Other publishers (tip sites, blogs, aggregators). Hidden by default and never used by the AI assistant.</span></li>
          </ul>
        </Card>
        <Card title="Official sources" subtitle="Open the primary record directly">
          <ul className="space-y-2 text-sm">{OFFICIAL.map(([l, u]) => <li key={u}><a href={u} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-600 hover:underline dark:text-brand-300">{l}<ExternalLink className="h-3 w-3" /></a></li>)}</ul>
          <p className="mt-3 text-xs muted">EquityPilot fetches automatically only from feeds the publisher offers for subscription (NSE, RBI and SEBI RSS). Other official sites are linked, not scraped.</p>
        </Card>
      </div>
      </div>
    </div>
  )
}
