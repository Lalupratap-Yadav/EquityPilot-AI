// Earnings & Results: confirmed result dates from board-meeting filings, results as they are filed, and each
// company's quarterly history. Dates are never estimated; every row links to the filing it came from.
import { useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronLeft, ChevronRight, ExternalLink, FileCheck2, List, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Pill, SourceLabel } from '../components/status'
import { Card, cx, EmptyState, ErrorState, Loading, Notice, PageHeader, Segmented, Stat } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, dayLabel, ist, timeAgo } from '../lib/format'
import { useDebounced } from '../lib/hooks'
import { QuarterlyTab } from './company/Sections'

interface Src { label: string; url: string; filed: string | null }
interface Meeting {
  company: string; symbol: string | null; tracked: boolean; industry: string | null; meeting_date: string; purpose: string; period: string | null
  results: boolean; filed: string | null; sources: Src[]; status_label: string; state: 'upcoming' | 'filed' | 'awaiting' | 'not_seen'; state_label: string
  results_filing?: { url: string; filed: string; subject: string }
}
interface Filed {
  company: string; symbol: string | null; tracked: boolean; industry: string | null; filed: string | null; kind: 'results' | 'delay'; subject: string
  detail: string | null; period: string | null; basis: string | null; url: string; source: string
}
interface Cal<T> {
  view: string; today: string; items: T[]; total: number; counts: { upcoming: number; filed_recent: number; tracked_upcoming: number }
  collected_since: string | null; sources: { label: string; url: string; tier: string }[]; notes: string[]; industries: Record<string, string>
}
interface CompanyEvents { board_meetings: Meeting[]; results_filed: Filed[] }

type View = 'upcoming' | 'recent' | 'company'

const STATE_TONE = { upcoming: 'info', filed: 'good', awaiting: 'warn', not_seen: 'muted' } as const

function CompanyName({ name, symbol }: { name: string; symbol: string | null }) {
  if (!symbol) return <span className="font-medium">{name}</span>
  return <Link to={`/company/${encodeURIComponent(symbol)}`} className="font-medium hover:text-brand-600 hover:underline">{name}</Link>
}

