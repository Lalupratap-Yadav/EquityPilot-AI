import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { TradeTicket } from '../src/components/common'
import DataQuality from '../src/pages/DataQuality'
import { HealthTab } from '../src/pages/company/Health'
import { mockApi, renderPage } from './helpers'

const metric = (key: string, label: string, value: number | null, rating: string | null, unit = 'x') => ({
  key, label, value, unit, period: 'FY2026', formula: `${label} formula`, rating, rating_label: rating ? rating[0].toUpperCase() + rating.slice(1) : null,
  rating_text: rating ? `${label} is ${rating}.` : null, rated: !!rating, missing: value === null, note: null,
})
const HEALTH = {
  symbol: 'TCS.NS', is_financial: false, latest_fy: 'FY2026', basis: 'unspecified', sources: ['Yahoo Finance (via yfinance)'], fetched_at: '2026-11-12T10:00:00',
  areas_with_data: 2, areas_rateable: 3, benchmark_note: 'General rules of thumb.',
  method: ['Areas without a rated metric show \'Insufficient data\'. There is no overall company score.'],
  areas: [
    { key: 'growth', title: 'Growth', question: 'Are sales and profits growing?', status: 'adequate', status_label: 'Adequate', explain: 'Average of 2 rated metrics: 1.00 points out of 2.',
      metrics: [metric('revenue_growth', 'Revenue growth', 0.046, 'weak', 'pct'), metric('net_income_growth', 'Net profit growth', 0.13, 'strong', 'pct')], rated_count: 2, points: 1 },
    { key: 'debt', title: 'Debt', question: 'Is borrowing at a safe level?', status: 'insufficient', status_label: 'Insufficient data',
      explain: 'None of the rated metrics for this area is available for the latest period.', metrics: [metric('debt_to_equity', 'Debt to equity', null, null)], rated_count: 0, points: null },
    { key: 'cash_flow', title: 'Cash flow', question: 'Do profits turn into cash?', status: 'not_applicable', status_label: 'Not applicable',
      explain: 'For banks and NBFCs, borrowing and lending are the business.', metrics: [], rated_count: 0, points: null },
  ],
}

describe('Financial Health tab', () => {
  it('shows each area with its metrics, never a number for missing data, and explains the calculation', async () => {
    mockApi({ '/companies/TCS.NS/health': HEALTH })
    renderPage(<HealthTab symbol="TCS.NS" />)
    expect(await screen.findByText('2 of 3 areas have enough data to rate · latest fiscal year FY2026')).toBeInTheDocument()
    const debt = screen.getByRole('heading', { name: 'Debt' }).closest('section')!
    expect(within(debt).getByText('Insufficient data')).toBeInTheDocument()
    expect(within(debt).getByText('—')).toBeInTheDocument()                                    // missing, not 0
    expect(screen.getByText('Not applicable')).toBeInTheDocument()
    const growth = screen.getByRole('heading', { name: 'Growth' }).closest('section')!
    expect(within(growth).getByText('4.6%')).toBeInTheDocument()
    await userEvent.click(within(growth).getByRole('button', { name: /How this is calculated/ }))
    expect(within(growth).getByText('Revenue growth formula')).toBeInTheDocument()
    expect(within(growth).getByText('Average of 2 rated metrics: 1.00 points out of 2.')).toBeInTheDocument()
    expect(screen.getByText(/no overall company score/)).toBeInTheDocument()
  })
})

