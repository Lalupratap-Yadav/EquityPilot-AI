// Indian number formatting. Missing values always render as an em dash.

export const DASH = '—'

export const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

const inGroup = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
const inGroup0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export function inr(v: unknown, decimals = 2): string {
  if (!isNum(v)) return DASH
  return '₹' + (decimals === 0 ? inGroup0.format(v) : inGroup.format(v))
}

export function num(v: unknown, decimals = 2): string {
  if (!isNum(v)) return DASH
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }).format(v)
}

/** Absolute rupees -> "₹1,23,456 Cr" or "₹1.23 L Cr" for very large values. */
export function crore(v: unknown, compact = true): string {
  if (!isNum(v)) return DASH
  const cr = v / 1e7
  if (compact && Math.abs(cr) >= 1e5) return `₹${(cr / 1e5).toFixed(2)} L Cr`
  return `₹${inGroup0.format(cr)} Cr`
}

export function pct(v: unknown, decimals = 1, signed = false): string {
  if (!isNum(v)) return DASH
  const s = (v * 100).toFixed(decimals)
  return `${signed && v > 0 ? '+' : ''}${s}%`
}

export function mult(v: unknown, decimals = 1): string {
  return isNum(v) ? `${v.toFixed(decimals)}x` : DASH
}

export function compactNum(v: unknown): string {
  if (!isNum(v)) return DASH
  if (Math.abs(v) >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`
  if (Math.abs(v) >= 1e5) return `${(v / 1e5).toFixed(2)} L`
  return inGroup0.format(v)
}

/** Format by metric kind as used by the backend (pct | x | inr | cr | num | days | pctpt). */
export function byKind(v: unknown, kind: string): string {
  switch (kind) {
    case 'pct': return pct(v)
    case 'x': return mult(v)
    case 'inr': return inr(v)
    case 'cr': return crore(v)
    case 'days': return isNum(v) ? `${v.toFixed(0)} d` : DASH
    case 'pctpt': return isNum(v) ? `${v.toFixed(2)}%` : DASH
    default: return isNum(v) ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : DASH
  }
}

export function ist(iso: string | null | undefined, withTime = true): string {
  if (!iso) return DASH
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
  }) + (withTime ? ' IST' : '')
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return DASH
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  const s = (Date.now() - d.getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 86400 * 30) return `${Math.floor(s / 86400)}d ago`
  return ist(iso, false)
}

export const baseSymbol = (s: string) => s.replace(/\.(NS|BO)$/, '')

export const upDown = (v: unknown) => (isNum(v) ? (v > 0 ? 'text-up' : v < 0 ? 'text-down' : 'muted') : 'muted')
