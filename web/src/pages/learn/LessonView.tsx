import { ArrowRight, BookMarked, CheckCircle2, ChevronLeft, ChevronRight, Circle, Clock, ExternalLink, Lightbulb, MessageSquareText, Sigma, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Markdown } from '../../components/Markdown'
import { cx } from '../../components/ui'
import { CalculatorView } from './Calculators'
import { CaseStudy } from './CaseStudy'
import { KnowledgeCheck } from './Quiz'
import { LEVEL_LABEL, reviewedLabel, type Lesson, type LessonStub, type ModuleFull, type RatioCard } from './types'
import { useProgress } from './useProgress'

function Part({ n, title, icon, children, id }: { n: number; title: string; icon?: ReactNode; children: ReactNode; id?: string }) {
  return (
    <section className="card card-pad" aria-labelledby={id}>
      <h2 id={id} className="mb-2.5 flex items-center gap-2 section-title">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-xs font-semibold text-brand-700 dark:bg-brand-500/15 dark:text-brand-200">{n}</span>
        {icon}{title}
      </h2>
      <div className="text-[15px] leading-relaxed">{children}</div>
    </section>
  )
}

function Card({ c, open }: { c: RatioCard; open?: boolean }) {
  const rows: [string, string | undefined][] = [['Meaning', c.what], ['Formula', c.formula], ['Why it matters', c.why], ['How to read it', c.read],
    ['Worked example', c.example], ['Limitations', c.limits], ['When it is not suitable', c.unsuitable]]
  return (
    <details className="rounded-xl border border-slate-200/80 px-3 py-2 dark:border-ink-700" open={open}>
      <summary className="cursor-pointer text-sm font-semibold">{c.name}</summary>
      <dl className="mt-2 space-y-1.5 text-sm">
        {rows.filter(([, v]) => v).map(([k, v]) => (
          <div key={k}><dt className="text-[11px] font-semibold uppercase tracking-wide muted">{k}</dt><dd className={k === 'Formula' ? 'font-mono text-[13px]' : ''}>{v}</dd></div>
        ))}
      </dl>
    </details>
  )
}

