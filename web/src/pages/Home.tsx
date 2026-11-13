import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ExternalLink, Landmark, PiggyBank, Scale, Sparkles, Star } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkline } from '../components/charts'
import { CardRow, CompanyAvatar } from '../components/common'
import { LivePrice, MarketClock, useIndexOverview } from '../components/live'
import { Card, ChangePill, cx, DataBadge, EmptyState, Segmented, Skeleton, SourceNote } from '../components/ui'
import { api, type CompanyCardData, type Mover } from '../lib/api'
import { baseSymbol, inr, isNum, num, pct, timeAgo } from '../lib/format'
import { useMe } from '../lib/hooks'

interface Movers { gainers: Mover[]; losers: Mover[]; active: Mover[]; breadth: { advances: number; declines: number; unchanged: number; median_change: number } | null; universe: number; latest_time: string; note: string }
interface Sectors { industries: { industry: string; name: string; avg_change: number; companies: number; advances: number; declines: number }[]; note: string }
interface NewsItem { title: string; url: string | null; published: string | null; source: string; category: string; symbol: string | null; summary?: string | null }

function greeting() {
  const h = Number(new Date().toLocaleString('en-IN', { hour: 'numeric', hour12: false, timeZone: 'Asia/Kolkata' }))
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

const ASK_EXAMPLES = ['How is the market today?', 'Compare TCS and Infosys', 'Top 10 banks by ROE', 'Is Reliance\'s debt high?']

/** Ask-anything box: sends the question to the AI research assistant. */
function AskBox() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const go = (text: string) => { if (text.trim()) nav(`/assistant?q=${encodeURIComponent(text.trim())}`) }
  return (
    <div className="min-w-0">
      <form onSubmit={(e) => { e.preventDefault(); go(q) }} className="flex items-center gap-2 rounded-xl bg-white/10 p-1.5 ring-1 ring-white/15 focus-within:ring-white/40">
        <Sparkles className="ml-2 h-4 w-4 shrink-0 text-saffron-400" />
        <input value={q} onChange={(e) => setQ(e.target.value)} maxLength={1000} aria-label="Ask the AI research assistant"
          placeholder="Ask anything - a company, a comparison, the market…" className="min-w-0 flex-1 bg-transparent py-1.5 text-sm text-white placeholder:text-slate-300 focus:outline-none" />
        <button className="btn shrink-0 bg-white text-ink-900 hover:bg-brand-50" disabled={!q.trim()}>Ask AI</button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {ASK_EXAMPLES.slice(0, 3).map((x) => <button key={x} onClick={() => go(x)} className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-slate-200 transition-colors hover:bg-white/20">{x}</button>)}
      </div>
    </div>
  )
}

export default function Home() {
  const me = useMe()
  const ov = useIndexOverview()
  const liveSession = ov.data?.status.phase === 'open'
  const mv = useQuery({ queryKey: ['movers'], queryFn: () => api.get<Movers>('/market/movers?n=6'), refetchInterval: liveSession ? 30_000 : 120_000 })
  const sec = useQuery({ queryKey: ['sectors'], queryFn: () => api.get<Sectors>('/market/sectors'), refetchInterval: 300_000 })
  const wl = useQuery({ queryKey: ['watchlists'], queryFn: () => api.get<{ id: number; name: string; items: (Mover & { note: string | null })[] }[]>('/watchlists'), refetchInterval: liveSession ? 30_000 : false })
  const recent = useQuery({ queryKey: ['recent'], queryFn: () => api.get<{ views: CompanyCardData[] }>('/recent') })
  const ann = useQuery({ queryKey: ['news', 'disclosures-home'], queryFn: () => api.get<{ items: NewsItem[] }>('/news?section=disclosures&tracked_only=true&limit=8') })
  const reg = useQuery({ queryKey: ['news', 'reg-home'], queryFn: async () => {
    const [a, b] = await Promise.all([api.get<{ items: NewsItem[] }>('/news?section=economy&limit=3'), api.get<{ items: NewsItem[] }>('/news?section=regulation&limit=3')])
    return [...a.items, ...b.items]
  } })
  const inv = useQuery({ queryKey: ['invest-summary'], queryFn: () => api.get<{ total_value: number; total_return: number; holdings: unknown[]; cash: number }>('/invest/summary') })
  const ex = useQuery({ queryKey: ['explore'], queryFn: () => api.get<{ collections: { id: string; title: string; description: string; companies: CompanyCardData[] }[] }>('/explore') })
  const [moverTab, setMoverTab] = useState<'gainers' | 'losers' | 'active'>('gainers')

  const broad = (ov.data?.indices ?? []).filter((i) => i.kind === 'broad')
  const nifty = broad.find((i) => i.symbol === '^NSEI')
  const b = mv.data?.breadth
  const best = sec.data?.industries[0], worst = sec.data?.industries[sec.data.industries.length - 1]

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------- System 1 summary */}
      <section className="rounded-2xl bg-ink-900 p-4 text-white sm:p-5 dark:bg-ink-850 dark:ring-1 dark:ring-ink-700">
        <div className="grid items-center gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
              <span>{greeting()}{me.data?.user && !me.data.user.is_guest ? `, ${me.data.user.display_name}` : ''}</span>
              <span className="rounded-full bg-white/90"><MarketClock /></span>
            </div>
            {nifty && b ? (
              <p className="mt-2 text-[15px] leading-relaxed text-slate-200">
                NIFTY 50 is <b className={nifty.change_pct >= 0 ? 'text-emerald-300' : 'text-rose-300'}>{nifty.change_pct >= 0 ? 'up' : 'down'} {pct(Math.abs(nifty.change_pct), 2)}</b> at <b className="num text-white">{num(nifty.last, 2)}</b>
                {ov.data?.status.open ? ' (delayed)' : ` (close, ${nifty.as_of})`}. Of {mv.data?.universe} tracked companies, <b className="text-white">{b.advances}</b> rose and <b className="text-white">{b.declines}</b> fell
                {best && worst ? <>; <b className="text-white">{best.name}</b> led ({pct(best.avg_change, 2, true)}), <b className="text-white">{worst.name}</b> lagged ({pct(worst.avg_change, 2, true)})</> : null}.
              </p>
            ) : <div className="mt-2 space-y-2"><Skeleton className="h-4 w-full bg-white/10" /><Skeleton className="h-4 w-2/3 bg-white/10" /></div>}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
              <Link to="/markets" className="text-slate-300 hover:text-white hover:underline">Market Tracker <ArrowRight className="inline h-3 w-3" /></Link>
              <Link to="/news" className="text-slate-300 hover:text-white hover:underline">Today's news <ArrowRight className="inline h-3 w-3" /></Link>
              <Link to="/invest" className="text-slate-300 hover:text-white hover:underline"><PiggyBank className="mr-0.5 inline h-3 w-3" />Practise with ₹10 lakh virtual money</Link>
            </div>
          </div>
          <AskBox />
        </div>
      </section>

      {/* ---------------------------------------------- indices */}
      <section>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {ov.isLoading && Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[104px] rounded-2xl" />)}
          {broad.map((i) => (
            <Link key={i.symbol} to={`/markets?symbol=${encodeURIComponent(i.symbol)}`} className="card p-3.5 transition-colors hover:border-brand-300">
              <div className="flex items-center justify-between gap-2"><span className="min-w-0 truncate text-xs font-semibold muted" title={i.name}>{i.name}</span><DataBadge className="shrink-0" type={ov.data?.status.open ? (ov.data.status.realtime ? 'live' : 'delayed') : 'close'} /></div>
              <div className="mt-1 text-lg font-semibold"><LivePrice value={i.last} /></div>
              <div className="flex items-end justify-between">
                <ChangePill value={i.symbol === '^INDIAVIX' ? null : i.change_pct} />{i.symbol === '^INDIAVIX' && <span className="text-xs muted">{pct(i.change_pct, 2, true)}</span>}
                <Sparkline data={i.spark} width={80} height={30} positive={i.symbol === '^INDIAVIX' ? i.change_pct <= 0 : undefined} />
              </div>
            </Link>
          ))}
        </div>
        {ov.data && <SourceNote sources={[ov.data.source]} extra={ov.data.status.note} />}
      </section>

      <div className="grid gap-6 xl:grid-cols-3 xl:grid-rows-[auto_1fr]">
        <div className="space-y-6 xl:col-span-2 xl:row-span-2">
          {/* ------------------------------------------ breadth + movers */}
          <Card title="Market movers" subtitle={mv.data?.note}
            action={<Segmented size="xs" value={moverTab} onChange={setMoverTab} options={[{ id: 'gainers', label: 'Gainers' }, { id: 'losers', label: 'Losers' }, { id: 'active', label: 'Most active' }]} />}>
            {b && (
              <div className="mb-4">
                <div className="mb-1.5 flex justify-between text-xs"><span className="text-up">{b.advances} advancing</span><span className="muted">{b.unchanged} unchanged</span><span className="text-down">{b.declines} declining</span></div>
                <div className="flex h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-ink-700">
                  <div className="bg-up" style={{ width: `${(b.advances / (b.advances + b.declines + b.unchanged)) * 100}%` }} />
                  <div className="bg-slate-300 dark:bg-ink-600" style={{ width: `${(b.unchanged / (b.advances + b.declines + b.unchanged)) * 100}%` }} />
                  <div className="bg-down flex-1" />
                </div>
              </div>
            )}
            {mv.isLoading ? <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10" />)}</div> : (
              <ul className="divide-y divide-slate-100 dark:divide-ink-700">
                {(mv.data?.[moverTab] ?? []).map((m) => (
                  <li key={m.symbol}><Link to={`/company/${encodeURIComponent(m.symbol)}`} className="flex items-center gap-3 py-2.5 hover:opacity-80">
                    <CompanyAvatar symbol={m.symbol} size="sm" />
                    <div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{m.name}</div><div className="text-xs muted">{baseSymbol(m.symbol)}</div></div>
                    <div className="text-right"><div className="num text-sm font-semibold">{inr(m.price)}</div>
                      {moverTab === 'active' ? <div className="text-xs muted">₹{num(((m.price ?? 0) * (m.volume ?? 0)) / 1e7, 0)} Cr traded</div> : <ChangePill value={m.change_pct} />}</div>
                  </Link></li>
                ))}
              </ul>
            )}
          </Card>

          {/* ------------------------------------------ sector heat map */}
          <Card title="Sector heat map" subtitle={sec.data?.note} action={<Link to="/industries" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">All industries</Link>}>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {(sec.data?.industries ?? []).map((s) => {
                const a = Math.min(1, Math.abs(s.avg_change) / 0.025)
                return (
                  <Link key={s.industry} to={`/industries/${s.industry}`} className="rounded-xl p-3 transition-transform hover:scale-[1.02]"
                    style={{ background: s.avg_change >= 0 ? `rgba(18,161,80,${0.08 + a * 0.32})` : `rgba(220,53,69,${0.08 + a * 0.32})` }}>
                    <div className="truncate text-xs font-semibold">{s.name}</div>
                    <div className={cx('num mt-1 text-base font-bold', s.avg_change >= 0 ? 'text-up' : 'text-down')}>{pct(s.avg_change, 2, true)}</div>
                    <div className="text-[10px] muted">{s.advances}▲ {s.declines}▼ · {s.companies} cos</div>
                  </Link>
                )
              })}
              {sec.isLoading && Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} className="h-[74px]" />)}
            </div>
          </Card>
        </div>

        {/* ------------------------------------------ right rail: personal first (shown right after the indices on phones) */}
        <div className="order-first space-y-6 xl:order-none">
          <Card title={<span className="inline-flex items-center gap-1.5"><Star className="h-4 w-4 text-saffron-500" />{wl.data?.[0]?.name ?? 'Watchlist'}</span>}
            action={<Link to="/watchlists" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">Manage</Link>}>
            {(wl.data?.[0]?.items ?? []).length === 0 ? (
              <EmptyState title="Your watchlist is empty" body="Tap the star on any company page to follow it here." />
            ) : (
              <ul className="space-y-2">
                {wl.data![0].items.slice(0, 7).map((i) => (
                  <li key={i.symbol}><Link to={`/company/${encodeURIComponent(i.symbol)}`} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate font-medium">{i.name}</span><span className="flex shrink-0 items-center gap-2"><LivePrice value={i.price} prefix="₹" /><ChangePill value={i.change_pct} /></span>
                  </Link></li>
                ))}
              </ul>
            )}
          </Card>

          <Link to="/invest" className="card block p-5 transition-colors hover:border-brand-300">
            <div className="flex items-center gap-2 text-sm font-semibold"><PiggyBank className="h-4 w-4 text-brand-600" />Virtual Invest</div>
            {inv.data ? (<>
              <div className="num mt-2 text-2xl font-semibold">{inr(inv.data.total_value, 0)}</div>
              <div className="mt-0.5 flex items-center gap-2 text-sm"><ChangePill value={inv.data.total_return} /><span className="muted">{inv.data.holdings.length} holdings · {inr(inv.data.cash, 0)} cash</span></div>
            </>) : <Skeleton className="mt-2 h-8 w-40" />}
            <p className="mt-2 text-xs muted">Paper trading with ₹10 lakh virtual money. No real orders.</p>
          </Link>
        </div>

        <div className="space-y-6">

          <Card title="Recently viewed">
            {(recent.data?.views ?? []).length === 0 ? <p className="text-sm muted">Companies you open will appear here.</p> : (
              <div className="flex flex-wrap gap-2">
                {recent.data!.views.map((v) => (
                  <Link key={v.symbol} to={`/company/${encodeURIComponent(v.symbol)}`} className="chip">{baseSymbol(v.symbol)} {isNum(v.change_pct) && <span className={v.change_pct >= 0 ? 'text-up' : 'text-down'}>{pct(v.change_pct, 1, true)}</span>}</Link>
                ))}
              </div>
            )}
          </Card>

          <Card title={<span className="inline-flex items-center gap-1.5"><Landmark className="h-4 w-4 text-brand-600" />Exchange announcements</span>}
            action={<Link to="/news" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">All news</Link>}>
            <ul className="space-y-3">
              {(ann.data?.items ?? []).slice(0, 6).map((n, i) => (
                <li key={i} className="text-sm">
                  <div className="flex items-center gap-2 text-[11px] muted"><span className="font-semibold text-brand-700 dark:text-brand-300">{n.symbol ? baseSymbol(n.symbol) : ''}</span>{n.category} · {timeAgo(n.published)}</div>
                  <a href={n.url ?? '#'} target="_blank" rel="noopener noreferrer" className="line-clamp-2 hover:underline">{n.summary || n.title}</a>
                </li>
              ))}
              {ann.isLoading && <Skeleton className="h-24" />}
              {ann.data && ann.data.items.length === 0 && <li className="text-sm muted">No recent announcements from tracked companies.</li>}
            </ul>
            <SourceNote sources={['NSE India corporate announcements (RSS)']} />
          </Card>

          <Card title={<span className="inline-flex items-center gap-1.5"><Scale className="h-4 w-4 text-brand-600" />RBI & SEBI updates</span>}>
            <ul className="space-y-3">
              {(reg.data ?? []).map((n, i) => (
                <li key={i} className="text-sm"><div className="text-[11px] muted">{n.source.replace(' (RSS)', '')} · {timeAgo(n.published)}</div>
                  <a href={n.url ?? '#'} target="_blank" rel="noopener noreferrer" className="line-clamp-2 hover:underline">{n.title} <ExternalLink className="inline h-3 w-3" /></a></li>
              ))}
              {reg.isLoading && <Skeleton className="h-20" />}
            </ul>
          </Card>
        </div>
      </div>

      {(ex.data?.collections ?? []).slice(0, 3).map((c) => (
        <CardRow key={c.id} title={c.title} subtitle={`${c.description} · rule-based screen, not a recommendation`} items={c.companies}
          action={<Link to="/explore" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">Explore</Link>} />
      ))}
    </div>
  )
}