function MeetingRow({ e }: { e: Meeting }) {
  return (
    <li className="flex flex-col gap-1.5 px-4 py-3 sm:flex-row sm:items-start sm:gap-4 sm:px-5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <CompanyName name={e.company} symbol={e.symbol} />
          {e.symbol && <span className="text-xs muted">{baseSymbol(e.symbol)}</span>}
          {e.state !== 'upcoming' && <Pill tone={STATE_TONE[e.state]} title={e.status_label}>{e.state_label}</Pill>}
          {e.period && <Pill tone="neutral">{e.period}</Pill>}
        </div>
        <p className="mt-0.5 line-clamp-2 text-sm text-slate-600 dark:text-slate-300" title={e.status_label}>{e.purpose}</p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs sm:flex-col sm:items-end">
        {e.sources.map((s) => (
          <a key={s.url} href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-300" title={s.filed ? `Filed ${ist(s.filed)} IST` : undefined}>
            {s.label}<ExternalLink className="h-3 w-3" /></a>))}
        {e.results_filing && <a href={e.results_filing.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-up hover:underline">Results filing<ExternalLink className="h-3 w-3" /></a>}
      </div>
    </li>
  )
}

function MonthCalendar({ items, today, onPick, picked }: { items: Meeting[]; today: string; onPick: (d: string | null) => void; picked: string | null }) {
  const [offset, setOffset] = useState(0)
  const base = new Date(today + 'T00:00:00')
  const first = new Date(base.getFullYear(), base.getMonth() + offset, 1)
  const days = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate()
  const lead = (first.getDay() + 6) % 7                      // Monday first
  const byDay = useMemo(() => {
    const m: Record<string, Meeting[]> = {}
    items.forEach((e) => { (m[e.meeting_date] ??= []).push(e) })
    return m
  }, [items])
  const iso = (d: number) => `${first.getFullYear()}-${String(first.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <button className="btn-ghost p-1.5" onClick={() => setOffset(offset - 1)} aria-label="Previous month"><ChevronLeft className="h-4 w-4" /></button>
        <div className="text-sm font-semibold">{first.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</div>
        <button className="btn-ghost p-1.5" onClick={() => setOffset(offset + 1)} aria-label="Next month"><ChevronRight className="h-4 w-4" /></button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-semibold uppercase tracking-wide muted">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d} className="py-1">{d}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: lead }).map((_, i) => <div key={`b${i}`} />)}
        {Array.from({ length: days }).map((_, i) => {
          const d = iso(i + 1), list = byDay[d] ?? [], isToday = d === today, sel = picked === d
          return (
            <button key={d} onClick={() => onPick(sel ? null : d)} disabled={!list.length} aria-pressed={sel}
              aria-label={`${dayLabel(d, { day: 'numeric', month: 'long' })}: ${list.length} result date${list.length === 1 ? '' : 's'}`}
              className={cx('flex min-h-[64px] flex-col rounded-lg border p-1.5 text-left transition-colors',
                sel ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/15' : list.length ? 'border-slate-200 hover:border-brand-300 dark:border-ink-700' : 'border-transparent bg-slate-50/60 dark:bg-ink-900/40',
                !list.length && 'cursor-default')}>
              <span className={cx('text-xs font-semibold', isToday && 'rounded bg-brand-600 px-1 text-white')}>{i + 1}</span>
              {list.slice(0, 2).map((e) => <span key={e.company} className="mt-0.5 truncate text-[10px] leading-tight text-slate-600 dark:text-slate-300">{e.company.replace(/ (Limited|Ltd\.?)$/i, '')}</span>)}
              {list.length > 2 && <span className="mt-auto text-[10px] font-semibold text-brand-600 dark:text-brand-300">+{list.length - 2} more</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function CompanyHistory() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const ev = useQuery({ queryKey: ['events-company', symbol], enabled: !!symbol, queryFn: () => api.get<CompanyEvents>(`/events/company/${encodeURIComponent(symbol)}`) })
  return (
    <div className="space-y-5">
      <Card title="Company result history" subtitle="Quarterly revenue and profit with QoQ and YoY growth, plus the company's board-meeting and results filings">
        <CompanyPicker value={symbol} trackedOnly onChange={(s) => setParams((p) => { p.set('symbol', s); return p }, { replace: true })} className="max-w-md"
          placeholder="Search a tracked company…" />
        {!symbol && <p className="mt-3 text-sm muted">Choose a company to see its quarterly results history.</p>}
      </Card>
      {symbol && (
        <>
          <QuarterlyTab symbol={symbol} />
          <Card title="Filings collected for this company" subtitle="Board-meeting intimations and results filings from NSE">
            {ev.isLoading ? <Loading /> : !ev.data || (ev.data.board_meetings.length + ev.data.results_filed.length === 0)
              ? <p className="text-sm muted">No board-meeting or results filing collected for {baseSymbol(symbol)} since EquityPilot started reading the NSE feeds. Older filings are on the NSE website.</p>
              : (
                <ul className="divide-y divide-slate-100 dark:divide-ink-700">
                  {ev.data.board_meetings.map((e) => <MeetingRow key={e.meeting_date + e.purpose} e={e} />)}
                  {ev.data.results_filed.map((f) => (
                    <li key={f.url + f.filed} className="flex flex-wrap items-center gap-2 px-4 py-3 text-sm sm:px-5">
                      <FileCheck2 className="h-4 w-4 text-up" /><span className="font-medium">{f.subject || 'Results'}</span>{f.period && <span className="muted">· {f.period}</span>}
                      <span className="text-xs muted">{ist(f.filed)} IST</span>
                      <a href={f.url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-300">Open filing<ExternalLink className="h-3 w-3" /></a>
                    </li>))}
                </ul>)}
          </Card>
        </>
      )}
      <Notice>EquityPilot has no source of analyst estimates, so it does not show an earnings "surprise". Growth figures compare reported numbers only.</Notice>
    </div>
  )
}

export default function Earnings() {
  const [params, setParams] = useSearchParams()
  const view = (params.get('view') as View) || 'upcoming'
  const setView = (v: View) => setParams((p) => { p.set('view', v); return p }, { replace: true })
  const [layout, setLayout] = useState<'list' | 'calendar'>('list')
  const [q, setQ] = useState('')
  const [industry, setIndustry] = useState('')
  const [tracked, setTracked] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const dq = useDebounced(q, 250)
  const qs = `&tracked_only=${tracked}` + (dq ? `&q=${encodeURIComponent(dq)}` : '') + (industry ? `&industry=${industry}` : '')
  const apiView = view === 'upcoming' && layout === 'calendar' ? 'all' : view
  const cal = useQuery({ queryKey: ['events-results', apiView, qs], enabled: view !== 'company', placeholderData: (p) => p,
    queryFn: () => api.get<Cal<Meeting | Filed>>(`/events/results?view=${apiView}${qs}&limit=500`), refetchInterval: 300_000 })
  const d = cal.data
  const meetings = (view === 'upcoming' ? (d?.items ?? []) : []) as Meeting[]
  const shown = picked ? meetings.filter((e) => e.meeting_date === picked) : layout === 'calendar' ? meetings.filter((e) => e.meeting_date >= (d?.today ?? '')) : meetings
  const groups = useMemo(() => {
    const g: [string, Meeting[]][] = []
    shown.forEach((e) => { const last = g[g.length - 1]; if (last && last[0] === e.meeting_date) last[1].push(e); else g.push([e.meeting_date, [e]]) })
    return g
  }, [shown])
  const filed = (view === 'recent' ? (d?.items ?? []) : []) as Filed[]

  return (
    <div className="page-enter">
      <PageHeader eyebrow="Markets" title="Earnings & Results"
        subtitle="Confirmed result dates from companies' board-meeting filings with NSE, and results as they are filed. Nothing here is estimated." />
      {view !== 'company' && <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Upcoming result dates" value={d?.counts.upcoming ?? '—'} sub="confirmed by board-meeting filings" />
        <Stat label="Tracked companies" value={d?.counts.tracked_upcoming ?? '—'} sub="with an upcoming result date" />
        <Stat label="Results filed" value={d?.counts.filed_recent ?? '—'} sub="in the last 120 days" />
        <Stat label="Collected since" value={d?.collected_since ? ist(d.collected_since, false) : '—'} sub="earlier periods may be incomplete" />
      </div>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Segmented value={view} onChange={(v) => { setView(v); setPicked(null) }}
          options={[{ id: 'upcoming', label: 'Upcoming' }, { id: 'recent', label: 'Recently filed' }, { id: 'company', label: 'Company history' }]} />
        {view !== 'company' && (
          <>
            <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input className="input pl-9" placeholder="Company or symbol" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter by company" />
            </div>
            <select className="input w-auto" value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Sector">
              <option value="">All sectors</option>
              {Object.entries(d?.industries ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={tracked} onChange={(e) => setTracked(e.target.checked)} />Tracked companies only</label>
            {view === 'upcoming' && (
              <div className="ml-auto"><Segmented size="xs" value={layout} onChange={(l) => { setLayout(l); setPicked(null) }}
                options={[{ id: 'list', label: <span className="inline-flex items-center gap-1"><List className="h-3.5 w-3.5" />List</span> }, { id: 'calendar', label: <span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />Calendar</span> }]} /></div>
            )}
          </>
        )}
      </div>
      {industry && view !== 'company' && <p className="-mt-2 mb-3 text-xs muted">Sector filters apply to the companies EquityPilot tracks; other listed companies have no sector classification here.</p>}

      {view === 'company' ? <CompanyHistory /> : cal.error ? <ErrorState error={cal.error} retry={() => cal.refetch()} /> : !d ? <Loading /> : (
        <div className={cx('grid gap-5', view === 'upcoming' && layout === 'calendar' && 'xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]')}>
          {view === 'upcoming' && layout === 'calendar' && (
            <Card title="Calendar" subtitle="Days with a confirmed results board meeting. Select a day to list it.">
              <MonthCalendar items={meetings} today={d.today} onPick={setPicked} picked={picked} />
            </Card>
          )}
          {view === 'upcoming' && (
            <Card pad={false} title={picked ? `Result dates on ${dayLabel(picked, { weekday: 'long', day: 'numeric', month: 'long' })}` : 'Upcoming result dates'}
              subtitle="Board meetings whose stated purpose includes approving financial results">
              {groups.length === 0 ? <div className="p-4 sm:p-5"><EmptyState icon={<CalendarDays className="h-5 w-5" />} title="No upcoming result dates found"
                body={dq || industry || tracked ? 'Try clearing the filters.' : 'No company has filed a results board-meeting date for the coming days yet.'} /></div> : (
                <div className="mt-2">
                  {groups.map(([day, list]) => (
                    <section key={day}>
                      <h3 className="sticky top-0 z-[1] border-y border-slate-100 bg-slate-50/95 px-4 py-1.5 text-xs font-semibold backdrop-blur-sm sm:px-5 dark:border-ink-700 dark:bg-ink-900/90">
                        {dayLabel(day, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}{day === d.today ? ' · Today' : ''} <span className="font-normal muted">· {list.length} {list.length === 1 ? 'company' : 'companies'}</span></h3>
                      <ul className="divide-y divide-slate-100 dark:divide-ink-700">{list.map((e) => <MeetingRow key={e.company + e.meeting_date} e={e} />)}</ul>
                    </section>))}
                </div>)}
            </Card>
          )}
          {view === 'recent' && (
            <Card pad={false} title="Recently filed results" subtitle="'Outcome of board meeting' and financial-results filings, newest first">
              {filed.length === 0 ? <div className="p-4 sm:p-5"><EmptyState title="No results filings found" body="Try clearing the filters." /></div> : (
                <ul className="mt-2 divide-y divide-slate-100 dark:divide-ink-700">
                  {filed.slice(0, 200).map((f) => (
                    <li key={f.url + f.filed + f.company} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:gap-4 sm:px-5">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2"><CompanyName name={f.company} symbol={f.symbol} />
                          {f.kind === 'delay' ? <Pill tone="warn">Delay notice</Pill> : <Pill tone="good">Results filed</Pill>}
                          {f.basis && <Pill tone="neutral">{f.basis}</Pill>}</div>
                        <p className="mt-0.5 line-clamp-1 text-sm muted">{f.period ? `${f.period} · ` : ''}{f.subject}{f.detail && f.detail !== f.subject ? ` - ${f.detail}` : ''}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-3 text-xs">
                        <span className="muted" title={f.filed ? `${ist(f.filed)} IST` : undefined}>{timeAgo(f.filed)}</span>
                        <a href={f.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-300">Open filing<ExternalLink className="h-3 w-3" /></a>
                      </div>
                    </li>))}
                </ul>)}
              {filed.length > 200 && <p className="px-5 pb-4 text-xs muted">Showing the latest 200 of {filed.length}. Narrow the list with the filters.</p>}
            </Card>
          )}
        </div>
      )}

      {d && view !== 'company' && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Card title="Where these dates come from">
            <ul className="space-y-2 text-sm">{d.sources.map((s) => (
              <li key={s.label} className="flex items-center gap-2"><SourceLabel tier={s.tier} />
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">{s.label}<ExternalLink className="h-3 w-3 opacity-60" /></a></li>))}</ul>
          </Card>
          <Card title="How to read this page">
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-600 dark:text-slate-300">{d.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          </Card>
        </div>
      )}
    </div>
  )
}
