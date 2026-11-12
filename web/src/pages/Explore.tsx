import { useQuery } from '@tanstack/react-query'
import { BookOpen, Flame, Layers } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CardRow } from '../components/common'
import { Card, ChangePill, cx, Loading, Notice, PageHeader, Segmented } from '../components/ui'
import { api, type CompanyCardData } from '../lib/api'
import { crore, mult, pct } from '../lib/format'

interface ExploreResp {
  collections: { id: string; title: string; description: string; companies: CompanyCardData[]; count: number }[]
  categories: { category: string; tracked: number; listed: number; companies: CompanyCardData[] }[]
  trending: CompanyCardData[]; featured: CompanyCardData[]
  topics: { id: string; title: string; summary: string }[]
  categories_as_of: string | null; note: string
}
interface IndustryRow { id: string; name: string; companies: number; market_cap: number | null; median_pe: number | null; median_roe: number | null; day_change: number | null; favourite: boolean }

export default function Explore() {
  const q = useQuery({ queryKey: ['explore'], queryFn: () => api.get<ExploreResp>('/explore') })
  const ind = useQuery({ queryKey: ['industries'], queryFn: () => api.get<{ industries: IndustryRow[] }>('/industries') })
  const [cat, setCat] = useState('Large Cap')
  if (q.isLoading) return <Loading label="Building discovery rows…" />
  const d = q.data!
  const active = d.categories.find((c) => c.category === cat)
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Explore markets" title="Discover Indian companies" subtitle="Browse by market-cap category, industry and rule-based collections. Every collection is a transparent screen - open it in the Screener to see the rules." />

      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="section-title flex items-center gap-1.5"><Layers className="h-4 w-4 text-brand-600" />By market capitalisation</h2>
            <p className="text-xs muted">Official AMFI categorisation ({d.categories_as_of ?? 'latest available list'}): Large Cap = top 100, Mid Cap = 101-250, Small Cap = 251+ by average market cap.</p></div>
          <Segmented value={cat} onChange={setCat} options={d.categories.map((c) => ({ id: c.category, label: `${c.category.replace(' Cap', '')} · ${c.listed.toLocaleString('en-IN')}` }))} />
        </div>
        {active && <CardRow title={`${active.category} companies tracked in EquityPilot (${active.tracked})`} subtitle={`${active.listed.toLocaleString('en-IN')} ${active.category.toLowerCase()} companies are listed; search any of them to fetch its data.`}
          items={active.companies} empty="No tracked companies in this category yet - use search to add one." />}
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between"><h2 className="section-title">Industries</h2><Link to="/industries" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">Industry Intelligence Centre</Link></div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {(ind.data?.industries ?? []).map((i) => (
            <Link key={i.id} to={`/industries/${i.id}`} className="card p-3.5 transition-all hover:-translate-y-0.5 hover:border-brand-300">
              <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{i.name}</span><ChangePill value={i.day_change} /></div>
              <div className="mt-2 space-y-0.5 text-[11px] muted">
                <div>{i.companies} companies · {crore(i.market_cap)}</div>
                <div>Median P/E {mult(i.median_pe)} · ROE {pct(i.median_roe, 0)}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <Notice>{d.note}</Notice>
      {d.collections.map((c) => (
        <CardRow key={c.id} title={`${c.title} (${c.count})`} subtitle={c.description} items={c.companies}
          action={<Link to={`/screener?preset=${encodeURIComponent(c.title)}`} className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">See the rules</Link>} />
      ))}

      {d.trending.length > 0 && <CardRow title={<span className="inline-flex items-center gap-1.5"><Flame className="h-4 w-4 text-orange-500" />Trending on EquityPilot</span>} subtitle="Most-viewed company pages by EquityPilot users" items={d.trending} />}
      <CardRow title="Featured: India's largest companies" subtitle="By market capitalisation among tracked companies" items={d.featured} />

      <section>
        <h2 className="section-title mb-3 flex items-center gap-1.5"><BookOpen className="h-4 w-4 text-brand-600" />Popular research topics</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {d.topics.map((t, i) => (
            <Link key={t.id} to={`/learn?module=${t.id}`} className={cx('card p-4 transition-colors hover:border-brand-300')}>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-300">Module {i + 1}</div>
              <div className="mt-1 font-semibold">{t.title}</div><p className="mt-1 line-clamp-2 text-xs muted">{t.summary}</p>
            </Link>
          ))}
        </div>
      </section>
      <Card title="How collections work">
        <p className="text-sm muted">Collections are filters applied to EquityPilot's tracked universe using each company's latest fiscal-year data (Yahoo Finance, third-party). They help you find companies to research - they are not recommendations, and companies with missing data are excluded.</p>
      </Card>
    </div>
  )
}
