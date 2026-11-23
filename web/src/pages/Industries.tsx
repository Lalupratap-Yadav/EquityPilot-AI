import { useMutation, useQuery } from '@tanstack/react-query'
import { Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Sparkline } from '../components/Sparkline'
import { ChangePill, cx, Loading, PageHeader } from '../components/ui'
import { api, type IndexRow } from '../lib/api'
import { crore, mult, pct } from '../lib/format'
import { useInvalidate } from '../lib/hooks'

interface IndustryRow { id: string; name: string; overview: string; companies: number; market_cap: number | null; median_pe: number | null; median_roe: number | null; day_change: number | null; index: IndexRow | null; favourite: boolean }

export default function Industries() {
  const q = useQuery({ queryKey: ['industries'], queryFn: () => api.get<{ industries: IndustryRow[] }>('/industries') })
  const inv = useInvalidate()
  const fav = useMutation({ mutationFn: (id: string) => api.post(`/industries/${id}/favourite`), onSuccess: () => inv('industries', 'explore') })
  if (q.isLoading) return <Loading />
  const rows = [...(q.data?.industries ?? [])].sort((a, b) => Number(b.favourite) - Number(a.favourite))
  return (
    <div>
      <PageHeader eyebrow="Industry Intelligence Centre" title="Understand industries before companies"
        subtitle="Each industry page explains how the business works, what drives growth, the key risks, how analysts value it, and compares its listed companies on metrics that make sense for that industry." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((i) => (
          <div key={i.id} className="card flex flex-col p-5">
            <div className="flex items-start justify-between gap-3">
              <Link to={`/industries/${i.id}`} className="text-lg font-semibold hover:text-brand-600">{i.name}</Link>
              <button onClick={() => fav.mutate(i.id)} className="btn-ghost -mr-2 -mt-1 p-1.5" aria-label={i.favourite ? 'Remove from favourites' : 'Add to favourites'}>
                <Star className={cx('h-4 w-4', i.favourite ? 'fill-saffron-400 text-saffron-500' : 'text-slate-400')} />
              </button>
            </div>
            <p className="mt-1 line-clamp-3 flex-1 text-sm muted">{i.overview}</p>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div><div className="text-[10px] font-semibold uppercase muted">Companies</div><div className="num font-semibold">{i.companies}</div></div>
              <div><div className="text-[10px] font-semibold uppercase muted">Median P/E</div><div className="num font-semibold">{mult(i.median_pe)}</div></div>
              <div><div className="text-[10px] font-semibold uppercase muted">Median ROE</div><div className="num font-semibold">{pct(i.median_roe, 0)}</div></div>
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-ink-700">
              <div className="text-xs"><div className="muted">{i.index ? i.index.name : 'Tracked companies'} today</div>
                <ChangePill value={i.index ? i.index.change_pct : i.day_change} /></div>
              {i.index && <Sparkline data={i.index.spark} width={110} height={34} />}
              <span className="text-xs muted">{crore(i.market_cap)}</span>
            </div>
            <Link to={`/industries/${i.id}`} className="btn-outline mt-4">Open industry</Link>
          </div>
        ))}
      </div>
    </div>
  )
}
