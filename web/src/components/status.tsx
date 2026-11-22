// Small status labels shared by the Earnings, Corporate Actions, Data Quality and Health views.
import type { ReactNode } from 'react'
import { cx, DataBadge } from './ui'

export type Tone = 'good' | 'warn' | 'bad' | 'neutral' | 'info' | 'muted'

const TONES: Record<Tone, string> = {
  good: 'bg-up/10 text-up ring-up/20',
  warn: 'bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300',
  bad: 'bg-down/10 text-down ring-down/20',
  neutral: 'bg-slate-500/10 text-slate-600 ring-slate-500/15 dark:text-slate-300',
  info: 'bg-brand-500/10 text-brand-700 ring-brand-500/20 dark:text-brand-200',
  muted: 'bg-slate-500/5 text-slate-500 ring-slate-500/10 dark:text-slate-400',
}

export function Pill({ tone = 'neutral', children, title, className }: { tone?: Tone; children: ReactNode; title?: string; className?: string }) {
  return (
    <span title={title} className={cx('inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset', TONES[tone], className)}>
      {children}
    </span>
  )
}

const TIER_TO_TYPE: Record<string, string> = {
  OFFICIAL: 'official', 'THIRD-PARTY': 'third_party', DELAYED: 'delayed', HISTORICAL: 'historical', CALCULATED: 'calculated',
  ASSUMPTION: 'assumption', SAMPLE: 'sample', 'USER-ENTERED': 'user_entered',
}

/** OFFICIAL / SECONDARY / THIRD-PARTY / DELAYED / HISTORICAL / CALCULATED / ASSUMPTION / SAMPLE / USER-ENTERED. */
export function SourceLabel({ tier, className }: { tier?: string | null; className?: string }) {
  if (!tier) return null
  if (tier === 'SECONDARY') {
    return <span title="Established media publisher reporting on events" className={cx('inline-flex shrink-0 items-center whitespace-nowrap rounded-md bg-brand-500/10 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-brand-700 dark:text-brand-200', className)}>SECONDARY</span>
  }
  return <DataBadge type={TIER_TO_TYPE[tier] ?? tier.toLowerCase()} className={className} />
}

const FRESH: Record<string, [Tone, string]> = {
  fresh: ['good', 'Fresh'], ageing: ['warn', 'Ageing'], stale: ['bad', 'Stale'], failing: ['bad', 'Failing'], missing: ['muted', 'Missing'],
  not_applicable: ['muted', 'Not applicable'],
}

export function FreshPill({ state }: { state: string }) {
  const [tone, label] = FRESH[state] ?? ['neutral', state]
  return <Pill tone={tone}>{label}</Pill>
}

/** Thin horizontal meter, e.g. data coverage. */
export function Meter({ value, className }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(1, value))
  return (
    <div className={cx('h-1.5 w-full overflow-hidden rounded-full bg-slate-200/80 dark:bg-ink-700', className)} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(v * 100)}>
      <div className={cx('h-full rounded-full', v >= 0.75 ? 'bg-up' : v >= 0.5 ? 'bg-amber-500' : 'bg-down')} style={{ width: `${v * 100}%` }} />
    </div>
  )
}
