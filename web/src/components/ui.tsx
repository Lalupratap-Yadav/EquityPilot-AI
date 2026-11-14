import clsx from 'clsx'
import { Info, Loader2, X } from 'lucide-react'
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { ist, isNum, pct } from '../lib/format'

export const cx = clsx

// ------------------------------------------------------------------ layout primitives
export function PageHeader({ title, subtitle, actions, eyebrow }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-300">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Card({ title, action, children, className, pad = true, subtitle }: {
  title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; pad?: boolean; subtitle?: ReactNode
}) {
  return (
    <section className={cx('card', className)}>
      {(title || action) && (
        <header className={cx('flex flex-wrap items-start justify-between gap-x-3 gap-y-2', pad ? 'px-4 pt-4 sm:px-5' : 'px-4 pt-4')}>
          <div className="min-w-0">
            {title && <h2 className="section-title">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={pad ? 'card-pad' : ''}>{children}</div>
    </section>
  )
}

// ------------------------------------------------------------------ data labels
const STATUS: Record<string, [string, string, string]> = {
  live: ['LIVE', 'bg-up/10 text-up', 'Real-time price from a licensed feed'],
  delayed: ['DELAYED', 'bg-brand-500/10 text-brand-700 dark:text-brand-200', 'Third-party price, typically ~15 minutes delayed'],
  close: ['LAST CLOSE', 'bg-slate-500/10 text-slate-600 dark:text-slate-300', 'Market closed or data not fresh: last available price'],
  historical: ['HISTORICAL', 'bg-slate-500/10 text-slate-600 dark:text-slate-300', 'End-of-day historical data'],
  sample: ['SAMPLE', 'bg-saffron-500/15 text-amber-700 dark:text-saffron-400', 'Fictional demonstration data'],
  third_party: ['THIRD-PARTY', 'bg-slate-500/10 text-slate-600 dark:text-slate-300', 'Secondary data provider - verify with filings'],
  official_upload: ['OFFICIAL (UPLOADED)', 'bg-up/10 text-up', 'Entered from an official filing'],
  official: ['OFFICIAL', 'bg-up/10 text-up', 'Primary source: exchange, regulator or government publication'],
  user_entered: ['USER-ENTERED', 'bg-violet-500/10 text-violet-700 dark:text-violet-300', 'Entered by a user'],
  calculated: ['CALCULATED', 'bg-slate-500/10 text-slate-600 dark:text-slate-300', 'Computed by EquityPilot'],
  assumption: ['ASSUMPTION', 'bg-orange-500/10 text-orange-700 dark:text-orange-300', 'Editable assumption, not a reported figure'],
  unavailable: ['NO DATA', 'bg-slate-500/10 text-slate-500', 'No price available'],
  editorial: ['EDITORIAL', 'bg-slate-500/10 text-slate-600 dark:text-slate-300', 'General educational background, not real-time'],
}

export function DataBadge({ type, className }: { type?: string | null; className?: string }) {
  if (!type) return null
  const [label, cls, tip] = STATUS[type] ?? [type.toUpperCase(), 'bg-slate-500/10 text-slate-600', '']
  return <span title={tip} className={cx('inline-flex shrink-0 items-center whitespace-nowrap rounded-md px-1.5 py-0.5 text-[10px] font-semibold tracking-wide', cls, className)}>{label}</span>
}

const TIERS: Record<string, { label: string; title: string; cls: string }> = {
  primary: { label: 'Official', title: 'Primary source: exchange, regulator or government publication', cls: 'bg-up/10 text-up' },
  established: { label: 'Secondary', title: 'Secondary reporting by an established news organisation - verify material facts against the official filing', cls: 'bg-brand-500/10 text-brand-700 dark:text-brand-200' },
  unrated: { label: 'Unrated', title: 'Publisher not classified as an established news organisation - treat with caution', cls: 'bg-orange-500/10 text-orange-700 dark:text-orange-300' },
  sample: { label: 'Sample', title: 'Fictional sample data', cls: 'bg-saffron-500/15 text-amber-800 dark:text-amber-200' },
  user: { label: 'Your entry', title: 'Entered by you', cls: 'bg-slate-500/10 text-slate-600 dark:text-slate-300' },
}

/** Source reliability badge shown on every news item. */
export function TierBadge({ tier }: { tier?: string | null }) {
  const t = TIERS[tier ?? '']
  if (!t) return null
  return <span title={t.title} className={cx('rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide', t.cls)}>{t.label}</span>
}

export function ChangePill({ value, className, size = 'sm' }: { value: number | null | undefined; className?: string; size?: 'sm' | 'md' }) {
  if (!isNum(value)) return <span className={cx('muted', className)}>—</span>
  const up = value > 0, flat = value === 0
  return (
    <span className={cx('num inline-flex shrink-0 items-center whitespace-nowrap rounded-md font-semibold', size === 'md' ? 'px-2 py-0.5 text-sm' : 'px-1.5 py-0.5 text-xs',
      flat ? 'bg-slate-500/10 text-slate-500' : up ? 'bg-up/10 text-up' : 'bg-down/10 text-down', className)}>
      {up ? '▲' : flat ? '' : '▼'} {pct(Math.abs(value), 2)}
    </span>
  )
}

export function Stat({ label, value, sub, help, tone }: { label: ReactNode; value: ReactNode; sub?: ReactNode; help?: string; tone?: 'up' | 'down' }) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-200/70 bg-white px-3.5 py-3 shadow-[0_1px_2px_rgb(16_24_40/0.04)] dark:border-ink-700/80 dark:bg-ink-850 dark:shadow-none">
      <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide muted">
        <span className="truncate">{label}</span>{help && <InfoTip text={help} />}
      </div>
      <div className={cx('num mt-1 truncate text-lg font-semibold', tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-slate-900 dark:text-white')}>{value}</div>
      {sub && <div className="mt-0.5 truncate text-xs muted">{sub}</div>}
    </div>
  )
}

export function InfoTip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <Info className="h-3.5 w-3.5 cursor-help text-slate-400" aria-label={text} />
      <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-64 -translate-x-1/2 rounded-lg bg-ink-900 px-2.5 py-2 text-[11px] font-normal normal-case leading-snug tracking-normal text-white shadow-[var(--shadow-pop)] group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  )
}

export function SourceNote({ sources, time, extra, className }: { sources?: (string | null | undefined)[]; time?: string | null; extra?: ReactNode; className?: string }) {
  const s = (sources ?? []).filter(Boolean)
  return (
    <p className={cx('mt-3 border-t border-dashed border-slate-200 pt-2 text-[11px] leading-relaxed muted dark:border-ink-700', className)}>
      {s.length > 0 && <><span className="font-semibold">Source:</span> {s.join('; ')}</>}
      {time && <> · <span className="font-semibold">Updated:</span> {ist(time)}</>}
      {extra && <> · {extra}</>}
    </p>
  )
}

// ------------------------------------------------------------------ states
export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton', className ?? 'h-4 w-full')} />
}

