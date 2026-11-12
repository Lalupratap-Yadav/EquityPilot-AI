// Plain-English metric explanations: "what it means, why it matters, how to read it, example".
// Content comes from the backend (equitypilot/content/metrics_guide.py) so the web app, PDF reports
// and the assistant share one source of truth.
import { useQuery } from '@tanstack/react-query'
import { HelpCircle } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import { LinesChart } from './charts'
import { cx, Modal } from './ui'

export interface GuideEntry { what: string; why: string; read: string; example: string }
export interface Assessment { level: 'strong' | 'moderate' | 'weak'; text: string }

export function useMetricGuide() {
  return useQuery({
    queryKey: ['metric-guide'], staleTime: Infinity,
    queryFn: () => api.get<{ guide: Record<string, GuideEntry>; benchmark_note: string }>('/learn/metrics'),
  })
}

const LEVEL = {
  strong: { label: 'Strong', cls: 'bg-up/10 text-up' },
  moderate: { label: 'Moderate', cls: 'bg-amber-500/15 text-amber-700 dark:text-amber-300' },
  weak: { label: 'Weak', cls: 'bg-down/10 text-down' },
}

/** Rating chip. Always carries a text label so meaning never relies on colour alone. */
export function AssessChip({ a, className }: { a?: Assessment | null; className?: string }) {
  if (!a) return null
  const l = LEVEL[a.level]
  return <span title={a.text} className={cx('inline-flex shrink-0 items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide', l.cls, className)}>{l.label}</span>
}

export function ExplainBody({ guide, value, assessment, formula, history, benchmarkNote, fmt }: {
  guide?: GuideEntry; value?: ReactNode; assessment?: Assessment | null; formula?: string
  history?: { label: string; value: number | null }[]; benchmarkNote?: string; fmt?: (v: number) => string
}) {
  return (
    <div className="space-y-4 text-sm">
      {(value !== undefined || assessment) && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3 dark:bg-ink-800">
          {value !== undefined && <div><div className="text-[11px] font-semibold uppercase muted">This company (latest)</div><div className="num text-xl font-semibold">{value}</div></div>}
          {assessment && <div className="min-w-0 flex-1"><AssessChip a={assessment} /><p className="mt-1 text-xs text-slate-600 dark:text-slate-300">{assessment.text}</p></div>}
        </div>
      )}
      {guide ? (
        <dl className="space-y-3">
          {([['What it means', guide.what], ['Why it matters', guide.why], ['How to read it', guide.read], ['Example', guide.example]] as const).map(([k, v]) => (
            <div key={k}><dt className="text-[11px] font-semibold uppercase tracking-wide muted">{k}</dt><dd className="mt-0.5 leading-relaxed">{v}</dd></div>
          ))}
        </dl>
      ) : <p className="muted">No explanation available for this metric.</p>}
      {formula && <div><div className="text-[11px] font-semibold uppercase tracking-wide muted">Formula</div><p className="mt-1 rounded-lg bg-slate-50 px-3 py-2 font-mono text-xs dark:bg-ink-800">{formula}</p></div>}
      {history && history.filter((h) => h.value !== null).length > 1 && (
        <div><div className="text-[11px] font-semibold uppercase tracking-wide muted">History</div>
          <LinesChart data={history} xKey="label" series={[{ key: 'value', label: 'Value' }]} height={180} fmt={fmt} yFmt={fmt} /></div>
      )}
      {assessment && benchmarkNote && <p className="text-xs muted">{benchmarkNote}</p>}
    </div>
  )
}

/** A metric label that opens a full explanation when clicked. */
export function ExplainLabel({ metric, label, value, assessment, formula, history, className, fmt }: {
  metric: string; label: ReactNode; value?: ReactNode; assessment?: Assessment | null; formula?: string
  history?: { label: string; value: number | null }[]; className?: string; fmt?: (v: number) => string
}) {
  const [open, setOpen] = useState(false)
  const g = useMetricGuide()
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={cx('group inline-flex items-center gap-1 text-left hover:text-brand-600 dark:hover:text-brand-300', className)} aria-label={`Explain ${typeof label === 'string' ? label : metric}`}>
        <span className="underline decoration-slate-300 decoration-dotted underline-offset-4 group-hover:decoration-brand-500 dark:decoration-ink-600">{label}</span>
        <HelpCircle className="h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-brand-500" />
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={label} wide={!!history}>
        <ExplainBody guide={g.data?.guide[metric]} value={value} assessment={assessment} formula={formula} history={history} benchmarkNote={g.data?.benchmark_note} fmt={fmt} />
      </Modal>
    </>
  )
}
