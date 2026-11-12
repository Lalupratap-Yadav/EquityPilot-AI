import { useMutation, useQuery } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BarsChart, LinesChart } from '../components/charts'
import { CompanyPicker } from '../components/CompanyPicker'
import { Card, cx, DataBadge, EmptyState, InfoTip, Loading, Notice, PageHeader, Stat, Tabs, useToast } from '../components/ui'
import { api, ApiError } from '../lib/api'
import { baseSymbol, crore, inr, isNum, mult, num, pct } from '../lib/format'
import { useDebounced } from '../lib/hooks'

interface ValResp {
  snapshot: Record<string, number | null> & { basis: Record<string, string | null> }
  formulas: Record<string, string>; is_financial: boolean
  history: { label: string; price: number; pe: number | null; pb: number | null }[]
  dcf_defaults: Record<string, number> | null; dcf_notes: Record<string, string>; provider_beta: number | null; kd_hint: number | null
  peers: { symbol: string; name: string; pe: number | null; pb: number | null; ev_ebitda: number | null; roe: number | null }[]
  relative: { Method: string; 'Peer median': number | null; 'Company metric': number | null; 'Implied price': number | null; 'Peers used': number }[]
  roe_3y: number | null; bvps: number | null; saved: { per_share: number; saved: string } | null; hist_cagr_3y: number | null
  bands: Record<'pe' | 'pb', Band>; implied_from_history: { pe: number | null; pb: number | null }
  fcfe_defaults: { net_margin: number; debt_ratio: number } | null; fcfe_notes: Record<string, string>
}
interface Band { n: number; median: number | null; min: number | null; max: number | null; current: number | null; vs_median: number | null }
interface FCFEOut { per_share?: number; equity_value?: number; pv_fcfe?: number; terminal_value?: number; pv_terminal?: number; terminal_share?: number; projection?: Record<string, number>[]; margin_of_safety?: number | null; error?: string }
interface DCFResp {
  per_share: number; enterprise_value: number; equity_value: number; pv_fcff: number; terminal_value: number; pv_terminal: number; terminal_share: number; price: number | null
  projection: Record<string, number>[]; scenarios: Record<string, { per_share?: number; terminal_share?: number; error?: string }>
  sensitivity: { waccs: number[]; growths: number[]; values: (number | null)[][] }; implied_growth: number | null
  margin_of_safety: number | null; fcfe?: FCFEOut
}

/** One row of the valuation range chart: a point estimate or a low-high range. */
interface Est { label: string; low: number | null; high: number | null; mid: number | null; note: string }