export function Loading({ label = 'Loading…', className }: { label?: string; className?: string }) {
  return <div className={cx('flex items-center justify-center gap-2 py-10 text-sm muted', className)}><Loader2 className="h-4 w-4 animate-spin" />{label}</div>
}

export function EmptyState({ icon, title, body, action }: { icon?: ReactNode; title: string; body?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300/90 bg-slate-50/60 px-6 py-10 text-center dark:border-ink-600 dark:bg-ink-900/40">
      {icon && <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-white text-slate-400 shadow-[var(--shadow-card)] ring-1 ring-slate-200/70 dark:bg-ink-800 dark:ring-ink-700">{icon}</div>}
      <div className="font-semibold text-slate-800 dark:text-slate-100">{title}</div>
      {body && <div className="mt-1 max-w-md text-sm muted">{body}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="rounded-2xl border border-down/30 bg-down/5 px-4 py-4 text-sm text-down">
      <div className="font-semibold">Couldn't load this section</div>
      <div className="mt-0.5 opacity-90">{error instanceof Error ? error.message : 'Unknown error'}</div>
      {retry && <button className="btn-outline mt-3" onClick={retry}>Try again</button>}
    </div>
  )
}

export function Notice({ tone = 'info', children, className }: { tone?: 'info' | 'warn' | 'sample' | 'success'; children: ReactNode; className?: string }) {
  const cls = { info: 'border-brand-500/30 bg-brand-500/5', warn: 'border-orange-400/40 bg-orange-500/5', sample: 'border-saffron-500/40 bg-saffron-500/10', success: 'border-up/30 bg-up/5' }[tone]
  return <div className={cx('rounded-xl border px-3.5 py-2.5 text-sm leading-relaxed text-slate-700 dark:text-slate-200', cls, className)}>{children}</div>
}

// ------------------------------------------------------------------ controls
export function Tabs<T extends string>({ tabs, value, onChange, className }: { tabs: { id: T; label: ReactNode }[]; value: T; onChange: (t: T) => void; className?: string }) {
  return (
    <div role="tablist" className={cx('flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-ink-700', className)}>
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cx('-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
            value === t.id ? 'border-brand-600 text-slate-900 dark:border-brand-400 dark:text-white' : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800 dark:hover:border-ink-600 dark:hover:text-slate-200')}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

export function Segmented<T extends string>({ options, value, onChange, size = 'sm' }: { options: { id: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; size?: 'sm' | 'xs' }) {
  return (
    <div className="inline-flex rounded-xl bg-slate-100/90 p-0.5 shadow-[inset_0_1px_2px_rgb(16_24_40/0.05)] dark:bg-ink-800 dark:shadow-none">
      {options.map((o) => (
        <button key={o.id} onClick={() => onChange(o.id)}
          className={cx('rounded-[10px] font-medium transition-all', size === 'xs' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm',
            value === o.id ? 'bg-white text-slate-900 shadow-[0_1px_2px_rgb(16_24_40/0.08),0_0_0_1px_rgb(16_24_40/0.04)] dark:bg-ink-600 dark:text-white dark:shadow-none' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink-950/50 p-4 pt-[10vh] backdrop-blur-sm" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" className={cx('card page-enter w-full', wide ? 'max-w-3xl' : 'max-w-md')} onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5 dark:border-ink-700">
          <h3 className="font-semibold">{title}</h3>
          <button className="btn-ghost -mr-2 p-1.5" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ toasts
type ToastItem = { id: number; text: ReactNode; tone: 'success' | 'error' | 'info' }
const ToastCtx = createContext<(text: ReactNode, tone?: ToastItem['tone']) => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const push = useCallback((text: ReactNode, tone: ToastItem['tone'] = 'success') => {
    const id = Date.now() + Math.random()
    setItems((s) => [...s, { id, text, tone }])
    window.setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex max-w-sm flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cx('page-enter rounded-xl px-4 py-3 text-sm font-medium shadow-[var(--shadow-pop)]',
            t.tone === 'error' ? 'bg-down text-white' : t.tone === 'info' ? 'bg-ink-800 text-white' : 'bg-ink-900 text-white')}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => useContext(ToastCtx)
