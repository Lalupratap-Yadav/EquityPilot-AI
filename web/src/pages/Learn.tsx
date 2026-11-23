import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, BookOpen, Calculator, CheckCircle2, ChevronLeft, ChevronRight, Clock, GraduationCap, History, PlayCircle, Shuffle, Trophy } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, cx, EmptyState, ErrorState, Loading, Notice, PageHeader, Tabs } from '../components/ui'
import { api } from '../lib/api'
import { CalculatorView } from './learn/Calculators'
import { Glossary } from './learn/Glossary'
import { LessonView } from './learn/LessonView'
import { QuizRunner } from './learn/Quiz'
import { LEVEL_LABEL, lessonIndex, reviewedLabel, type LearnOverview, type LessonStub, type ModuleCard, type ModuleFull, type ProgressSummary, type Question } from './learn/types'

type Tab = 'learn' | 'glossary' | 'calculators' | 'progress'
const ALIASES: Record<string, string> = { ra: 'analysis', risk: 'portfolio' }     // module ids of the earlier Learning Centre

export default function Learn() {
  const q = useQuery({ queryKey: ['learn'], queryFn: () => api.get<LearnOverview>('/learn'), staleTime: 5 * 60_000 })
  const [params, setParams] = useSearchParams()
  const lessonId = params.get('lesson')
  const moduleParam = params.get('module')
  const quiz = params.get('quiz')
  const tab = (params.get('tab') as Tab) || 'learn'
  const idx = useMemo(() => (q.data ? lessonIndex(q.data.levels) : {}), [q.data])
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} retry={q.refetch} />
  const d = q.data
  const moduleId = lessonId ? idx[lessonId]?.module.id : moduleParam ? (ALIASES[moduleParam] ?? moduleParam) : quiz && quiz !== 'revision' ? (ALIASES[quiz] ?? quiz) : null
  if (lessonId && !idx[lessonId]) return <NotFound what="lesson" />
  if (moduleId) return <ModuleRoute overview={d} moduleId={moduleId} lessonId={lessonId} quiz={!!quiz} />
  if (quiz === 'revision') return <RevisionQuiz overview={d} />

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Learn" title="Learning Centre"
        subtitle={<>Practical lessons on money, Indian markets, financial statements, valuation and investor protection, from beginner to advanced. Educational content checked against official sources (reviewed {reviewedLabel(d.reviewed)}); not investment advice.</>} />
      <Tabs<Tab> tabs={[{ id: 'learn', label: 'Lessons' }, { id: 'glossary', label: `Glossary (${d.counts.terms})` }, { id: 'calculators', label: 'Calculators' }, { id: 'progress', label: 'My progress' }]}
        value={tab} onChange={(t) => setParams(t === 'learn' ? {} : { tab: t })} />
      {tab === 'learn' && <Home d={d} idx={idx} />}
      {tab === 'glossary' && <Glossary key={params.get('term') ?? ''} terms={d.glossary} initial={params.get('term') ?? ''} />}
      {tab === 'calculators' && <Calculators d={d} initial={params.get('calc')} />}
      {tab === 'progress' && <ProgressTab d={d} idx={idx} />}
    </div>
  )
}

function NotFound({ what }: { what: string }) {
  return <EmptyState icon={<BookOpen className="h-5 w-5" />} title={`This ${what} could not be found`} body="It may have moved in the updated Learning Centre." action={<Link to="/learn" className="btn-primary">Back to the Learning Centre</Link>} />
}

