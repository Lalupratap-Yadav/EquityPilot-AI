// Company page: Financial Health - seven areas, each with its metrics, formulas and the rule used to rate them.
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, HeartPulse } from 'lucide-react'
import { useState } from 'react'
import { Pill, type Tone } from '../../components/status'
import { Card, cx, EmptyState, Loading, Notice, SourceNote } from '../../components/ui'
import { api } from '../../lib/api'
import { mult, num, pct } from '../../lib/format'

interface Metric { key: string; label: string; value: number | null; unit: string; period: string | null; formula: string | null; rating: string | null
  rating_label: string | null; rating_text: string | null; rated: boolean; missing: boolean; note: string | null }
interface Area { key: string; title: string; question: string; status: string; status_label: string; explain: string; metrics: Metric[]; rated_count: number; points: number | null }
interface Health { symbol: string; is_financial: boolean; latest_fy: string | null; basis: string | null; sources: string[]; fetched_at: string | null; areas: Area[]
  areas_with_data: number; areas_rateable: number; method: string[]; benchmark_note: string }

const STATUS_TONE: Record<string, Tone> = { strong: 'good', adequate: 'warn', weak: 'bad', insufficient: 'muted', not_applicable: 'muted', context: 'info' }
const RATING_TONE: Record<string, Tone> = { strong: 'good', good: 'good', moderate: 'warn', warning: 'warn', weak: 'bad', serious: 'bad', critical: 'bad' }
const ACCENT: Record<string, string> = { strong: 'before:bg-up', adequate: 'before:bg-amber-500', weak: 'before:bg-down', context: 'before:bg-brand-500', insufficient: 'before:bg-slate-300 dark:before:bg-ink-600', not_applicable: 'before:bg-slate-300 dark:before:bg-ink-600' }

function fmt(m: Metric): string {
  if (m.value === null) return '—'
  if (m.unit === 'pct') return pct(m.value, 1)
  if (m.unit === 'pct_points') return `${num(m.value, 2)}%`
  if (m.unit === 'count') return `${m.value} of 3 years`
  return mult(m.value, 2)
}

function AreaCard({ a }: { a: Area }) {
  const [open, setOpen] = useState(false)
  return (
    <section className={cx('card relative overflow-hidden p-4 before:absolute before:inset-y-0 before:left-0 before:w-1 sm:p-5', ACCENT[a.status])}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold">{a.title}</h3>
          <p className="text-xs muted">{a.question}</p>
        </div>
        <Pill tone={STATUS_TONE[a.status] ?? 'neutral'}>{a.status_label}</Pill>
      </div>
      {a.metrics.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {a.metrics.map((m) => (
            <li key={m.key} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="min-w-0 truncate text-slate-600 dark:text-slate-300" title={m.formula ?? undefined}>{m.label}</span>
              <span className="flex shrink-0 items-center gap-2">
                <span className={cx('num font-semibold', m.missing && 'font-normal muted')}>{fmt(m)}</span>
                {m.rating && <Pill tone={RATING_TONE[m.rating] ?? 'neutral'}>{m.rating_label}</Pill>}
              </span>
            </li>))}
        </ul>
      ) : <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{a.explain}</p>}
      {a.metrics.length > 0 && (
        <>
          <button className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => setOpen(!open)} aria-expanded={open}>
            How this is calculated<ChevronDown className={cx('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} /></button>
          {open && (
            <div className="mt-2 space-y-2 rounded-lg bg-slate-50 p-3 text-xs dark:bg-ink-900/50">
              <p className="font-medium">{a.explain}</p>
              {a.metrics.map((m) => (
                <div key={m.key}>
                  <div className="font-semibold">{m.label}{m.period ? <span className="font-normal muted"> · {m.period}</span> : null}</div>
                  {m.formula && <div className="muted">{m.formula}</div>}
                  {m.rating_text && <div>{m.rating_text}</div>}
                  {!m.rated && !m.missing && m.key !== 'pe' && m.key !== 'pb' && <div className="muted">Shown without a rating: no fair general benchmark.</div>}
                  {m.note && <div className="muted">{m.note}</div>}
                  {m.missing && !m.note && <div className="muted">Not available for the latest period.</div>}
                </div>))}
            </div>)}
        </>
      )}
    </section>
  )
}

export function HealthTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['health', symbol], queryFn: () => api.get<Health>(`/companies/${encodeURIComponent(symbol)}/health`) })
  if (q.isLoading) return <Loading label="Checking financial health…" />
  if (!q.data) return <EmptyState icon={<HeartPulse className="h-5 w-5" />} title="Financial health unavailable" body="The provider has not returned enough statement data for this company." />
  const d = q.data
  return (
    <div className="space-y-5">
      <Card title="Financial health" subtitle={`${d.areas_with_data} of ${d.areas_rateable} areas have enough data to rate · latest fiscal year ${d.latest_fy ?? 'n/a'}${d.is_financial ? ' · bank / NBFC framework' : ''}`}>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          A rule-based check of the latest annual figures. Each area shows the metrics behind it and the rule used to rate them; there is no single overall score.
        </p>
        {d.is_financial && <Notice className="mt-3">Banks and NBFCs are judged on asset quality, capital and funding. Those figures come from the bank's own quarterly disclosures and are entered on the Bank metrics tab (Advanced mode).</Notice>}
      </Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{d.areas.map((a) => <AreaCard key={a.key} a={a} />)}</div>
      <Card title="Method">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-600 dark:text-slate-300">{d.method.map((m) => <li key={m}>{m}</li>)}</ul>
        <SourceNote sources={[...d.sources, 'EquityPilot calculations (CALCULATED)']} time={d.fetched_at} extra={d.benchmark_note} />
      </Card>
    </div>
  )
}
