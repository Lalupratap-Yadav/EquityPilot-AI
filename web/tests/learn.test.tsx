import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import Learn from '../src/pages/Learn'
import { mockApi, renderPage, requested } from './helpers'

const mcq = (id: string, answer = 1) => ({
  id, type: 'mcq', q: `Question ${id}: if the discount rate rises, present value…`, options: ['Rises', 'Falls', 'Is unchanged', 'Doubles'], answer,
  explain: 'A larger rate enlarges the denominator.', wrong: ['A higher rate cannot raise PV.', null, 'PV depends on the rate.', 'Nothing doubles here.'],
  steps: null, level: 'easy', kind: 'concept', source: { lesson: 'money-tvm', module: 'money' },
})
const numq = (id: string) => ({
  id, type: 'num', q: 'PAT ₹90 crore; average equity ₹600 crore. What is ROE, in %?', answer: 15, unit: '%', tolerance: 0.05,
  explain: 'Use average equity.', steps: '90 ÷ 600 = 15%', level: 'medium', kind: 'numerical', source: { lesson: 'money-tvm', module: 'money' },
})
const lesson = (id: string, title: string, prev: string | null, next: string | null) => ({
  id, title, summary: `${title} summary.`, minutes: 4, module: 'money', level: 'beginner', prev, next,
  concept: 'A rupee today is worth **more** than a rupee later.', why: 'Every investment compares money at different dates.',
  formulas: ['FV = PV × (1 + r)^n'], rules: [], example: '_Illustrative numbers, not company data._\n- ₹10,000 at 8% for 3 years grows to ₹12,597.',
  interpret: 'PV falls when the rate rises.', mistakes: ['Typing 8 instead of 0.08.', 'Mixing monthly and yearly rates.', 'Ignoring timing.'],
  application: 'Use it to compare a deposit with a bond.', revision: ['Money today is worth more.', 'FV compounds forward.', 'PV discounts back.'],
  check: [mcq(`${id}:c1`), numq(`${id}:c2`)], detail: null, calculators: [{ id: 'interest', title: 'Simple vs compound interest' }],
  tools: [{ tool: 'valuation', label: 'Valuation Lab', to: '/valuation', text: 'See discounting in a DCF.' }],
  sources: [{ key: 'rbi', name: 'Reserve Bank of India', url: 'https://www.rbi.org.in/' }], terms: [{ term: 'Present value', definition: 'Today’s value of a future amount.' }],
  cards: [], case: [],
})
const progress = (over = {}) => ({
  modules: { money: { lessons_done: 1, lessons_total: 2, test: { best: 6, last: 6, total: 8, attempts: 1 }, passed: true, complete: false } },
  lessons_done: 1, lessons_total: 2, modules_complete: 0, modules_total: 1, continue: 'money-interest', recent: ['money-tvm'],
  lessons: { 'money-tvm': { done: '23 Nov 2026' } }, quizzes: { money: { best: 6, last: 6, total: 8, attempts: 1 } }, questions_total: 12, ...over,
})
const OVERVIEW = {
  levels: [{ id: 'beginner', title: 'Beginner', summary: 'Money and markets.', modules: [{ id: 'money', title: 'Money, interest and returns', level: 'beginner',
    summary: 'Time value of money and interest.', minutes: 8, questions: 2,
    lessons: [{ id: 'money-tvm', title: 'Time value of money', minutes: 4, summary: 'A rupee today…' }, { id: 'money-interest', title: 'Simple and compound interest', minutes: 4, summary: 'Interest…' }] }] }],
  reviewed: '2026-11-23', pass_mark: 0.6, calculators: [{ id: 'interest', title: 'Simple vs compound interest' }, { id: 'dcf', title: 'Basic DCF' }],
  counts: { modules: 1, lessons: 2, questions: 12, terms: 3 }, progress: progress(), sources: {}, case_companies: [],
  glossary: [
    { term: 'ROCE', aliases: ['return on capital employed'], definition: 'Pre-tax operating return on all long-term capital.', formula: 'ROCE = EBIT / Capital employed',
      related: ['ROE'], lessons: [{ id: 'money-tvm', title: 'Time value of money', module: 'money' }], letter: 'R' },
    { term: 'ROE', aliases: ['return on equity'], definition: 'Profit for each rupee of shareholders’ capital.', related: ['ROCE'], lessons: [], letter: 'R' },
    { term: 'Debt to equity', aliases: ['d/e'], definition: 'Borrowings relative to shareholders’ funds.', related: [], lessons: [], letter: 'D' },
  ],
}
const MODULE = {
  id: 'money', title: 'Money, interest and returns', level: 'beginner', summary: 'Time value of money and interest.', minutes: 8, questions: 2,
  lessons: [lesson('money-tvm', 'Time value of money', null, 'money-interest'), lesson('money-interest', 'Simple and compound interest', 'money-tvm', null)],
  test: [mcq('money:t1'), numq('money:t2')], prev_module: null, next_module: null,
}