// ------------------------------------------------------------------ home
function Home({ d, idx }: { d: LearnOverview; idx: ReturnType<typeof lessonIndex> }) {
  const p = d.progress
  const cont = p.continue ? idx[p.continue] : null
  const contStub = cont ? cont.module.lessons[cont.index] : null
  const started = p.lessons_done > 0 || Object.keys(p.quizzes).length > 0
  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="card card-pad md:col-span-2">
          <div className="flex items-start gap-3">
            <PlayCircle className="mt-0.5 h-8 w-8 shrink-0 text-brand-600" />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold uppercase tracking-wide muted">{started ? 'Continue learning' : 'Start here'}</div>
              {contStub && cont ? (
                <>
                  <div className="mt-0.5 font-semibold">{contStub.title}</div>
                  <div className="text-xs muted">{cont.module.title} · {LEVEL_LABEL[cont.module.level]} · {contStub.minutes} min</div>
                  <Link to={`/learn?lesson=${contStub.id}`} className="btn-primary mt-3">{started ? 'Continue' : 'Start the first lesson'}<ArrowRight className="h-4 w-4" /></Link>
                </>
              ) : <div className="mt-0.5 font-semibold">You have completed every lesson. Try a revision quiz.</div>}
            </div>
          </div>
        </div>
        <div className="card card-pad">
          <div className="flex items-center gap-3"><GraduationCap className="h-8 w-8 text-brand-600" />
            <div><div className="num text-2xl font-semibold">{p.lessons_done}/{p.lessons_total}</div><div className="text-xs muted">lessons completed</div></div></div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-ink-700" role="progressbar" aria-valuenow={p.lessons_done} aria-valuemax={p.lessons_total} aria-label="Lessons completed">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${(p.lessons_done / Math.max(1, p.lessons_total)) * 100}%` }} />
          </div>
          <div className="mt-2 text-xs muted">{p.modules_complete}/{p.modules_total} modules complete · <Link to="/learn?quiz=revision" className="font-medium text-brand-700 hover:underline dark:text-brand-300">Revision quiz</Link></div>
        </div>
      </div>
      {p.recent.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="inline-flex items-center gap-1 muted"><History className="h-3.5 w-3.5" />Recently viewed:</span>
          {p.recent.slice(0, 5).map((id) => idx[id] && <Link key={id} to={`/learn?lesson=${id}`} className="chip py-0.5">{idx[id].module.lessons[idx[id].index].title}</Link>)}
        </div>
      )}
      {d.levels.map((lv) => (
        <section key={lv.id} aria-labelledby={`lv-${lv.id}`}>
          <div className="mb-3">
            <h2 id={`lv-${lv.id}`} className="text-lg font-semibold">{lv.title}</h2>
            <p className="text-sm muted">{lv.summary}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {lv.modules.map((m) => <ModuleTile key={m.id} m={m} p={p} />)}
          </div>
        </section>
      ))}
      <p className="text-xs muted">Lessons are written for learning, with official sources listed on each one; formulas and quiz answers are checked automatically. Nothing here is a recommendation to buy or sell. For certification, use the official NISM workbooks.</p>
    </div>
  )
}

function ModuleTile({ m, p }: { m: ModuleCard; p: ProgressSummary }) {
  const mp = p.modules[m.id]
  const test = mp?.test
  return (
    <Link to={`/learn?module=${m.id}`} className="card card-pad card-hover flex flex-col" data-testid={`module-${m.id}`}>
      <div className="flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-wide">
        <span className="text-brand-600 dark:text-brand-300">{LEVEL_LABEL[m.level]}</span>
        <span className="inline-flex items-center gap-1 muted"><Clock className="h-3 w-3" />{m.minutes} min</span>
      </div>
      <h3 className="mt-1.5 font-semibold">{m.title}</h3>
      <p className="mt-1 line-clamp-2 text-sm muted">{m.summary}</p>
      <ul className="mt-2 space-y-0.5 text-xs muted">
        {m.lessons.slice(0, 3).map((l) => <li key={l.id} className="truncate">· {l.title}</li>)}
        {m.lessons.length > 3 && <li>+ {m.lessons.length - 3} more</li>}
      </ul>
      <div className="mt-auto pt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="muted">{mp?.lessons_done ?? 0}/{m.lessons.length} lessons</span>
          <span className={cx('font-medium', mp?.passed ? 'text-up' : 'muted')}>
            {mp?.passed ? <span className="inline-flex items-center gap-1"><CheckCircle2 className="h-3.5 w-3.5" />Test passed</span>
              : test ? `Test best ${test.best}/${test.total}` : 'Test not taken'}
          </span>
        </div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-ink-700">
          <div className="h-full rounded-full bg-brand-600" style={{ width: `${((mp?.lessons_done ?? 0) / m.lessons.length) * 100}%` }} />
        </div>
      </div>
    </Link>
  )
}

// ------------------------------------------------------------------ module, lesson and module test
function ModuleRoute({ overview, moduleId, lessonId, quiz }: { overview: LearnOverview; moduleId: string; lessonId: string | null; quiz: boolean }) {
  const q = useQuery({ queryKey: ['learn-module', moduleId], queryFn: () => api.get<ModuleFull>(`/learn/modules/${moduleId}`), staleTime: 30 * 60_000 })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return (q.error as { status?: number })?.status === 404 ? <NotFound what="module" /> : <ErrorState error={q.error} retry={q.refetch} />
  const m = q.data
  const stubs: Record<string, LessonStub> = {}
  for (const lv of overview.levels) for (const mm of lv.modules) for (const l of mm.lessons) stubs[l.id] = l
  const caseNames = Object.fromEntries(overview.case_companies.map((c) => [c.symbol, c.name]))
  if (lessonId) {
    const lesson = m.lessons.find((l) => l.id === lessonId)
    if (!lesson) return <NotFound what="lesson" />
    return <LessonView lesson={lesson} module={m} stubs={stubs} done={!!overview.progress.lessons[lesson.id]} caseNames={caseNames} reviewed={overview.reviewed} />
  }
  if (quiz) return <ModuleTest m={m} passMark={overview.pass_mark} />
  return <ModuleView m={m} overview={overview} />
}

