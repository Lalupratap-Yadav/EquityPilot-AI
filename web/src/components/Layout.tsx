import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Bell, BookOpen, Bot, Briefcase, Building2, Calculator, CalendarDays, ChevronRight, Compass, FileText, Filter, Gift, GitCompare, HelpCircle, Home,
  LineChart, Menu, Moon, Newspaper, PanelLeftClose, PanelLeftOpen, PiggyBank, Search, Settings, ShieldCheck, Star, Sun, Telescope, UploadCloud, X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { timeAgo } from '../lib/format'
import { useExperience, useHotkey, useInvalidate, useMe, useTheme } from '../lib/hooks'
import { ErrorBoundary } from './ErrorBoundary'
import { SearchPalette } from './SearchPalette'
import { LiveTicker, MarketClock, MobileTabBar } from './live'
import { cx, Segmented } from './ui'

const NAV: { section: string; items: { to: string; label: string; icon: ReactNode }[] }[] = [
  { section: 'Markets', items: [
    { to: '/', label: 'Home', icon: <Home /> }, { to: '/markets', label: 'Market Tracker', icon: <LineChart /> },
    { to: '/news', label: 'News', icon: <Newspaper /> }, { to: '/earnings', label: 'Earnings & Results', icon: <CalendarDays /> },
    { to: '/corporate-actions', label: 'Corporate Actions', icon: <Gift /> }, { to: '/explore', label: 'Explore', icon: <Compass /> },
    { to: '/industries', label: 'Industries', icon: <Building2 /> },
  ] },
  { section: 'Research', items: [
    { to: '/research', label: 'Equity Research', icon: <Telescope /> }, { to: '/screener', label: 'Screener', icon: <Filter /> },
    { to: '/compare', label: 'Compare', icon: <GitCompare /> }, { to: '/valuation', label: 'Valuation Lab', icon: <Calculator /> },
    { to: '/assistant', label: 'AI Assistant', icon: <Bot /> }, { to: '/reports', label: 'Reports', icon: <FileText /> },
  ] },
  { section: 'My space', items: [
    { to: '/watchlists', label: 'Watchlists', icon: <Star /> }, { to: '/portfolio', label: 'Portfolio', icon: <Briefcase /> },
    { to: '/invest', label: 'Virtual Invest', icon: <PiggyBank /> }, { to: '/documents', label: 'Documents', icon: <UploadCloud /> },
  ] },
  { section: 'Learn', items: [
    { to: '/learn', label: 'Learning Centre', icon: <BookOpen /> }, { to: '/guide', label: 'How to Use', icon: <HelpCircle /> },
    { to: '/data-quality', label: 'Data Quality', icon: <ShieldCheck /> }, { to: '/settings', label: 'Settings', icon: <Settings /> },
  ] },
]

function Logo({ mini }: { mini?: boolean }) {
  return (
    <Link to="/" className={cx('flex items-center gap-2.5', mini ? 'justify-center' : 'px-2')} aria-label="EquityPilot AI home">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden className="shrink-0 drop-shadow-[0_2px_6px_rgb(63_75_232/0.35)]">
        <defs>
          <linearGradient id="ep-logo-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#5b6cf9" /><stop offset="1" stopColor="#2f3ac4" /></linearGradient>
          <linearGradient id="ep-logo-sheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity="0.22" /><stop offset="0.5" stopColor="#fff" stopOpacity="0" /></linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#ep-logo-bg)" /><rect width="64" height="64" rx="16" fill="url(#ep-logo-sheen)" />
        <path d="M14 44 L28 30 L36 37 L50 20" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M42 19 L51 19 L51 28" fill="none" stroke="#FDBA4D" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" /></svg>
      {!mini && <div className="leading-tight">
        <div className="text-[15px] font-bold tracking-tight text-slate-900 dark:text-white">EquityPilot <span className="text-brand-600 dark:text-brand-300">AI</span></div>
        <div className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Indian equity research</div>
      </div>}
    </Link>
  )
}

