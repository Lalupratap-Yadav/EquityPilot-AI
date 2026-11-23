import { BookOpen, Search, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { cx, EmptyState } from '../../components/ui'
import { normalise, score } from '../../lib/fuzzy'
import type { Term } from './types'

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

/** Searchable, typo-tolerant glossary with A-Z browsing. Each entry shows its definition, formula, example, how to read it,
 *  related concepts and the lessons that teach it. */
export function Glossary({ terms, initial = '' }: { terms: Term[]; initial?: string }) {
  const [q, setQ] = useState(initial)
  const [letter, setLetter] = useState<string | null>(null)
  const top = useRef<HTMLDivElement>(null)
  const have = useMemo(() => new Set(terms.map((t) => t.letter)), [terms])
  const list = useMemo(() => {
    const s = normalise(q)
    if (!s) return [...terms].filter((t) => !letter || t.letter === letter).sort((a, b) => a.term.localeCompare(b.term))
    return terms.map((t) => {
      let sc = score(q, [t.term, ...t.aliases])
      if (sc < 30 && s.length >= 4 && normalise(t.definition).includes(s)) sc = 25          // mentioned in a definition
      return [t, sc] as const
    }).filter(([, sc]) => sc >= 25).sort((a, b) => b[1] - a[1] || a[0].term.localeCompare(b[0].term)).map(([t]) => t)
  }, [q, letter, terms])
  const exact = list[0] && normalise(list[0].term) === normalise(q) ? list[0].term : null
  const jump = (t: string) => { setLetter(null); setQ(t); top.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }) }

  return (
    <div className="space-y-4" ref={top}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-md flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9 pr-9" placeholder="Search terms, e.g. ROCE, repo rate, SCORES" aria-label="Search the glossary"
            value={q} onChange={(e) => { setQ(e.target.value); setLetter(null) }} />
          {q && <button className="btn-ghost absolute right-1 top-1/2 -translate-y-1/2 p-1.5" aria-label="Clear search" onClick={() => setQ('')}><X className="h-4 w-4" /></button>}
        </div>
        <span className="text-xs muted">{q ? `${list.length} match${list.length === 1 ? '' : 'es'}` : `${terms.length} terms`} · spelling mistakes are tolerated</span>
      </div>
      <nav aria-label="Browse by letter" className="flex flex-wrap gap-1">
        <button className={cx('chip px-2.5', !letter && !q && 'chip-active')} onClick={() => { setLetter(null); setQ('') }}>All</button>
        {LETTERS.map((l) => (
          <button key={l} disabled={!have.has(l)} aria-pressed={letter === l}
            className={cx('chip px-2.5 disabled:cursor-not-allowed disabled:opacity-35', letter === l && 'chip-active')}
            onClick={() => { setQ(''); setLetter(l) }}>{l}</button>
        ))}
      </nav>
      {list.length === 0 ? (
        <EmptyState icon={<BookOpen className="h-5 w-5" />} title="No matching terms"
          body={<>Try another spelling or a shorter word, or <Link className="text-brand-700 underline dark:text-brand-300" to={`/assistant?q=${encodeURIComponent(`Explain ${q} in simple words`)}`}>ask the AI Assistant</Link>.</>} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((t) => (
            <article key={t.term} className={cx('card card-pad', exact === t.term && 'ring-2 ring-brand-400')} data-testid="glossary-term">
              <h3 className="section-title">{t.term}</h3>
              <p className="mt-1.5 text-sm leading-relaxed">{t.definition}</p>
              {t.formula && <p className="mt-2 rounded-xl bg-slate-50 px-3 py-2 font-mono text-[13px] dark:bg-ink-800">{t.formula}</p>}
              {t.example && <p className="mt-2 text-sm"><span className="font-medium">Example: </span>{t.example}</p>}
              {t.interpretation && <p className="mt-2 text-sm muted">{t.interpretation}</p>}
              {(t.related.length > 0 || t.lessons.length > 0) && (
                <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 text-xs dark:border-ink-700">
                  {t.related.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5"><span className="muted">Related:</span>
                      {t.related.map((r) => <button key={r} className="chip py-0.5" onClick={() => jump(r)}>{r}</button>)}
                    </div>
                  )}
                  {t.lessons.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5"><span className="muted">Learn it in:</span>
                      {t.lessons.map((l) => <Link key={l.id} to={`/learn?lesson=${l.id}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{l.title}</Link>)}
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