function ModuleView({ m, overview }: { m: ModuleFull; overview: LearnOverview }) {
  const p = overview.progress
  const mp = p.modules[m.id]
  const titles: Record<string, string> = {}
  for (const lv of overview.levels) for (const mm of lv.modules) titles[mm.id] = mm.title
  return (
    <div className="mx-auto max-w-4xl space-y-5 page-enter">
      <Link className="btn-ghost px-0" to="/learn"><ChevronLeft className="h-4 w-4" />All modules</Link>
      <PageHeader eyebrow={`${LEVEL_LABEL[m.level]} module · ${m.minutes} min`} title={m.title} subtitle={m.summary} />
      <Card title="Lessons" subtitle={`${mp?.lessons_done ?? 0} of ${m.lessons.length} completed`}>
        <ol className="divide-y divide-slate-100 dark:divide-ink-700">
          {m.lessons.map((l, i) => {
            const done = !!p.lessons[l.id]
            return (
              <li key={l.id}>
                <Link to={`/learn?lesson=${l.id}`} className="flex items-center gap-3 py-3 hover:text-brand-700 dark:hover:text-brand-300">
                  {done ? <CheckCircle2 className="h-5 w-5 shrink-0 text-up" aria-label="Completed" /> : <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-slate-300 text-[11px] font-semibold dark:border-ink-500">{i + 1}</span>}
                  <span className="min-w-0 flex-1"><span className="block font-medium">{l.title}</span><span className="block truncate text-xs muted">{l.summary}</span></span>
                  <span className="shrink-0 text-xs muted">{l.minutes} min</span>
                  <ChevronRight className="h-4 w-4 shrink-0 muted" />
                </Link>
              </li>)
          })}
        </ol>
      </Card>
      <Card title={<span className="inline-flex items-center gap-1.5"><Trophy className="h-4 w-4 text-saffron-500" />Module test</span>}
        subtitle={`${m.test.length} questions: easy, medium and hard; concepts, numbers, statements and cases. Pass mark ${Math.round(overview.pass_mark * 100)}%.`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-sm">{mp?.test ? <>Best {mp.test.best}/{mp.test.total} · last {mp.test.last}/{mp.test.total} · {mp.test.attempts} attempt{mp.test.attempts === 1 ? '' : 's'}{mp.test.legacy ? ' (earlier version of this quiz)' : ''}</> : 'Not taken yet.'}</span>
          <Link to={`/learn?quiz=${m.id}`} className="btn-primary">{mp?.test ? 'Retake the test' : 'Take the test'}</Link>
        </div>
      </Card>
      <nav className="flex justify-between gap-2" aria-label="Module navigation">
        {m.prev_module ? <Link to={`/learn?module=${m.prev_module}`} className="btn-outline"><ChevronLeft className="h-4 w-4" />{titles[m.prev_module]}</Link> : <span />}
        {m.next_module ? <Link to={`/learn?module=${m.next_module}`} className="btn-outline">{titles[m.next_module]}<ChevronRight className="h-4 w-4" /></Link> : <span />}
      </nav>
    </div>
  )
}

function ModuleTest({ m, passMark }: { m: ModuleFull; passMark: number }) {
  return (
    <div className="mx-auto max-w-3xl space-y-5 page-enter">
      <Link className="btn-ghost px-0" to={`/learn?module=${m.id}`}><ChevronLeft className="h-4 w-4" />{m.title}</Link>
      <PageHeader eyebrow="Module test" title={m.title} subtitle="Answer every question, then submit to see your score, the correct answers, the calculations and why the other options are wrong." />
      <QuizRunner key={m.id} quizId={m.id} title="Module test" questions={m.test} passMark={passMark} />
    </div>
  )
}

function RevisionQuiz({ overview }: { overview: LearnOverview }) {
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1e9))
  const started = Object.entries(overview.progress.modules).filter(([, v]) => v.lessons_done > 0 || v.test).map(([k]) => k)
  const [scope, setScope] = useState<'mine' | 'all'>(started.length ? 'mine' : 'all')
  const mods = scope === 'mine' ? started : []
  const q = useQuery({ queryKey: ['learn-revision', seed, mods.join(',')],
    queryFn: () => api.get<{ questions: Question[] }>(`/learn/quiz/revision?n=10&seed=${seed}&modules=${encodeURIComponent(mods.join(','))}`) })
  return (
    <div className="mx-auto max-w-3xl space-y-5 page-enter">
      <Link className="btn-ghost px-0" to="/learn"><ChevronLeft className="h-4 w-4" />Learning Centre</Link>
      <PageHeader eyebrow="Revision" title="Revision quiz" subtitle="Ten questions drawn across modules and difficulty levels. Each set is different."
        actions={started.length > 0 && (
          <div className="flex gap-1.5">
            <button className={cx('chip', scope === 'mine' && 'chip-active')} onClick={() => setScope('mine')}>Modules I've started</button>
            <button className={cx('chip', scope === 'all' && 'chip-active')} onClick={() => setScope('all')}>All modules</button>
          </div>)} />
      {q.isLoading ? <Loading /> : q.error || !q.data ? <ErrorState error={q.error} retry={q.refetch} />
        : <QuizRunner key={seed + scope} quizId="revision" title="Revision quiz" questions={q.data.questions} passMark={overview.pass_mark}
          onRestart={() => setSeed(Math.floor(Math.random() * 1e9))} />}
    </div>
  )
}

