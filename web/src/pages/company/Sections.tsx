import { useMutation, useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BarsChart, Donut, LinesChart } from '../../components/charts'
import { StockChart, type LiveQuote } from '../../components/StockChart'
import { DataTable, type Column } from '../../components/common'
import { Card, ChangePill, cx, DataBadge, EmptyState, Loading, Notice, SourceNote, Stat, TierBadge, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { baseSymbol, crore, inr, isNum, mult, num, pct, timeAgo } from '../../lib/format'
import { useInvalidate } from '../../lib/hooks'

// ------------------------------------------------------------------ chart
export function ChartTab({ symbol, compact, live }: { symbol: string; compact?: boolean; live?: LiveQuote | null }) {
  return (
    <Card title={compact ? 'Price' : undefined}>
      <StockChart symbol={symbol} compact={compact} live={live} fullLink={compact ? `/company/${encodeURIComponent(symbol)}?tab=chart` : undefined} />
    </Card>
  )
}

// ------------------------------------------------------------------ quarterly
interface QRow { period: string; label: string; revenue: number | null; ebitda: number | null; net_income: number | null; eps: number | null; revenue_qoq: number | null; revenue_yoy: number | null; net_income_yoy: number | null; ebitda_margin: number | null; net_margin: number | null }

export function QuarterlyTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['quarterly', symbol], queryFn: () => api.get<{ empty?: boolean; quarters: QRow[]; missing: string[]; currency: string; sources: string[]; fetched_at: string }>(`/companies/${encodeURIComponent(symbol)}/quarterly`) })
  if (q.isLoading) return <Loading />
  if (!q.data || q.data.empty) return <EmptyState title="No quarterly results stored" body="Refresh the company, or upload quarterly figures in Documents." />
  const d = q.data, last = d.quarters[d.quarters.length - 1]
  const div = d.currency === 'INR' ? 1e7 : 1e6, unit = d.currency === 'INR' ? '₹ Cr' : `${d.currency} mn`
  return (
    <div className="space-y-5">
      <div><h3 className="section-title">Latest quarter: {last.label}</h3><p className="text-xs muted">Quarter ended {last.period}. Quarterly results are typically limited-review (unaudited) when published.</p></div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Revenue" value={isNum(last.revenue) ? `${num(last.revenue / div, 0)} ${unit}` : '—'} sub={`YoY ${pct(last.revenue_yoy, 1, true)} · QoQ ${pct(last.revenue_qoq, 1, true)}`} />
        <Stat label="Net profit" value={isNum(last.net_income) ? `${num(last.net_income / div, 0)} ${unit}` : '—'} sub={`YoY ${pct(last.net_income_yoy, 1, true)}`} />
        <Stat label="EBITDA margin" value={pct(last.ebitda_margin)} /><Stat label="Net margin" value={pct(last.net_margin)} /><Stat label="Diluted EPS" value={num(last.eps)} />
      </div>
      {d.missing.length > 0 && <Notice tone="warn">Not provided by the source: {d.missing.join(', ')}. Growth that needs these quarters is left blank.</Notice>}
      <Card title={`Quarterly revenue and net profit (${unit})`}>
        <BarsChart data={d.quarters.map((r) => ({ label: r.label, Revenue: isNum(r.revenue) ? r.revenue / div : null, 'Net profit': isNum(r.net_income) ? r.net_income / div : null }))}
          xKey="label" series={[{ key: 'Revenue', label: 'Revenue' }, { key: 'Net profit', label: 'Net profit' }]} fmt={(v) => num(v, 0)} yFmt={(v) => num(v, 0)} />
        <SourceNote sources={d.sources} time={d.fetched_at} />
      </Card>
      <DataTable rows={[...d.quarters].reverse()} rowKey={(r) => r.period} columns={[
        { key: 'label', label: 'Quarter' },
        { key: 'revenue', label: `Revenue (${unit})`, align: 'right', render: (r) => (isNum(r.revenue) ? num(r.revenue / div, 0) : '—') },
        { key: 'revenue_yoy', label: 'YoY', align: 'right', render: (r) => <ChangePill value={r.revenue_yoy} /> },
        { key: 'revenue_qoq', label: 'QoQ', align: 'right', render: (r) => pct(r.revenue_qoq, 1, true) },
        { key: 'ebitda_margin', label: 'EBITDA margin', align: 'right', render: (r) => pct(r.ebitda_margin) },
        { key: 'net_income', label: `Net profit (${unit})`, align: 'right', render: (r) => (isNum(r.net_income) ? num(r.net_income / div, 0) : '—') },
        { key: 'net_income_yoy', label: 'Profit YoY', align: 'right', render: (r) => <ChangePill value={r.net_income_yoy} /> },
        { key: 'eps', label: 'EPS', align: 'right', render: (r) => num(r.eps) },
      ]} />
    </div>
  )
}

