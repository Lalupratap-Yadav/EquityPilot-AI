import type { Question } from './types'

/** Grading helpers shared by the quiz components (kept separate so components hot-reload cleanly). */
export type Response = { choice?: number; value?: string }

export function isCorrect(q: Question, r?: Response): boolean {
  if (!r) return false
  if (q.type === 'mcq') return r.choice === q.answer
  const v = parseNumber(r.value)
  return v !== null && Math.abs(v - q.answer) <= (q.tolerance ?? 0.05)
}

export function parseNumber(s?: string): number | null {
  if (!s) return null
  const t = s.replace(/[,₹%x\s]/gi, '')
  if (!/^-?\d*\.?\d+$/.test(t)) return null
  return Number(t)
}

/** Common slips in numerical answers: fraction vs percentage, sign. */
export function numericHint(q: Question, v: number): string | null {
  const tol = q.tolerance ?? 0.05
  if (q.answer && Math.abs(v * 100 - q.answer) <= tol) return 'You may have entered a fraction (0.15) where a percentage (15) was asked for.'
  if (q.answer && Math.abs(v / 100 - q.answer) <= Math.max(tol, Math.abs(q.answer) * 0.01)) return 'You may have entered a percentage where a plain number was asked for.'
  if (q.answer && Math.abs(-v - q.answer) <= tol) return `Check the sign: the answer is ${q.answer < 0 ? 'negative' : 'positive'}.`
  return null
}

export const formatAnswer = (q: Question) => {
  const v = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(q.answer)
  if (!q.unit) return v
  if (q.unit === '₹') return '₹' + v
  return ['%', 'x'].includes(q.unit) ? v + q.unit : `${v} ${q.unit}`
}