function api(extra: Record<string, unknown> = {}) {
  return mockApi({ '/learn/modules/money': MODULE, '/learn/progress': (_u: URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body ?? '{}'))
    return progress({ recent: body.viewed ? [body.viewed] : ['money-tvm'], lessons: body.lesson ? { [body.lesson]: { done: 'now' } } : {}, lessons_done: body.lesson ? 1 : 0 })
  }, '/learn': OVERVIEW, ...extra })
}
const posts = (fn: ReturnType<typeof mockApi>) => fn.mock.calls.filter((c) => (c[1] as RequestInit | undefined)?.method === 'POST').map((c) => JSON.parse(String((c[1] as RequestInit).body)))

describe('Learning Centre', () => {
  it('home shows levels, module cards with reading time, completion and quiz status, and continue learning', async () => {
    api()
    renderPage(<Learn />, { route: '/learn' })
    expect(await screen.findByRole('heading', { name: 'Beginner' })).toBeInTheDocument()
    const card = screen.getByTestId('module-money')
    expect(within(card).getByText('8 min')).toBeInTheDocument()
    expect(within(card).getByText('1/2 lessons')).toBeInTheDocument()
    expect(within(card).getByText('Test passed')).toBeInTheDocument()
    expect(screen.getByText('Continue learning')).toBeInTheDocument()
    expect(screen.getAllByText('Simple and compound interest').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Continue/ })).toHaveAttribute('href', '/learn?lesson=money-interest')
    expect(screen.getByText(/reviewed 23 Nov 2026/)).toBeInTheDocument()
  })

  it('a lesson shows all nine parts, records the view, checks answers and links the assistant', async () => {
    const fn = api()
    renderPage(<Learn />, { route: '/learn?lesson=money-tvm' })
    expect(await screen.findByRole('heading', { name: 'Time value of money', level: 1 })).toBeInTheDocument()
    for (const part of ['Concept', 'Why it matters', 'Formula', 'Simple example', 'Interpretation', 'Common mistakes', 'Real-world application', 'Quick revision', 'Knowledge check']) {
      expect(screen.getByRole('heading', { name: new RegExp(part) })).toBeInTheDocument()
    }
    await waitFor(() => expect(posts(fn)).toContainEqual({ viewed: 'money-tvm' }))
    expect(screen.getByTestId('calculator')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Valuation Lab/ })).toHaveAttribute('href', '/valuation')
    expect(screen.getByRole('link', { name: /Reserve Bank of India/ })).toHaveAttribute('href', 'https://www.rbi.org.in/')
    // multiple choice: instant feedback with why the other options are wrong
    const q1 = screen.getByTestId('q-money-tvm:c1')
    await userEvent.click(within(q1).getByRole('radio', { name: /Rises/ }))
    expect(within(q1).getByText('Not quite.')).toBeInTheDocument()
    expect(within(q1).getByText(/A higher rate cannot raise PV/)).toBeInTheDocument()
    expect(within(q1).getByRole('link', { name: /Ask the AI Assistant why/ }).getAttribute('href')).toContain(encodeURIComponent('Question money-tvm:c1'))
    // numerical: a fraction instead of a percentage gets a hint; the score is saved once all questions are checked
    const q2 = screen.getByTestId('q-money-tvm:c2')
    await userEvent.type(within(q2).getByRole('textbox'), '0.15')
    await userEvent.click(within(q2).getByRole('button', { name: 'Check' }))
    expect(within(q2).getByText(/entered a fraction/)).toBeInTheDocument()
    expect(within(q2).getByText('90 ÷ 600 = 15%')).toBeInTheDocument()
    await waitFor(() => expect(posts(fn)).toContainEqual({ quiz: 'money-tvm', score: 0, total: 2 }))
    expect(screen.getByRole('link', { name: 'Explain more simply' }).getAttribute('href')).toContain(encodeURIComponent('Explain Present value in simple words'))
    // completion and next lesson
    await userEvent.click(screen.getByRole('button', { name: /Mark as not done|Mark complete/ }))
    await waitFor(() => expect(posts(fn).some((b) => b.lesson === 'money-tvm')).toBe(true))
    expect(screen.getAllByRole('link', { name: /Simple and compound interest/ })[0]).toHaveAttribute('href', '/learn?lesson=money-interest')
  })

  it('module test: answer all, submit, see the score and explanations, and the result is saved', async () => {
    const fn = api()
    renderPage(<Learn />, { route: '/learn?quiz=money' })
    expect(await screen.findByText('Module test', { selector: 'div' })).toBeInTheDocument()
    const submit = screen.getByRole('button', { name: 'Submit answers' })
    expect(submit).toBeDisabled()
    await userEvent.click(within(screen.getByTestId('q-money:t1')).getByRole('radio', { name: /Falls/ }))
    await userEvent.type(within(screen.getByTestId('q-money:t2')).getByRole('textbox'), '15')
    await userEvent.click(submit)
    expect(await screen.findByText(/Module test: 2\/2 \(100%\)/)).toBeInTheDocument()
    expect(screen.getAllByText('Correct.')).toHaveLength(2)
    await waitFor(() => expect(posts(fn)).toContainEqual({ quiz: 'money', score: 2, total: 2 }))
  })

  it('old module links still open (risk -> portfolio) and unknown lessons explain themselves', async () => {
    const fn = api({ '/learn/modules/portfolio': { ...MODULE, id: 'portfolio', title: 'Portfolio construction and risk' } })
    renderPage(<Learn />, { route: '/learn?module=risk' })
    expect(await screen.findByRole('heading', { name: 'Portfolio construction and risk' })).toBeInTheDocument()
    expect(requested(fn).some((u) => u.endsWith('/api/learn/modules/portfolio'))).toBe(true)
  })

  it('glossary search tolerates typos and browses A-Z with related terms and lesson links', async () => {
    api()
    renderPage(<Learn />, { route: '/learn?tab=glossary' })
    const box = await screen.findByRole('textbox', { name: 'Search the glossary' })
    fireEvent.change(box, { target: { value: 'rocce' } })
    let cards = screen.getAllByTestId('glossary-term')
    expect(within(cards[0]).getByRole('heading', { name: 'ROCE' })).toBeInTheDocument()
    expect(within(cards[0]).getByRole('link', { name: 'Time value of money' })).toHaveAttribute('href', '/learn?lesson=money-tvm')
    await userEvent.click(within(cards[0]).getByRole('button', { name: 'ROE' }))
    expect(box).toHaveValue('ROE')
    fireEvent.change(box, { target: { value: '' } })
    await userEvent.click(screen.getByRole('button', { name: 'D' }))
    cards = screen.getAllByTestId('glossary-term')
    expect(cards).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Z' })).toBeDisabled()
  })

  it('calculators recompute as inputs change and explain invalid inputs', async () => {
    api()
    renderPage(<Learn />, { route: '/learn?tab=calculators&calc=dcf' })
    const result = await screen.findByTestId('calc-result')
    expect(result).toHaveTextContent('₹164.46')
    const tg = screen.getByRole('spinbutton', { name: /Terminal growth/ })
    fireEvent.change(tg, { target: { value: '13' } })
    expect(screen.getByTestId('calc-result')).toHaveTextContent('Not defined for these inputs')
    expect(screen.getByText(/Terminal growth must be below the discount rate/)).toBeInTheDocument()
  })
})
