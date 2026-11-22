// Corporate Actions: dividends, splits, bonus issues, rights, buybacks and schemes with the ex-date and record date
// set by the exchange, board announcements whose dates are still to come, and each company's dividend/split history.
import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Gift, Search } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Pill, SourceLabel } from '../components/status'
import { Card, cx, EmptyState, ErrorState, Loading, Notice, PageHeader, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, dayLabel, inr, ist, num, timeAgo } from '../lib/format'
import { useDebounced } from '../lib/hooks'

interface Action {
  company: string; symbol: string | null; tracked: boolean; industry: string | null; type: string; type_label: string; purpose: string; series: string | null
  ex_date: string | null; record_date: string | null; book_closure: string | null; face_value: string | null; amount: number | null; ratio: string | null
  payment_date: string | null; announced: string | null; status_label: string; source: string; tier: string; url: string
}
interface Announcement { company: string; symbol: string | null; type: string; type_label: string; subject: string; detail: string | null; filed: string | null; url: string | null; tier: string }
interface Centre {
  when: string; today: string; items: Action[]; total: number; announcements: Announcement[]; counts_upcoming: Record<string, number>
  types: Record<string, { label: string; explain: string }>; sources: { label: string; url: string | null; tier: string }[]; notes: string[]; industries: Record<string, string>
}
interface History { symbol: string; type: string; type_label: string; ex_date: string; value: number; source: string; tier: string; note: string }

const TYPE_TONE: Record<string, 'good' | 'info' | 'warn' | 'neutral'> = { dividend: 'good', bonus: 'info', split: 'info', rights: 'warn', buyback: 'info', merger: 'warn', distribution: 'good' }
const ORDER = ['dividend', 'split', 'bonus', 'rights', 'buyback', 'merger', 'distribution', 'meeting', 'other']

function Company({ name, symbol }: { name: string; symbol: string | null }) {
  return symbol ? <Link to={`/company/${encodeURIComponent(symbol)}`} className="font-medium hover:text-brand-600 hover:underline">{name}</Link> : <span className="font-medium">{name}</span>
}

function Details({ a }: { a: Action }) {
  if (a.type === 'dividend' || a.type === 'distribution') return <span>{a.amount != null ? `${inr(a.amount)} per ${a.type === 'distribution' ? 'unit' : 'share'}` : a.purpose}</span>
  if (a.ratio) return <span>{a.ratio}</span>
  return <span className="line-clamp-2">{a.purpose}</span>
}

function CompanyActions() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const q = useQuery({ queryKey: ['events-company', symbol], enabled: !!symbol, queryFn: () => api.get<{ actions: Action[]; history: History[] }>(`/events/company/${encodeURIComponent(symbol)}`) })
  return (
    <div className="space-y-5">
      <Card title="Company dividend and split history" subtitle="Exchange records collected by EquityPilot, plus the market-data provider's history">
        <CompanyPicker value={symbol} trackedOnly onChange={(s) => setParams((p) => { p.set('symbol', s); return p }, { replace: true })} className="max-w-md" placeholder="Search a tracked company…" />
      </Card>
      {symbol && (q.isLoading ? <Loading /> : (
        <>
          {(q.data?.actions.length ?? 0) > 0 && (
            <Card pad={false} title="From the exchange" subtitle="Ex-dates and record dates set by NSE">
              <ActionTable rows={q.data!.actions} />
            </Card>
          )}
          <Card pad={false} title="Provider history" subtitle="Yahoo Finance dividend and split records. Amounts are adjusted for later splits and bonus issues.">
            {(q.data?.history.length ?? 0) === 0 ? <p className="p-5 text-sm muted">No dividend or split history from the provider for {baseSymbol(symbol)}.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="table-head"><th className="px-4 py-2 text-left">Ex-date</th><th className="px-4 py-2 text-left">Action</th><th className="px-4 py-2 text-right">Value</th><th className="px-4 py-2 text-left">Label</th></tr></thead>
                  <tbody>{q.data!.history.slice(0, 60).map((h) => (
                    <tr key={h.ex_date + h.type} className="border-t border-slate-100 dark:border-ink-700">
                      <td className="num px-4 py-2">{ist(h.ex_date, false)}</td><td className="px-4 py-2">{h.type_label}</td>
                      <td className="num px-4 py-2 text-right">{h.type === 'split' ? `${num(h.value, 2)}×` : inr(h.value)}</td>
                      <td className="px-4 py-2"><SourceLabel tier={h.tier} /></td></tr>))}</tbody>
                </table>
                <p className="px-4 pb-4 pt-2 text-xs muted">{q.data!.history[0]?.note} Split factor = shares after / before; bonus issues appear as splits.</p>
              </div>)}
          </Card>
        </>
      ))}
    </div>
  )
}

