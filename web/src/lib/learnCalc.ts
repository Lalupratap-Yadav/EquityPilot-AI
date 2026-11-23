/** Learning Centre formulas, the same as equitypilot/content/curriculum/calc.py (tested against the same hand calculations).
 *  Rates are fractions (0.08 = 8%). Functions return NaN instead of throwing when an input makes a formula undefined. */

export const fv = (pv: number, rate: number, years: number, perYear = 1) => pv * (1 + rate / perYear) ** (perYear * years)
export const pv = (future: number, rate: number, years: number) => future / (1 + rate) ** years
export const simpleInterest = (p: number, rate: number, years: number) => p * rate * years
export const effectiveRate = (rate: number, perYear: number) => (1 + rate / perYear) ** perYear - 1
export const realReturn = (nominal: number, inflation: number) => (1 + nominal) / (1 + inflation) - 1
export const eps = (profit: number, shares: number) => (shares ? profit / shares : NaN)
export const pe = (price: number, epsValue: number) => (epsValue > 0 ? price / epsValue : NaN)
export const roe = (profit: number, eq0: number, eq1: number) => { const avg = (eq0 + eq1) / 2; return avg > 0 ? profit / avg : NaN }
export const roce = (ebit: number, assets: number, currentLiab: number) => { const ce = assets - currentLiab; return ce > 0 ? ebit / ce : NaN }
export const freeCashFlow = (cfo: number, capex: number) => cfo - Math.abs(capex)
export const currentYield = (coupon: number, price: number) => (price > 0 ? coupon / price : NaN)
export const approxYtm = (coupon: number, face: number, price: number, years: number) =>
  years > 0 && face + price > 0 ? (coupon + (face - price) / years) / ((face + price) / 2) : NaN
export const portfolioReturn = (weights: number[], returns: number[]) => weights.reduce((a, w, i) => a + w * (returns[i] ?? 0), 0)
export const twoAssetSd = (w1: number, sd1: number, sd2: number, corr: number) => {
  const w2 = 1 - w1
  return Math.sqrt(w1 ** 2 * sd1 ** 2 + w2 ** 2 * sd2 ** 2 + 2 * w1 * w2 * corr * sd1 * sd2)
}
export const sharpe = (rp: number, rf: number, sd: number) => (sd > 0 ? (rp - rf) / sd : NaN)
export const capm = (rf: number, beta: number, erp: number) => rf + beta * erp
export const wacc = (ke: number, kd: number, tax: number, wEquity: number) => wEquity * ke + (1 - wEquity) * kd * (1 - tax)
export const gordon = (nextCf: number, rate: number, growth: number) => (growth < rate ? nextCf / (rate - growth) : NaN)

export interface DcfResult {
  flows: number[]; pvs: number[]; terminalValue: number; pvTerminal: number
  enterpriseValue: number; equityValue: number; perShare: number; terminalShare: number
}

/** FCF grows at `growth` for `years`, then at `terminalGrowth` for ever. Returns null when terminal growth >= the discount rate. */
export function dcf(fcf0: number, growth: number, years: number, rate: number, terminalGrowth: number, netDebt = 0, shares = 1): DcfResult | null {
  if (terminalGrowth >= rate || years < 1) return null
  const flows = Array.from({ length: years }, (_, i) => fcf0 * (1 + growth) ** (i + 1))
  const pvs = flows.map((f, i) => f / (1 + rate) ** (i + 1))
  const terminalValue = gordon(flows[flows.length - 1] * (1 + terminalGrowth), rate, terminalGrowth)
  const pvTerminal = terminalValue / (1 + rate) ** years
  const enterpriseValue = pvs.reduce((a, b) => a + b, 0) + pvTerminal
  const equityValue = enterpriseValue - netDebt
  return { flows, pvs, terminalValue, pvTerminal, enterpriseValue, equityValue, perShare: shares ? equityValue / shares : NaN, terminalShare: pvTerminal / enterpriseValue }
}

export interface LinkedYear {
  ebitda: number; ebit: number; pbt: number; tax: number; pat: number
  cfo: number; cfi: number; cff: number; cashChange: number; closingCash: number
  closingPpe: number; closingRetained: number; closingDebt: number; fcf: number
}

/** One year of linked statements: the P&L down to PAT, the cash flow statement, and the balance-sheet items they move. */
export function linkedYear(i: {
  revenue: number; opex: number; depreciation: number; interest: number; taxRate: number; dividends: number
  capex: number; wcIncrease: number; debtChange: number; openingCash: number; openingPpe: number; openingRetained: number; openingDebt: number
}): LinkedYear {
  const ebitda = i.revenue - i.opex
  const ebit = ebitda - i.depreciation
  const pbt = ebit - i.interest
  const tax = Math.max(pbt, 0) * i.taxRate
  const pat = pbt - tax
  const cfo = pat + i.depreciation - i.wcIncrease
  const cfi = -i.capex
  const cff = i.debtChange - i.dividends
  const cashChange = cfo + cfi + cff
  return {
    ebitda, ebit, pbt, tax, pat, cfo, cfi, cff, cashChange, closingCash: i.openingCash + cashChange,
    closingPpe: i.openingPpe + i.capex - i.depreciation, closingRetained: i.openingRetained + pat - i.dividends,
    closingDebt: i.openingDebt + i.debtChange, fcf: cfo - i.capex,
  }
}
