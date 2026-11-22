import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import CorporateActions from '../src/pages/CorporateActions'
import Earnings from '../src/pages/Earnings'
import { mockApi, renderPage, requested } from './helpers'

const TODAY = '2026-11-15'
const meeting = (company: string, symbol: string | null, date: string, state = 'upcoming') => ({
  company, symbol, tracked: !!symbol, industry: symbol ? 'it' : null, meeting_date: date, purpose: 'Consider and approve the financial results',
  period: 'Quarter ended September 2026', results: true, filed: '2026-11-12T06:00:00', status: 'confirmed',
  status_label: 'Confirmed - date stated in the company\'s board-meeting intimation', state, state_label: state === 'upcoming' ? 'Upcoming' : 'Results filed',
  sources: [{ label: 'NSE board-meetings feed', url: `https://x.test/${company}.pdf`, filed: '2026-11-12T06:00:00' }],
})
const CAL = {
  view: 'upcoming', today: TODAY, total: 3, counts: { upcoming: 3, filed_recent: 2, tracked_upcoming: 1 }, collected_since: '2026-11-11T19:26:00',
  items: [meeting('Tata Consultancy Services Limited', 'TCS.NS', '2026-11-18'), meeting('Konstelec Engineers Limited', null, '2026-11-18'),
    meeting('BLS Polymers Limited', null, '2026-11-20')],
  sources: [{ label: 'NSE board meetings (RSS)', url: 'https://www.nseindia.com/x', tier: 'OFFICIAL' }],
  notes: ['Dates come only from companies\' board-meeting intimations filed with NSE; EquityPilot never estimates a result date.'],
  industries: { it: 'Information Technology', banking: 'Banking' },
}
const RECENT = {
  ...CAL, view: 'recent', total: 2, items: [
    { company: 'Wipro Limited', symbol: 'WIPRO.NS', tracked: true, industry: 'it', filed: '2026-11-14T12:00:00', kind: 'results', subject: 'Outcome of Board Meeting',
      detail: 'financial results', period: 'Period ended September 30, 2026', basis: 'Consolidated', url: 'https://x.test/r1.pdf', source: 'NSE corporate announcement' },
    { company: 'Ansal Properties Limited', symbol: null, tracked: false, industry: null, filed: '2026-11-13T12:00:00', kind: 'delay',
      subject: 'Reasons for Delayed/Non-submission of Financial Results', detail: null, period: null, basis: null, url: 'https://x.test/r2.pdf', source: 'NSE corporate announcement' }],
}