function ActionTable({ rows }: { rows: Action[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] text-sm">
        <thead>
          <tr className="table-head">
            <th className="px-4 py-2 text-left">Company</th><th className="px-4 py-2 text-left">Action</th><th className="px-4 py-2 text-left">Details</th>
            <th className="px-4 py-2 text-left">Ex-date</th><th className="px-4 py-2 text-left">Record date</th><th className="px-4 py-2 text-left">Payment date</th><th className="px-4 py-2 text-left">Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.company + a.ex_date + a.purpose} className="border-t border-slate-100 align-top dark:border-ink-700">
              <td className="px-4 py-2.5"><Company name={a.company} symbol={a.symbol} />{a.symbol && <div className="text-xs muted">{baseSymbol(a.symbol)}</div>}</td>
              <td className="px-4 py-2.5"><Pill tone={TYPE_TONE[a.type] ?? 'neutral'}>{a.type_label}</Pill></td>
              <td className="max-w-[340px] px-4 py-2.5 text-slate-700 dark:text-slate-200"><Details a={a} /></td>
              <td className="num whitespace-nowrap px-4 py-2.5 font-medium">{a.ex_date ? dayLabel(a.ex_date) : '—'}</td>
              <td className="num whitespace-nowrap px-4 py-2.5">{a.record_date ? dayLabel(a.record_date) : '—'}</td>
              <td className="whitespace-nowrap px-4 py-2.5 text-xs muted" title="Payment dates are not in the exchange feed">See filing</td>
              <td className="whitespace-nowrap px-4 py-2.5"><a href={a.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:underline dark:text-brand-300"><SourceLabel tier={a.tier} />NSE<ExternalLink className="h-3 w-3" /></a></td>
            </tr>))}
        </tbody>
      </table>
    </div>
  )
}

