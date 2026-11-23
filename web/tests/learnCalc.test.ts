import { describe, expect, it } from 'vitest'
import { editDistance, fuzzyFilter, score } from '../src/lib/fuzzy'
import * as L from '../src/lib/learnCalc'

// The same hand calculations as tests/test_learning_v28.py::test_calc_formulas_by_hand, so the browser calculators and
// the server-side formulas agree.
describe('learning formulas', () => {
  it('time value of money and interest', () => {
    expect(Math.round(L.fv(10_000, 0.08, 3))).toBe(12_597)
    expect(Math.round(L.pv(121_000, 0.1, 2))).toBe(100_000)
    expect(L.simpleInterest(20_000, 0.06, 4)).toBeCloseTo(4800)
    expect(L.effectiveRate(0.12, 12)).toBeCloseTo(0.126825, 5)
    expect(L.realReturn(0.07, 0.05)).toBeCloseTo(0.019048, 5)
    expect(Math.round(L.fv(100_000, 0.09, 5))).toBe(153_862)
  })
  it('ratios, bonds and portfolio', () => {
    expect(L.pe(840, 42)).toBe(20)
    expect(L.pe(100, 0)).toBeNaN()                                       // meaningless for zero or negative EPS
    expect(L.roe(90, 550, 650)).toBeCloseTo(0.15)
    expect(L.roce(300, 2500, 500)).toBeCloseTo(0.15)
    expect(L.freeCashFlow(300, -120)).toBe(180)                         // capex sign does not matter
    expect(L.approxYtm(80, 1000, 950, 5)).toBeCloseTo(0.0923, 4)
    expect(L.currentYield(70, 875)).toBeCloseTo(0.08)
    expect(L.portfolioReturn([0.5, 0.3, 0.2], [0.12, 0.08, -0.05])).toBeCloseTo(0.074)
    expect(L.twoAssetSd(0.5, 0.2, 0.2, 0.3)).toBeCloseTo(0.161245, 5)
    expect(L.sharpe(0.15, 0.065, 0.17)).toBeCloseTo(0.5)
    expect(L.capm(0.07, 1.2, 0.06)).toBeCloseTo(0.142)
    expect(L.wacc(0.136, 0.09, 0.25, 0.8)).toBeCloseTo(0.1223)
  })
  it('DCF matches the worked example and refuses g >= r', () => {
    const d = L.dcf(100, 0.1, 5, 0.12, 0.05, 200, 10)!
    expect(d.enterpriseValue).toBeCloseTo(1844.61, 1)
    expect(d.perShare).toBeCloseTo(164.46, 1)
    expect(d.terminalShare).toBeCloseTo(0.743, 2)
    expect(L.dcf(100, 0.1, 5, 0.05, 0.06)).toBeNull()
    expect(L.gordon(208, 0.12, 0.04)).toBeCloseTo(2600)
  })
  it('linked statements balance like the lesson example', () => {
    const y = L.linkedYear({ revenue: 1000, opex: 750, depreciation: 50, interest: 20, taxRate: 0.25, dividends: 40, capex: 90, wcIncrease: 40,
      debtChange: -30, openingCash: 80, openingPpe: 600, openingRetained: 450, openingDebt: 300 })
    expect(y.pat).toBeCloseTo(135)            // 1000 - 750 - 50 - 20 = 180 PBT; 25% tax
    expect(y.cfo).toBeCloseTo(145)
    expect(y.closingCash).toBeCloseTo(80 + 145 - 90 - 70)
    expect(y.closingPpe).toBe(640)
    expect(y.closingRetained).toBeCloseTo(450 + 135 - 40)
  })
})

describe('typo-tolerant search', () => {
  const terms = [['ROCE', 'return on capital employed'], ['ROE', 'return on equity'], ['Debt to equity', 'd/e'], ['Sharpe ratio', 'sharpe'],
    ['Repo rate', 'policy rate'], ['Free cash flow', 'fcf']]
  const find = (q: string) => fuzzyFilter(terms, q, (t) => t)[0]?.[0]
  it('ranks exact, prefix and misspelt matches', () => {
    expect(find('roce')).toBe('ROCE')
    expect(find('rocce')).toBe('ROCE')
    expect(find('debt to equty')).toBe('Debt to equity')
    expect(find('sharp ratio')).toBe('Sharpe ratio')
    expect(find('repo')).toBe('Repo rate')
    expect(find('free cash')).toBe('Free cash flow')
    expect(fuzzyFilter(terms, 'zzzzzz', (t) => t)).toEqual([])
  })
  it('edit distance handles transpositions', () => {
    expect(editDistance('ratio', 'raito')).toBe(1)
    expect(editDistance('equity', 'equty')).toBe(1)
    expect(score('', ['x'])).toBe(0)
  })
})
