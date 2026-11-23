import { Calculator } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { cx } from '../../components/ui'
import * as L from '../../lib/learnCalc'

/** Interactive calculators for the Learning Centre. Every input starts with round illustrative numbers that the learner
 *  can change; results show each step. Formulas match equitypilot/content/curriculum/calc.py. */

const nf = (v: number, d = 2) => (Number.isFinite(v) ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: d, minimumFractionDigits: 0 }).format(v) : '—')
const rs = (v: number, d = 0) => (Number.isFinite(v) ? `₹${nf(v, d)}` : '—')
const pc = (v: number, d = 2) => (Number.isFinite(v) ? `${(v * 100).toFixed(d)}%` : '—')
const x = (v: number, d = 2) => (Number.isFinite(v) ? `${v.toFixed(d)}x` : '—')

type Vals = Record<string, string>
function useVals(init: Record<string, number>): [Record<string, number>, Vals, (k: string, v: string) => void] {
  const [raw, setRaw] = useState<Vals>(() => Object.fromEntries(Object.entries(init).map(([k, v]) => [k, String(v)])))
  const num = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v.trim() === '' || Number.isNaN(Number(v)) ? NaN : Number(v)]))
  return [num, raw, (k, v) => setRaw((p) => ({ ...p, [k]: v }))]
}

function Field({ id, label, unit, raw, set, step = 'any' }: { id: string; label: string; unit?: string; raw: Vals; set: (k: string, v: string) => void; step?: string }) {
  const bad = raw[id].trim() === '' || Number.isNaN(Number(raw[id]))
  return (
    <label className="block min-w-0">
      <span className="label">{label}{unit ? ` (${unit})` : ''}</span>
      <input className={cx('input num', bad && 'border-down focus:border-down')} inputMode="decimal" type="number" step={step}
        value={raw[id]} aria-invalid={bad} onChange={(e) => set(id, e.target.value)} />
    </label>
  )
}