describe('Earnings & Results', () => {
  it('lists confirmed result dates grouped by day, with the filing each date came from', async () => {
    mockApi({ '/events/results?view=upcoming': CAL })
    renderPage(<Earnings />, { route: '/earnings' })
    expect(await screen.findByRole('heading', { name: 'Earnings & Results' })).toBeInTheDocument()
    const tcs = await screen.findByRole('link', { name: 'Tata Consultancy Services Limited' })
    expect(tcs).toHaveAttribute('href', '/company/TCS.NS')
    expect(screen.getByText('Konstelec Engineers Limited').tagName).not.toBe('A')        // untracked, no symbol: plain text
    expect(screen.getByText(/Wednesday, 18 November 2026/)).toBeInTheDocument()
    expect(screen.getByText(/2 companies/)).toBeInTheDocument()
    const src = screen.getAllByRole('link', { name: /NSE board-meetings feed/ })
    expect(src[0]).toHaveAttribute('href', 'https://x.test/Tata Consultancy Services Limited.pdf')
    expect(screen.getByText(/never estimates a result date/)).toBeInTheDocument()
  })

  it('filters by company and sector and switches to recently filed results', async () => {
    const fetch = mockApi({ '/events/results?view=upcoming': CAL, '/events/results?view=recent': RECENT })
    renderPage(<Earnings />, { route: '/earnings' })
    await screen.findByRole('link', { name: 'Tata Consultancy Services Limited' })
    await userEvent.type(screen.getByLabelText('Filter by company'), 'tata')
    await userEvent.selectOptions(screen.getByLabelText('Sector'), 'it')
    await waitFor(() => expect(requested(fetch).some((u) => u.includes('q=tata') && u.includes('industry=it'))).toBe(true))
    await userEvent.click(screen.getByRole('button', { name: 'Recently filed' }))
    expect(await screen.findByText('Delay notice')).toBeInTheDocument()
    expect(within(screen.getByRole('link', { name: 'Wipro Limited' }).closest('li')!).getByText('Results filed')).toBeInTheDocument()
    expect(screen.getByText('Consolidated')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('view=recent')
  })

  it('shows a calendar and lists a chosen day', async () => {
    mockApi({ '/events/results?view=all': { ...CAL, view: 'all' }, '/events/results?view=upcoming': CAL })
    renderPage(<Earnings />, { route: '/earnings' })
    await screen.findByRole('link', { name: 'Tata Consultancy Services Limited' })
    await userEvent.click(screen.getByRole('button', { name: /Calendar/ }))
    const day = await screen.findByRole('button', { name: /20 November: 1 result date/ })
    await userEvent.click(day)
    expect(await screen.findByText(/Result dates on Friday, 20 November/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tata Consultancy Services Limited' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /19 November: 0 result dates/ })).toBeDisabled()
  })

  it('shows an error state with retry when the API fails', async () => {
    mockApi({ '/events/results': new Response(JSON.stringify({ detail: 'Server unavailable' }), { status: 503, headers: { 'content-type': 'application/json' } }) })
    renderPage(<Earnings />, { route: '/earnings' })
    expect(await screen.findByText("Couldn't load this section")).toBeInTheDocument()
    expect(screen.getByText('Server unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

const ACTIONS = {
  when: 'upcoming', today: TODAY, total: 2, counts_upcoming: { dividend: 1, split: 1 },
  items: [
    { company: 'Cochin Shipyard Limited', symbol: 'COCHINSHIP.NS', tracked: false, industry: null, type: 'dividend', type_label: 'Dividend', purpose: 'Interim Dividend - Rs 3 Per Share',
      series: 'EQ', ex_date: '2026-11-16', record_date: '2026-11-16', book_closure: null, face_value: '5', amount: 3, ratio: null, payment_date: null, announced: null,
      status_label: 'Ex-date set by the exchange', source: 'NSE corporate-actions feed', tier: 'OFFICIAL', url: 'https://www.nseindia.com/actions' },
    { company: 'BN Agrochem Limited', symbol: null, tracked: false, industry: null, type: 'split', type_label: 'Stock split', purpose: 'Face Value Split',
      series: 'EQ', ex_date: '2026-11-17', record_date: '2026-11-17', book_closure: null, face_value: '10', amount: null, ratio: 'Face value ₹10 → ₹2 (each share becomes 5)',
      payment_date: null, announced: null, status_label: 'Ex-date set by the exchange', source: 'NSE corporate-actions feed', tier: 'OFFICIAL', url: 'https://www.nseindia.com/actions' }],
  announcements: [{ company: 'Ashok Leyland Limited', symbol: 'ASHOKLEY.NS', type: 'dividend', type_label: 'Dividend', subject: 'Dividend', detail: 'Interim dividend declared',
    filed: '2026-11-14T09:00:00', url: 'https://x.test/a.pdf', tier: 'OFFICIAL' }],
  types: { dividend: { label: 'Dividend', explain: 'A cash payment to shareholders.' }, split: { label: 'Stock split', explain: 'Each share is divided.' },
    bonus: { label: 'Bonus issue', explain: 'Free extra shares.' }, rights: { label: 'Rights issue', explain: 'Optional new shares.' },
    buyback: { label: 'Buyback', explain: 'The company buys back shares.' }, merger: { label: 'Merger / demerger', explain: 'A scheme.' } },
  sources: [{ label: 'NSE corporate actions (RSS)', url: 'https://www.nseindia.com/actions', tier: 'OFFICIAL' }],
  notes: ['Payment dates are not in the exchange feed - see the company\'s filing.'], industries: { it: 'Information Technology' },
}

describe('Corporate Actions', () => {
  it('shows exchange ex-dates, amounts and split terms, without inventing payment dates', async () => {
    mockApi({ '/events/actions': ACTIONS })
    renderPage(<CorporateActions />, { route: '/corporate-actions' })
    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    expect(rows).toHaveLength(3)
    expect(within(rows[1]).getByText('₹3.00 per share')).toBeInTheDocument()
    expect(within(rows[2]).getByText(/each share becomes 5/)).toBeInTheDocument()
    expect(within(table).getAllByText('See filing')).toHaveLength(2)
    expect(within(table).getAllByText('OFFICIAL').length).toBe(2)
    expect(screen.getByText('Announced')).toBeInTheDocument()
    expect(screen.getByText('A cash payment to shareholders.')).toBeInTheDocument()
  })

  it('filters by action type', async () => {
    const fetch = mockApi({ '/events/actions': ACTIONS })
    renderPage(<CorporateActions />, { route: '/corporate-actions' })
    await screen.findByRole('table')
    await userEvent.click(screen.getByRole('button', { name: /^Dividend/ }))
    await waitFor(() => expect(requested(fetch).some((u) => u.includes('type=dividend'))).toBe(true))
    expect(screen.getByRole('button', { name: /^Dividend/ })).toHaveAttribute('aria-pressed', 'true')
  })
})
