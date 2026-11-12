import { ArrowRight, Keyboard, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, DataBadge, Notice, PageHeader } from '../components/ui'

const STEPS: { title: string; body: string; to: string; cta: string }[] = [
  { title: 'Find a company', body: 'Press Ctrl+K (or /) anywhere and type a name, NSE symbol or ISIN. Over 5,000 NSE-listed companies are searchable; opening one that is not yet tracked fetches its data from Yahoo Finance (delayed).', to: '/explore', cta: 'Explore companies' },
  { title: 'Read the company page', body: 'Overview, price chart, statements, quarterly results, ratios, technicals, risk flags, peers, ownership, news and your own notes - each figure shows its source, date and data type.', to: '/research', cta: 'Equity Research' },
  { title: 'Value it', body: 'The Valuation Lab runs a DCF with your assumptions, bull/base/bear scenarios, sensitivity tables, a reverse DCF (what growth the price implies) and peer multiples. Banks use justified P/B instead.', to: '/valuation', cta: 'Valuation Lab' },
  { title: 'Screen and compare', body: 'Filter the tracked universe on growth, profitability, leverage and valuation; save screens; compare up to five companies side by side.', to: '/screener', cta: 'Open Screener' },
  { title: 'Follow the market', body: 'Indices, sector performance, gainers and losers, exchange announcements, results, RBI and SEBI updates. Industry pages explain each sector and the metrics that matter.', to: '/markets', cta: 'Market Tracker' },
  { title: 'Ask the assistant', body: 'Ask about a company or an uploaded annual report. Answers cite numbered sources (and page numbers for documents). The free offline engine is the default; Claude is optional.', to: '/assistant', cta: 'AI Assistant' },
  { title: 'Practise with Virtual Invest', body: 'Get ₹10,00,000 of virtual money, place practice orders at the latest delayed price and compare your performance with the NIFTY 50. No real money or orders are involved.', to: '/invest', cta: 'Virtual Invest' },
  { title: 'Track and report', body: 'Keep multiple watchlists with notes and price alerts, record your real holdings for portfolio analysis, and export a PDF research report.', to: '/watchlists', cta: 'Watchlists' },
]

const LABELS: { type: string; meaning: string }[] = [
  { type: 'delayed', meaning: 'Market price from Yahoo Finance, typically delayed ~15 minutes or more. Not real-time.' },
  { type: 'close', meaning: 'Last closing price, shown when the market is closed.' },
  { type: 'historical', meaning: 'Past prices or financial statements from a third-party data provider.' },
  { type: 'third_party', meaning: 'Data from a third-party source (e.g. Yahoo Finance statements, news publishers).' },
  { type: 'official_upload', meaning: 'Extracted from a filing or report you uploaded; cited by page.' },
  { type: 'user_entered', meaning: 'Typed in by a user from a filing. Always check the linked source.' },
  { type: 'calculated', meaning: 'Computed by EquityPilot from the data above; the formula is shown.' },
  { type: 'assumption', meaning: 'An input you chose (e.g. DCF growth or discount rate). Not a fact.' },
  { type: 'sample', meaning: 'Fictional demonstration data. It does not describe any real company.' },
]

const KEYS: [string, string][] = [['Ctrl + K', 'Open search'], ['/', 'Open search'], ['Esc', 'Close dialogs and search'], ['↑ ↓ Enter', 'Move through and open search results']]

const FAQ: [string, string][] = [
  ['Are prices live?', 'No. Free real-time NSE/BSE data is not available. EquityPilot uses delayed Yahoo Finance quotes and labels every price. Real-time data needs a licensed vendor or a broker API tied to your own trading account; see Settings → Data sources.'],
  ['Does EquityPilot give buy or sell recommendations?', 'No. It is an educational research tool. It shows data, calculations and labelled interpretations so you can form your own view. Consult a SEBI-registered adviser for personal advice.'],
  ['Where do financial statements come from?', 'From Yahoo Finance (third-party) for tracked listed companies, or from filings you upload. Always confirm important figures against the annual report or exchange filing linked on the company page.'],
  ['Is my data private?', 'Watchlists, notes, portfolios, Virtual Invest accounts and uploaded documents belong to your session or account and are not shown to other users. The leaderboard is opt-in. You can export your data from Settings.'],
  ['Does the AI cost money?', 'Not by default. The offline engine is free and deterministic. If you connect the Claude API with your own key, EquityPilot shows the estimated cost per question first.'],
  ['What happens if a guest session ends?', 'Guest data is tied to a browser cookie. Create a free account in Settings to keep it across browsers and devices.'],
]

export default function Guide() {
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Learn" title="How to use EquityPilot AI" subtitle="A quick tour of the workflow, what each data label means, and the answers to common questions." />
      <Notice><ShieldCheck className="mr-1 inline h-4 w-4 text-up" />EquityPilot is for research and education. It never places real orders, never connects to your demat account and never invents data - when something is unavailable it says so.</Notice>

      <section>
        <h2 className="section-title mb-3">The research workflow</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.title} className="card card-pad flex flex-col">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-sm font-semibold text-white">{i + 1}</span>
              <h3 className="mt-3 font-semibold">{s.title}</h3>
              <p className="mt-1 flex-1 text-sm muted">{s.body}</p>
              <Link to={s.to} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">{s.cta}<ArrowRight className="h-3.5 w-3.5" /></Link>
            </div>))}
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="What the data labels mean" className="lg:col-span-2">
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">
            {LABELS.map((l) => (
              <li key={l.type} className="flex items-start gap-3 py-2.5 text-sm"><span className="w-32 shrink-0"><DataBadge type={l.type} /></span><span>{l.meaning}</span></li>))}
          </ul>
          <p className="mt-3 text-xs muted">Times are shown in IST. Financial figures state whether they are consolidated or standalone, and the fiscal period (e.g. FY25 = April 2024 – March 2025).</p>
        </Card>
        <Card title={<span className="inline-flex items-center gap-1.5"><Keyboard className="h-4 w-4 text-brand-600" />Keyboard shortcuts</span>}>
          <ul className="space-y-2">{KEYS.map(([k, v]) => (
            <li key={k} className="flex items-center justify-between gap-3 text-sm"><span className="muted">{v}</span><kbd className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-xs dark:border-ink-600 dark:bg-ink-800">{k}</kbd></li>))}</ul>
        </Card>
      </div>

      <Card title="Frequently asked questions">
        <div className="divide-y divide-slate-100 dark:divide-ink-700">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-3">
              <summary className="cursor-pointer list-none font-medium marker:hidden group-open:text-brand-600 dark:group-open:text-brand-300">{q}</summary>
              <p className="mt-2 text-sm muted">{a}</p>
            </details>))}
        </div>
      </Card>
    </div>
  )
}