function Panel({ title, inputs, steps, result, note }: { title: string; inputs: ReactNode; steps: ReactNode[]; result: ReactNode; note?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 p-4 dark:border-ink-700" data-testid="calculator">
      <div className="mb-3 flex items-center gap-2 font-semibold"><Calculator className="h-4 w-4 text-brand-600" />{title}</div>
      <p className="mb-3 text-xs muted">Illustrative starting numbers: change any input. These are not company data.</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{inputs}</div>
      <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm dark:bg-ink-800">
        <div className="text-[11px] font-semibold uppercase tracking-wide muted">Steps</div>
        <ol className="mt-1.5 list-decimal space-y-1 pl-5 font-mono text-[13px]">{steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
        <div className="mt-3 text-base font-semibold" data-testid="calc-result">{result}</div>
        {note && <p className="mt-1 text-xs muted">{note}</p>}
      </div>
    </div>
  )
}

const pctOf = (v: number) => v / 100

function Interest() {
  const [v, raw, set] = useVals({ p: 100000, r: 9, n: 5, m: 1 })
  const r = pctOf(v.r)
  const si = L.simpleInterest(v.p, r, v.n), amt = L.fv(v.p, r, v.n, v.m)
  return <Panel title="Simple vs compound interest"
    inputs={<><Field id="p" label="Principal" unit="₹" raw={raw} set={set} /><Field id="r" label="Annual rate" unit="%" raw={raw} set={set} />
      <Field id="n" label="Years" raw={raw} set={set} /><Field id="m" label="Compounding per year" raw={raw} set={set} step="1" /></>}
    steps={[`Simple interest = ${rs(v.p)} × ${nf(r, 4)} × ${nf(v.n)} = ${rs(si)}`,
      `Compound amount = ${rs(v.p)} × (1 + ${nf(r, 4)} ÷ ${nf(v.m, 0)})^(${nf(v.m, 0)} × ${nf(v.n)}) = ${rs(amt)}`,
      `Compound interest = ${rs(amt)} − ${rs(v.p)} = ${rs(amt - v.p)}`, `Effective annual rate = ${pc(L.effectiveRate(r, v.m))}`]}
    result={<>Compound {rs(amt)} vs simple {rs(v.p + si)}</>} note={`Interest on interest adds ${rs(amt - v.p - si)}.`} />
}

function RealReturn() {
  const [v, raw, set] = useVals({ n: 7, i: 5, t: 0 })
  const after = pctOf(v.n) * (1 - pctOf(v.t))
  return <Panel title="Nominal vs real return"
    inputs={<><Field id="n" label="Nominal return" unit="%" raw={raw} set={set} /><Field id="i" label="Inflation" unit="%" raw={raw} set={set} /><Field id="t" label="Tax on the return" unit="%" raw={raw} set={set} /></>}
    steps={[`After-tax return = ${pc(pctOf(v.n))} × (1 − ${pc(pctOf(v.t), 0)}) = ${pc(after)}`,
      `Real return = (1 + ${nf(after, 4)}) ÷ (1 + ${nf(pctOf(v.i), 4)}) − 1 = ${pc(L.realReturn(after, pctOf(v.i)))}`]}
    result={<>Real return {pc(L.realReturn(after, pctOf(v.i)))}</>} note="A negative real return means your money buys less than before." />
}

function EpsPe() {
  const [v, raw, set] = useVals({ pat: 1425, sh: 50, price: 570 })
  const e = L.eps(v.pat, v.sh), p = L.pe(v.price, e)
  return <Panel title="EPS and P/E"
    inputs={<><Field id="pat" label="Net profit" unit="₹ crore" raw={raw} set={set} /><Field id="sh" label="Shares" unit="crore" raw={raw} set={set} /><Field id="price" label="Share price" unit="₹" raw={raw} set={set} /></>}
    steps={[`EPS = ${nf(v.pat)} ÷ ${nf(v.sh)} = ${rs(e, 2)}`, `P/E = ${rs(v.price, 2)} ÷ ${rs(e, 2)} = ${x(p, 1)}`, `Earnings yield = 1 ÷ P/E = ${pc(1 / p)}`]}
    result={<>EPS {rs(e, 2)} · P/E {x(p, 1)}</>} note={Number.isFinite(p) ? undefined : 'P/E is not meaningful when EPS is zero or negative.'} />
}

function RoeRoce() {
  const [v, raw, set] = useVals({ pat: 150, e0: 900, e1: 1100, ebit: 280, ta: 2000, cl: 400 })
  return <Panel title="ROE and ROCE"
    inputs={<><Field id="pat" label="Net profit" unit="₹ cr" raw={raw} set={set} /><Field id="e0" label="Opening equity" unit="₹ cr" raw={raw} set={set} />
      <Field id="e1" label="Closing equity" unit="₹ cr" raw={raw} set={set} /><Field id="ebit" label="EBIT" unit="₹ cr" raw={raw} set={set} />
      <Field id="ta" label="Total assets" unit="₹ cr" raw={raw} set={set} /><Field id="cl" label="Current liabilities" unit="₹ cr" raw={raw} set={set} /></>}
    steps={[`Average equity = (${nf(v.e0)} + ${nf(v.e1)}) ÷ 2 = ${nf((v.e0 + v.e1) / 2)}`, `ROE = ${nf(v.pat)} ÷ ${nf((v.e0 + v.e1) / 2)} = ${pc(L.roe(v.pat, v.e0, v.e1), 1)}`,
      `Capital employed = ${nf(v.ta)} − ${nf(v.cl)} = ${nf(v.ta - v.cl)}`, `ROCE = ${nf(v.ebit)} ÷ ${nf(v.ta - v.cl)} = ${pc(L.roce(v.ebit, v.ta, v.cl), 1)}`]}
    result={<>ROE {pc(L.roe(v.pat, v.e0, v.e1), 1)} · ROCE {pc(L.roce(v.ebit, v.ta, v.cl), 1)}</>} />
}

function Statements() {
  const [v, raw, set] = useVals({ rev: 1000, opex: 750, dep: 50, int: 20, tax: 25, div: 40, capex: 90, wc: 40, debt: -30, cash: 80, ppe: 600, re: 450, d0: 300 })
  const y = L.linkedYear({ revenue: v.rev, opex: v.opex, depreciation: v.dep, interest: v.int, taxRate: pctOf(v.tax), dividends: v.div, capex: v.capex,
    wcIncrease: v.wc, debtChange: v.debt, openingCash: v.cash, openingPpe: v.ppe, openingRetained: v.re, openingDebt: v.d0 })
  return <Panel title="Linked financial statements (one year, ₹ crore)"
    inputs={<><Field id="rev" label="Revenue" raw={raw} set={set} /><Field id="opex" label="Operating costs" raw={raw} set={set} /><Field id="dep" label="Depreciation" raw={raw} set={set} />
      <Field id="int" label="Finance costs" raw={raw} set={set} /><Field id="tax" label="Tax rate" unit="%" raw={raw} set={set} /><Field id="div" label="Dividends paid" raw={raw} set={set} />
      <Field id="capex" label="Capex" raw={raw} set={set} /><Field id="wc" label="Increase in working capital" raw={raw} set={set} /><Field id="debt" label="New borrowing (− = repaid)" raw={raw} set={set} />
      <Field id="cash" label="Opening cash" raw={raw} set={set} /><Field id="ppe" label="Opening PPE" raw={raw} set={set} /><Field id="re" label="Opening retained earnings" raw={raw} set={set} /></>}
    steps={[`P&L: EBITDA ${nf(y.ebitda)} → EBIT ${nf(y.ebit)} → PBT ${nf(y.pbt)} → tax ${nf(y.tax)} → PAT ${nf(y.pat)}`,
      `CFO = PAT ${nf(y.pat)} + depreciation ${nf(v.dep)} − working capital ${nf(v.wc)} = ${nf(y.cfo)}`,
      `CFI = −capex = ${nf(y.cfi)}; CFF = borrowing ${nf(v.debt)} − dividends ${nf(v.div)} = ${nf(y.cff)}`,
      `Cash: ${nf(v.cash)} + ${nf(y.cfo)} + (${nf(y.cfi)}) + (${nf(y.cff)}) = ${nf(y.closingCash)}`,
      `PPE: ${nf(v.ppe)} + ${nf(v.capex)} − ${nf(v.dep)} = ${nf(y.closingPpe)}; retained earnings: ${nf(v.re)} + ${nf(y.pat)} − ${nf(v.div)} = ${nf(y.closingRetained)}`]}
    result={<>PAT {nf(y.pat)} · CFO {nf(y.cfo)} · FCF {nf(y.fcf)} · closing cash {nf(y.closingCash)}</>}
    note="Profit flows into retained earnings; depreciation is added back in CFO; capex moves PPE; the cash flow explains the change in cash." />
}

function Fcf() {
  const [v, raw, set] = useVals({ cfo: 300, capex: 120, rev: 1500, mcap: 6000 })
  const f = L.freeCashFlow(v.cfo, v.capex)
  return <Panel title="Free cash flow"
    inputs={<><Field id="cfo" label="Cash from operations" unit="₹ cr" raw={raw} set={set} /><Field id="capex" label="Capex" unit="₹ cr" raw={raw} set={set} />
      <Field id="rev" label="Revenue" unit="₹ cr" raw={raw} set={set} /><Field id="mcap" label="Market cap" unit="₹ cr" raw={raw} set={set} /></>}
    steps={[`FCF = ${nf(v.cfo)} − ${nf(Math.abs(v.capex))} = ${nf(f)}`, `FCF margin = ${nf(f)} ÷ ${nf(v.rev)} = ${pc(f / v.rev, 1)}`, `FCF yield = ${nf(f)} ÷ ${nf(v.mcap)} = ${pc(f / v.mcap, 1)}`]}
    result={<>FCF ₹{nf(f)} crore</>} note={f < 0 ? 'Negative FCF has to be funded by borrowing, new equity or cash reserves.' : undefined} />
}

function Bond() {
  const [v, raw, set] = useVals({ face: 1000, c: 8, price: 950, n: 5 })
  const coupon = v.face * pctOf(v.c)
  return <Panel title="Bond yield"
    inputs={<><Field id="face" label="Face value" unit="₹" raw={raw} set={set} /><Field id="c" label="Coupon rate" unit="%" raw={raw} set={set} />
      <Field id="price" label="Market price" unit="₹" raw={raw} set={set} /><Field id="n" label="Years to maturity" raw={raw} set={set} /></>}
    steps={[`Annual coupon = ${rs(v.face)} × ${pc(pctOf(v.c), 1)} = ${rs(coupon, 2)}`, `Current yield = ${rs(coupon, 2)} ÷ ${rs(v.price, 2)} = ${pc(L.currentYield(coupon, v.price))}`,
      `Approx. YTM = (${nf(coupon)} + (${nf(v.face)} − ${nf(v.price)}) ÷ ${nf(v.n)}) ÷ ((${nf(v.face)} + ${nf(v.price)}) ÷ 2) = ${pc(L.approxYtm(coupon, v.face, v.price, v.n))}`]}
    result={<>Current yield {pc(L.currentYield(coupon, v.price))} · YTM ≈ {pc(L.approxYtm(coupon, v.face, v.price, v.n))}</>}
    note="Below face value the yield is above the coupon; above face value it is below. The approximation is close for typical bonds." />
}

function Portfolio() {
  const [v, raw, set] = useVals({ w1: 50, r1: 12, w2: 30, r2: 8, w3: 20, r3: -5, sd: 15, rf: 7 })
  const w = [v.w1, v.w2, v.w3].map(pctOf), r = [v.r1, v.r2, v.r3].map(pctOf)
  const total = w.reduce((a, b) => a + b, 0), rp = L.portfolioReturn(w, r)
  return <Panel title="Portfolio return and Sharpe ratio"
    inputs={<><Field id="w1" label="Weight 1" unit="%" raw={raw} set={set} /><Field id="r1" label="Return 1" unit="%" raw={raw} set={set} /><Field id="w2" label="Weight 2" unit="%" raw={raw} set={set} />
      <Field id="r2" label="Return 2" unit="%" raw={raw} set={set} /><Field id="w3" label="Weight 3" unit="%" raw={raw} set={set} /><Field id="r3" label="Return 3" unit="%" raw={raw} set={set} />
      <Field id="sd" label="Portfolio volatility" unit="%" raw={raw} set={set} /><Field id="rf" label="Risk-free rate" unit="%" raw={raw} set={set} /></>}
    steps={[`Return = ${w.map((wi, i) => `${nf(wi, 2)} × ${pc(r[i], 0)}`).join(' + ')} = ${pc(rp)}`, `Sharpe = (${pc(rp)} − ${pc(pctOf(v.rf), 1)}) ÷ ${pc(pctOf(v.sd), 0)} = ${nf(L.sharpe(rp, pctOf(v.rf), pctOf(v.sd)))}`]}
    result={<>Return {pc(rp)} · Sharpe {nf(L.sharpe(rp, pctOf(v.rf), pctOf(v.sd)))}</>}
    note={Math.abs(total - 1) > 0.001 ? `Weights add up to ${pc(total, 0)}; they should add up to 100%.` : undefined} />
}

function Diversification() {
  const [v, raw, set] = useVals({ w: 50, s1: 20, s2: 20, c: 0.3 })
  const sd = L.twoAssetSd(pctOf(v.w), pctOf(v.s1), pctOf(v.s2), v.c)
  const avg = pctOf(v.w) * pctOf(v.s1) + (1 - pctOf(v.w)) * pctOf(v.s2)
  return <Panel title="Diversification with two assets"
    inputs={<><Field id="w" label="Weight in asset A" unit="%" raw={raw} set={set} /><Field id="s1" label="Volatility of A" unit="%" raw={raw} set={set} />
      <Field id="s2" label="Volatility of B" unit="%" raw={raw} set={set} /><Field id="c" label="Correlation (−1 to 1)" raw={raw} set={set} /></>}
    steps={[`σp = √(w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρσ₁σ₂) = ${pc(sd, 1)}`, `Weighted average volatility = ${pc(avg, 1)}`, `Diversification benefit = ${pc(avg - sd, 1)}`]}
    result={<>Portfolio volatility {pc(sd, 1)}</>} note={v.c > 1 || v.c < -1 ? 'Correlation must be between −1 and 1.' : 'Lower correlation means a larger benefit. Correlations often rise in crises.'} />
}

function Dcf() {
  const [v, raw, set] = useVals({ f0: 100, g: 10, n: 5, r: 12, tg: 5, nd: 200, sh: 10 })
  const d = L.dcf(v.f0, pctOf(v.g), Math.round(v.n), pctOf(v.r), pctOf(v.tg), v.nd, v.sh)
  return <Panel title="Basic DCF (₹ crore)"
    inputs={<><Field id="f0" label="FCF this year" raw={raw} set={set} /><Field id="g" label="Growth" unit="%/yr" raw={raw} set={set} /><Field id="n" label="Forecast years" raw={raw} set={set} step="1" />
      <Field id="r" label="Discount rate (WACC)" unit="%" raw={raw} set={set} /><Field id="tg" label="Terminal growth" unit="%" raw={raw} set={set} />
      <Field id="nd" label="Net debt" raw={raw} set={set} /><Field id="sh" label="Shares" unit="crore" raw={raw} set={set} /></>}
    steps={d ? [`FCF: ${d.flows.map((f) => nf(f, 1)).join(', ')}`, `Present values: ${d.pvs.map((f) => nf(f, 1)).join(', ')} (sum ${nf(d.pvs.reduce((a, b) => a + b, 0), 1)})`,
      `Terminal value = ${nf(d.flows[d.flows.length - 1], 1)} × (1 + ${nf(pctOf(v.tg), 3)}) ÷ (${nf(pctOf(v.r), 3)} − ${nf(pctOf(v.tg), 3)}) = ${nf(d.terminalValue, 1)}; today ${nf(d.pvTerminal, 1)}`,
      `EV = ${nf(d.enterpriseValue, 1)}; equity = EV − net debt = ${nf(d.equityValue, 1)}; per share = ${rs(d.perShare, 2)}`]
      : ['Terminal growth must be below the discount rate, and there must be at least one forecast year.']}
    result={d ? <>Value per share {rs(d.perShare, 2)}</> : <span className="text-down">Not defined for these inputs</span>}
    note={d ? `The terminal value is ${pc(d.terminalShare, 0)} of enterprise value: the long-run assumptions matter most.` : undefined} />
}

function Wacc() {
  const [v, raw, set] = useVals({ rf: 7, b: 1.1, erp: 6, kd: 9, t: 25, we: 80 })
  const ke = L.capm(pctOf(v.rf), v.b, pctOf(v.erp)), w = L.wacc(ke, pctOf(v.kd), pctOf(v.t), pctOf(v.we))
  return <Panel title="Cost of equity (CAPM) and WACC"
    inputs={<><Field id="rf" label="Risk-free rate" unit="%" raw={raw} set={set} /><Field id="b" label="Beta" raw={raw} set={set} /><Field id="erp" label="Equity risk premium" unit="%" raw={raw} set={set} />
      <Field id="kd" label="Pre-tax cost of debt" unit="%" raw={raw} set={set} /><Field id="t" label="Tax rate" unit="%" raw={raw} set={set} /><Field id="we" label="Equity weight" unit="%" raw={raw} set={set} /></>}
    steps={[`Ke = ${pc(pctOf(v.rf), 1)} + ${nf(v.b)} × ${pc(pctOf(v.erp), 1)} = ${pc(ke)}`, `After-tax Kd = ${pc(pctOf(v.kd), 1)} × (1 − ${pc(pctOf(v.t), 0)}) = ${pc(pctOf(v.kd) * (1 - pctOf(v.t)))}`,
      `WACC = ${pc(pctOf(v.we), 0)} × ${pc(ke)} + ${pc(1 - pctOf(v.we), 0)} × ${pc(pctOf(v.kd) * (1 - pctOf(v.t)))} = ${pc(w)}`]}
    result={<>Ke {pc(ke)} · WACC {pc(w)}</>} note="Use market-value weights. The equity risk premium is a judgement, so test a range." />
}

const CALCULATORS: Record<string, () => ReactNode> = {
  interest: Interest, 'real-return': RealReturn, 'eps-pe': EpsPe, 'roe-roce': RoeRoce, statements: Statements, fcf: Fcf,
  bond: Bond, portfolio: Portfolio, diversification: Diversification, dcf: Dcf, wacc: Wacc,
}

export function CalculatorView({ id }: { id: string }) {
  const C = CALCULATORS[id]
  return C ? <C /> : null
}
