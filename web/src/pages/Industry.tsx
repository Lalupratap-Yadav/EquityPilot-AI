import { useQuery } from '@tanstack/react-query'
import { CheckSquare, ExternalLink, Scale, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BarsChart, Sparkline } from '../components/charts'
import { CompanyAvatar, DataTable, type Column } from '../components/common'
import { Card, ChangePill, DataBadge, ErrorState, Loading, Notice, PageHeader, SourceNote } from '../components/ui'
import { api, type IndexRow } from '../lib/api'
import { baseSymbol, byKind, inr, isNum, timeAgo } from '../lib/format'

interface IndustryResp {
  id: string; name: string; overview: string; drivers: string[]; trends: string[]; risks: string[]; valuation: string[]; disclosure_kpis: string[]
  metrics: Record<string, { label: string; kind: string }>
  companies: Record<string, string | number | null>[]
  index: IndexRow | null
  announcements: { title: string; summary: string; url: string; published: string; category: string; symbol: string }[]
  news: { title: string; url: string; date: string; publisher: string; symbol: string }[]
  editorial_note: string
}

function List({ title, icon, items }: { title: string; icon: React.ReactNode; items: string[] }) {
  return (
    <Card title={<span className="inline-flex items-center gap-1.5">{icon}{title}</span>} action={<DataBadge type="editorial" />}>
      <ul className="space-y-2 text-sm">{items.map((t) => <li key={t} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{t}</li>)}</ul>
    </Card>
  )
}

export default function Industry() {
  const { id = '' } = useParams()
  const nav = useNavigate()
  const q = useQuery({ queryKey: ['industry', id], queryFn: () => api.get<IndustryResp>(`/industries/${id}`) })
  const [metric, setMetric] = useState<string>('')
  if (q.isLoading) return <Loading />
  if (q.error) return <ErrorState error={q.error} />
  const d = q.data!
  const metricKeys = Object.keys(d.metrics)
  const m = metric || metricKeys.find((k) => k !== 'market_cap') || metricKeys[0]
  const def = d.metrics[m]
  const chartData = d.companies.filter((c) => isNum(c[m])).map((c) => ({ name: baseSymbol(String(c.symbol)),
    value: def.kind === 'pct' ? (c[m] as number) * 100 : def.kind === 'cr' ? (c[m] as number) / 1e7 : (c[m] as number) }))
    .sort((a, b) => b.value - a.value)
  const cols: Column<Record<string, string | number | null>>[] = [
    { key: 'name', label: 'Company', render: (r) => <span className="flex items-center gap-2"><CompanyAvatar symbol={String(r.symbol)} size="sm" /><span className="font-medium">{String(r.name)}</span></span> },
    { key: 'category', label: 'Cap', render: (r) => <span className="text-xs muted">{String(r.category ?? '—').replace(' Cap', '')}</span> },
    { key: 'price', label: 'Price', align: 'right', value: (r) => r.price as number, render: (r) => inr(r.price) },
    { key: 'change_pct', label: 'Day', align: 'right', value: (r) => r.change_pct as number, render: (r) => <ChangePill value={r.change_pct as number} /> },
    ...metricKeys.map((k) => ({ key: k, label: d.metrics[k].label, align: 'right' as const, value: (r: Record<string, string | number | null>) => r[k] as number,
      render: (r: Record<string, string | number | null>) => byKind(r[k], d.metrics[k].kind) })),
  ]
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Industry Intelligence" title={d.name} subtitle={d.overview}
        actions={d.index && (
          <div className="card flex items-center gap-4 px-4 py-3">
            <div><div className="text-xs font-semibold muted">{d.index.name}</div><div className="num font-semibold">{d.index.last.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div><ChangePill value={d.index.change_pct} /></div>
            <Sparkline data={d.index.spark} width={120} height={40} />
          </div>
        )} />
      <Notice>{d.editorial_note}</Notice>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <List title="Growth drivers" icon={<TrendingUp className="h-4 w-4 text-up" />} items={d.drivers} />
        <List title="Business trends" icon={<Sparkles className="h-4 w-4 text-brand-600" />} items={d.trends} />
        <List title="Major risks" icon={<ShieldAlert className="h-4 w-4 text-down" />} items={d.risks} />
        <List title="How analysts value it" icon={<Scale className="h-4 w-4 text-saffron-500" />} items={d.valuation} />
      </div>

      <Card title="Competitive landscape" subtitle="Listed companies compared on metrics relevant to this industry (latest fiscal year; delayed prices). Click a row to open the company."
        action={<Link className="btn-outline" to={`/compare?symbols=${d.companies.slice(0, 5).map((c) => c.symbol).join(',')}`}>Compare top 5</Link>}>
        <DataTable rows={d.companies} rowKey={(r) => String(r.symbol)} columns={cols} onRowClick={(r) => nav(`/company/${encodeURIComponent(String(r.symbol))}`)} initialSort={{ key: 'market_cap', dir: 'desc' }} />
        {id === 'banking' || id === 'financial-services' ? <p className="mt-2 text-xs muted">Bank metrics (GNPA, NNPA, CRAR, CASA, NIM) are entered from quarterly disclosures on each company's Bank metrics tab - blank until entered.</p> : null}
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Compare on a metric" className="lg:col-span-2"
          action={<select className="input w-auto" value={m} onChange={(e) => setMetric(e.target.value)} aria-label="Metric">{metricKeys.map((k) => <option key={k} value={k}>{d.metrics[k].label}</option>)}</select>}>
          {chartData.length ? <BarsChart data={chartData} xKey="name" series={[{ key: 'value', label: def.label }]} height={280}
            fmt={(v) => def.kind === 'pct' ? `${v.toFixed(1)}%` : def.kind === 'cr' ? `₹${Math.round(v).toLocaleString('en-IN')} Cr` : v.toFixed(2)} /> : <p className="text-sm muted">No data for this metric.</p>}
        </Card>
        <Card title={<span className="inline-flex items-center gap-1.5"><CheckSquare className="h-4 w-4 text-brand-600" />Operating KPIs to check</span>} subtitle="Found in company results & presentations - not available from free data feeds">
          <ul className="space-y-1.5 text-sm">{d.disclosure_kpis.map((k) => <li key={k} className="flex gap-2"><span className="text-brand-500">□</span>{k}</li>)}</ul>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Recent exchange filings" subtitle="From the NSE announcements feed for companies in this industry">
          {d.announcements.length === 0 ? <p className="text-sm muted">No recent filings in the feed for these companies.</p> : (
            <ul className="space-y-3">{d.announcements.slice(0, 10).map((a, i) => (
              <li key={i} className="text-sm"><div className="text-[11px] muted"><b>{baseSymbol(a.symbol)}</b> · {a.category} · {timeAgo(a.published)}</div>
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="hover:underline">{a.summary || a.title} <ExternalLink className="inline h-3 w-3" /></a></li>))}</ul>
          )}
          <SourceNote sources={['NSE India corporate announcements (RSS)']} />
        </Card>
        <Card title="Recent developments in the news" subtitle="Headlines for this industry's companies (third-party publishers)">
          {d.news.length === 0 ? <p className="text-sm muted">No headlines stored yet - they are fetched when you open company news.</p> : (
            <ul className="space-y-3">{d.news.map((n, i) => (
              <li key={i} className="text-sm"><div className="text-[11px] muted"><b>{baseSymbol(n.symbol)}</b> · {n.publisher} · {timeAgo(n.date)}</div>
                <a href={n.url} target="_blank" rel="noopener noreferrer" className="hover:underline">{n.title}</a></li>))}</ul>
          )}
        </Card>
      </div>
    </div>
  )
}
