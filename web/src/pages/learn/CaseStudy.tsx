import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { cx, DataBadge, ErrorState, Loading, Notice } from '../../components/ui'
import { api } from '../../lib/api'
import { baseSymbol, crore, mult, pct } from '../../lib/format'

interface CaseRatio { key: string; name: string; value: number; kind: 'pct' | 'mult' | 'inr'; formula: string; steps: string }
interface CaseData {
  symbol: string; name: string; industry?: string; available: boolean; note?: string; financial?: boolean; sample?: boolean
  period?: string; previous_period?: string | null; basis?: string; basis_note?: string; source?: string; source_urls?: string[]
  data_types?: string[]; fetched_at?: string | null; figures?: { key: string; label: string; value: number; previous: number | null }[]
  ratios?: CaseRatio[]; notes?: string[]; reading?: string | null; links: Record<string, string>
  labels?: { facts: string; calculations: string; interpretation: string }
}

const fmt = (r: CaseRatio) => (r.kind === 'pct' ? pct(r.value, 1) : r.kind === 'mult' ? mult(r.value, 2) : crore(r.value, false))

/** Real-company case study from EquityPilot's stored statements, with period, source, basis and every calculation shown. */
export function CaseStudy({ symbols, names }: { symbols: string[]; names: Record<string, string> }) {
  const [sym, setSym] = useState(symbols[0])
  const q = useQuery({ queryKey: ['learn-case', sym], queryFn: () => api.get<CaseData>(`/learn/case/${encodeURIComponent(sym)}`), staleTime: 10 * 60_000 })
  const d = q.data
  return (
    <div className="space-y-4" data-testid="case-study">
      <div role="tablist" aria-label="Case study company" className="flex flex-wrap gap-1.5">
        {symbols.map((s) => <button key={s} role="tab" aria-selected={s === sym} className={cx('chip', s === sym && 'chip-active')} onClick={() => setSym(s)}>{names[s] ?? baseSymbol(s)}</button>)}
      </div>
      {q.isLoading ? <Loading /> : q.error || !d ? <ErrorState error={q.error} retry={q.refetch} /> : !d.available ? (
        <Notice tone="warn">{d.note} <Link className="font-medium underline" to={`/company/${encodeURIComponent(d.symbol)}`}>Open {d.name}</Link></Notice>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="font-semibold">{d.name} <span className="font-normal muted">· {d.industry}</span></div>
              <div className="mt-0.5 text-xs muted">Financial year <b>{d.period}</b>{d.previous_period ? ` (averages use ${d.previous_period} and ${d.period})` : ''} · source: {d.source}{d.fetched_at ? ` · fetched ${d.fetched_at}` : ''}</div>
            </div>
            <div className="flex gap-1.5">{(d.data_types ?? []).map((t) => <DataBadge key={t} type={t} />)}{d.sample && <DataBadge type="sample" />}</div>
          </div>
          <Notice tone="info" className="text-[13px]">{d.basis_note} Verify important figures against the annual report before relying on them.</Notice>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h4 className="text-sm font-semibold">Reported figures <span className="font-normal muted">(facts from the source)</span></h4>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[320px] text-sm">
                  <thead><tr className="text-left text-[11px] uppercase tracking-wide muted"><th className="py-1.5 pr-2 font-semibold">Item</th><th className="py-1.5 pr-2 text-right font-semibold">{d.period}</th><th className="py-1.5 text-right font-semibold">{d.previous_period ?? ''}</th></tr></thead>
                  <tbody>{(d.figures ?? []).map((f) => (
                    <tr key={f.key} className="border-t border-slate-100 dark:border-ink-700"><td className="py-1.5 pr-2">{f.label}</td><td className="num py-1.5 pr-2 text-right">{crore(f.value, false)}</td><td className="num py-1.5 text-right muted">{f.previous !== null ? crore(f.previous, false) : ''}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold">Ratios <span className="font-normal muted">(calculated by EquityPilot, inputs shown)</span></h4>
              <ul className="mt-2 space-y-2">{(d.ratios ?? []).map((r) => (
                <li key={r.key} className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-ink-800">
                  <div className="flex items-baseline justify-between gap-2"><span className="text-sm font-medium">{r.name}</span><span className="num font-semibold">{fmt(r)}</span></div>
                  <div className="text-[11px] muted">{r.formula}</div>
                  <div className="mt-0.5 font-mono text-[12px] break-words">{r.steps}</div>
                </li>
              ))}</ul>
            </div>
          </div>
          {(d.notes ?? []).map((n) => <Notice key={n} tone="warn" className="text-[13px]">{n}</Notice>)}
          {d.reading && <p className="text-sm"><span className="font-semibold">Reading note (educational interpretation): </span>{d.reading}</p>}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
            <Link to={`/company/${encodeURIComponent(d.symbol)}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">Open the {baseSymbol(d.symbol)} company page</Link>
            {Object.entries(d.links).map(([label, url]) => <a key={label} href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-700 hover:underline dark:text-brand-300">{label}<ExternalLink className="h-3 w-3" /></a>)}
          </div>
          <p className="text-[11px] muted">Figures in ₹ crore. This case study is for learning and is not a view on the shares.</p>
        </div>
      )}
    </div>
  )
}