const QUALITY = {
  generated_at: '2026-11-15T05:00:00', offline: false,
  labels: { OFFICIAL: 'Primary source', SECONDARY: 'Media publisher', 'THIRD-PARTY': 'Aggregator', DELAYED: 'May lag', HISTORICAL: 'Past data',
    CALCULATED: 'Computed', ASSUMPTION: 'Model input', SAMPLE: 'Fictional', 'USER-ENTERED': 'Typed in' },
  feeds: [
    { key: 'nse_announcements', source: 'NSE India - corporate announcements', url: 'https://x.test/a', tier: 'OFFICIAL', refresh_minutes: 10, last_refreshed: '2026-11-15T04:55:00',
      last_failed: null, state: 'fresh', items_stored: 31464, newest_item: '2026-11-15T04:50:00' },
    { key: 'sebi', source: 'SEBI', url: 'https://x.test/s', tier: 'OFFICIAL', refresh_minutes: 60, last_refreshed: '2026-11-14T04:55:00',
      last_failed: '2026-11-15T04:00:00', state: 'failing', items_stored: 57, newest_item: null },
  ],
  feeds_failing: ['sebi'], feeds_stale: [],
  market_data: { provider: 'Yahoo Finance (delayed)', tier: 'DELAYED', realtime: false, quotes_stored: 125, quotes_within_1d: 120, newest_quote: '2026-11-15T04:00:00', note: 'Prices may lag.' },
  statements: { companies: 120, with_3y_annual: 120, with_quarterly: 118, no_statements: [], basis_note: 'Basis not stated.', eps_warning_count: 1,
    eps_warnings: [{ symbol: 'HDFCBANK.NS', check: 'Diluted EPS above basic EPS (Mar 2023)', detail: 'Basic 44.51 vs diluted 88.68.' }] },
  securities: { count: 5552, as_of: 'Dec 2025', source: 'AMFI and NSE' }, rules: ['Missing values are shown as missing, never as zero.'],
}

describe('Data Quality page', () => {
  it('shows every label, feed health and the EPS warning', async () => {
    mockApi({ '/data/quality': QUALITY })
    renderPage(<DataQuality />, { route: '/data-quality' })
    expect(await screen.findByRole('heading', { name: 'Data Quality & Sources' })).toBeInTheDocument()
    expect(await screen.findByText('Failing')).toBeInTheDocument()                             // data loaded
    for (const l of ['OFFICIAL', 'SECONDARY', 'THIRD-PARTY', 'DELAYED', 'HISTORICAL', 'CALCULATED', 'ASSUMPTION', 'SAMPLE', 'USER-ENTERED']) {
      expect(screen.getAllByText(l).length).toBeGreaterThan(0)
    }
    expect(screen.getByText('1 / 2')).toBeInTheDocument()                                       // feeds healthy
    expect(screen.getByText('Failing')).toBeInTheDocument()
    expect(screen.getByText(/cached items shown/)).toBeInTheDocument()
    expect(screen.getByText(/HDFCBANK: Diluted EPS above basic EPS/)).toBeInTheDocument()
    expect(screen.getByText('Missing values are shown as missing, never as zero.')).toBeInTheDocument()
  })
})

describe('Virtual Invest order ticket', () => {
  it('blocks orders larger than the virtual cash and sends whole-share orders', async () => {
    let sent: unknown = null
    mockApi({
      '/invest/summary': { cash: 10000, holdings: [] },
      '/invest/orders': (_u: URL, init?: RequestInit) => { sent = JSON.parse(String(init?.body)); return { price: 2500, qty: 2, price_status: 'delayed' } },
    })
    renderPage(<TradeTicket symbol="TCS.NS" name="Tata Consultancy Services" quote={{ symbol: 'TCS.NS', price: 2500, status: 'delayed' } as never} />)
    expect(await screen.findByText('₹10,000.00')).toBeInTheDocument()
    const qty = screen.getByLabelText('Quantity (shares)')
    await userEvent.clear(qty)
    await userEvent.type(qty, '5')
    expect(screen.getByText('Order value exceeds available virtual cash.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Buy with virtual money' })).toBeDisabled()
    await userEvent.clear(qty)
    await userEvent.type(qty, '2')
    await userEvent.click(screen.getByRole('button', { name: 'Buy with virtual money' }))
    await waitFor(() => expect(sent).toEqual({ symbol: 'TCS.NS', side: 'BUY', qty: 2 }))
    await userEvent.click(screen.getByRole('button', { name: 'Sell' }))
    expect(screen.getByText('You hold 0 shares.')).toBeInTheDocument()
    expect(screen.getByText(/no real order is placed/)).toBeInTheDocument()
  })
})