// ------------------------------------------------------------------ technicals
export function TechnicalsTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['tech', symbol], queryFn: () => api.get<{ empty?: boolean; readings: { Indicator: string; Value: string; Reading: string; tone: string }[]; stats: Record<string, number | null>; source: string; period: string[] }>(`/companies/${encodeURIComponent(symbol)}/technicals`) })
  if (q.isLoading) return <Loading />
  if (!q.data || q.data.empty) return <EmptyState title="Not enough price history" />
  const s = q.data.stats
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <Stat label="1M" value={pct(s.r1m, 1, true)} tone={(s.r1m ?? 0) >= 0 ? 'up' : 'down'} /><Stat label="3M" value={pct(s.r3m, 1, true)} tone={(s.r3m ?? 0) >= 0 ? 'up' : 'down'} />
        <Stat label="1Y" value={pct(s.r1y, 1, true)} tone={(s.r1y ?? 0) >= 0 ? 'up' : 'down'} /><Stat label="3Y" value={pct(s.r3y, 1, true)} tone={(s.r3y ?? 0) >= 0 ? 'up' : 'down'} />
        <Stat label="Volatility 1Y" value={pct(s.vol1y)} help="Annualised std. dev. of daily returns" /><Stat label="Max DD 1Y" value={pct(s.mdd1y)} />
        <Stat label="Beta vs NIFTY" value={num(s.beta)} help="Cov(stock, index) / Var(index), last 12 months" /><Stat label="ATR (14)" value={inr(s.atr)} />
      </div>
      <Card title="Indicator readings (latest)" subtitle="Descriptive readings of past price behaviour - not buy/sell signals">
        <ul className="divide-y divide-slate-100 dark:divide-ink-700">
          {q.data.readings.map((r) => (
            <li key={r.Indicator} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <span className="font-medium">{r.Indicator}</span><span className="flex-1 text-right muted">{r.Reading}</span>
              <span className={cx('num w-20 text-right font-semibold', r.tone === 'good' ? 'text-up' : r.tone === 'warning' ? 'text-orange-600' : '')}>{r.Value}</span>
            </li>
          ))}
        </ul>
        <SourceNote sources={[q.data.source]} extra={`Daily data ${q.data.period.join(' to ')}`} />
      </Card>
      <ChartTab symbol={symbol} />
    </div>
  )
}

// ------------------------------------------------------------------ risk
const LEVEL: Record<string, [string, string]> = { good: ['LOW', 'bg-up/10 text-up'], warning: ['MODERATE', 'bg-amber-500/15 text-amber-700 dark:text-amber-300'],
  serious: ['ELEVATED', 'bg-orange-500/15 text-orange-700 dark:text-orange-300'], critical: ['HIGH', 'bg-down/10 text-down'],
  na: ['N/A', 'bg-slate-500/10 text-slate-500'], info: ['INFO', 'bg-slate-500/10 text-slate-500'] }

