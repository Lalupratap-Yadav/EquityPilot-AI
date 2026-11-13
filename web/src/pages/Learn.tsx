import { useMutation, useQuery } from '@tanstack/react-query'
import { BookOpen, CheckCircle2, ChevronLeft, GraduationCap, Search, Sigma, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Card, cx, EmptyState, ErrorState, Loading, Notice, PageHeader, Tabs, useToast } from '../components/ui'
import { api } from '../lib/api'
import { useInvalidate } from '../lib/hooks'

type QuizQ = [string, string[], number, string]
interface Module { id: string; title: string; summary: string; sections: [string, string][]; formulas: string[]; quiz: QuizQ[] }
interface Progress { best: number; last: number; attempts: number; updated: string }
interface Term { term: string; aliases: string[]; definition: string; formula?: string; interpretation?: string }
interface LearnResp { modules: Module[]; progress: Record<string, Progress>; glossary: Term[] }

export default function Learn() {
  const q = useQuery({ queryKey: ['learn'], queryFn: () => api.get<LearnResp>('/learn') })
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as 'modules' | 'glossary') || 'modules'
  const open = params.get('module')
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} retry={q.refetch} />
  const { modules, progress, glossary } = q.data
  const mod = modules.find((m) => m.id === open)
  const done = modules.filter((m) => (progress[m.id]?.best ?? 0) >= Math.ceil(m.quiz.length * 0.6)).length

  if (mod) return <ModuleView mod={mod} progress={progress[mod.id]} onBack={() => setParams({})} />
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Learn" title="Learning Centre"
        subtitle="Short, practical modules on Indian markets and fundamental analysis, each with formulas and a quiz. Content is educational and aligned with the topics of the NISM Series XV (Research Analyst) syllabus; it is not investment advice." />
      <div className="grid gap-3 sm:grid-cols-3">
        <Card><div className="flex items-center gap-3"><GraduationCap className="h-8 w-8 text-brand-600" /><div><div className="text-2xl font-semibold num">{done}/{modules.length}</div><div className="text-xs muted">modules passed (60%+ in the quiz)</div></div></div></Card>
        <Card><div className="flex items-center gap-3"><BookOpen className="h-8 w-8 text-saffron-500" /><div><div className="text-2xl font-semibold num">{glossary.length}</div><div className="text-xs muted">glossary terms with formulas</div></div></div></Card>
        <Card><div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-ink-700"><div className="h-full rounded-full bg-brand-600" style={{ width: `${(done / Math.max(1, modules.length)) * 100}%` }} /></div><div className="mt-2 text-xs muted">Your progress is saved to your profile.</div></Card>
      </div>
      <Tabs tabs={[{ id: 'modules', label: 'Modules' }, { id: 'glossary', label: 'Glossary' }]} value={tab} onChange={(t) => setParams(t === 'modules' ? {} : { tab: t })} />
      {tab === 'modules' ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((m, i) => {
            const p = progress[m.id]
            const passed = (p?.best ?? 0) >= Math.ceil(m.quiz.length * 0.6)
            return (
              <button key={m.id} onClick={() => setParams({ module: m.id })} className="card card-pad text-left transition hover:-translate-y-0.5 hover:shadow-lg">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-sm font-semibold text-brand-700 dark:bg-ink-700 dark:text-brand-200">{i + 1}</span>
                  {p && <span className={cx('chip', passed && 'text-up')}>{passed ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}Best {p.best}/{m.quiz.length}</span>}
                </div>
                <h3 className="mt-3 font-semibold">{m.title}</h3>
                <p className="mt-1 text-sm muted">{m.summary}</p>
                <div className="mt-3 text-xs muted">{m.sections.length} sections · {m.formulas.length} formulas · {m.quiz.length}-question quiz</div>
              </button>)
          })}
        </div>
      ) : <Glossary terms={glossary} initial={params.get('term') ?? ''} />}
    </div>
  )
}

