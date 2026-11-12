import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ExternalLink, Landmark, PiggyBank, Scale, Star } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkline } from '../components/charts'
import { CardRow, CompanyAvatar } from '../components/common'
import { Card, ChangePill, cx, DataBadge, EmptyState, Segmented, Skeleton, SourceNote } from '../components/ui'
import { api, type CompanyCardData, type IndexRow, type MarketStatus, type Mover } from '../lib/api'
import { baseSymbol, inr, isNum, num, pct, timeAgo } from '../lib/format'
import { useMe } from '../lib/hooks'

interface Overview { status: MarketStatus; indices: IndexRow[]; source: string }
interface Movers { gainers: Mover[]; losers: Mover[]; active: Mover[]; breadth: { advances: number; declines: number; unchanged: number; median_change: number } | null; universe: number; latest_time: string; note: string }
interface Sectors { industries: { industry: string; name: string; avg_change: number; companies: number; advances: number; declines: number }[]; note: string }
interface NewsItem { title: string; url: string | null; published: string | null; source: string; category: string; symbol: string | null; summary?: string | null }

function greeting() {
  const h = Number(new Date().toLocaleString('en-IN', { hour: 'numeric', hour12: false, timeZone: 'Asia/Kolkata' }))
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

export default function Home() {
  const me = useMe()
  const ov = useQuery({ queryKey: ['market-overview'], queryFn: () => api.get<Overview>('/market/overview'), refetchInterval: 120_000 })
  const mv = useQuery({ queryKey: ['movers'], queryFn: () => api.get<Movers>('/market/movers?n=6'), refetchInterval: 120_000 })
  const sec = useQuery({ queryKey: ['sectors'], queryFn: () => api.get<Sectors>('/market/sectors'), refetchInterval: 300_000 })
  const wl = useQuery({ queryKey: ['watchlists'], queryFn: () => api.get<{ id: number; name: string; items: (Mover & { note: string | null })[] }[]>('/watchlists') })
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
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-900 via-ink-800 to-brand-900 p-5 text-white sm:p-7">
        <div className="relative z-10 max-w-3xl">
          <p className="text-sm text-brand-200">{greeting()}{me.data?.user && !me.data.user.is_guest ? `, ${me.data.user.display_name}` : ''} · {ov.data?.status.now_ist ?? ''}</p>
          <h1 className="mt-1 text-2xl font-semibold !text-white sm:text-3xl">What's happening in Indian markets</h1>
          {nifty && b ? (
            <p className="mt-3 text-[15px] leading-relaxed text-slate-200">
              NIFTY 50 is <b className={nifty.change_pct >= 0 ? 'text-emerald-300' : 'text-rose-300'}>{nifty.change_pct >= 0 ? 'up' : 'down'} {pct(Math.abs(nifty.change_pct), 2)}</b> at {num(nifty.last, 2)}
              {ov.data?.status.open ? ' (delayed)' : ` (last close, ${nifty.as_of})`}. Among the {mv.data?.universe} companies EquityPilot tracks, <b>{b.advances}</b> rose and <b>{b.declines}</b> fell
              {best && worst ? <>; <b>{best.name}</b> led ({pct(best.avg_change, 2, true)}) while <b>{worst.name}</b> lagged ({pct(worst.avg_change, 2, true)})</> : null}.
            </p>
          ) : <div className="mt-3 space-y-2"><Skeleton className="h-4 w-full bg-white/10" /><Skeleton className="h-4 w-2/3 bg-white/10" /></div>}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/explore" className="btn bg-white text-ink-900 hover:bg-brand-50">Explore companies <ArrowRight className="h-4 w-4" /></Link>
            <Link to="/invest" className="btn bg-white/10 text-white hover:bg-white/20"><PiggyBank className="h-4 w-4" />Practise with ₹10 lakh virtual money</Link>
          </div>
        </div>
        <svg className="absolute -right-10 -top-10 h-72 w-72 opacity-20" viewBox="0 0 200 200" aria-hidden><path d="M10 160 L70 100 L105 125 L190 30" fill="none" stroke="#FDBA4D" strokeWidth="10" strokeLinecap="round" /></svg>
      </section>

      {/* ---------------------------------------------- indices */}
      <section>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {ov.isLoading && Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[104px] rounded-2xl" />)}
          {broad.map((i) => (
            <Link key={i.symbol} to={`/markets?symbol=${encodeURIComponent(i.symbol)}`} className="card p-3.5 transition-colors hover:border-brand-300">
              <div className="flex items-center justify-between gap-2"><span className="min-w-0 truncate text-xs font-semibold muted" title={i.name}>{i.name}</span><DataBadge className="shrink-0" type={ov.data?.status.open ? 'delayed' : 'close'} /></div>
              <div className="num mt-1 text-lg font-semibold">{num(i.last, 2)}</div>
              <div className="flex items-end justify-between">
                <ChangePill value={i.symbol === '^INDIAVIX' ? null : i.change_pct} />{i.symbol === '^INDIAVIX' && <span className="text-xs muted">{pct(i.change_pct, 2, true)}</span>}
                <Sparkline data={i.spark} width={80} height={30} positive={i.symbol === '^INDIAVIX' ? i.change_pct <= 0 : undefined} />
              </div>
            </Link>
          ))}
        </div>
        {ov.data && <SourceNote sources={[ov.data.source]} extra={ov.data.status.note} />}
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
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

        {/* ------------------------------------------ right rail */}
        <div className="space-y-6">
          <Card title={<span className="inline-flex items-center gap-1.5"><Star className="h-4 w-4 text-saffron-500" />{wl.data?.[0]?.name ?? 'Watchlist'}</span>}
            action={<Link to="/watchlists" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">Manage</Link>}>
            {(wl.data?.[0]?.items ?? []).length === 0 ? (
              <EmptyState title="Your watchlist is empty" body="Tap the star on any company page to follow it here." />
            ) : (
              <ul className="space-y-2">
                {wl.data![0].items.slice(0, 7).map((i) => (
                  <li key={i.symbol}><Link to={`/company/${encodeURIComponent(i.symbol)}`} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate font-medium">{i.name}</span><span className="flex items-center gap-2"><span className="num">{inr(i.price)}</span><ChangePill value={i.change_pct} /></span>
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