export function RiskTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['risk', symbol], queryFn: () => api.get<{ flags: { category: string; title: string; level: string; value: string; rule: string; detail: string }[]; summary: { Category: string; Level: string; Checks: number }[]; score: number | null; altman: { z: number | null; zone: string | null }; sector_considerations: string[]; regulatory: string[] }>(`/companies/${encodeURIComponent(symbol)}/risk`) })
  if (q.isLoading) return <Loading />
  const d = q.data!
  const band = d.score == null ? '—' : d.score < 25 ? 'Low' : d.score < 45 ? 'Moderate' : d.score < 65 ? 'Elevated' : 'High'
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <div className="card card-pad md:col-span-1">
          <div className="text-xs font-semibold uppercase muted">Composite risk score</div>
          <div className="num mt-1 text-4xl font-semibold">{d.score == null ? '—' : d.score.toFixed(0)}<span className="text-base muted">/100</span></div>
          <div className="mt-1 text-sm">{band} · lower is better</div>
          <div className="mt-3 h-2 rounded-full bg-gradient-to-r from-up via-amber-400 to-down"><div className="relative h-2"><span className="absolute -top-1 h-4 w-1 rounded bg-slate-900 dark:bg-white" style={{ left: `${d.score ?? 0}%` }} /></div></div>
          {isNum(d.altman.z) && <p className="mt-3 text-xs muted">Altman Z″ {d.altman.z.toFixed(2)} ({d.altman.zone})</p>}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:col-span-3">
          {d.summary.map((s) => (
            <div key={s.Category} className="card flex items-center gap-2.5 p-3"><span className={cx('rounded-md px-1.5 py-0.5 text-[10px] font-bold', LEVEL[s.Level]?.[1])}>{LEVEL[s.Level]?.[0]}</span>
              <div><div className="text-sm font-semibold">{s.Category}</div><div className="text-xs muted">{s.Checks} checks</div></div></div>
          ))}
        </div>
      </div>
      <Card title="Checks with thresholds" subtitle="Every flag shows the metric and the rule used, so you can disagree with a threshold">
        <ul className="space-y-2">
          {d.flags.map((f, i) => (
            <li key={i} className="flex gap-3 rounded-xl border border-slate-100 p-3 dark:border-ink-700">
              <span className={cx('h-fit rounded-md px-1.5 py-0.5 text-[10px] font-bold', LEVEL[f.level]?.[1])}>{LEVEL[f.level]?.[0]}</span>
              <div className="min-w-0 text-sm"><div className="font-medium">{f.category} · {f.title}: <span className="num">{f.value}</span></div>
                <div className="muted">{f.detail}</div><div className="mt-0.5 text-xs text-slate-400">Thresholds: {f.rule}</div></div>
            </li>
          ))}
        </ul>
      </Card>
      <div className="grid gap-5 md:grid-cols-2">
        <Card title="General sector considerations" subtitle="Industry-level risks, not findings about this company"><ul className="list-disc space-y-1.5 pl-5 text-sm">{d.sector_considerations.map((s) => <li key={s}>{s}</li>)}</ul></Card>
        <Card title="Regulatory & disclosure checklist"><ul className="list-disc space-y-1.5 pl-5 text-sm">{d.regulatory.map((s) => <li key={s}>{s}</li>)}</ul></Card>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ peers
export function PeersTab({ symbol }: { symbol: string }) {
  const q = useQuery({ queryKey: ['peers', symbol], queryFn: () => api.get<{ rows: Record<string, number | string | null>[] }>(`/companies/${encodeURIComponent(symbol)}/peers`) })
  if (q.isLoading) return <Loading />
  const rows = q.data?.rows ?? []
  if (rows.length < 2) return <EmptyState title="No peers found" body="Peers are suggested from the same industry among tracked companies." />
  const col = (key: string, label: string, kind: string): Column<Record<string, number | string | null>> => ({ key, label, align: 'right', value: (r) => r[key] as number, render: (r) => kind === 'pct' ? pct(r[key]) : kind === 'x' ? mult(r[key]) : crore(r[key]) })
  return (
    <Card title="Peer comparison" subtitle="Latest fiscal year for each company; '—' where a metric is not meaningful (e.g. EV/EBITDA for banks)"
      action={<Link className="btn-outline" to={`/compare?symbols=${rows.slice(0, 5).map((r) => r.symbol).join(',')}`}>Full comparison</Link>}>
      <DataTable rows={rows} rowKey={(r) => String(r.symbol)} columns={[
        { key: 'name', label: 'Company', render: (r) => <Link className={cx('font-medium hover:underline', r.symbol === symbol && 'text-brand-600')} to={`/company/${encodeURIComponent(String(r.symbol))}`}>{String(r.name)}</Link> },
        col('market_cap', 'Mkt cap', 'cr'), col('pe', 'P/E', 'x'), col('pb', 'P/B', 'x'), col('ev_ebitda', 'EV/EBITDA', 'x'),
        col('roe', 'ROE', 'pct'), col('roce', 'ROCE', 'pct'), col('revenue_growth', 'Rev growth', 'pct'), col('net_margin', 'Net margin', 'pct'), col('debt_to_equity', 'D/E', 'x'),
      ]} />
    </Card>
  )
}

// ------------------------------------------------------------------ ownership
const SH_DEFAULT = ['Promoter & Promoter Group', 'FII/FPI', 'DII', 'Public & Others']