function ModuleView({ mod, progress, onBack }: { mod: Module; progress?: Progress; onBack: () => void }) {
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [submitted, setSubmitted] = useState(false)
  const toast = useToast()
  const inv = useInvalidate()
  const score = mod.quiz.reduce((a, q, i) => a + (answers[i] === q[2] ? 1 : 0), 0)
  const save = useMutation({
    mutationFn: () => api.post('/learn/progress', { module: mod.id, score }),
    onSuccess: () => inv('learn'), onError: (e) => toast((e as Error).message, 'error'),
  })
  const submit = () => { setSubmitted(true); save.mutate() }
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <button className="btn-ghost px-0" onClick={onBack}><ChevronLeft className="h-4 w-4" />All modules</button>
      <PageHeader eyebrow="Learning module" title={mod.title} subtitle={mod.summary} />
      {mod.sections.map(([title, body]) => (
        <Card key={title} title={title}><Markdown text={body} /></Card>
      ))}
      {mod.formulas.length > 0 && (
        <Card title={<span className="inline-flex items-center gap-1.5"><Sigma className="h-4 w-4 text-brand-600" />Key formulas</span>}>
          <ul className="space-y-2">{mod.formulas.map((f) => <li key={f} className="rounded-xl bg-slate-50 px-3 py-2 font-mono text-[13px] dark:bg-ink-800">{f}</li>)}</ul>
        </Card>
      )}
      <Card title="Check your understanding" subtitle={progress ? `Best score ${progress.best}/${mod.quiz.length} · ${progress.attempts} attempt(s)` : `${mod.quiz.length} questions`}>
        <ol className="space-y-5">
          {mod.quiz.map(([question, options, correct, why], i) => (
            <li key={i}>
              <p className="font-medium">{i + 1}. {question}</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {options.map((o, j) => {
                  const chosen = answers[i] === j
                  const state = submitted ? (j === correct ? 'right' : chosen ? 'wrong' : '') : ''
                  return (
                    <button key={j} disabled={submitted} onClick={() => setAnswers({ ...answers, [i]: j })}
                      className={cx('flex items-center gap-2 rounded-xl border px-3 py-2 text-left text-sm transition',
                        state === 'right' ? 'border-up bg-up/10' : state === 'wrong' ? 'border-down bg-down/10'
                          : chosen ? 'border-brand-500 bg-brand-50 dark:bg-ink-700' : 'border-slate-200 hover:border-brand-300 dark:border-ink-600')}>
                      {state === 'right' ? <CheckCircle2 className="h-4 w-4 shrink-0 text-up" /> : state === 'wrong' ? <XCircle className="h-4 w-4 shrink-0 text-down" /> : null}{o}
                    </button>)
                })}
              </div>
              {submitted && <p className="mt-2 text-xs muted">{why}</p>}
            </li>))}
        </ol>
        <div className="mt-5 flex items-center justify-between gap-3">
          {submitted ? <Notice tone={score >= Math.ceil(mod.quiz.length * 0.6) ? 'success' : 'warn'} className="flex-1">You scored {score}/{mod.quiz.length}.{score >= Math.ceil(mod.quiz.length * 0.6) ? ' Module passed.' : ' Review the sections above and try again.'}</Notice> : <span className="text-xs muted">{Object.keys(answers).length}/{mod.quiz.length} answered</span>}
          {submitted ? <button className="btn-outline" onClick={() => { setAnswers({}); setSubmitted(false) }}>Retake</button>
            : <button className="btn-primary" disabled={Object.keys(answers).length < mod.quiz.length} onClick={submit}>Submit answers</button>}
        </div>
      </Card>
    </div>
  )
}

function Glossary({ terms, initial = '' }: { terms: Term[]; initial?: string }) {
  const [q, setQ] = useState(initial)
  const list = useMemo(() => {
    const s = q.trim().toLowerCase()
    const sorted = [...terms].sort((a, b) => a.term.localeCompare(b.term))
    return s ? sorted.filter((t) => t.term.toLowerCase().includes(s) || t.aliases.some((a) => a.includes(s)) || t.definition.toLowerCase().includes(s)) : sorted
  }, [q, terms])
  return (
    <div className="space-y-4">
      <div className="relative max-w-md"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input className="input pl-9" placeholder="Search terms, e.g. ROCE, free cash flow, beta" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {list.length === 0 ? <EmptyState title="No matching terms" body="Try a different word, or ask the AI Assistant to explain a concept." /> : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((t) => (
            <Card key={t.term} title={t.term}>
              <p className="text-sm">{t.definition}</p>
              {t.formula && <p className="mt-2 rounded-xl bg-slate-50 px-3 py-2 font-mono text-[13px] dark:bg-ink-800">{t.formula}</p>}
              {t.interpretation && <p className="mt-2 text-sm muted">{t.interpretation}</p>}
            </Card>))}
        </div>
      )}
    </div>
  )
}
