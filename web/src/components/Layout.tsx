import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Bell, BookOpen, Bot, Briefcase, Building2, Calculator, Compass, FileText, Filter, GitCompare, HelpCircle, Home, LineChart,
  Menu, Moon, Newspaper, PiggyBank, Search, Settings, Star, Sun, Telescope, UploadCloud, X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { timeAgo } from '../lib/format'
import { useHotkey, useInvalidate, useMe, useTheme } from '../lib/hooks'
import { SearchPalette } from './common'
import { LiveTicker, MarketClock, MobileTabBar } from './live'
import { cx } from './ui'

const NAV: { section: string; items: { to: string; label: string; icon: ReactNode }[] }[] = [
  { section: 'Discover', items: [
    { to: '/', label: 'Home', icon: <Home /> }, { to: '/explore', label: 'Explore', icon: <Compass /> },
    { to: '/industries', label: 'Industries', icon: <Building2 /> }, { to: '/markets', label: 'Market Tracker', icon: <LineChart /> },
  ] },
  { section: 'Research', items: [
    { to: '/research', label: 'Equity Research', icon: <Telescope /> }, { to: '/valuation', label: 'Valuation Lab', icon: <Calculator /> },
    { to: '/screener', label: 'Screener', icon: <Filter /> }, { to: '/compare', label: 'Compare', icon: <GitCompare /> },
    { to: '/news', label: 'News & Intelligence', icon: <Newspaper /> }, { to: '/assistant', label: 'AI Assistant', icon: <Bot /> },
    { to: '/reports', label: 'Reports', icon: <FileText /> },
  ] },
  { section: 'My space', items: [
    { to: '/watchlists', label: 'Watchlists', icon: <Star /> }, { to: '/portfolio', label: 'Portfolio', icon: <Briefcase /> },
    { to: '/invest', label: 'Virtual Invest', icon: <PiggyBank /> }, { to: '/documents', label: 'Documents', icon: <UploadCloud /> },
  ] },
  { section: 'Learn', items: [
    { to: '/learn', label: 'Learning Centre', icon: <BookOpen /> }, { to: '/guide', label: 'How to Use', icon: <HelpCircle /> },
    { to: '/settings', label: 'Settings', icon: <Settings /> },
  ] },
]

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-2" aria-label="EquityPilot AI home">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden><rect width="64" height="64" rx="16" fill="#3F5BF6" />
        <path d="M14 44 L28 30 L36 37 L50 20" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M42 19 L51 19 L51 28" fill="none" stroke="#FDBA4D" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" /></svg>
      <div className="leading-tight">
        <div className="text-[15px] font-bold tracking-tight text-slate-900 dark:text-white">EquityPilot <span className="text-brand-600 dark:text-brand-300">AI</span></div>
        <div className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Research smarter</div>
      </div>
    </Link>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex h-full flex-col gap-5 overflow-y-auto px-3 py-4" aria-label="Main">
      <Logo />
      {NAV.map((g) => (
        <div key={g.section}>
          <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">{g.section}</div>
          <ul className="space-y-0.5">
            {g.items.map((it) => (
              <li key={it.to}>
                <NavLink to={it.to} end={it.to === '/'} onClick={onNavigate}
                  className={({ isActive }) => cx('flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors [&>svg]:h-[18px] [&>svg]:w-[18px]',
                    isActive ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-ink-800 dark:hover:text-white')}>
                  {it.icon}{it.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <p className="mt-auto px-3 text-[10px] leading-relaxed text-slate-400">Educational research platform. Not investment advice. Prices are delayed unless marked LIVE.</p>
    </nav>
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
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-slate-200 bg-white lg:block dark:border-ink-700 dark:bg-ink-900"><Sidebar /></aside>
      {drawer && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setDrawer(false)}>
          <div className="absolute inset-0 bg-ink-950/50" />
          <aside className="absolute inset-y-0 left-0 w-64 bg-white dark:bg-ink-900" onClick={(e) => e.stopPropagation()}>
            <button className="btn-ghost absolute right-2 top-3 p-2" onClick={() => setDrawer(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
            <Sidebar onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur-md dark:border-ink-700 dark:bg-ink-950/80">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-2 px-4 sm:px-6">
            <button className="btn-ghost p-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
            <button onClick={() => setPalette(true)} className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 text-left text-sm text-slate-400 transition-colors hover:border-brand-300 sm:max-w-md dark:border-ink-600 dark:bg-ink-850">
              <Search className="h-4 w-4 shrink-0" /><span className="flex-1 truncate"><span className="sm:hidden">Search…</span><span className="hidden sm:inline">Search 5,500+ companies, symbols, industries…</span></span>
              <kbd className="hidden rounded-md border border-slate-200 px-1.5 text-[10px] font-semibold sm:inline dark:border-ink-600">Ctrl K</kbd>
            </button>
            <div className="ml-auto flex shrink-0 items-center gap-1">
              <span className="hidden sm:inline-flex md:hidden"><MarketClock compact /></span><span className="hidden md:inline-flex"><MarketClock /></span>
              <button className="btn-ghost p-2" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">
                {theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
              </button>
              <Notifications />
              <Link to="/settings" className="ml-1 flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-slate-100 dark:hover:bg-ink-800">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
                  {(user?.display_name ?? '?').slice(0, 1).toUpperCase()}
                </span>
                <span className="hidden text-sm font-medium md:inline">{user?.display_name ?? '…'}</span>
              </Link>
            </div>
          </div>
          <LiveTicker />
        </header>
        <main key={loc.pathname} className="page-enter mx-auto max-w-[1400px] px-4 pb-24 pt-6 sm:px-6 lg:pb-8"><Outlet /></main>
      </div>
      <MobileTabBar />
      <SearchPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