// ------------------------------------------------------------------ calculators and progress tabs
function Calculators({ d, initial }: { d: LearnOverview; initial: string | null }) {
  const [, setParams] = useSearchParams()
  const id = initial && d.calculators.some((c) => c.id === initial) ? initial : d.calculators[0].id
  return (
    <div className="grid gap-4 lg:grid-cols-[230px_minmax(0,1fr)]">
      <nav aria-label="Calculators" className="flex gap-1.5 overflow-x-auto lg:flex-col lg:overflow-visible">
        {d.calculators.map((c) => (
          <button key={c.id} onClick={() => setParams({ tab: 'calculators', calc: c.id })}
            className={cx('flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-left text-sm', c.id === id ? 'bg-brand-50 font-medium text-brand-700 dark:bg-brand-500/15 dark:text-brand-200' : 'hover:bg-slate-100 dark:hover:bg-ink-800')}>
            <Calculator className="h-4 w-4 shrink-0" />{c.title}
          </button>
        ))}
      </nav>
      <CalculatorView key={id} id={id} />
    </div>
  )
}

function ProgressTab({ d, idx }: { d: LearnOverview; idx: ReturnType<typeof lessonIndex> }) {
  const p = d.progress
  const qc = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const reset = useMutation({
    mutationFn: () => api.del<ProgressSummary>('/learn/progress'),
    onSuccess: (s) => { qc.setQueryData<LearnOverview>(['learn'], (o) => (o ? { ...o, progress: s } : o)); setConfirm(false) },
  })
  const lessonQuizzes = Object.entries(p.quizzes).filter(([k]) => idx[k])
  return (
    <div className="space-y-4">
      <Notice>Your progress is saved to your EquityPilot account and is visible only to you. It records the lessons you complete, quiz scores and recently viewed lessons, nothing about your investments or opinions.</Notice>
      <Card title="Modules" pad={false}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead><tr className="table-head"><th className="px-4 py-2">Module</th><th className="px-3 py-2">Level</th><th className="px-3 py-2">Lessons</th><th className="px-3 py-2">Module test</th><th className="px-3 py-2">Status</th></tr></thead>
            <tbody>
              {d.levels.flatMap((lv) => lv.modules).map((m) => {
                const mp = p.modules[m.id]
                return (
                  <tr key={m.id} className="border-t border-slate-100 dark:border-ink-700">
                    <td className="px-4 py-2"><Link className="font-medium hover:underline" to={`/learn?module=${m.id}`}>{m.title}</Link></td>
                    <td className="px-3 py-2 muted">{LEVEL_LABEL[m.level]}</td>
                    <td className="num px-3 py-2">{mp?.lessons_done ?? 0}/{m.lessons.length}</td>
                    <td className="num px-3 py-2">{mp?.test ? `${mp.test.best}/${mp.test.total}` : '—'}</td>
                    <td className={cx('px-3 py-2', mp?.complete ? 'text-up' : 'muted')}>{mp?.complete ? 'Complete' : mp?.passed ? 'Test passed' : mp?.lessons_done ? 'In progress' : 'Not started'}</td>
                  </tr>)
              })}
            </tbody>
          </table>
        </div>
      </Card>
      {lessonQuizzes.length > 0 && (
        <Card title="Knowledge checks">
          <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
            {lessonQuizzes.map(([k, r]) => <li key={k} className="flex justify-between gap-2"><Link className="truncate hover:underline" to={`/learn?lesson=${k}`}>{idx[k].module.lessons[idx[k].index].title}</Link><span className="num muted">{r.best}/{r.total}</span></li>)}
          </ul>
        </Card>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Link to="/learn?quiz=revision" className="btn-outline"><Shuffle className="h-4 w-4" />Revision quiz</Link>
        {!confirm ? <button className="btn-ghost" onClick={() => setConfirm(true)}>Reset my progress</button> : (
          <span className="flex items-center gap-2 text-sm">Clear all lessons and scores?
            <button className="btn-danger" disabled={reset.isPending} onClick={() => reset.mutate()}>Yes, reset</button>
            <button className="btn-ghost" onClick={() => setConfirm(false)}>Cancel</button></span>
        )}
      </div>
    </div>
  )
}
