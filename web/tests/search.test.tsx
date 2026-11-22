import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SearchPalette } from '../src/components/SearchPalette'
import { mockApi, renderPage, requested } from './helpers'

const RESULT = {
  query: 'tcs', order: ['companies', 'tools', 'news'], companies: [
    { symbol: 'TCS.NS', name: 'Tata Consultancy Services Limited', exchange: 'NSE', category: 'Large Cap', tracked: true, price: 3050.5, change_pct: 0.012, market_cap: 1.1e13, pe: 22.4, status: 'delayed' },
  ], indices: [], industries: [], concepts: [],
  tools: [{ label: 'Earnings & Results', description: 'Confirmed result dates', to: '/earnings' }],
  news: [{ title: 'TCS wins deal', url: 'https://x.test/n', source: 'Reuters', published: '2026-11-14T10:00:00', tier: 'established', symbol: 'TCS.NS' }],
}

function setup(extra: Record<string, unknown> = {}) {
  return mockApi({
    '/recent': { views: [], searches: ['infosys'] },
    '/search?q=tcs': RESULT,
    '/search?q=zzqq': { query: 'zzqq', order: [], companies: [], indices: [], industries: [], concepts: [], tools: [], news: [] },
    ...extra,
  })
}

describe('global search', () => {
  it('groups results, previews the company and opens it with the keyboard', async () => {
    const fetch = setup()
    const onClose = vi.fn()
    renderPage(<SearchPalette open onClose={onClose} />)
    const box = screen.getByPlaceholderText(/Search companies, symbols/)
    await userEvent.type(box, 'tcs')
    const dialog = screen.getByRole('dialog', { name: 'Search' })
    expect((await within(dialog).findAllByText('Tata Consultancy Services Limited')).length).toBe(2)   // result row + preview panel
    expect(within(dialog).getByText('Companies')).toBeInTheDocument()
    expect(within(dialog).getByText('Research tools')).toBeInTheDocument()
    expect(within(dialog).getAllByText(/Large Cap/).length).toBeGreaterThan(0)          // preview: exchange and size category
    expect(requested(fetch).some((u) => u.includes('/api/search?q=tcs'))).toBe(true)
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/company/TCS.NS'))
  })

  it('shows recent searches and an honest no-result state', async () => {
    setup()
    renderPage(<SearchPalette open onClose={() => {}} />)
    expect(await screen.findByRole('button', { name: 'infosys' })).toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/Search companies, symbols/), 'zzqq')
    expect(await screen.findByText(/No company, index or topic matches/)).toBeInTheDocument()
    expect(screen.queryByText('Tata Consultancy Services Limited')).not.toBeInTheDocument()
  })

  it('moves through results with the arrow keys', async () => {
    setup()
    renderPage(<SearchPalette open onClose={() => {}} />)
    await userEvent.type(screen.getByPlaceholderText(/Search companies, symbols/), 'tcs')
    await screen.findAllByText('Tata Consultancy Services Limited')
    await userEvent.keyboard('{ArrowDown}{Enter}')
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/earnings"))   // second row: the research tool
  })
})
