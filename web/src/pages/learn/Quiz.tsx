import { CheckCircle2, MessageSquareText, RotateCcw, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { cx, Notice } from '../../components/ui'
import { formatAnswer, isCorrect, numericHint, parseNumber, type Response } from './quizLogic'
import { KIND_LABEL, type Question } from './types'
import { useProgress } from './useProgress'

const LEVEL_TONE: Record<string, string> = { easy: 'text-up', medium: 'text-amber-600 dark:text-saffron-400', hard: 'text-down' }

function askWhy(q: Question, r?: Response) {
  const mine = q.type === 'mcq' ? (r?.choice !== undefined ? `I chose "${q.options![r.choice]}"` : '') : (r?.value ? `I answered ${r.value}` : '')
  return `/assistant?q=${encodeURIComponent(`Why is my quiz answer wrong? Question ${q.id}: ${mine}`.trim())}`
}

/** One question. `reveal` shows the answer, explanation, calculation and why each wrong option is wrong. */
export function QuestionCard({ q, n, response, onChange, reveal, onCheck }: {
  q: Question; n: number; response?: Response; onChange: (r: Response) => void; reveal: boolean; onCheck?: () => void
}) {
  const ok = isCorrect(q, response)
  const v = parseNumber(response?.value)
  const hint = reveal && !ok && v !== null && q.type === 'num' ? numericHint(q, v) : null
  return (
    <li className="rounded-2xl border border-slate-200/80 p-4 dark:border-ink-700" data-testid={`q-${q.id}`}>
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide">
        <span className="muted">Question {n}</span>
        <span className={LEVEL_TONE[q.level]}>{q.level}</span>
        <span className="muted">{KIND_LABEL[q.kind] ?? q.kind}</span>
      </div>
      <p className="font-medium leading-relaxed">{q.q}</p>
      {q.type === 'mcq' ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label={`Question ${n} options`}>
          {q.options!.map((o, j) => {
            const chosen = response?.choice === j
            const state = reveal ? (j === q.answer ? 'right' : chosen ? 'wrong' : '') : ''
            return (
              <button key={j} type="button" role="radio" aria-checked={chosen} disabled={reveal}
                onClick={() => { onChange({ choice: j }); onCheck?.() }}
                className={cx('flex items-start gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition',
                  state === 'right' ? 'border-up bg-up/10' : state === 'wrong' ? 'border-down bg-down/10'
                    : chosen ? 'border-brand-500 bg-brand-50 dark:bg-ink-700' : 'border-slate-200 hover:border-brand-300 dark:border-ink-600')}>
                <span className="mt-px shrink-0 font-semibold muted">{String.fromCharCode(65 + j)}.</span>
                <span className="flex-1">{o}</span>
                {state === 'right' && <CheckCircle2 className="h-4 w-4 shrink-0 text-up" />}
                {state === 'wrong' && <XCircle className="h-4 w-4 shrink-0 text-down" />}
              </button>)
          })}
        </div>
      ) : (
        <form className="mt-3 flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); onCheck?.() }}>
          <label className="sr-only" htmlFor={`a-${q.id}`}>Your answer</label>
          {q.unit === '₹' && <span className="muted">₹</span>}
          <input id={`a-${q.id}`} className="input w-40" inputMode="decimal" disabled={reveal} placeholder="Your answer"
            value={response?.value ?? ''} onChange={(e) => onChange({ value: e.target.value })} />
          {q.unit && q.unit !== '₹' && <span className="text-sm muted">{q.unit}</span>}
          {onCheck && !reveal && <button className="btn-outline" type="submit" disabled={parseNumber(response?.value) === null}>Check</button>}
        </form>
      )}
      {reveal && (
        <div className="mt-3 space-y-2 text-sm" aria-live="polite">
          <p className={cx('font-semibold', ok ? 'text-up' : 'text-down')}>
            {ok ? 'Correct.' : response && (response.choice !== undefined || response.value) ? 'Not quite.' : 'Not answered.'}
            {' '}<span className="font-normal text-slate-700 dark:text-slate-200">Answer: {q.type === 'mcq' ? q.options![q.answer] : formatAnswer(q)}</span>
          </p>
          {hint && <p className="text-amber-700 dark:text-saffron-400">{hint}</p>}
          <p>{q.explain}</p>
          {q.steps && <p className="rounded-xl bg-slate-50 px-3 py-2 font-mono text-[13px] dark:bg-ink-800">{q.steps}</p>}
          {q.type === 'mcq' && q.wrong && q.wrong.some(Boolean) && (
            <details className="group" open={!ok}>
              <summary className="cursor-pointer text-xs font-medium text-brand-700 dark:text-brand-300">Why the other options are wrong</summary>
              <ul className="mt-1.5 space-y-1 text-[13px] muted">
                {q.options!.map((o, j) => q.wrong![j] && <li key={j}><span className="font-medium text-slate-700 dark:text-slate-200">{String.fromCharCode(65 + j)}. {o}</span>: {q.wrong![j]}</li>)}
              </ul>
            </details>
          )}
          {!ok && <Link to={askWhy(q, response)} className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline dark:text-brand-300"><MessageSquareText className="h-3.5 w-3.5" />Ask the AI Assistant why</Link>}
        </div>
      )}
    </li>
  )
}

/** Knowledge check inside a lesson: instant feedback per question; the score is saved once every question is checked. */
export function KnowledgeCheck({ quizId, questions }: { quizId: string; questions: Question[] }) {
  const [resp, setResp] = useState<Record<string, Response>>({})
  const [shown, setShown] = useState<Record<string, boolean>>({})
  const save = useSaveQuiz()
  const check = (id: string, latest?: Response) => {
    const all = latest ? { ...resp, [id]: latest } : resp
    const next = { ...shown, [id]: true }
    setShown(next)
    if (questions.every((q) => next[q.id])) {
      save.mutate({ quiz: quizId, score: questions.filter((q) => isCorrect(q, all[q.id])).length, total: questions.length })
    }
  }
  return (
    <ol className="space-y-3">
      {questions.map((q, i) => (
        <QuestionCard key={q.id} q={q} n={i + 1} response={resp[q.id]} reveal={!!shown[q.id]}
          onChange={(r) => { setResp((p) => ({ ...p, [q.id]: r })); if (q.type === 'mcq') check(q.id, r) }}
          onCheck={q.type === 'num' ? () => check(q.id) : undefined} />
      ))}
    </ol>
  )
}

function useSaveQuiz() {
  const save = useProgress()
  return { mutate: (b: { quiz: string; score: number; total: number }) => save.mutate(b) }
}

/** Module test or revision quiz: answer everything, then submit to see the score and a full review. */
export function QuizRunner({ quizId, title, questions, passMark, onRestart }: {
  quizId: string; title: string; questions: Question[]; passMark: number; onRestart?: () => void
}) {
  const [resp, setResp] = useState<Record<string, Response>>({})
  const [done, setDone] = useState(false)
  const save = useSaveQuiz()
  const answered = questions.filter((q) => (q.type === 'mcq' ? resp[q.id]?.choice !== undefined : parseNumber(resp[q.id]?.value) !== null)).length
  const score = useMemo(() => questions.filter((q) => isCorrect(q, resp[q.id])).length, [questions, resp])
  const passed = score >= Math.ceil(passMark * questions.length)
  const submit = () => { setDone(true); save.mutate({ quiz: quizId, score, total: questions.length }); window.scrollTo?.({ top: 0, behavior: 'smooth' }) }
  const restart = () => { setResp({}); setDone(false); onRestart?.() }
  const byLevel = (['easy', 'medium', 'hard'] as const).map((l) => [l, questions.filter((q) => q.level === l)] as const).filter(([, qs]) => qs.length)
  return (
    <div className="space-y-4">
      {done && (
        <Notice tone={passed ? 'success' : 'warn'}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-semibold">{title}: {score}/{questions.length} ({Math.round((score / questions.length) * 100)}%)</div>
              <div className="text-xs muted">
                {passed ? 'Passed.' : `The pass mark is ${Math.round(passMark * 100)}%. Review the explanations below and try again.`}{' '}
                {byLevel.map(([l, qs]) => `${l}: ${qs.filter((q) => isCorrect(q, resp[q.id])).length}/${qs.length}`).join(' · ')}
              </div>
            </div>
            <button className="btn-outline" onClick={restart}><RotateCcw className="h-4 w-4" />{onRestart ? 'New set' : 'Retake'}</button>
          </div>
        </Notice>
      )}
      <ol className="space-y-3">
        {questions.map((q, i) => (
          <QuestionCard key={q.id} q={q} n={i + 1} response={resp[q.id]} reveal={done} onChange={(r) => setResp((p) => ({ ...p, [q.id]: r }))} />
        ))}
      </ol>
      {!done && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs muted">{answered}/{questions.length} answered</span>
          <button className="btn-primary" disabled={answered < questions.length} onClick={submit}>Submit answers</button>
        </div>
      )}
    </div>
  )
}