export function LessonView({ lesson, module, stubs, done, caseNames, reviewed }: {
  lesson: Lesson; module: ModuleFull; stubs: Record<string, LessonStub>; done: boolean; caseNames: Record<string, string>; reviewed: string
}) {
  const progress = useProgress()
  const viewed = useProgress(true)
  const sent = useRef<string | null>(null)
  useEffect(() => {
    if (sent.current !== lesson.id) { sent.current = lesson.id; viewed.mutate({ viewed: lesson.id }) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lesson.id])
  const idx = module.lessons.findIndex((l) => l.id === lesson.id)
  const topic = lesson.terms[0]?.term ?? lesson.title
  const ask = (q: string) => `/assistant?q=${encodeURIComponent(q)}`
  const prev = lesson.prev ? stubs[lesson.prev] : null, next = lesson.next ? stubs[lesson.next] : null
  const nav = (
    <nav className="flex items-stretch justify-between gap-2" aria-label="Lesson navigation">
      {prev ? <Link to={`/learn?lesson=${prev.id}`} className="btn-outline min-w-0 max-w-[48%] justify-start"><ChevronLeft className="h-4 w-4 shrink-0" /><span className="truncate">{prev.title}</span></Link> : <span />}
      {next ? <Link to={`/learn?lesson=${next.id}`} className="btn-outline min-w-0 max-w-[48%] justify-end"><span className="truncate">{next.title}</span><ChevronRight className="h-4 w-4 shrink-0" /></Link> : <span />}
    </nav>
  )
  return (
    <article className="mx-auto max-w-3xl space-y-4 page-enter">
      <div className="flex flex-wrap items-center gap-1.5 text-sm muted">
        <Link to="/learn" className="hover:text-brand-700 dark:hover:text-brand-300">Learning Centre</Link><ChevronRight className="h-3.5 w-3.5" />
        <Link to={`/learn?module=${module.id}`} className="hover:text-brand-700 dark:hover:text-brand-300">{module.title}</Link>
      </div>
      <header>
        <div className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-300">{LEVEL_LABEL[lesson.level]} · Lesson {idx + 1} of {module.lessons.length}</div>
        <h1 className="mt-1 text-2xl font-semibold sm:text-[28px]">{lesson.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs muted">
          <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{lesson.minutes} min</span>
          <span>{lesson.check.length} check questions</span>
          {done && <span className="inline-flex items-center gap-1 font-medium text-up"><CheckCircle2 className="h-3.5 w-3.5" />Completed</span>}
        </div>
      </header>

      <Part n={1} title="Concept" id="p-concept"><Markdown text={lesson.concept} /></Part>
      <Part n={2} title="Why it matters" id="p-why"><p>{lesson.why}</p></Part>
      <Part n={3} title={lesson.formulas.length ? 'Formula' : 'Key rules'} icon={<Sigma className="h-4 w-4 text-brand-600" />} id="p-formula">
        {lesson.formulas.length > 0 && <ul className="space-y-2">{lesson.formulas.map((f) => <li key={f} className="rounded-xl bg-slate-50 px-3 py-2 font-mono text-[13px] dark:bg-ink-800">{f}</li>)}</ul>}
        {lesson.rules.length > 0 && (
          <>
            {lesson.formulas.length > 0 && <h3 className="mb-1.5 mt-4 text-sm font-semibold">Key rules</h3>}
            <ul className="list-disc space-y-1.5 pl-5 text-sm">{lesson.rules.map((r) => <li key={r}>{r}</li>)}</ul>
            <p className="mt-2 text-xs muted">Rules checked against the official sources below on {reviewedLabel(reviewed)}. Regulations change: confirm the current version on the regulator's website.</p>
          </>
        )}
      </Part>
      <Part n={4} title="Simple example" id="p-example">
        <Markdown text={lesson.example} />
        {lesson.case.length > 0 && <div className="mt-4"><CaseStudy symbols={lesson.case} names={caseNames} /></div>}
        {lesson.calculators.length > 0 && (
          <div className="mt-4 space-y-3">
            <h3 className="text-sm font-semibold">Try it yourself</h3>
            {lesson.calculators.map((c) => <CalculatorView key={c.id} id={c.id} />)}
          </div>
        )}
      </Part>
      <Part n={5} title="Interpretation" id="p-interpret"><p>{lesson.interpret}</p></Part>
      <Part n={6} title="Common mistakes" icon={<TriangleAlert className="h-4 w-4 text-amber-600" />} id="p-mistakes">
        <ul className="space-y-1.5 text-sm">{lesson.mistakes.map((m) => <li key={m} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-down" />{m}</li>)}</ul>
      </Part>
      <Part n={7} title="Real-world application" id="p-apply">
        <p>{lesson.application}</p>
        {lesson.tools.length > 0 && (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {lesson.tools.map((t) => (
              <Link key={t.to + t.text} to={t.to} className="group flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm hover:border-brand-300 dark:border-ink-600">
                <span><span className="font-medium">{t.label}</span><span className="block text-xs muted">{t.text}</span></span>
                <ArrowRight className="h-4 w-4 shrink-0 text-brand-600 transition-transform group-hover:translate-x-0.5" />
              </Link>
            ))}
          </div>
        )}
      </Part>
      <Part n={8} title="Quick revision" icon={<Lightbulb className="h-4 w-4 text-saffron-500" />} id="p-revision">
        <ul className="space-y-1.5 text-sm">{lesson.revision.map((r) => <li key={r} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />{r}</li>)}</ul>
      </Part>
      <Part n={9} title="Knowledge check" id="p-check">
        <KnowledgeCheck key={lesson.id} quizId={lesson.id} questions={lesson.check} />
      </Part>

      {(lesson.cards.length > 0 || lesson.terms.length > 0 || lesson.detail) && (
        <section className="card card-pad space-y-3">
          <h2 className="section-title flex items-center gap-2"><BookMarked className="h-4 w-4 text-brand-600" />Go deeper (optional)</h2>
          {lesson.detail && <details><summary className="cursor-pointer text-sm font-semibold">More detail</summary><div className="mt-2 text-sm"><Markdown text={lesson.detail} /></div></details>}
          {lesson.cards.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Ratio cards: meaning, formula, interpretation, limits and when not to use them</h3>
              {lesson.cards.map((c, i) => <Card key={c.key} c={c} open={i === 0} />)}
            </div>
          )}
          {lesson.terms.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm font-semibold">Key terms in this lesson ({lesson.terms.length})</summary>
              <dl className="mt-2 space-y-1.5 text-sm">
                {lesson.terms.map((t) => <div key={t.term}><dt className="inline font-medium"><Link to={`/learn?tab=glossary&term=${encodeURIComponent(t.term)}`} className="hover:underline">{t.term}</Link>: </dt><dd className="inline muted">{t.definition}</dd></div>)}
              </dl>
            </details>
          )}
        </section>
      )}

      <section className="card card-pad">
        <h2 className="section-title flex items-center gap-2"><MessageSquareText className="h-4 w-4 text-brand-600" />Ask the AI Assistant</h2>
        <p className="mt-1 text-xs muted">Works free with the offline analyst; answers are built from this curriculum, and made-up numbers are labelled as illustrative.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link className="chip" to={ask(`Explain ${topic} in simple words`)}>Explain more simply</Link>
          <Link className="chip" to={ask(`Give me another numerical example of ${topic}`)}>Another numerical example</Link>
          <Link className="chip" to={ask(`How do I calculate ${topic} step by step?`)}>Formula step by step</Link>
          <Link className="chip" to={ask(`Practice questions on ${topic}`)}>Practice questions</Link>
        </div>
      </section>

      {lesson.sources.length > 0 && (
        <section className="rounded-2xl border border-slate-200/80 px-4 py-3 text-sm dark:border-ink-700" aria-label="Sources">
          <div className="text-[11px] font-semibold uppercase tracking-wide muted">Official sources · content reviewed {reviewedLabel(reviewed)}</div>
          <ul className="mt-1.5 space-y-1">
            {lesson.sources.map((s) => <li key={s.key}><a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-700 hover:underline dark:text-brand-300">{s.name}<ExternalLink className="h-3 w-3" /></a></li>)}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-ink-800">
        <span className="text-sm">{done ? 'You have completed this lesson.' : 'Finished reading and checking your understanding?'}</span>
        <div className="flex gap-2">
          <button className={cx(done ? 'btn-outline' : 'btn-primary')} disabled={progress.isPending}
            onClick={() => progress.mutate({ lesson: lesson.id, done: !done })}>
            {done ? <><Circle className="h-4 w-4" />Mark as not done</> : <><CheckCircle2 className="h-4 w-4" />Mark complete</>}
          </button>
          {next && <Link to={`/learn?lesson=${next.id}`} className="btn-outline" onClick={() => { if (!done) progress.mutate({ lesson: lesson.id, done: true }) }}>{done ? 'Next lesson' : 'Complete and continue'}<ChevronRight className="h-4 w-4" /></Link>}
        </div>
      </div>
      {nav}
    </article>
  )
}