function ShareholdingForm({ symbol, onDone }: { symbol: string; onDone: () => void }) {
  const [period, setPeriod] = useState('')
  const [url, setUrl] = useState('')
  const [rows, setRows] = useState(SH_DEFAULT.map((category) => ({ category, pct: '', pledged: '' })))
  const toast = useToast()
  const filled = rows.filter((r) => r.category.trim() && r.pct !== '')
  const total = filled.reduce((a, r) => a + Number(r.pct), 0)
  const save = useMutation({
    mutationFn: () => api.post(`/companies/${encodeURIComponent(symbol)}/shareholding`, {
      period, source_url: url || null,
      rows: filled.map((r) => ({ category: r.category, pct: Number(r.pct), pledged_pct: r.pledged === '' ? null : Number(r.pledged) })) }),
    onSuccess: () => { toast('Shareholding saved'); onDone() }, onError: (e) => toast((e as Error).message, 'error'),
  })
  const set = (i: number, k: 'category' | 'pct' | 'pledged', v: string) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)))
  return (
    <div className="space-y-3">
      <p className="text-xs muted">Copy the figures from the quarterly shareholding pattern filed on NSE or BSE. Saved values are labelled “user-entered” with your source link.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div><label className="label">Quarter end</label><input className="input" type="date" value={period} onChange={(e) => setPeriod(e.target.value)} /></div>
        <div><label className="label">Source URL (exchange filing)</label><input className="input" placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} /></div>
      </div>
      <div className="space-y-2">
        <div className="grid grid-cols-[1fr_6rem_6rem] gap-2 text-xs font-medium muted"><span>Category</span><span>Holding %</span><span>Pledged %</span></div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[1fr_6rem_6rem] gap-2">
            <input className="input" value={r.category} maxLength={60} onChange={(e) => set(i, 'category', e.target.value)} />
            <input className="input num" type="number" min="0" max="100" step="0.01" value={r.pct} onChange={(e) => set(i, 'pct', e.target.value)} />
            <input className="input num" type="number" min="0" max="100" step="0.01" value={r.pledged} placeholder={i === 0 ? '' : '—'} onChange={(e) => set(i, 'pledged', e.target.value)} />
          </div>))}
        {rows.length < 12 && <button className="btn-ghost px-0 text-xs" onClick={() => setRows([...rows, { category: '', pct: '', pledged: '' }])}>+ Add category</button>}
      </div>
      <div className="flex items-center justify-between gap-3">
        <span className={cx('text-sm num', filled.length && Math.abs(total - 100) > 1 ? 'text-down' : 'muted')}>Total: {total.toFixed(2)}%</span>
        <button className="btn-primary" disabled={!period || !filled.length || Math.abs(total - 100) > 1 || save.isPending} onClick={() => save.mutate()}>Save shareholding</button>
      </div>
    </div>
  )
}

