import { useMutation, useQuery } from '@tanstack/react-query'
import { Bookmark, BookmarkCheck, ExternalLink, Info, Lightbulb, Link2, Newspaper, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Card, ChangePill, cx, EmptyState, ErrorState, PageHeader, Skeleton, TierBadge, useToast } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, ist, num, timeAgo } from '../lib/format'
import { useDebounced, useInvalidate } from '../lib/hooks'

interface Item {
  id: string; title: string; summary: string | null; url: string | null; source: string; publisher: string | null; tier: string; kind: string
  category: string; sections: string[]; symbol: string | null; company: string | null; industry: string | null; industry_name: string | null
  published: string | null; fetched_at: string | null; important: boolean; tentative: boolean; also: string[]
}
interface Feed { section: string; title: string; items: Item[]; total: number; hidden_unrated: number; sources: string[]; note: string | null; sections: Record<string, string> }
interface Summary { date: string; phase: string; headline: string; indices: { label: string; value: number; change: number; change_pct: number; as_of: string }[]
  bullets: string[]; filings_today: Record<string, number>; status_note: string; sources: string[] }
interface Explain { what: string; who: string; why: string; factors: string[]; status: string; note: string }
interface Saved { url: string; title: string; source: string | null; published: string | null; symbol: string | null; saved_at: string }

const SECTIONS: [string, string][] = [
  ['top', 'Top market news'], ['breaking', 'Breaking'], ['market', 'Indian stock market'], ['company', 'Company news'],
  ['announcements', 'Corporate announcements'], ['results', 'Quarterly results'], ['banking', 'Banking & financial services'],
  ['economy', 'Economy & RBI'], ['regulation', 'SEBI & regulation'], ['sector', 'Sector & industry'], ['global', 'Global markets'],
  ['commodities', 'Commodities & currency'], ['ipo', 'IPO & corporate actions'], ['saved', 'Saved articles'],
]
const FILING_SECTIONS = ['company', 'announcements', 'results', 'sector', 'ipo', 'banking']
const INDUSTRIES: [string, string][] = [['', 'All sectors'], ['banking', 'Banking'], ['financial-services', 'Financial services'], ['it', 'IT'], ['pharma', 'Pharma'],
  ['healthcare', 'Healthcare'], ['automobiles', 'Automobiles'], ['fmcg', 'FMCG'], ['agriculture', 'Agriculture'], ['energy', 'Energy'],
  ['infrastructure', 'Infrastructure'], ['metals', 'Metals'], ['real-estate', 'Real estate'], ['telecom', 'Telecom'], ['consumer-durables', 'Consumer durables'], ['chemicals', 'Chemicals']]