export default function CorporateActions() {
  const [params, setParams] = useSearchParams()
  const view = params.get('view') || 'upcoming'
  const setView = (v: string) => setParams((p) => { p.set('view', v); return p }, { replace: true })
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [industry, setIndustry] = useState('')
  const [tracked, setTracked] = useState(false)
  const dq = useDebounced(q, 250)
  const url = `/events/actions?when=${view === 'past' ? 'past' : 'upcoming'}&tracked_only=${tracked}` + (type ? `&type=${type}` : '') + (dq ? `&q=${encodeURIComponent(dq)}` : '') + (industry ? `&industry=${industry}` : '')
  const c = useQuery({ queryKey: ['events-actions', url], enabled: view !== 'company', placeholderData: (p) => p, queryFn: () => api.get<Centre>(url), refetchInterval: 600_000 })
  const d = c.data
  const types = ORDER.filter((t) => d?.types[t])

  return (
    <div className="page-enter">
      <PageHeader eyebrow="Markets" title="Corporate Actions"
        subtitle="Dividends, splits, bonus issues, rights issues, buybacks and schemes, with the ex-date and record date set by the exchange." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Segmented value={view} onChange={setView} options={[{ id: 'upcoming', label: 'Upcoming' }, { id: 'past', label: 'Recent' }, { id: 'company', label: 'Company history' }]} />
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
          </>
        )}
      </div>

      {view === 'company' ? <CompanyActions /> : (
        <>
          <div className="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Action type">
            <button className={cx('chip', !type && 'chip-active')} onClick={() => setType('')} aria-pressed={!type}>All types</button>
            {types.map((t) => (
              <button key={t} className={cx('chip', type === t && 'chip-active')} onClick={() => setType(type === t ? '' : t)} aria-pressed={type === t}>
                {d!.types[t].label}{view === 'upcoming' && d!.counts_upcoming[t] ? <span className="num ml-1 opacity-70">{d!.counts_upcoming[t]}</span> : null}
              </button>))}
          </div>
          {c.error ? <ErrorState error={c.error} retry={() => c.refetch()} /> : !d ? <Loading /> : (
            <div className="space-y-5">
              <Card pad={false} title={view === 'upcoming' ? 'Upcoming ex-dates' : 'Recent ex-dates'} subtitle={`${d.total} action${d.total === 1 ? '' : 's'} · confirmed by the exchange`}>
                  {d.items.length === 0 ? <div className="p-4 sm:p-5"><EmptyState icon={<Gift className="h-5 w-5" />} title="No corporate actions found" body={dq || industry || tracked || type ? 'Try clearing the filters.' : 'The exchange feed has no actions in this window yet.'} /></div>
                    : <div className="mt-3"><ActionTable rows={d.items.slice(0, 200)} /></div>}
                </Card>
              <div className="grid gap-5 xl:grid-cols-3">
                <Card className="xl:col-span-2" title="Announced - dates to follow" subtitle="Board decisions filed with NSE before the exchange sets the ex-date. Not confirmed dates.">
                  {d.announcements.length === 0 ? <p className="text-sm muted">No recent announcements match.</p> : (
                    <ul className="divide-y divide-slate-100 dark:divide-ink-700">{d.announcements.slice(0, 25).map((a) => (
                      <li key={(a.url ?? '') + a.filed} className="flex flex-col gap-1 py-2.5 text-sm sm:flex-row sm:items-center sm:gap-3">
                        <span className="min-w-0 flex-1"><Company name={a.company} symbol={a.symbol} /> <span className="muted">· {a.subject || a.type_label}</span>
                          {a.detail && <span className="block truncate text-xs muted">{a.detail}</span>}</span>
                        <span className="flex shrink-0 items-center gap-2 text-xs"><Pill tone="warn">Announced</Pill><span className="muted">{timeAgo(a.filed)}</span>
                          {a.url && <a href={a.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-300">Filing<ExternalLink className="h-3 w-3" /></a>}</span>
                      </li>))}</ul>)}
                </Card>
              <div className="space-y-5">
                <Card title="What these actions mean" subtitle="In plain English">
                  <dl className="space-y-3 text-sm">{ORDER.filter((t) => !['meeting', 'other', 'distribution'].includes(t)).map((t) => d.types[t] && (
                    <div key={t}><dt className="font-semibold">{d.types[t].label}</dt><dd className="mt-0.5 text-slate-600 dark:text-slate-300">{d.types[t].explain}</dd></div>))}</dl>
                </Card>
                <Card title="Sources and limits">
                  <ul className="space-y-2 text-sm">{d.sources.map((s) => (
                    <li key={s.label} className="flex items-center gap-2"><SourceLabel tier={s.tier} />{s.url ? <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">{s.label}<ExternalLink className="h-3 w-3 opacity-60" /></a> : <span>{s.label}</span>}</li>))}</ul>
                  <ul className="mt-3 list-disc space-y-1.5 pl-5 text-xs muted">{d.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                </Card>
                <Notice>Virtual Invest credits dividends and applies splits automatically to positions held before the ex-date. A split or bonus never changes the value of a holding.</Notice>
              </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