export function OwnershipTab({ symbol, sample }: { symbol: string; sample?: boolean }) {
  const q = useQuery({ queryKey: ['ownership', symbol], queryFn: () => api.get<{ shareholding: { period: string; category: string; pct: number; pledged_pct: number | null; source: string; data_type: string }[]; segments: { period: string; segment: string; revenue: number; source: string; data_type: string }[] }>(`/companies/${encodeURIComponent(symbol)}/ownership`) })
  const [entry, setEntry] = useState(false)
  const inv = useInvalidate()
  if (q.isLoading) return <Loading />
  const sh = q.data?.shareholding ?? [], seg = q.data?.segments ?? []
  const lastP = sh.length ? sh.map((s) => s.period).sort().at(-1) : null
  const lastS = seg.length ? seg.map((s) => s.period).sort().at(-1) : null
  const pledge = sh.filter((s) => s.period === lastP).find((s) => (s.pledged_pct ?? 0) > 0)
  const enter = !sample && <button className="btn-ghost text-xs" onClick={() => setEntry(!entry)}>{entry ? 'Close' : 'Enter pattern'}</button>
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Shareholding pattern" subtitle={lastP ? `Quarter ended ${lastP}` : undefined} action={enter}>
        {entry ? <ShareholdingForm symbol={symbol} onDone={() => { setEntry(false); inv('ownership') }} /> : !lastP ? <EmptyState title="No shareholding data" body="Shareholding patterns are filed quarterly with NSE/BSE (SEBI LODR Reg. 31). Use “Enter pattern” to record one from the exchange filing." /> : (<>
          <Donut data={sh.filter((s) => s.period === lastP).map((s) => ({ name: s.category, value: s.pct }))} fmt={(v) => `${v.toFixed(2)}%`} />
          {pledge && <Notice tone="warn" className="mt-3">Promoter pledge: {pledge.pledged_pct}% of promoter holding.</Notice>}
          <SourceNote sources={[...new Set(sh.map((s) => s.source))]} extra={<DataBadge type={sh[0].data_type} />} />
        </>)}
      </Card>
      <Card title="Revenue segments" subtitle={lastS ?? undefined}>
        {!lastS ? <EmptyState title="No segment data" body="Segment revenue comes from the segment note (Ind AS 108) of the annual report." /> : (<>
          <Donut data={seg.filter((s) => s.period === lastS).map((s) => ({ name: s.segment, value: s.revenue / 1e7 }))} fmt={(v) => `₹${num(v, 0)} Cr`} />
          <SourceNote sources={[...new Set(seg.map((s) => s.source))]} extra={<DataBadge type={seg[0].data_type} />} />
        </>)}
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------ bank metrics
interface BankResp { definitions: Record<string, { label: string; help: string }>; periods: string[]; values: Record<string, (number | null)[]>; flags: { title: string; level: string; value: string; detail: string; rule: string }[]; sources: string[] }

export function BankTab({ symbol, sample }: { symbol: string; sample: boolean }) {
  const q = useQuery({ queryKey: ['bank', symbol], queryFn: () => api.get<BankResp>(`/companies/${encodeURIComponent(symbol)}/bank`) })
  const toast = useToast()
  const inv = useInvalidate()
  const [form, setForm] = useState<Record<string, string>>({ period: '2026-09-30', source: '', source_url: '' })
  const save = useMutation({
    mutationFn: () => api.post(`/companies/${encodeURIComponent(symbol)}/bank`, {
      period: form.period, source: form.source, source_url: form.source_url || null,
      values: Object.fromEntries(Object.keys(q.data?.definitions ?? {}).map((k) => [k, form[k] ? Number(form[k]) : null])) }),
    onSuccess: () => { toast('Bank metrics saved'); inv('bank', 'risk') }, onError: (e) => toast((e as Error).message, 'error'),
  })
  if (q.isLoading) return <Loading />
  const d = q.data!
  const has = d.periods.length > 0
  const series = d.periods.map((p, i) => ({ period: p, ...Object.fromEntries(Object.entries(d.values).map(([k, v]) => [k, v[i]])) }))
  return (
    <div className="space-y-5">
      <Notice>Banks are analysed on asset quality, capital and funding rather than debt/equity. These figures come from each bank's quarterly results or investor presentation; the market-data provider does not supply them.</Notice>
      {has ? (<>
        <Card title="Bank metrics by quarter" pad={false}>
          <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
            <thead><tr><th className="table-head px-4 py-2">Metric</th>{d.periods.map((p) => <th key={p} className="table-head px-4 py-2 text-right">{p}</th>)}</tr></thead>
            <tbody>{Object.entries(d.values).map(([k, v]) => (
              <tr key={k} className="border-t border-slate-100 dark:border-ink-700"><td className="px-4 py-2">{d.definitions[k]?.label}</td>{v.map((x, i) => <td key={i} className="num px-4 py-2 text-right">{isNum(x) ? `${x.toFixed(2)}%` : '—'}</td>)}</tr>))}
            </tbody></table></div>
          <div className="px-4 pb-3"><SourceNote sources={d.sources} /></div>
        </Card>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Asset quality (%)"><LinesChart data={series} xKey="period" series={[{ key: 'gnpa', label: 'Gross NPA' }, { key: 'nnpa', label: 'Net NPA' }]} fmt={(v) => `${v.toFixed(2)}%`} /></Card>
          <Card title="Capital & funding (%)"><LinesChart data={series} xKey="period" series={[{ key: 'crar', label: 'CRAR' }, { key: 'casa', label: 'CASA' }]} fmt={(v) => `${v.toFixed(2)}%`} /></Card>
        </div>
        <Card title="Screening bands"><ul className="space-y-2">{d.flags.map((f) => (
          <li key={f.title} className="flex gap-3 text-sm"><span className={cx('h-fit rounded-md px-1.5 py-0.5 text-[10px] font-bold', LEVEL[f.level]?.[1])}>{LEVEL[f.level]?.[0]}</span>
            <span><b className="font-medium">{f.title}: {f.value}</b> <span className="muted">{f.detail}</span> <span className="text-xs text-slate-400">({f.rule})</span></span></li>))}</ul></Card>
      </>) : <EmptyState title="No bank metrics yet" body="Enter the latest quarter from the bank's results press release." />}
      {!sample && (
        <Card title="Enter a quarter" subtitle="Values in percent, e.g. 1.35 for 1.35%">
          <div className="grid gap-3 sm:grid-cols-3">
            <div><label className="label">Quarter end</label><input className="input" type="date" value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })} /></div>
            <div className="sm:col-span-2"><label className="label">Source document</label><input className="input" placeholder="Q2 FY27 results press release, p. 4" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} /></div>
            {Object.entries(d.definitions).map(([k, def]) => (
              <div key={k}><label className="label" title={def.help}>{def.label}</label><input className="input num" type="number" step="0.01" min="0" max="100" value={form[k] ?? ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></div>))}
            <div className="sm:col-span-3"><label className="label">Source URL</label><input className="input" placeholder="https://…" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} /></div>
          </div>
          <button className="btn-primary mt-4" disabled={save.isPending || form.source.length < 3} onClick={() => save.mutate()}>Save quarter</button>
        </Card>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ news
interface NewsItem { title: string; url: string | null; published: string | null; source: string; category: string; symbol: string | null; summary: string | null }

export function NewsTab({ symbol, compact }: { symbol: string; compact?: boolean }) {
  const [unrated, setUnrated] = useState(false)
  const q = useQuery({ queryKey: ['news', 'company', symbol, unrated], queryFn: () => api.get<{ items: (NewsItem & { tier?: string })[]; hidden_unrated?: number }>(`/news?section=company&symbol=${encodeURIComponent(symbol)}&limit=${compact ? 6 : 40}&include_unrated=${unrated}`) })
  const hidden = q.data?.hidden_unrated ?? 0
  return (
    <Card title={compact ? 'Latest news & filings' : 'News, filings & announcements'} subtitle={compact ? undefined : 'NSE filings link to the original PDF; headlines link to the original publisher'}
      action={compact ? <Link to={`/company/${encodeURIComponent(symbol)}?tab=news`} className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">All</Link> : undefined}>
      {q.isLoading ? <Loading /> : (q.data?.items.length ?? 0) === 0 ? <p className="text-sm muted">No news or filings stored for {baseSymbol(symbol)}.</p> : (
        <ul className="space-y-3">
          {q.data!.items.map((n, i) => (
            <li key={i} className="text-sm">
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] muted"><TierBadge tier={n.tier} />{n.category} · {n.source} · {timeAgo(n.published)}</div>
              <a href={n.url ?? '#'} target="_blank" rel="noopener noreferrer" className="hover:underline">{n.summary && n.source.includes('NSE') ? n.summary : n.title} <ExternalLink className="inline h-3 w-3 opacity-60" /></a>
            </li>
          ))}
        </ul>
      )}
      {!compact && (hidden > 0 || unrated) && <p className="mt-3 text-xs muted">{unrated ? 'Including unrated publishers. ' : `${hidden} headline${hidden === 1 ? '' : 's'} from unrated publishers hidden. `}
        <button className="font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => setUnrated(!unrated)}>{unrated ? 'Hide them' : 'Show them'}</button></p>}
    </Card>
  )
}

// ------------------------------------------------------------------ notes
const NOTE_FIELDS: [string, string][] = [['business_model', 'Business model - how the company makes money'], ['products', 'Key products, services & brands'],
  ['moat', 'Competitive position & moat'], ['management', 'Management & governance'], ['risks', 'Company-specific risks'], ['source', 'Source references (annual report pages, URLs)']]

export function NotesTab({ symbol, initial }: { symbol: string; initial: Record<string, string> }) {
  const [notes, setNotes] = useState<Record<string, string>>(initial ?? {})
  const toast = useToast()
  const save = useMutation({ mutationFn: () => api.put<{ updated: string }>(`/companies/${encodeURIComponent(symbol)}/notes`, notes), onSuccess: (r) => toast(`Notes saved · ${r.updated}`) })
  return (
    <Card title="My research notes" subtitle="Private to your profile. They feed the AI assistant and your PDF report (labelled as your own notes).">
      <div className="grid gap-4 md:grid-cols-2">
        {NOTE_FIELDS.map(([k, label]) => (
          <div key={k} className={k === 'source' ? 'md:col-span-2' : ''}><label className="label">{label}</label>
            <textarea className="input min-h-[88px]" value={notes[k] ?? ''} onChange={(e) => setNotes({ ...notes, [k]: e.target.value })} /></div>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-3"><button className="btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>Save notes</button>{notes.updated && <span className="text-xs muted">Last saved {notes.updated}</span>}</div>
    </Card>
  )
}