function FootballField({ rows, price }: { rows: Est[]; price: number | null }) {
  const vals = rows.flatMap((r) => [r.low, r.high, r.mid]).filter((v): v is number => isNum(v) && v > 0)
  if (!vals.length) return <p className="text-sm muted">Not enough data for any method.</p>
  const all = isNum(price) ? [...vals, price] : vals
  const lo = Math.min(...all) * 0.85, hi = Math.max(...all) * 1.1
  const x = (v: number) => `${((Math.max(lo, v) - lo) / (hi - lo)) * 100}%`
  return (
    <div>
      <div className="space-y-3">
        {rows.map((r) => {
          const ok = [r.low, r.high, r.mid].some((v) => isNum(v) && v > 0)
          const range = isNum(r.low) && isNum(r.high) && r.low > 0 && r.high > r.low
          return (
            <div key={r.label} className="grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)_5.5rem] items-center gap-3 text-sm sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_7.5rem]">
              <div className="min-w-0"><div className="truncate font-medium">{r.label}</div><div className="truncate text-[11px] muted">{r.note}</div></div>
              <div className="relative h-6 rounded bg-slate-100 dark:bg-ink-800">
                {range && <div className="absolute inset-y-1 rounded bg-brand-500/30" style={{ left: x(r.low!), width: `calc(${x(r.high!)} - ${x(r.low!)})` }} />}
                {isNum(r.mid) && r.mid > 0 && <div className="absolute inset-y-0 w-1.5 -translate-x-1/2 rounded bg-brand-600" style={{ left: x(r.mid) }} title={inr(r.mid)} />}
                {isNum(price) && <div className="absolute -inset-y-1 w-0.5 bg-slate-900 dark:bg-white" style={{ left: x(price) }} />}
              </div>
              <div className="num text-right text-xs">{!ok ? <span className="muted">Not available</span> : range ? `${inr(r.low, 0)}–${inr(r.high, 0)}` : inr(r.mid, 0)}</div>
            </div>
          )
        })}
      </div>
      {isNum(price) && <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs muted"><span className="inline-block h-3 w-0.5 bg-slate-900 dark:bg-white" />Market price {inr(price)} · <span className="inline-block h-3 w-1.5 rounded bg-brand-600" />estimate · <span className="inline-block h-3 w-4 rounded bg-brand-500/30" />bear–bull range</p>}
    </div>
  )
}

function BandCard({ title, b, implied, unit }: { title: string; b?: Band; implied: number | null; unit: string }) {
  if (!b || b.n < 2 || !isNum(b.median)) return <Card title={title}><p className="text-sm muted">Data not available - needs at least two fiscal years with positive {unit} and price history.</p></Card>
  const vs = b.vs_median
  return (
    <Card title={title} subtitle={`Fiscal year-end values over ${b.n} years`}>
      <dl className="grid grid-cols-4 gap-2 text-center">
        {[['Now', mult(b.current)], ['Median', mult(b.median)], ['Low', mult(b.min)], ['High', mult(b.max)]].map(([k, v]) => <div key={k} className="rounded-lg bg-slate-50 py-1.5 dark:bg-ink-800"><dt className="text-[10px] uppercase muted">{k}</dt><dd className="num font-semibold">{v}</dd></div>)}
      </dl>
      <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        {isNum(vs) ? <>Today's multiple is <b>{pct(Math.abs(vs), 0)} {vs >= 0 ? 'above' : 'below'}</b> its {b.n}-year median. </> : null}
        {isNum(implied) && <>At the median multiple, today's {unit} would imply about <b className="num">{inr(implied, 0)}</b> per share. </>}
        A different multiple can be justified if growth, margins or risk have changed.
      </p>
    </Card>
  )
}

function PctInput({ label, value, onChange, help, step = 0.25 }: { label: string; value: number; onChange: (v: number) => void; help?: string; step?: number }) {
  return (
    <div><label className="label flex items-center gap-1">{label}{help && <InfoTip text={help} />}</label>
      <div className="relative"><input className="input num pr-7" type="number" step={step} value={Number.isFinite(value) ? +(value * 100).toFixed(3) : ''}
        onChange={(e) => onChange(Number(e.target.value) / 100)} /><span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs muted">%</span></div>
    </div>
  )
}

export default function Valuation() {
  const { symbol = '' } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const [tab, setTab] = useState<'summary' | 'multiples' | 'dcf' | 'fcfe' | 'scenarios' | 'comps' | 'banks'>('summary')
  const q = useQuery({ queryKey: ['valuation', symbol], enabled: !!symbol, queryFn: () => api.get<ValResp>(`/companies/${encodeURIComponent(symbol)}/valuation`), retry: false })
  const [inp, setInp] = useState<Record<string, number> | null>(null)
  const [capm, setCapm] = useState({ rf: 0.07, beta: 1, erp: 0.07, kd: 0.09, override: false, wacc: 0.12 })
  const [shifts, setShifts] = useState<Record<string, number[]>>({ Bear: [-0.04, -0.03, 0.01, -0.01], Base: [0, 0, 0, 0], Bull: [0.03, 0.02, -0.01, 0.005] })
  const [bank, setBank] = useState({ roe: 0.14, ke: 0.135, g: 0.06 })
  const [fx, setFx] = useState<{ net_margin: number; debt_ratio: number; keOverride: number | null } | null>(null)
  const [mosReq, setMosReq] = useState(0.25)

  useEffect(() => {
    if (!q.data) return
    const d = q.data
    setInp(d.dcf_defaults ? { ...d.dcf_defaults } : null)
    const beta = isNum(d.provider_beta) && d.provider_beta > 0.2 && d.provider_beta < 3 ? +d.provider_beta.toFixed(2) : 1
    setCapm((c) => ({ ...c, beta, kd: isNum(d.kd_hint) ? Math.min(0.14, Math.max(0.06, d.kd_hint)) : 0.09, override: false }))
    if (isNum(d.roe_3y)) setBank((b) => ({ ...b, roe: Math.max(-0.5, Math.min(1.5, d.roe_3y!)) }))
    setFx(d.fcfe_defaults ? { ...d.fcfe_defaults, keOverride: null } : null)
    setTab('summary')
  }, [q.data])

  const snap = q.data?.snapshot
  const w = useMemo(() => {
    const E = snap?.market_cap ?? 0, D = snap?.debt ?? 0, tax = inp?.tax_rate ?? 0.25
    const ke = capm.rf + capm.beta * capm.erp, kd = capm.kd * (1 - tax)
    const we = E + D > 0 ? E / (E + D) : 1
    return { ke, kd, we, wacc: we * ke + (1 - we) * kd }
  }, [capm, snap, inp?.tax_rate])
  const waccUsed = capm.override ? capm.wacc : w.wacc
  const keUsed = fx?.keOverride ?? w.ke
  const body = useMemo(() => (inp ? { ...inp, wacc: waccUsed, scenario_shifts: shifts, fcfe: fx ? { net_margin: fx.net_margin, debt_ratio: fx.debt_ratio, cost_of_equity: keUsed } : null } : null), [inp, waccUsed, shifts, fx, keUsed])
  const dBody = useDebounced(body, 350)
  const dcf = useQuery({
    queryKey: ['dcf', symbol, dBody], enabled: !!dBody && !q.data?.is_financial,
    queryFn: () => api.post<DCFResp>(`/companies/${encodeURIComponent(symbol)}/dcf`, dBody), retry: false, placeholderData: (p) => p,
  })
  const save = useMutation({ mutationFn: () => api.post(`/companies/${encodeURIComponent(symbol)}/dcf`, { ...body, save: true }), onSuccess: () => toast('Valuation saved - it will appear in your PDF report') })

  if (!symbol) {
    return (<div><PageHeader eyebrow="Valuation Lab" title="Value a company" subtitle="Multiples, discounted cash flow, scenarios, sensitivity and comparable-company analysis - with every assumption editable and every formula shown." />
      <Card className="max-w-xl"><CompanyPicker onChange={(s) => nav(`/valuation/${encodeURIComponent(s)}`)} /></Card></div>)
  }
  if (q.isLoading) return <Loading />
  if (q.error instanceof ApiError && q.error.status === 404) return <EmptyState title="Company not tracked yet" action={<Link className="btn-primary" to={`/company/${encodeURIComponent(symbol)}`}>Open company page to fetch data</Link>} />
  const d = q.data!
  const set = (k: string, v: number) => setInp((p) => (p ? { ...p, [k]: v } : p))
  const r = dcf.data
  const updown = r && isNum(r.price) ? r.per_share / r.price - 1 : null
  const price = snap?.price ?? null
  const rel = (m: string) => d.relative.find((x) => x.Method === m)?.['Implied price'] ?? null
  const jpb = bank.ke > bank.g ? (bank.roe - bank.g) / (bank.ke - bank.g) : null
  const jpbValue = jpb && isNum(d.bvps) ? jpb * d.bvps : null
  const scnVals = r ? Object.values(r.scenarios).map((v) => v.per_share).filter(isNum) : []
  const estimates: Est[] = [
    ...(!d.is_financial ? [
      { label: 'DCF (FCFF)', low: scnVals.length ? Math.min(...scnVals) : null, high: scnVals.length ? Math.max(...scnVals) : null, mid: r?.per_share ?? null, note: 'Base case; bar = bear to bull' },
      { label: 'DCF (FCFE)', low: null, high: null, mid: r?.fcfe?.per_share ?? null, note: 'Equity cash flows at cost of equity' },
    ] : [{ label: 'Justified P/B', low: null, high: null, mid: jpbValue, note: '(ROE − g) / (Ke − g) × book value' }]),
    { label: 'Peer median P/E', low: null, high: null, mid: rel('pe'), note: 'Peer median × company earnings' },
    { label: 'Peer median P/B', low: null, high: null, mid: rel('pb'), note: 'Peer median × book value' },
    ...(!d.is_financial ? [{ label: 'Peer median EV/EBITDA', low: null, high: null, mid: rel('ev_ebitda'), note: 'Less net debt' }] : []),
    { label: 'Own median P/E', low: null, high: null, mid: d.implied_from_history?.pe ?? null, note: 'Historical median × current EPS' },
    { label: 'Own median P/B', low: null, high: null, mid: d.implied_from_history?.pb ?? null, note: 'Historical median × book value' },
  ]
  const anchor = d.is_financial ? jpbValue : r?.per_share ?? null
  const mos = isNum(anchor) && isNum(price) && anchor > 0 ? (anchor - price) / anchor : null

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Valuation Lab" title={<Link to={`/company/${encodeURIComponent(symbol)}`} className="hover:text-brand-600">{baseSymbol(symbol)} valuation</Link>}
        subtitle="Model outputs depend entirely on the assumptions below. They are an analytical exercise, not a recommendation or price target."
        actions={<div className="w-72"><CompanyPicker value={symbol} onChange={(s) => nav(`/valuation/${encodeURIComponent(s)}`)} /></div>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
        <Stat label="Price" value={inr(snap?.price)} /><Stat label="Market cap" value={crore(snap?.market_cap)} />
        <Stat label="P/E" value={mult(snap?.pe)} sub={snap?.basis.earnings ?? undefined} help={d.formulas.pe} /><Stat label="P/B" value={mult(snap?.pb)} help={d.formulas.pb} />
        <Stat label="EV/EBITDA" value={d.is_financial ? 'n.m.' : mult(snap?.ev_ebitda)} help={d.formulas.ev_ebitda} />
        <Stat label="Enterprise value" value={d.is_financial ? 'n.m.' : crore(snap?.ev)} help={d.formulas.ev} /><Stat label="Dividend yield" value={pct(snap?.dividend_yield)} />
      </div>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: 'summary', label: 'Summary' }, { id: 'multiples', label: 'Multiples & history' }, { id: 'dcf', label: 'DCF (FCFF)' }, { id: 'fcfe', label: 'DCF (FCFE)' }, { id: 'scenarios', label: 'Scenarios & sensitivity' }, { id: 'comps', label: 'Comparable companies' }, { id: 'banks', label: 'Justified P/B (banks)' }]} />

      {tab === 'summary' && (
        <div className="grid gap-5 xl:grid-cols-3">
          <Card className="xl:col-span-2" title="Estimated value range" subtitle="Each method makes different assumptions, so each gives a different answer. A wide spread means more uncertainty.">
            {!d.is_financial && !r && !dcf.error ? <Loading label="Running the models…" /> : <FootballField rows={estimates} price={price} />}
            <Notice tone="warn" className="mt-4">These are <b>model estimates, not the stock's true or exact value</b>, and not price targets. Change the assumptions in the DCF tabs and the range moves. Peer methods assume the peers are fairly priced.</Notice>
          </Card>
          <div className="space-y-5">
            <Card title="Margin of safety" subtitle={d.is_financial ? 'Based on the justified P/B estimate' : 'Based on the base-case FCFF DCF'}>
              <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300"><b>What it means:</b> how far the price sits below your estimate of value. The cushion protects you if your assumptions prove too optimistic.</p>
              <p className="mt-1.5 font-mono text-xs muted">MoS = (Estimated value − Price) / Estimated value</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Stat label="Estimate" value={inr(anchor)} /><Stat label="Current MoS" value={pct(mos, 1, true)} tone={isNum(mos) ? (mos >= 0 ? 'up' : 'down') : undefined} />
              </div>
              <label className="label mt-3">Margin of safety you would want: {pct(mosReq, 0)}</label>
              <input type="range" min={0} max={0.5} step={0.05} value={mosReq} onChange={(e) => setMosReq(Number(e.target.value))} className="w-full accent-brand-600" aria-label="Required margin of safety" />
              <p className="mt-1 text-sm">Price that would give that cushion: <b className="num">{isNum(anchor) && anchor > 0 ? inr(anchor * (1 - mosReq), 0) : 'Data not available'}</b></p>
              {isNum(mos) && <p className="mt-2 text-xs muted">{mos >= 0 ? `Under these assumptions the price is ${pct(mos, 0)} below the estimate.` : 'Under these assumptions the price is above the estimate, so there is no margin of safety.'} This is arithmetic on your inputs, not a buy or sell signal.</p>}
            </Card>
            <Card title="How to read this">
              <ul className="list-disc space-y-1.5 pl-4 text-sm text-slate-600 dark:text-slate-300">
                <li><b>DCF</b> values the business from its future cash flows. It is most sensitive to growth, margin and discount rate.</li>
                <li><b>Peer multiples</b> ask what similar listed companies trade at. Useful as a cross-check.</li>
                <li><b>Own history</b> asks whether the stock is cheaper or dearer than it usually is.</li>
                <li>If the methods broadly agree, the estimate is more robust. If they disagree, find the assumption that drives the gap.</li>
              </ul>
            </Card>
          </div>
        </div>
      )}

      {tab === 'multiples' && (
        <div className="grid gap-5 lg:grid-cols-2">
          <BandCard title="P/E versus its own history" b={d.bands?.pe} implied={d.implied_from_history?.pe ?? null} unit="earnings" />
          <BandCard title="P/B versus its own history" b={d.bands?.pb} implied={d.implied_from_history?.pb ?? null} unit="book value" />
          <Card title="P/E at each fiscal year-end">{d.history.length ? <LinesChart data={d.history} xKey="label" series={[{ key: 'pe', label: 'P/E' }]} fmt={(v) => `${v.toFixed(1)}x`} /> : <p className="text-sm muted">Needs statements and price history.</p>}</Card>
          <Card title="P/B at each fiscal year-end">{d.history.length ? <LinesChart data={d.history} xKey="label" series={[{ key: 'pb', label: 'P/B' }]} fmt={(v) => `${v.toFixed(1)}x`} /> : <p className="text-sm muted">—</p>}</Card>
          <Card title="Formulas" className="lg:col-span-2"><ul className="grid gap-2 text-sm sm:grid-cols-2">{Object.entries(d.formulas).map(([k, f]) => <li key={k} className="rounded-lg bg-slate-50 px-3 py-2 font-mono text-xs dark:bg-ink-800">{f}</li>)}</ul></Card>
        </div>
      )}

      {tab === 'dcf' && (d.is_financial ? <Notice tone="warn">A free-cash-flow DCF is not appropriate for banks and financial companies - debt is an operating input, not financing. Use the Justified P/B tab.</Notice>
        : !inp ? <EmptyState title="DCF cannot be built" body={d.dcf_notes.error ?? 'Insufficient data.'} /> : (
        <div className="grid gap-5 xl:grid-cols-3">
          <div className="space-y-5">
            <Card title="1 · Cost of capital" subtitle="CAPM: Ke = Rf + β × ERP · WACC = We·Ke + Wd·Kd·(1−t)" action={<DataBadge type="assumption" />}>
              <div className="grid grid-cols-2 gap-3">
                <PctInput label="Risk-free rate" value={capm.rf} onChange={(v) => setCapm({ ...capm, rf: v })} help="Approx. 10-year G-sec yield on your valuation date (RBI/CCIL)" />
                <div><label className="label">Beta</label><input className="input num" type="number" step="0.05" value={capm.beta} onChange={(e) => setCapm({ ...capm, beta: Number(e.target.value) })} /></div>
                <PctInput label="Equity risk premium" value={capm.erp} onChange={(v) => setCapm({ ...capm, erp: v })} help="Practitioner estimates for India commonly 6-8%" />
                <PctInput label="Pre-tax cost of debt" value={capm.kd} onChange={(v) => setCapm({ ...capm, kd: v })} help={isNum(d.kd_hint) ? `Finance costs / borrowings = ${pct(d.kd_hint)}` : undefined} />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-ink-800">Ke <b className="num float-right">{pct(w.ke, 2)}</b></div>
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-ink-800">Kd post-tax <b className="num float-right">{pct(w.kd, 2)}</b></div>
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-ink-800">Equity weight <b className="num float-right">{pct(w.we)}</b></div>
                <div className="rounded-lg bg-brand-50 p-2 font-semibold dark:bg-brand-500/15">WACC <b className="num float-right">{pct(w.wacc, 2)}</b></div>
              </div>
              <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={capm.override} onChange={(e) => setCapm({ ...capm, override: e.target.checked, wacc: w.wacc })} />Override WACC</label>
              {capm.override && <div className="mt-2"><PctInput label="WACC used" value={capm.wacc} onChange={(v) => setCapm({ ...capm, wacc: v })} /></div>}
            </Card>
            <Card title="2 · Operating assumptions" action={<DataBadge type="assumption" />}>
              <div className="grid grid-cols-2 gap-3">
                <PctInput label="Revenue growth, year 1" value={inp.growth_start} onChange={(v) => set('growth_start', v)} help={d.dcf_notes.growth_start} />
                <PctInput label="Growth, final year" value={inp.growth_end} onChange={(v) => set('growth_end', v)} help={d.dcf_notes.growth_end} />
                <PctInput label="EBIT margin" value={inp.ebit_margin} onChange={(v) => set('ebit_margin', v)} help={d.dcf_notes.ebit_margin} />
                <PctInput label="Tax rate" value={inp.tax_rate} onChange={(v) => set('tax_rate', v)} help={d.dcf_notes.tax_rate} />
                <PctInput label="D&A % revenue" value={inp.da_pct} onChange={(v) => set('da_pct', v)} help={d.dcf_notes.da_pct} />
                <PctInput label="Capex % revenue" value={inp.capex_pct} onChange={(v) => set('capex_pct', v)} help={d.dcf_notes.capex_to_revenue} />
                <PctInput label="ΔNWC % Δrevenue" value={inp.nwc_pct} onChange={(v) => set('nwc_pct', v)} step={1} help={d.dcf_notes.nwc_pct} />
                <PctInput label="Terminal growth" value={inp.terminal_growth} onChange={(v) => set('terminal_growth', v)} help="Long-run nominal growth; must be below WACC" />
                <div className="col-span-2"><label className="label">Explicit forecast: {inp.years} years</label><input type="range" min={3} max={10} value={inp.years} onChange={(e) => set('years', Number(e.target.value))} className="w-full accent-brand-600" /></div>
              </div>
            </Card>
          </div>
          <div className="space-y-5 xl:col-span-2">
            {dcf.error && <Notice tone="warn">{(dcf.error as Error).message}</Notice>}
            {r && (<>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Stat label="Estimated value / share" value={inr(r.per_share)} help="Model output under the assumptions on the left - an estimate, not an exact or guaranteed value" />
                <Stat label="Margin of safety" value={pct(r.margin_of_safety, 1, true)} tone={isNum(r.margin_of_safety) ? (r.margin_of_safety >= 0 ? 'up' : 'down') : undefined} help="(Estimated value − Price) / Estimated value. Negative means the price is above the estimate." />
                <Stat label="Model vs market" value={pct(updown, 1, true)} tone={isNum(updown) ? (updown >= 0 ? 'up' : 'down') : undefined} help="Difference between model value and market price under these assumptions - not a recommendation" />
                <Stat label="Enterprise value" value={crore(r.enterprise_value)} />
                <Stat label="Terminal value share" value={pct(r.terminal_share)} help="Above ~75% means long-run assumptions dominate the result" />
              </div>
              {r.terminal_share > 0.8 && <Notice tone="warn">{pct(r.terminal_share, 0)} of value comes from the terminal value - check the sensitivity table.</Notice>}
              <Card title="Free cash flow to the firm (₹ Cr)" subtitle="FCFF = EBIT×(1−t) + D&A − Capex − ΔNWC">
                <BarsChart data={r.projection.map((p) => ({ year: `Y${p.Year}`, FCFF: p.FCFF / 1e7, 'PV of FCFF': p['PV of FCFF'] / 1e7 }))} xKey="year"
                  series={[{ key: 'FCFF', label: 'FCFF' }, { key: 'PV of FCFF', label: 'Present value' }]} height={220} fmt={(v) => `₹${num(v, 0)} Cr`} yFmt={(v) => num(v, 0)} />
                <div className="mt-3 overflow-x-auto"><table className="w-full min-w-max text-sm">
                  <thead><tr><th className="table-head px-3 py-2">₹ Cr</th>{r.projection.map((p) => <th key={p.Year} className="table-head px-3 py-2 text-right">Y{p.Year}</th>)}</tr></thead>
                  <tbody>{[['Growth', 'Growth', 'pct'], ['Revenue', 'Revenue', 'cr'], ['EBIT', 'EBIT', 'cr'], ['NOPAT', 'NOPAT', 'cr'], ['+ D&A', 'D&A', 'cr'], ['− Capex', 'Capex', 'cr'], ['− ΔNWC', 'ΔNWC', 'cr'], ['FCFF', 'FCFF', 'cr'], ['Discount factor', 'Discount factor', 'num'], ['PV of FCFF', 'PV of FCFF', 'cr']].map(([lbl, key, kind]) => (
                    <tr key={key} className={cx('border-t border-slate-100 dark:border-ink-700', (key === 'FCFF' || key === 'PV of FCFF') && 'font-semibold')}>
                      <td className="px-3 py-1.5">{lbl}</td>{r.projection.map((p) => <td key={p.Year} className="num px-3 py-1.5 text-right">{kind === 'pct' ? pct(p[key]) : kind === 'num' ? p[key].toFixed(3) : num(p[key] / 1e7, 0)}</td>)}</tr>))}</tbody></table></div>
              </Card>
              <Card title="Enterprise value → equity value">
                <dl className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
                  {[['Sum of PV of FCFF', crore(r.pv_fcff)], ['Terminal value (Gordon growth)', crore(r.terminal_value)], ['PV of terminal value', crore(r.pv_terminal)], ['Enterprise value', crore(r.enterprise_value)],
                    [inp.net_debt >= 0 ? 'Less: net debt' : 'Add: net cash', crore(Math.abs(inp.net_debt))], ['Equity value', crore(r.equity_value)],
                    ['Shares outstanding', `${num(inp.shares / 1e7)} Cr`], ['Value per share', inr(r.per_share)]].map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-slate-100 py-1 dark:border-ink-700"><dt className="muted">{k}</dt><dd className="num font-medium">{v}</dd></div>))}
                </dl>
                <button className="btn-primary mt-4" onClick={() => save.mutate()} disabled={save.isPending}><Save className="h-4 w-4" />Save valuation for my report</button>
                {d.saved && <span className="ml-3 text-xs muted">Last saved {d.saved.saved}: {inr(d.saved.per_share)}</span>}
              </Card>
            </>)}
          </div>
        </div>
      ))}

      {tab === 'fcfe' && (d.is_financial ? <Notice tone="warn">Use the Justified P/B tab for banks and financial companies.</Notice>
        : !inp || !fx ? <EmptyState title="FCFE model cannot be built" body={d.dcf_notes.error ?? 'Insufficient data.'} /> : (
        <div className="grid gap-5 xl:grid-cols-3">
          <Card title="Equity assumptions" subtitle="Growth, D&A, capex, working capital and forecast length are shared with the FCFF tab." action={<DataBadge type="assumption" />}>
            <div className="grid grid-cols-2 gap-3">
              <PctInput label="Net profit margin" value={fx.net_margin} onChange={(v) => setFx({ ...fx, net_margin: v })} help={d.fcfe_notes.net_margin} />
              <PctInput label="Debt-funded share" value={fx.debt_ratio} onChange={(v) => setFx({ ...fx, debt_ratio: v })} step={1} help={`Share of net reinvestment financed by new borrowing. ${d.fcfe_notes.debt_ratio ?? ''}`} />
              <PctInput label="Cost of equity" value={keUsed} onChange={(v) => setFx({ ...fx, keOverride: v })} help="Defaults to the CAPM cost of equity on the FCFF tab" />
              <PctInput label="Terminal growth" value={inp.terminal_growth} onChange={(v) => set('terminal_growth', v)} help="Shared with the FCFF tab; must be below the cost of equity" />
            </div>
            <p className="mt-3 text-xs muted">FCFE suits companies with stable leverage. The cash flows are after interest and debt repayment, so they are discounted at the cost of equity and net debt is not subtracted.</p>
          </Card>
          <div className="space-y-5 xl:col-span-2">
            {r?.fcfe?.error && <Notice tone="warn">{r.fcfe.error}</Notice>}
            {!r && !dcf.error && <Loading />}
            {r?.fcfe?.projection && (<>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Estimated value (FCFE)" value={inr(r.fcfe.per_share)} /><Stat label="Estimated value (FCFF)" value={inr(r.per_share)} />
                <Stat label="Margin of safety" value={pct(r.fcfe.margin_of_safety, 1, true)} tone={isNum(r.fcfe.margin_of_safety) ? (r.fcfe.margin_of_safety >= 0 ? 'up' : 'down') : undefined} help="(Estimated value − Price) / Estimated value" />
                <Stat label="Terminal value share" value={pct(r.fcfe.terminal_share)} />
              </div>
              <Card title="Free cash flow to equity (₹ Cr)" subtitle="FCFE = Net profit − (Capex − D&A + ΔNWC) × (1 − debt-funded share)">
                <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
                  <thead><tr><th className="table-head px-3 py-2">₹ Cr</th>{r.fcfe.projection.map((p) => <th key={p.Year} className="table-head px-3 py-2 text-right">Y{p.Year}</th>)}</tr></thead>
                  <tbody>{[['Revenue', 'cr'], ['Net profit', 'cr'], ['Net reinvestment', 'cr'], ['Equity-funded reinvestment', 'cr'], ['FCFE', 'cr'], ['Discount factor', 'num'], ['PV of FCFE', 'cr']].map(([key, kind]) => (
                    <tr key={key} className={cx('border-t border-slate-100 dark:border-ink-700', key.includes('FCFE') && 'font-semibold')}>
                      <td className="px-3 py-1.5">{key}</td>{r.fcfe!.projection!.map((p) => <td key={p.Year} className="num px-3 py-1.5 text-right">{kind === 'num' ? p[key].toFixed(3) : num(p[key] / 1e7, 0)}</td>)}</tr>))}</tbody></table></div>
                <dl className="mt-4 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
                  {[['Sum of PV of FCFE', crore(r.fcfe.pv_fcfe)], ['PV of terminal value', crore(r.fcfe.pv_terminal)], ['Equity value', crore(r.fcfe.equity_value)], ['Value per share', inr(r.fcfe.per_share)]].map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-slate-100 py-1 dark:border-ink-700"><dt className="muted">{k}</dt><dd className="num font-medium">{v}</dd></div>))}
                </dl>
              </Card>
              <p className="text-xs muted">If FCFE and FCFF give very different answers, the leverage or margin assumptions are inconsistent with each other. That is a useful check, not an error.</p>
            </>)}
          </div>
        </div>
      ))}

      {tab === 'scenarios' && (d.is_financial ? <Notice>Not applicable to financial companies.</Notice> : !r ? <Loading /> : (
        <div className="grid gap-5 xl:grid-cols-2">
          <Card title="Bear / base / bull" subtitle="Shifts applied to the base case (percentage points): growth, EBIT margin, WACC, terminal growth">
            <table className="w-full text-sm"><thead><tr className="text-xs muted"><th className="text-left">Scenario</th><th>Growth</th><th>Margin</th><th>WACC</th><th>g</th><th className="text-right">Value / share</th></tr></thead>
              <tbody>{Object.keys(shifts).map((n) => (
                <tr key={n} className="border-t border-slate-100 dark:border-ink-700"><td className="py-2 font-medium">{n}</td>
                  {shifts[n].map((v, i) => <td key={i} className="px-1"><input className="input num px-2 py-1 text-xs" type="number" step="0.5" value={+(v * 100).toFixed(2)} disabled={n === 'Base'}
                    onChange={(e) => setShifts({ ...shifts, [n]: shifts[n].map((x, j) => (j === i ? Number(e.target.value) / 100 : x)) })} /></td>)}
                  <td className="num text-right font-semibold">{r.scenarios[n]?.per_share ? inr(r.scenarios[n].per_share) : r.scenarios[n]?.error ?? '—'}</td></tr>))}</tbody></table>
            <div className="mt-4"><BarsChart data={Object.entries(r.scenarios).map(([k, v]) => ({ scenario: k, value: v.per_share ?? null }))} xKey="scenario" series={[{ key: 'value', label: 'Value per share' }]} height={200} fmt={(v) => inr(v, 0)} /></div>
            {isNum(r.price) && <p className="text-xs muted">Market price {inr(r.price)}.</p>}
          </Card>
          <Card title="Sensitivity: value per share" subtitle="Rows: WACC · Columns: terminal growth · Blue = above market price, red = below">
            <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr><th className="p-1 text-xs muted">WACC \ g</th>{r.sensitivity.growths.map((g) => <th key={g} className="p-1 text-xs muted">{pct(g, 1)}</th>)}</tr></thead>
              <tbody>{r.sensitivity.waccs.map((wv, i) => (<tr key={wv}><td className="p-1 text-xs font-semibold muted">{pct(wv, 1)}</td>
                {r.sensitivity.values[i].map((v, j) => { const rel = isNum(v) && isNum(r.price) ? v / r.price - 1 : 0, a = Math.min(1, Math.abs(rel) / 0.5)
                  return <td key={j} className="num rounded p-2 text-center text-xs font-semibold" style={{ background: isNum(v) ? (rel >= 0 ? `rgba(42,120,214,${0.1 + a * 0.45})` : `rgba(220,53,69,${0.1 + a * 0.45})`) : undefined }}>{isNum(v) ? num(v, 0) : '—'}</td> })}</tr>))}</tbody></table></div>
            <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm dark:bg-ink-800"><b>Reverse DCF:</b> the market price implies constant revenue growth of <b className="num">{pct(r.implied_growth)}</b> over the forecast period, versus a historical 3-year CAGR of <b className="num">{pct(d.hist_cagr_3y)}</b>.</div>
          </Card>
        </div>
      ))}

      {tab === 'comps' && (
        <Card title="Comparable companies" subtitle="Implied price = peer median multiple × company metric (EV methods subtract net debt). Assumes peers are fairly valued and comparable.">
          {d.peers.length === 0 ? <p className="text-sm muted">No peers found.</p> : (<>
            <table className="w-full text-sm"><thead><tr className="text-xs muted"><th className="text-left">Peer</th><th className="text-right">P/E</th><th className="text-right">P/B</th><th className="text-right">EV/EBITDA</th><th className="text-right">ROE</th></tr></thead>
              <tbody>{d.peers.map((p) => <tr key={p.symbol} className="border-t border-slate-100 dark:border-ink-700"><td className="py-1.5"><Link className="hover:underline" to={`/company/${encodeURIComponent(p.symbol)}`}>{p.name}</Link></td><td className="num text-right">{mult(p.pe)}</td><td className="num text-right">{mult(p.pb)}</td><td className="num text-right">{mult(p.ev_ebitda)}</td><td className="num text-right">{pct(p.roe)}</td></tr>)}</tbody></table>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">{d.relative.filter((x) => !(d.is_financial && x.Method === 'ev_ebitda')).map((x) => (
              <div key={x.Method} className="rounded-xl border border-slate-200 p-3 dark:border-ink-700"><div className="text-xs font-semibold uppercase muted">{({ pe: 'P/E', pb: 'P/B', ev_ebitda: 'EV/EBITDA' } as Record<string, string>)[x.Method]} method</div>
                <div className="num mt-1 text-lg font-semibold">{inr(x['Implied price'])}</div><div className="text-xs muted">Peer median {mult(x['Peer median'])} · {x['Peers used']} peers</div></div>))}</div>
          </>)}
        </Card>
      )}

      {tab === 'banks' && (() => {
        const val = jpbValue
        return (
          <Card title="Justified price-to-book" subtitle="Justified P/B = (ROE − g) / (Ke − g) · Value per share = Justified P/B × Book value per share">
            {!d.is_financial && <Notice className="mb-3">Designed for banks/NBFCs/insurers, but usable for any company with stable ROE.</Notice>}
            <div className="grid max-w-xl grid-cols-3 gap-3">
              <PctInput label="Sustainable ROE" value={bank.roe} onChange={(v) => setBank({ ...bank, roe: v })} help={`3-year average ROE: ${pct(d.roe_3y)}`} />
              <PctInput label="Cost of equity" value={bank.ke} onChange={(v) => setBank({ ...bank, ke: v })} help="CAPM: Rf + β × ERP" />
              <PctInput label="Long-run growth" value={bank.g} onChange={(v) => setBank({ ...bank, g: v })} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Justified P/B" value={jpb ? `${jpb.toFixed(2)}x` : 'Ke must exceed g'} /><Stat label="Current P/B" value={mult(snap?.pb, 2)} />
              <Stat label="Book value / share" value={inr(d.bvps)} /><Stat label="Implied value / share" value={inr(val)} sub={val && isNum(snap?.price) ? `${pct(val / snap!.price! - 1, 1, true)} vs market` : undefined} />
            </div>
            <p className="mt-3 text-xs muted">A bank earning ROE above its cost of equity can justify P/B above 1x. Also review asset quality (GNPA/NNPA), capital adequacy and CASA on the company's Bank metrics tab.</p>
          </Card>
        )
      })()}
    </div>
  )
}