function Sidebar({ onNavigate, mini = false, onToggle }: { onNavigate?: () => void; mini?: boolean; onToggle?: () => void }) {
  return (
    <nav className={cx('flex h-full flex-col overflow-y-auto py-4', mini ? 'gap-3 px-2' : 'gap-4 px-3')} aria-label="Main">
      <Logo mini={mini} />
      {NAV.map((g) => (
        <div key={g.section}>
          {mini ? <div className="mx-2 mb-2 border-t border-slate-200 dark:border-ink-700" />
            : <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">{g.section}</div>}
          <ul className="space-y-0.5">
            {g.items.map((it) => (
              <li key={it.to}>
                <NavLink to={it.to} end={it.to === '/'} onClick={onNavigate} title={mini ? it.label : undefined} aria-label={mini ? it.label : undefined}
                  className={({ isActive }) => cx('flex items-center rounded-lg text-[13px] font-medium transition-colors [&>svg]:h-[18px] [&>svg]:w-[18px] [&>svg]:shrink-0 [&>svg]:transition-colors',
                    mini ? 'justify-center p-2.5' : 'gap-2.5 px-3 py-[7px]',
                    isActive ? 'bg-brand-50 font-semibold text-brand-700 shadow-[inset_0_0_0_1px_rgb(79_99_244/0.14)] [&>svg]:text-brand-600 dark:bg-brand-500/15 dark:text-white dark:shadow-[inset_0_0_0_1px_rgb(113_132_250/0.25)] dark:[&>svg]:text-brand-300'
                      : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 [&>svg]:text-slate-400 dark:text-slate-300 dark:hover:bg-ink-800 dark:hover:text-white dark:[&>svg]:text-slate-500')}>
                  {it.icon}{!mini && it.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div className="mt-auto space-y-2">
        {onToggle && (
          <button onClick={onToggle} className={cx('flex w-full items-center gap-2 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-ink-800', mini ? 'justify-center p-2.5' : 'px-3 py-2')}
            aria-label={mini ? 'Expand sidebar' : 'Collapse sidebar'} title={mini ? 'Expand sidebar' : 'Collapse sidebar'}>
            {mini ? <PanelLeftOpen className="h-4 w-4" /> : <><PanelLeftClose className="h-4 w-4" />Collapse</>}
          </button>
        )}
        {!mini && <p className="px-3 text-[10px] leading-relaxed text-slate-400">Educational research platform. Not investment advice. Prices are delayed unless marked LIVE.</p>}
      </div>
    </nav>
  )
}

// ------------------------------------------------------------------ breadcrumbs (derived from the URL)
const SECTION_LABEL: Record<string, [string, string]> = {
  explore: ['Explore', '/explore'], industries: ['Industries', '/industries'], markets: ['Market Tracker', '/markets'], company: ['Companies', '/explore'],
  research: ['Equity Research', '/research'], valuation: ['Valuation Lab', '/valuation'], screener: ['Screener', '/screener'], compare: ['Compare', '/compare'],
  news: ['News', '/news'], assistant: ['AI Assistant', '/assistant'], reports: ['Reports', '/reports'], watchlists: ['Watchlists', '/watchlists'],
  portfolio: ['Portfolio', '/portfolio'], invest: ['Virtual Invest', '/invest'], documents: ['Documents', '/documents'], learn: ['Learning Centre', '/learn'],
  guide: ['How to Use', '/guide'], settings: ['Settings', '/settings'], earnings: ['Earnings & Results', '/earnings'],
  'corporate-actions': ['Corporate Actions', '/corporate-actions'], 'data-quality': ['Data Quality', '/data-quality'],
}

function Breadcrumbs() {
  const loc = useLocation()
  const parts = loc.pathname.split('/').filter(Boolean)
  if (!parts.length || !SECTION_LABEL[parts[0]]) return null
  const crumbs: [string, string | null][] = [['Home', '/'], [SECTION_LABEL[parts[0]][0], parts.length > 1 ? SECTION_LABEL[parts[0]][1] : null]]
  if (parts[1]) {
    const raw = decodeURIComponent(parts[1])
    crumbs.push([parts[0] === 'industries' ? raw.replace(/-/g, ' ').replace(/^./, (c) => c.toUpperCase()) : raw.replace(/\.(NS|BO)$/, ''), null])
  }
  return (
    <nav aria-label="Breadcrumb" className="mb-3 flex min-w-0 items-center gap-1 text-xs muted">
      {crumbs.map(([label, to], i) => (
        <span key={i} className="flex min-w-0 items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3 shrink-0 opacity-60" />}
          {to ? <Link to={to} className="truncate hover:text-slate-800 hover:underline dark:hover:text-slate-200">{label}</Link>
            : <span className="truncate font-medium text-slate-700 dark:text-slate-200" aria-current="page">{label}</span>}
        </span>
      ))}
    </nav>
  )
}

function ExperienceSwitch() {
  const [exp, setExp] = useExperience()
  return (
    <span title="Simple: the essentials with plain-English explanations. Advanced: full statements, historical ratios, valuation models and technical indicators.">
      <Segmented size="xs" value={exp} onChange={setExp} options={[{ id: 'simple', label: 'Simple' }, { id: 'advanced', label: 'Advanced' }]} />
    </span>
  )
}

function Notifications() {
  const [open, setOpen] = useState(false)
  const inv = useInvalidate()
  const q = useQuery({ queryKey: ['notifications'], queryFn: () => api.get<{ unread: number; items: { id: number; title: string; body: string; ts: string; link: string; read: boolean }[] }>('/notifications'), refetchInterval: 120_000 })
  const read = useMutation({ mutationFn: () => api.post('/notifications/read'), onSuccess: () => inv('notifications') })
  return (
    <div className="relative">
      <button className="btn-ghost relative p-2" aria-label="Notifications" onClick={() => { setOpen((o) => !o); if (!open && q.data?.unread) read.mutate() }}>
        <Bell className="h-[18px] w-[18px]" />
        {!!q.data?.unread && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-saffron-500" />}
      </button>
      {open && (
        <div className="card absolute right-0 z-40 mt-2 w-80 p-2 shadow-[var(--shadow-pop)]" onMouseLeave={() => setOpen(false)}>
          <div className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide muted">Notifications</div>
          {(q.data?.items ?? []).length === 0 ? <p className="px-2 py-4 text-sm muted">No notifications. Create price alerts from any company page.</p> : (
            <ul className="max-h-80 overflow-y-auto">
              {q.data!.items.map((n) => (
                <li key={n.id}><Link to={n.link || '/watchlists'} onClick={() => setOpen(false)} className="block rounded-lg px-2 py-2 hover:bg-slate-100 dark:hover:bg-ink-700">
                  <div className="text-sm font-medium">{n.title}</div><div className="text-xs muted">{n.body}</div><div className="mt-0.5 text-[10px] muted">{timeAgo(n.ts)}</div>
                </Link></li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const [mini, setMini] = useState(() => { try { return localStorage.getItem('ep-sidebar') === 'mini' } catch { return false } })
  const toggleMini = () => setMini((m) => { try { localStorage.setItem('ep-sidebar', m ? 'full' : 'mini') } catch { /* storage unavailable */ } return !m })
  const [drawer, setDrawer] = useState(false)
  const [palette, setPalette] = useState(false)
  const [theme, setTheme] = useTheme()
  const me = useMe()
  const loc = useLocation()
  useEffect(() => { setDrawer(false); window.scrollTo(0, 0) }, [loc.pathname])
  useHotkey((e) => (e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)),
    (e) => { e.preventDefault(); setPalette(true) })
  const user = me.data?.user
  return (
    <div className="min-h-screen">
      <aside className={cx('fixed inset-y-0 left-0 z-30 hidden border-r border-slate-200/80 bg-white transition-[width] duration-200 lg:block dark:border-ink-700/80 dark:bg-ink-900', mini ? 'w-[68px]' : 'w-56')}>
        <Sidebar mini={mini} onToggle={toggleMini} />
      </aside>
      {drawer && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setDrawer(false)}>
          <div className="absolute inset-0 bg-ink-950/50" />
          <aside className="absolute inset-y-0 left-0 w-64 bg-white dark:bg-ink-900" onClick={(e) => e.stopPropagation()}>
            <button className="btn-ghost absolute right-2 top-3 p-2" onClick={() => setDrawer(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
            <Sidebar onNavigate={() => setDrawer(false)} />
            <div className="absolute bottom-16 left-4"><ExperienceSwitch /></div>
          </aside>
        </div>
      )}
      <div className={cx('transition-[padding] duration-200', mini ? 'lg:pl-[68px]' : 'lg:pl-56')}>
        <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/75 backdrop-blur-xl backdrop-saturate-150 dark:border-ink-700/80 dark:bg-ink-950/75">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-2 px-4 sm:px-6">
            <button className="btn-ghost p-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
            <button onClick={() => setPalette(true)} className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-xl border border-slate-200/90 bg-slate-100/60 px-3 text-left text-sm text-slate-400 shadow-[inset_0_1px_2px_rgb(16_24_40/0.04)] transition-all hover:border-slate-300 hover:bg-white hover:shadow-[0_1px_3px_rgb(16_24_40/0.06)] sm:max-w-md dark:border-ink-600 dark:bg-ink-850 dark:shadow-none dark:hover:bg-ink-800">
              <Search className="h-4 w-4 shrink-0" /><span className="flex-1 truncate"><span className="sm:hidden">Search…</span><span className="hidden sm:inline">Search 5,500+ companies, symbols, industries…</span></span>
              <kbd className="hidden rounded-md border border-slate-200 bg-white px-1.5 py-px text-[10px] font-semibold text-slate-500 shadow-[0_1px_0_rgb(16_24_40/0.06)] sm:inline dark:border-ink-600 dark:bg-ink-900 dark:text-slate-400">Ctrl K</kbd>
            </button>
            <div className="ml-auto flex shrink-0 items-center gap-1">
              <span className="mr-1 hidden lg:inline-flex"><ExperienceSwitch /></span>
              <span className="hidden sm:inline-flex md:hidden"><MarketClock compact /></span><span className="hidden md:inline-flex"><MarketClock /></span>
              <button className="btn-ghost p-2" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">
                {theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
              </button>
              <Notifications />
              <Link to="/settings" className="ml-1 flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-slate-100 dark:hover:bg-ink-800">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-linear-to-br from-brand-400 to-brand-700 text-xs font-bold text-white ring-2 ring-white dark:ring-ink-900">
                  {(user?.display_name ?? '?').slice(0, 1).toUpperCase()}
                </span>
                <span className="hidden text-sm font-medium md:inline">{user?.display_name ?? '…'}</span>
              </Link>
            </div>
          </div>
          <LiveTicker />
        </header>
        <main key={loc.pathname} className="page-enter mx-auto max-w-[1400px] px-4 pb-24 pt-5 sm:px-6 lg:pb-8"><Breadcrumbs /><ErrorBoundary key={loc.pathname}><Outlet /></ErrorBoundary></main>
      </div>
      <MobileTabBar />
      <SearchPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
