// Data coverage of one company: which datasets exist, their source label, period and freshness.
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { timeAgo } from '../lib/format'
import { FreshPill, Meter, SourceLabel } from './status'

export interface CoverageItem { key: string; label: string; available: boolean; tier: string; period: string | null; fetched_at: string | null; state: string; note: string | null; applicable: boolean }
export interface Coverage { symbol: string; sample: boolean; items: CoverageItem[]; available: number; applicable: number; coverage_pct: number | null; basis: string | null
  basis_note: string | null; currency: string; units: string; checks: { level: string; check: string; detail: string }[] }

export function CoverageTable({ c }: { c: Coverage }) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        <div className="text-sm font-semibold">{c.available} of {c.applicable} datasets available</div>
        <Meter value={c.coverage_pct ?? 0} className="max-w-[180px]" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-sm">
          <thead><tr className="table-head"><th className="px-3 py-2 text-left">Dataset</th><th className="px-3 py-2 text-left">Label</th><th className="px-3 py-2 text-left">Period / extent</th><th className="px-3 py-2 text-left">Freshness</th><th className="px-3 py-2 text-left">Notes</th></tr></thead>
          <tbody>{c.items.map((i) => (
            <tr key={i.key} className="border-t border-slate-100 align-top dark:border-ink-700">
              <td className="px-3 py-2 font-medium">{i.label}</td>
              <td className="px-3 py-2">{i.applicable ? <SourceLabel tier={i.tier} /> : <span className="text-xs muted">—</span>}</td>
              <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{i.period ?? (i.available ? '—' : 'Not available')}</td>
              <td className="px-3 py-2"><FreshPill state={i.state} />{i.fetched_at && <div className="mt-0.5 text-[11px] muted">{timeAgo(i.fetched_at)}</div>}</td>
              <td className="px-3 py-2 text-xs muted">{i.note ?? ''}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="mt-3 text-xs muted">Amounts in {c.units}. {c.basis_note ?? (c.basis ? `Statements basis: ${c.basis}.` : '')}</p>
      {c.checks.length > 0 && (
        <div className="mt-4">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide muted">Consistency checks on the statements</div>
          <ul className="space-y-2">{c.checks.map((k) => (
            <li key={k.check} className="flex gap-2 text-sm">
              {k.level === 'info' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />}
              <span><b className="font-medium">{k.check}.</b> <span className="text-slate-600 dark:text-slate-300">{k.detail}</span></span></li>))}</ul>
        </div>
      )}
    </div>
  )
}
