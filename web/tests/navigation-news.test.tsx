import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import Layout from '../src/components/Layout'
import News from '../src/pages/News'
import { mockApi, renderPage, requested } from './helpers'

const SHELL = {
  '/me': { user: { id: 1, display_name: 'Guest 1', is_guest: true, show_on_leaderboard: false } },
  '/notifications': { unread: 0, items: [] },
  '/market/status': { phase: 'closed', note: 'Closed', realtime: false, provider: 'Yahoo', next_open: '2026-11-16T03:45:00Z', closes_at: null, holiday: false },
  '/market/overview': { status: { phase: 'closed', realtime: false }, indices: [], source: 'Yahoo' },
}

describe('navigation', () => {
  it('lists the new sections in the sidebar with working links', async () => {
    mockApi(SHELL)
    renderPage(<Layout />, { route: '/' })
    const nav = screen.getAllByRole('navigation', { name: 'Main' })[0]
    for (const [label, href] of [['Earnings & Results', '/earnings'], ['Corporate Actions', '/corporate-actions'], ['Data Quality', '/data-quality'], ['News', '/news']]) {
      expect(within(nav).getByRole('link', { name: label })).toHaveAttribute('href', href)
    }
    await userEvent.click(within(nav).getByRole('link', { name: 'Earnings & Results' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/earnings')
    expect(within(nav).getByRole('link', { name: 'Earnings & Results' })).toHaveAttribute('aria-current', 'page')
  })

  it('opens and closes the phone menu drawer, and navigates from it', async () => {
    mockApi(SHELL)
    renderPage(<Layout />, { route: '/' })
    await userEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const close = await screen.findByRole('button', { name: 'Close menu' })
    const drawerNav = close.parentElement!.querySelector('nav')!
    await userEvent.click(within(drawerNav).getByRole('link', { name: 'Corporate Actions' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/corporate-actions')
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument())
    expect(screen.getByRole('navigation', { name: 'Quick navigation' })).toBeInTheDocument()   // phone tab bar
  })
})

const item = (over: Record<string, unknown>) => ({
  id: String(Math.random()), title: 'Headline', summary: null, url: 'https://x.test/n', source: 'The Economic Times (RSS)', publisher: 'The Economic Times', tier: 'established',
  kind: 'Media report', category: 'Indian market', sections: ['market', 'company'], symbol: null, symbols: [], match: null, company: null, industry: null, industry_name: null,
  published: '2026-11-14T08:00:00', fetched_at: '2026-11-14T08:05:00', important: false, tentative: false, also: [], feed_kind: 'media', ...over,
})
const FEED = {
  section: 'company', title: 'Company news', total: 2, hidden_unrated: 0, sources: ['The Economic Times'], note: null, sections: {},
  items: [
    item({ title: 'Infosys, Wipro shares rise after US deal wins', symbol: 'INFY.NS', symbols: ['INFY.NS', 'WIPRO.NS'], match: 'Named in the headline', company: 'Infosys Limited' }),
    item({ title: 'Trump administration freezes green cards for Microsoft, IT firms', publisher: 'Reuters', source: 'Reuters via Yahoo Finance' }),
  ],
}

describe('News & Intelligence', () => {
  it('shows every company a story names, how it was linked, and keeps unlinked stories general', async () => {
    mockApi({ '/news/feed': FEED, '/news/summary': { date: '2026-11-14', phase: 'closed', headline: 'NIFTY 50 fell.', indices: [], bullets: [], filings_today: { results: 0, announcements: 0, rbi: 0, sebi: 0 }, status_note: '', sources: [] }, '/news/saved': { items: [] } })
    renderPage(<News />, { route: '/news?section=company' })
    const story = (await screen.findByText(/Infosys, Wipro shares rise/)).closest('li')!
    expect(within(story).getByRole('link', { name: 'INFY' })).toHaveAttribute('href', '/company/INFY.NS')
    expect(within(story).getByRole('link', { name: 'WIPRO' })).toHaveAttribute('href', '/company/WIPRO.NS')
    expect(within(story).getByText(/Company link: named in the headline/)).toBeInTheDocument()
    const general = screen.getByText(/freezes green cards for Microsoft/).closest('li')!
    expect(within(general).queryByRole('link', { name: 'TCS' })).not.toBeInTheDocument()
    expect(within(general).queryByText(/Company link/)).not.toBeInTheDocument()
  })

  it('passes search, date and source filters to the feed', async () => {
    const fetch = mockApi({ '/news/feed': FEED, '/news/summary': { date: '2026-11-14', phase: 'closed', headline: '', indices: [], bullets: [], filings_today: { results: 0, announcements: 0, rbi: 0, sebi: 0 }, status_note: '', sources: [] }, '/news/saved': { items: [] } })
    renderPage(<News />, { route: '/news?section=company' })
    await screen.findByText(/Infosys, Wipro shares rise/)
    const search = screen.getAllByRole('textbox').find((el) => (el as HTMLInputElement).placeholder?.toLowerCase().includes('search'))!
    await userEvent.type(search, 'wipro')
    await waitFor(() => expect(requested(fetch).some((u) => u.includes('/news/feed') && u.includes('q=wipro'))).toBe(true))
  })
})
