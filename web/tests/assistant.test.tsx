import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import Assistant from '../src/pages/Assistant'
import { mockApi, renderPage } from './helpers'

const sse = (...events: unknown[]) => new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''),
  { status: 200, headers: { 'content-type': 'text/event-stream' } })

const SETTINGS = { '/assistant/settings': { provider: 'offline' }, '/documents': [], '/search': { companies: [] } }
const SOURCES = [{ ID: 'T1', Content: 'Comparison: TCS.NS, INFY.NS', Source: 'EquityPilot calculations', Type: 'CALCULATED', Retrieved: '20 Nov 2026', Link: null }]

afterEach(() => { try { localStorage.clear() } catch { /* ignore */ } })

describe('AI assistant', () => {
  it('streams research steps and the answer; a source tag opens that source; unsupported figures are flagged', async () => {
    let body: { question?: string; history?: unknown[] } = {}
    mockApi({
      ...SETTINGS,
      '/assistant/stream': (_u: URL, init?: RequestInit) => {
        body = JSON.parse(String(init?.body))
        return sse({ type: 'status', text: 'Comparing TCS.NS, INFY.NS' }, { type: 'delta', text: '**Answer**\nTCS has the higher ROE [T1].' },
          { type: 'final', text: '**Answer**\nTCS has the higher ROE [T1].\nMargin was 99.9%.', sources: SOURCES,
            meta: { engine: 'claude-opus-5-5', seconds: 3.2, grounding: { figures: 1, untraced: ['99.9'], calculated: [], unknown_citations: [] } } })
      },
    })
    renderPage(<Assistant />)
    await userEvent.type(screen.getByLabelText('Your question'), 'Compare TCS and Infosys')
    await userEvent.click(screen.getByRole('button', { name: /Ask/ }))
    expect(await screen.findByText('Comparing TCS.NS, INFY.NS')).toBeInTheDocument()
    expect(await screen.findByText(/Check these figures:/)).toBeInTheDocument()
    expect(screen.getByText(/99\.9 - they were not found in the data/)).toBeInTheDocument()
    expect(body.question).toBe('Compare TCS and Infosys')
    await userEvent.click(screen.getByRole('button', { name: 'T1' }))                       // citation chip
    const item = document.getElementById('src-1-T1')!
    expect(item).toBeVisible()
    expect(item.className).toContain('ring-2')
  })

  it('offers Retry after an error and resends the same question without the failed exchange', async () => {
    let calls = 0
    const histories: unknown[][] = []
    mockApi({
      ...SETTINGS,
      '/assistant/stream': (_u: URL, init?: RequestInit) => {
        calls++
        histories.push(JSON.parse(String(init?.body)).history)
        if (calls === 1) return new Response(JSON.stringify({ detail: 'Too many requests' }), { status: 429, headers: { 'content-type': 'application/json' } })
        return sse({ type: 'final', text: 'Here you go.', sources: [], meta: { engine: 'offline analyst (rule-based)' } })
      },
    })
    renderPage(<Assistant />)
    await userEvent.type(screen.getByLabelText('Your question'), 'What is ROCE?')
    await userEvent.click(screen.getByRole('button', { name: /Ask/ }))
    expect(await screen.findByText(/Too many requests/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Retry/ }))
    expect(await screen.findByText('Here you go.')).toBeInTheDocument()
    expect(calls).toBe(2)
    expect(histories[1]).toEqual([])                                 // the failed exchange is not sent as history
    expect(screen.queryByText(/Too many requests/)).not.toBeInTheDocument()
  })

  it('keeps the conversation when the page is opened again', async () => {
    mockApi({ ...SETTINGS, '/assistant/stream': () => sse({ type: 'final', text: 'Kept answer.', sources: [], meta: { engine: 'offline analyst (rule-based)' } }) })
    const first = renderPage(<Assistant />)
    await userEvent.type(screen.getByLabelText('Your question'), 'Explain DCF valuation')
    await userEvent.click(screen.getByRole('button', { name: /Ask/ }))
    expect(await screen.findByText('Kept answer.')).toBeInTheDocument()
    await waitFor(() => expect(localStorage.getItem('ep-assistant-conversation')).toContain('Kept answer.'))
    first.unmount()
    renderPage(<Assistant />)
    expect(await screen.findByText('Kept answer.')).toBeInTheDocument()
    expect(screen.getByText('Explain DCF valuation')).toBeInTheDocument()
  })
})
