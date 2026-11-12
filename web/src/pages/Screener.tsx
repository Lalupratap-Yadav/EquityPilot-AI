import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, Save, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CompanyAvatar, DataTable, type Column } from '../components/common'
import { Card, ChangePill, cx, DataBadge, Loading, Notice, PageHeader, useToast } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, byKind } from '../lib/format'
import { useInvalidate } from '../lib/hooks'

type Row = Record<string, string | number | boolean | null>
type Range = [number | null, number | null]
interface ScreenerResp { rows: Row[]; metrics: Record<string, { label: string; kind: string }>; presets: Record<string, Record<string, Range>>; industries: { id: string; name: string }[] }

const FILTER_KEYS = ['market_cap', 'pe', 'pb', 'ev_ebitda', 'roe', 'roce', 'debt_to_equity', 'revenue_growth', 'net_income_growth', 'revenue_cagr_3y', 'ebitda_margin', 'net_margin', 'dividend_yield', 'cfo_to_net_income', 'fcf_margin']
const SCALE: Record<string, number> = { pct: 100, cr: 1e-7 }    // display units: % and ₹ crore
const unit = (kind: string) => (kind === 'pct' ? '%' : kind === 'cr' ? '₹ Cr' : kind === 'x' ? 'x' : '')

export default function Screener() {
  const [params] = useSearchParams()
  const q = useQuery({ queryKey: ['screener'], queryFn: () => api.get<ScreenerResp>('/screener') })
  const saved = useQuery({ queryKey: ['screens'], queryFn: () => api.get<{ id: number; name: string; filters: { ranges: Record<string, Range>; industries: string[]; category: string } }[]>('/screens') })
  const [ranges, setRanges] = useState<Record<string, Range>>({})
  const [industries, setIndustries] = useState<string[]>([])
  const [category, setCategory] = useState('')
  const [keepMissing, setKeepMissing] = useState(false)
  const [samples, setSamples] = useState(false)
  const [name, setName] = useState('')
  const nav = useNavigate()
  const toast = useToast()
  const inv = useInvalidate()

  useEffect(() => {
    const p = params.get('preset')
    if (p && q.data?.presets[p]) setRanges(q.data.presets[p])
  }, [params, q.data])

  const metrics = q.data?.metrics ?? {}
  const rows = useMemo(() => (q.data?.rows ?? []).filter((r) => {
    if (!samples && r.is_sample) return false
    if (industries.length && !industries.includes(String(r.industry_id))) return false
    if (category && r.category !== category) return false
    return Object.entries(ranges).every(([k, [lo, hi]]) => {
      const v = r[k]
      if (lo == null && hi == null) return true
      if (typeof v !== 'number') return keepMissing
      return (lo == null || v >= lo) && (hi == null || v <= hi)
    })
  }), [q.data, ranges, industries, category, keepMissing, samples])

  const saveScreen = useMutation({ mutationFn: () => api.post('/screens', { name, filters: { ranges, industries, category } }), onSuccess: () => { toast('Screen saved'); setName(''); inv('screens') } })
  const delScreen = useMutation({ mutationFn: (id: number) => api.del(`/screens/${id}`), onSuccess: () => inv('screens') })

  const setBound = (k: string, i: 0 | 1, raw: string) => {
    const kind = metrics[k]?.kind
    const v = raw === '' ? null : Number(raw) / (SCALE[kind] ?? 1)
    setRanges((r) => { const cur: Range = [...(r[k] ?? [null, null])] as Range; cur[i] = v; return { ...r, [k]: cur } })
  }
  const shown = (k: string, i: 0 | 1) => { const v = ranges[k]?.[i]; return v == null ? '' : String(+(v * (SCALE[metrics[k]?.kind] ?? 1)).toFixed(4)) }

  const exportCsv = () => {
    const cols = ['symbol', 'name', 'industry', ...FILTER_KEYS]
    const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => JSON.stringify(r[c] ?? '')).join(','))].join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    a.download = 'equitypilot_screen.csv'
    a.click()
  }

  if (q.isLoading) return <Loading label="Computing metrics for the universe…" />
  const d = q.data!
  const active = Object.entries(ranges).filter(([, [lo, hi]]) => lo != null || hi != null)
  const cols: Column<Row>[] = [
    { key: 'name', label: 'Company', render: (r) => <span className="flex items-center gap-2"><CompanyAvatar symbol={String(r.symbol)} size="sm" /><span><span className="block font-medium">{String(r.name)}</span><span className="text-[11px] muted">{baseSymbol(String(r.symbol))} · {String(r.category ?? '').replace(' Cap', '')}</span></span>{r.is_sample ? <DataBadge type="sample" /> : null}</span> },
    { key: 'change_pct', label: 'Day', align: 'right', value: (r) => r.change_pct as number, render: (r) => <ChangePill value={r.change_pct as number} /> },
    ...['market_cap', 'pe', 'pb', 'roe', 'roce', 'debt_to_equity', 'revenue_growth', 'net_income_growth', 'net_margin', 'dividend_yield', 'piotroski'].map((k) => ({
      key: k, label: k === 'piotroski' ? 'F-score' : metrics[k]?.label.replace(' (latest FY)', '').replace(' (YoY)', ' YoY') ?? k, align: 'right' as const,
      value: (r: Row) => r[k] as number, render: (r: Row) => byKind(r[k], metrics[k]?.kind ?? 'num') })),
  ]

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Stock screener" title="Screen the universe" subtitle={`Filter ${d.rows.filter((r) => !r.is_sample).length} tracked companies on quality, growth, leverage and valuation. Ratios use each company's latest fiscal year; P/E uses trailing-twelve-month earnings where available.`} />
      <div className="grid gap-5 xl:grid-cols-4">
        <div className="space-y-4 xl:col-span-1">
          <Card title="Presets">
            <div className="flex flex-wrap gap-1.5">{Object.keys(d.presets).map((p) => <button key={p} className="chip" onClick={() => setRanges(d.presets[p])}>{p}</button>)}</div>
            {(saved.data ?? []).length > 0 && (<>
              <div className="mt-4 text-xs font-semibold uppercase muted">My saved screens</div>
              <ul className="mt-1.5 space-y-1">{saved.data!.map((s) => (
                <li key={s.id} className="flex items-center gap-1"><button className="flex-1 truncate rounded-lg px-2 py-1 text-left text-sm hover:bg-slate-100 dark:hover:bg-ink-700"
                  onClick={() => { setRanges(s.filters.ranges ?? {}); setIndustries(s.filters.industries ?? []); setCategory(s.filters.category ?? '') }}>{s.name}</button>
                  <button className="btn-ghost p-1" onClick={() => delScreen.mutate(s.id)} aria-label="Delete screen"><Trash2 className="h-3.5 w-3.5" /></button></li>))}</ul>
            </>)}
          </Card>
          <Card title="Filters" action={active.length > 0 && <button className="text-xs font-medium text-brand-600" onClick={() => { setRanges({}); setIndustries([]); setCategory('') }}>Clear all</button>}>
            <div className="space-y-2.5">
              {FILTER_KEYS.map((k) => metrics[k] && (
                <div key={k}><div className="label">{metrics[k].label} {unit(metrics[k].kind) && <span className="muted">({unit(metrics[k].kind)})</span>}</div>
                  <div className="flex gap-1.5"><input className="input num px-2 py-1.5" placeholder="min" value={shown(k, 0)} onChange={(e) => setBound(k, 0, e.target.value)} />
                    <input className="input num px-2 py-1.5" placeholder="max" value={shown(k, 1)} onChange={(e) => setBound(k, 1, e.target.value)} /></div></div>
              ))}
              <div><div className="label">Market-cap category (AMFI)</div>
                <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Any</option><option>Large Cap</option><option>Mid Cap</option><option>Small Cap</option></select></div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={keepMissing} onChange={(e) => setKeepMissing(e.target.checked)} />Keep companies with missing data</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={samples} onChange={(e) => setSamples(e.target.checked)} />Include fictional sample companies</label>
            </div>
          </Card>
        </div>
        <div className="space-y-4 xl:col-span-3">
          <div className="flex flex-wrap gap-1.5">{d.industries.map((i) => (
            <button key={i.id} className={cx('chip', industries.includes(i.id) && 'chip-active')} onClick={() => setIndustries((s) => (s.includes(i.id) ? s.filter((x) => x !== i.id) : [...s, i.id]))}>{i.name}</button>))}</div>
          {active.length > 0 && (
            <div className="flex flex-wrap gap-1.5">{active.map(([k, [lo, hi]]) => (
              <span key={k} className="chip chip-active">{metrics[k]?.label}: {lo != null ? `≥ ${byKind(lo, metrics[k]?.kind)}` : ''}{lo != null && hi != null ? ' & ' : ''}{hi != null ? `≤ ${byKind(hi, metrics[k]?.kind)}` : ''}
                <button onClick={() => setRanges((r) => { const n = { ...r }; delete n[k]; return n })} aria-label="Remove filter"><X className="h-3 w-3" /></button></span>))}</div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">{rows.length} companies match</h2>
            <div className="flex gap-2">
              <input className="input w-44" placeholder="Name this screen" value={name} onChange={(e) => setName(e.target.value)} />
              <button className="btn-outline" disabled={!name.trim()} onClick={() => saveScreen.mutate()}><Save className="h-4 w-4" />Save</button>
              <button className="btn-outline" onClick={exportCsv}><Download className="h-4 w-4" />CSV</button>
            </div>
          </div>
          {ranges.debt_to_equity && !keepMissing && <Notice>Banks and NBFCs have no debt/equity (not meaningful for lenders), so a D/E filter excludes them.</Notice>}
          <DataTable rows={rows} rowKey={(r) => String(r.symbol)} columns={cols} initialSort={{ key: 'market_cap', dir: 'desc' }} maxHeight={720} dense
            onRowClick={(r) => nav(`/company/${encodeURIComponent(String(r.symbol))}`)} />
          <p className="text-xs muted">Screens are tools to find companies to research - not recommendations. Data: Yahoo Finance (third-party, delayed) and EquityPilot calculations.</p>
        </div>
      </div>
    </div>
  )
}
