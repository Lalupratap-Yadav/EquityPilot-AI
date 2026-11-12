// Thin typed client for the EquityPilot FastAPI backend. Cookies carry the (guest or signed-in) session.

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body && !isForm ? { 'Content-Type': 'application/json' } : undefined,
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  })
  if (!res.ok) {
    let msg = res.statusText
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: { msg: string }) => d.msg).join('; ') : msg
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, msg)
  }
  const type = res.headers.get('content-type') || ''
  return (type.includes('application/json') ? res.json() : res.blob()) as Promise<T>
}

export const api = {
  get: <T,>(p: string) => request<T>('GET', p),
  post: <T,>(p: string, b?: unknown) => request<T>('POST', p, b ?? {}),
  put: <T,>(p: string, b: unknown) => request<T>('PUT', p, b),
  patch: <T,>(p: string, b: unknown) => request<T>('PATCH', p, b),
  del: <T,>(p: string) => request<T>('DELETE', p),
  upload: <T,>(p: string, form: FormData) => request<T>('POST', p, form, true),
}

// ------------------------------------------------------------------ shared types
export type Status = 'live' | 'delayed' | 'close' | 'sample' | 'historical' | 'unavailable'

export interface Quote {
  symbol: string
  price: number | null
  prev_close: number | null
  change: number | null
  change_pct: number | null
  volume: number | null
  time: string | null
  status: Status
  source: string
}

export interface IndexRow {
  symbol: string
  name: string
  kind: 'broad' | 'sector'
  industry: string | null
  last: number
  change: number
  change_pct: number
  month_change_pct: number
  as_of: string
  spark: number[]
  status: Status
}

export interface MarketStatus { open: boolean; now_ist: string; note: string }

export interface Mover {
  symbol: string
  name: string
  industry: string | null
  price: number | null
  change_pct: number | null
  volume: number | null
  market_cap: number | null
  status: Status
}

export interface CompanyCardData {
  symbol: string
  name: string
  industry?: string | null
  category?: string | null
  market_cap?: number | null
  pe?: number | null
  roe?: number | null
  price?: number | null
  change_pct?: number | null
  status?: Status
}

export interface SearchResult {
  symbol: string
  name: string
  sector: string | null
  industry: string | null
  tracked: boolean
  is_sample: boolean
  category?: string | null
}

export interface Metrics {
  [key: string]: number | string | boolean | null | undefined
}

export interface User {
  id: number
  username: string | null
  display_name: string
  is_guest: boolean
  show_on_leaderboard: boolean
}
