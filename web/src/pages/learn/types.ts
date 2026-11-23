export interface Question {
  id: string; type: 'mcq' | 'num'; q: string; options?: string[]; answer: number; explain: string
  wrong?: (string | null)[]; steps?: string | null; unit?: string; tolerance?: number
  level: 'easy' | 'medium' | 'hard'; kind: string; source: { lesson?: string; module: string }
}
export interface RatioCard { key: string; name: string; what?: string; why?: string; read?: string; example?: string; formula?: string; limits?: string; unsuitable?: string }
export interface ToolLink { tool: string; label: string; to: string; text: string }
export interface SourceLink { key: string; name: string; url: string }
export interface Lesson {
  id: string; title: string; summary: string; minutes: number; module: string; level: string; prev: string | null; next: string | null
  concept: string; why: string; formulas: string[]; rules: string[]; example: string; interpret: string; mistakes: string[]
  application: string; revision: string[]; check: Question[]; detail: string | null
  calculators: { id: string; title: string }[]; tools: ToolLink[]; sources: SourceLink[]; terms: { term: string; definition: string }[]
  cards: RatioCard[]; case: string[]
}
export interface LessonStub { id: string; title: string; minutes: number; summary: string }
export interface ModuleCard { id: string; title: string; level: string; summary: string; minutes: number; lessons: LessonStub[]; questions: number }
export interface ModuleFull extends Omit<ModuleCard, 'lessons'> { lessons: Lesson[]; test: Question[]; prev_module: string | null; next_module: string | null }
export interface Level { id: string; title: string; summary: string; modules: ModuleCard[] }
export interface QuizRecord { best: number; last: number; total: number; attempts: number; updated?: string; legacy?: boolean }
export interface ModuleProgress { lessons_done: number; lessons_total: number; test: QuizRecord | null; passed: boolean; complete: boolean }
export interface ProgressSummary {
  modules: Record<string, ModuleProgress>; lessons_done: number; lessons_total: number; modules_complete: number; modules_total: number
  continue: string | null; recent: string[]; lessons: Record<string, { done: string }>; quizzes: Record<string, QuizRecord>; questions_total: number
}
export interface Term {
  term: string; aliases: string[]; definition: string; formula?: string | null; interpretation?: string | null; example?: string | null
  related: string[]; lessons: { id: string; title: string; module: string }[]; letter: string; ratio?: string | null
}
export interface LearnOverview {
  levels: Level[]; reviewed: string; pass_mark: number; calculators: { id: string; title: string }[]
  counts: { modules: number; lessons: number; questions: number; terms: number }
  progress: ProgressSummary; glossary: Term[]; sources: Record<string, { name: string; url: string }>; case_companies: { symbol: string; name: string }[]
}

export const LEVEL_LABEL: Record<string, string> = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }
export const KIND_LABEL: Record<string, string> = { concept: 'Concept', numerical: 'Numerical', statement: 'Statement reading', case: 'Case', rule: 'Rules' }

/** Lesson id -> its module card and position, from the overview. */
export function lessonIndex(levels: Level[]): Record<string, { module: ModuleCard; index: number }> {
  const out: Record<string, { module: ModuleCard; index: number }> = {}
  for (const lv of levels) for (const m of lv.modules) m.lessons.forEach((l, index) => { out[l.id] = { module: m, index } })
  return out
}

export const reviewedLabel = (iso: string) => new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