const OFFICIAL = [
  ['NSE corporate filings', 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'], ['BSE corporate announcements', 'https://www.bseindia.com/corporates/ann.html'],
  ['SEBI', 'https://www.sebi.gov.in/'], ['RBI press releases', 'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx'],
  ['Ministry of Finance', 'https://finmin.gov.in/'], ['Press Information Bureau', 'https://pib.gov.in/'], ['MOSPI (GDP, inflation, IIP)', 'https://mospi.gov.in/'],
]

function DailySummary({ go }: { go: (s: string) => void }) {
  const q = useQuery({ queryKey: ['news-summary'], queryFn: () => api.get<Summary>('/news/summary'), refetchInterval: 300_000 })
  if (q.isLoading) return <Skeleton className="h-36 rounded-2xl" />
  if (!q.data) return null
  const d = q.data
  const f = d.filings_today
  return (
    <section className="card p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[15px] font-semibold">Daily market summary · {ist(d.date + 'T06:30:00', false)}</h2>
        <span className="text-xs muted">{d.status_note}</span>
      </div>
      <p className="mt-1.5 text-[15px]">{d.headline}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {d.indices.map((i) => (
          <span key={i.label} className="inline-flex items-center gap-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs dark:bg-ink-800">
            <b>{i.label}</b><span className="num">{num(i.value, 2)}</span><ChangePill value={i.change_pct} /></span>
        ))}
      </div>
      {d.bullets.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">{d.bullets.map((b) => <li key={b}>{b}</li>)}</ul>}
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="muted">Filed today:</span>
        <button className="chip" onClick={() => go('results')}>{f.results} results filings</button>
        <button className="chip" onClick={() => go('announcements')}>{f.announcements} exchange announcements</button>
        <button className="chip" onClick={() => go('economy')}>{f.rbi} RBI / economy items</button>
        <button className="chip" onClick={() => go('regulation')}>{f.sebi} SEBI items</button>
      </div>
      <p className="mt-3 text-[11px] muted">Built only from data: {d.sources.join(' · ')}. Not a forecast.</p>
    </section>
  )
}

function ExplainPanel({ item }: { item: Item }) {
  const q = useQuery({ queryKey: ['explain', item.id], queryFn: () => api.post<Explain>('/news/explain', {
    title: item.title, summary: item.summary, source: item.publisher || item.source, category: item.category, symbol: item.symbol, tier: item.tier,
    sections: item.sections, company: item.company }) })
  if (q.isLoading) return <Skeleton className="mt-2 h-24" />
  if (!q.data) return null
  const e = q.data
  return (
    <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-sm dark:border-ink-700 dark:bg-ink-800/60">
      <dl className="grid gap-2 sm:grid-cols-2">
        <div><dt className="text-xs font-semibold muted">What happened</dt><dd>{e.what}</dd></div>
        <div><dt className="text-xs font-semibold muted">Who is affected</dt><dd>{e.who}</dd></div>
        <div className="sm:col-span-2"><dt className="text-xs font-semibold muted">Why it can matter</dt><dd>{e.why}</dd></div>
        <div className="sm:col-span-2"><dt className="text-xs font-semibold muted">What to check</dt><dd><ul className="list-disc pl-5">{e.factors.map((x) => <li key={x}>{x}</li>)}</ul></dd></div>
        <div className="sm:col-span-2"><dt className="text-xs font-semibold muted">Confirmed or developing?</dt><dd>{e.status}</dd></div>
      </dl>
      <p className="mt-2 text-[11px] muted"><Info className="mr-1 inline h-3 w-3" />{e.note}</p>
    </div>
  )
}

function Related({ item }: { item: Item }) {
  const q = useQuery({ queryKey: ['related', item.id], queryFn: () => api.get<{ items: Item[] }>(`/news/related?title=${encodeURIComponent(item.title)}${item.symbol ? `&symbol=${encodeURIComponent(item.symbol)}` : ''}`) })
  if (q.isLoading) return <Skeleton className="mt-2 h-16" />
  const items = q.data?.items ?? []
  return (
    <div className="mt-2 rounded-xl border border-slate-200 p-3 text-sm dark:border-ink-700">
      {items.length === 0 ? <p className="muted">No related items in the last two weeks.</p> : (
        <ul className="space-y-1.5">{items.map((r) => (
          <li key={r.id} className="flex gap-2"><span className="w-16 shrink-0 text-xs muted">{timeAgo(r.published)}</span>
            <a href={r.url ?? '#'} target="_blank" rel="noopener noreferrer" className="min-w-0 hover:underline">{r.company && r.tier === 'primary' ? `${r.company}: ${r.summary ?? r.title}` : r.title}</a></li>))}</ul>
      )}
      {item.symbol && <Link to={`/news?section=company&symbol=${encodeURIComponent(item.symbol)}`} className="mt-2 inline-block text-xs font-medium text-brand-600 hover:underline dark:text-brand-300">All news for {baseSymbol(item.symbol)} →</Link>}
    </div>
  )
}

function NewsRow({ item, saved, onSave }: { item: Item; saved: boolean; onSave: (i: Item, on: boolean) => void }) {
  const [open, setOpen] = useState<'' | 'explain' | 'related'>('')
  const fresh = item.published && (Date.now() - new Date(item.published + 'Z').getTime()) / 3.6e6 <= 3
  const filing = item.tier === 'primary' && !!item.company && ['announcements', 'results', 'company'].some((s) => item.sections.includes(s))
  const headline = filing ? (item.summary ?? item.title) : item.title
  return (
    <li className="px-4 py-4 sm:px-5">
      <div className="mb-1 flex flex-wrap items-center gap-1.5 text-[11px]">
        <TierBadge tier={item.tier} />
        <span className="rounded bg-slate-500/10 px-1.5 py-0.5 font-medium muted">{item.category}</span>
        {item.important && <span className="rounded bg-saffron-500/15 px-1.5 py-0.5 font-semibold text-amber-700 dark:text-saffron-400">Important</span>}
        {fresh && <span className="rounded bg-up/10 px-1.5 py-0.5 font-semibold text-up">New</span>}
        {item.tentative && <span className="rounded bg-orange-500/10 px-1.5 py-0.5 font-medium text-orange-700 dark:text-orange-300" title="The headline uses tentative language (may, plans, reportedly…). Treat it as unconfirmed.">Unconfirmed report</span>}
        {item.symbol && <Link to={`/company/${encodeURIComponent(item.symbol)}`} className="rounded bg-brand-50 px-1.5 py-0.5 font-semibold text-brand-700 hover:underline dark:bg-brand-500/15 dark:text-brand-200">{baseSymbol(item.symbol)}</Link>}
        {item.industry_name && <Link to={`/industries/${item.industry}`} className="rounded px-1.5 py-0.5 muted hover:underline">{item.industry_name}</Link>}
      </div>
      {filing && <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{item.company}</div>}
      <a href={item.url ?? '#'} target="_blank" rel="noopener noreferrer" className="text-[15px] font-medium leading-snug hover:text-brand-600 hover:underline">
        {headline}<ExternalLink className="ml-1 inline h-3 w-3 opacity-50" /></a>
      {!filing && item.summary && <p className="mt-1 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{item.summary}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs muted">
        <span className="font-medium text-slate-600 dark:text-slate-300">{(item.publisher || item.source).replace(' (RSS)', '')}</span>
        <span title={`Published ${ist(item.published)} IST · fetched by EquityPilot ${ist(item.fetched_at)} IST`}>{item.published ? `${ist(item.published)} IST` : 'Publication time not given'}</span>
        {item.also.length > 0 && <span>Also reported by {item.also.slice(0, 3).join(', ')}{item.also.length > 3 ? ` +${item.also.length - 3}` : ''}</span>}
        <span className="ml-auto flex items-center gap-1">
          <button className={cx('btn-ghost px-2 py-1 text-xs', open === 'explain' && 'text-brand-600')} onClick={() => setOpen(open === 'explain' ? '' : 'explain')} aria-expanded={open === 'explain'}><Lightbulb className="h-3.5 w-3.5" />What this means</button>
          <button className={cx('btn-ghost px-2 py-1 text-xs', open === 'related' && 'text-brand-600')} onClick={() => setOpen(open === 'related' ? '' : 'related')} aria-expanded={open === 'related'}><Link2 className="h-3.5 w-3.5" />Related</button>
          {item.url && <button className="btn-ghost px-2 py-1 text-xs" onClick={() => onSave(item, !saved)} aria-pressed={saved} title={saved ? 'Remove from saved' : 'Save for later'}>
            {saved ? <BookmarkCheck className="h-3.5 w-3.5 text-brand-600" /> : <Bookmark className="h-3.5 w-3.5" />}{saved ? 'Saved' : 'Save'}</button>}
        </span>
      </div>
      {open === 'explain' && <ExplainPanel item={item} />}
      {open === 'related' && <Related item={item} />}
    </li>
  )
}

export default function News() {
  const [params, setParams] = useSearchParams()
  const section = params.get('section') || 'top'
  const symbol = params.get('symbol') || ''
  const industry = params.get('industry') || ''
  const [query, setQuery] = useState(params.get('q') || '')
  const [source, setSource] = useState('')
  const [days, setDays] = useState(symbol ? 90 : 7)
  const [sort, setSort] = useState<'latest' | 'relevant'>('latest')
  const [tracked, setTracked] = useState(true)
  const [unrated, setUnrated] = useState(false)
  const [limit, setLimit] = useState(30)
  const dq = useDebounced(query, 300)
  const toast = useToast()
  const inv = useInvalidate()
  const set = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next, { replace: true })
    setLimit(30)
  }
  const isSaved = section === 'saved'
  const url = `/news/feed?section=${section}&days=${days}&sort=${sort}&limit=${limit}&tracked_only=${tracked && FILING_SECTIONS.includes(section)}&include_unrated=${unrated}`
    + (dq ? `&q=${encodeURIComponent(dq)}` : '') + (symbol ? `&symbol=${encodeURIComponent(symbol)}` : '') + (industry ? `&industry=${industry}` : '') + (source ? `&source=${encodeURIComponent(source)}` : '')
  const feed = useQuery({ queryKey: ['newsfeed', url], queryFn: () => api.get<Feed>(url), enabled: !isSaved, placeholderData: (p) => p, refetchInterval: 180_000 })
  const saved = useQuery({ queryKey: ['news-saved'], queryFn: () => api.get<{ items: Saved[] }>('/news/saved') })
  const savedUrls = useMemo(() => new Set((saved.data?.items ?? []).map((s) => s.url)), [saved.data])
  const save = useMutation({
    mutationFn: ({ i, on }: { i: Item; on: boolean }) => on
      ? api.post('/news/saved', { url: i.url, title: i.company && i.tier === 'primary' ? `${i.company}: ${i.summary ?? i.title}`.slice(0, 500) : i.title, source: i.publisher || i.source, published: i.published, symbol: i.symbol })
      : api.del(`/news/saved?url=${encodeURIComponent(i.url ?? '')}`),
    onSuccess: (_, v) => { inv('news-saved'); toast(v.on ? 'Saved to your reading list' : 'Removed from saved') },
  })
  const label = SECTIONS.find(([k]) => k === section)?.[1] ?? 'News'
  const d = feed.data

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="News & market intelligence" title="Market news from trusted sources"
        subtitle="Official filings and regulator releases first, then established publishers - each labelled, de-duplicated and linked to the original. EquityPilot never rewrites headlines." />
      <div className="grid items-start gap-5 lg:grid-cols-[13.5rem_minmax(0,1fr)] xl:grid-cols-[13.5rem_minmax(0,1fr)_17rem]">
        {/* section navigation */}
        <nav aria-label="News sections" className="lg:sticky lg:top-28">
          <select className="input lg:hidden" value={section} onChange={(e) => set({ section: e.target.value })} aria-label="News section">
            {SECTIONS.map(([k, l]) => <option key={k} value={k}>{l}{k === 'saved' && saved.data ? ` (${saved.data.items.length})` : ''}</option>)}
          </select>
          <ul className="card hidden p-1.5 lg:block">
            {SECTIONS.map(([k, l]) => (
              <li key={k}><button onClick={() => set({ section: k })} aria-current={section === k}
                className={cx('flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-[13px]', section === k ? 'bg-brand-50 font-semibold text-brand-700 shadow-[inset_0_0_0_1px_rgb(79_99_244/0.14)] dark:bg-brand-500/15 dark:text-white dark:shadow-[inset_0_0_0_1px_rgb(113_132_250/0.25)]' : 'text-slate-600 transition-colors hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-ink-800 dark:hover:text-white')}>
                {l}{k === 'saved' && (saved.data?.items.length ?? 0) > 0 && <span className="text-[11px] opacity-70">{saved.data!.items.length}</span>}
              </button></li>))}
          </ul>
        </nav>

        <div className="min-w-0 space-y-4">
          {section === 'top' && !dq && !symbol && !industry && <DailySummary go={(s) => set({ section: s })} />}

          {!isSaved && (
            <div className="card flex flex-wrap items-center gap-2 p-3">
              <div className="relative min-w-[12rem] flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input className="input pl-9" placeholder="Search headlines…" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search news" /></div>
              <CompanyPicker className="w-full sm:w-52" value={symbol} placeholder="Company…" onChange={(s) => { set({ symbol: s, industry: '', section: section === 'top' || section === 'breaking' ? 'company' : section }); setDays(90) }} />
              <select className="input w-auto" value={industry} onChange={(e) => set({ industry: e.target.value, symbol: '' })} aria-label="Sector">{INDUSTRIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              <select className="input w-auto" value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
                <option value="">All sources</option>{(d?.sources ?? []).map((s) => <option key={s} value={s}>{s}</option>)}</select>
              <select className="input w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Date range">
                <option value={1}>Last 24 hours</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={0}>Any time</option></select>
              <select className="input w-auto" value={sort} onChange={(e) => setSort(e.target.value as 'latest' | 'relevant')} aria-label="Sort"><option value="latest">Latest first</option><option value="relevant">Most relevant</option></select>
              {FILING_SECTIONS.includes(section) && !symbol && <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={tracked} onChange={(e) => setTracked(e.target.checked)} />Tracked companies only</label>}
              {(symbol || industry || dq || source) && <button className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => { setQuery(''); setSource(''); set({ symbol: '', industry: '', q: '' }) }}>Clear filters</button>}
            </div>
          )}

          <div className="card overflow-hidden">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 px-4 py-3 sm:px-5 dark:border-ink-700">
              <h2 className="text-[15px] font-semibold">{label}{symbol ? ` · ${baseSymbol(symbol)}` : ''}{industry ? ` · ${INDUSTRIES.find(([v]) => v === industry)?.[1]}` : ''}</h2>
              {!isSaved && d && <span className="text-xs muted">{d.total} item{d.total === 1 ? '' : 's'}{section === 'breaking' ? ' published in the last 3 hours' : ''}{section === 'top' ? ' · ranked by importance and freshness' : ''}</span>}
            </div>
            {!isSaved && (d?.hidden_unrated ?? 0) + (unrated ? 1 : 0) > 0 && (
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-2 text-xs sm:px-5 dark:border-ink-700">
                <span className="muted">{unrated ? 'Including unrated publishers (marked UNRATED).' : `${d!.hidden_unrated} headlines from unrated publishers hidden.`}</span>
                <button className="font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => setUnrated(!unrated)}>{unrated ? 'Hide them' : 'Show them'}</button>
              </div>
            )}
            {isSaved ? (
              (saved.data?.items.length ?? 0) === 0 ? <div className="p-5"><EmptyState icon={<Bookmark className="h-6 w-6" />} title="No saved articles" body="Use Save on any news item to keep it here." /></div> : (
                <ul className="divide-y divide-slate-100 dark:divide-ink-700">{saved.data!.items.map((s) => (
                  <li key={s.url} className="flex items-start gap-3 px-4 py-3.5 sm:px-5">
                    <div className="min-w-0 flex-1"><a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">{s.title}<ExternalLink className="ml-1 inline h-3 w-3 opacity-50" /></a>
                      <div className="mt-0.5 text-xs muted">{(s.source ?? '').replace(' (RSS)', '')} · {s.published ? `${ist(s.published)} IST` : ''} · saved {timeAgo(s.saved_at)}</div></div>
                    <button className="btn-ghost px-2 py-1 text-xs" onClick={() => api.del(`/news/saved?url=${encodeURIComponent(s.url)}`).then(() => inv('news-saved'))}>Remove</button>
                  </li>))}</ul>)
            ) : feed.isError ? <div className="p-5"><ErrorState error={feed.error} retry={feed.refetch} /></div>
              : feed.isLoading ? <div className="space-y-3 p-5">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
                : (d?.items.length ?? 0) === 0 ? (
                  <div className="p-5"><EmptyState icon={<Newspaper className="h-6 w-6" />} title="Nothing here right now" body={d?.note ?? 'No items match these filters. Try a longer date range or clear the filters.'} /></div>
                ) : (<>
                  <ul className={cx('divide-y divide-slate-100 dark:divide-ink-700', feed.isFetching && feed.isPlaceholderData && 'opacity-60')}>
                    {d!.items.map((i) => <NewsRow key={i.id} item={i} saved={!!i.url && savedUrls.has(i.url)} onSave={(it, on) => save.mutate({ i: it, on })} />)}
                  </ul>
                  {d!.total > d!.items.length && <div className="border-t border-slate-100 p-3 text-center dark:border-ink-700"><button className="btn-outline" onClick={() => setLimit((l) => l + 30)} disabled={feed.isFetching}>{feed.isFetching ? 'Loading…' : `Show more (${d!.total - d!.items.length} left)`}</button></div>}
                </>)}
          </div>
          <p className="px-1 text-[11px] muted">Times are publication times in IST (hover a time to see when EquityPilot fetched it). Media headlines come from the publishers' own RSS feeds and Yahoo Finance; open the original to read the full article.</p>
        </div>

        <aside className="hidden space-y-5 xl:block">
          <Card title="How sources are labelled">
            <ul className="space-y-2.5 text-sm">
              <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="primary" /></span><span className="text-slate-600 dark:text-slate-300">Official disclosure: exchange, regulator or government. The authoritative record.</span></li>
              <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="established" /></span><span className="text-slate-600 dark:text-slate-300">Media report by an established publisher. Check material facts against the filing.</span></li>
              <li className="flex gap-2"><span className="mt-0.5"><TierBadge tier="unrated" /></span><span className="text-slate-600 dark:text-slate-300">Other publishers. Hidden by default and never used by the AI assistant.</span></li>
            </ul>
          </Card>
          <Card title="Official sources" subtitle="Go to the primary record">
            <ul className="space-y-2 text-sm">{OFFICIAL.map(([l, u]) => <li key={u}><a href={u} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-600 hover:underline dark:text-brand-300">{l}<ExternalLink className="h-3 w-3" /></a></li>)}</ul>
          </Card>
        </aside>
      </div>
    </div>
  )
}
