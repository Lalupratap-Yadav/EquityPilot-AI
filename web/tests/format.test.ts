import { describe, expect, it } from 'vitest'
import { baseSymbol, crore, dayLabel, inr, isNum, mult, pct } from '../src/lib/format'

describe('number formatting never invents values', () => {
  it('shows a dash for missing or invalid values, never zero', () => {
    for (const v of [null, undefined, NaN, Infinity, 'abc']) {
      expect(inr(v)).toBe('—')
      expect(pct(v)).toBe('—')
      expect(mult(v)).toBe('—')
    }
    expect(isNum(0)).toBe(true)
    expect(isNum(NaN)).toBe(false)
  })
  it('formats real values in Indian style', () => {
    expect(inr(1234567.5)).toContain('12,34,567')
    expect(pct(0.1234)).toBe('12.3%')
    expect(mult(17.12)).toBe('17.1x')
    expect(crore(5e11)).toMatch(/Cr/)
  })
  it('handles symbols and calendar dates', () => {
    expect(baseSymbol('TCS.NS')).toBe('TCS')
    expect(baseSymbol('M&M.BO')).toBe('M&M')
    expect(dayLabel('2026-11-18', { day: 'numeric', month: 'short', year: 'numeric' })).toMatch(/18 Nov 2026/)
  })
})
