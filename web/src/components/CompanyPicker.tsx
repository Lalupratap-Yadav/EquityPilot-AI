import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type SearchResult } from '../lib/api'
import { baseSymbol } from '../lib/format'
import { useDebounced } from '../lib/hooks'
import { CompanyAvatar } from './common'
import { cx, DataBadge } from './ui'

/** Type-ahead company picker over the full securities master. */
export function CompanyPicker({ value, onChange, placeholder = 'Search a company…', className, trackedOnly }: {
  value?: string; onChange: (symbol: string, name: string) => void; placeholder?: string; className?: string; trackedOnly?: boolean
}) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const dq = useDebounced(q, 180)
  const box = useRef<HTMLDivElement>(null)
  const res = useQuery({ queryKey: ['search', dq], enabled: dq.trim().length >= 1, queryFn: () => api.get<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(dq)}&limit=10`) })
  useEffect(() => {
    const h = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const results = (res.data?.results ?? []).filter((r) => !trackedOnly || r.tracked)
  return (
    <div ref={box} className={cx('relative', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input className="input pl-9" value={q} placeholder={value ? `${baseSymbol(value)} - type to change` : placeholder}
        onChange={(e) => { setQ(e.target.value); setOpen(true) }} onFocus={() => setOpen(true)} aria-label="Company search" />
      {open && q.trim() && (
        <ul className="card absolute z-30 mt-1 max-h-80 w-full overflow-y-auto p-1 shadow-[var(--shadow-pop)]">
          {results.map((r) => (
            <li key={r.symbol}>
              <button className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-slate-100 dark:hover:bg-ink-700"
                onClick={() => { onChange(r.symbol, r.name); setQ(''); setOpen(false) }}>
                <CompanyAvatar symbol={r.symbol} size="sm" />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{r.name}</span><span className="block text-xs muted">{baseSymbol(r.symbol)}{r.category ? ` · ${r.category}` : ''}</span></span>
                {r.is_sample ? <DataBadge type="sample" /> : !r.tracked && <span className="text-[10px] muted">fetches on open</span>}
              </button>
            </li>
          ))}
          {res.isFetched && results.length === 0 && <li className="px-3 py-3 text-sm muted">No matches.</li>}
        </ul>
      )}
    </div>
  )
}
