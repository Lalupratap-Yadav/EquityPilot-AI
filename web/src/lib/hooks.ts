import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type MarketStatus, type Quote, type User } from './api'

// ------------------------------------------------------------------ theme
export type Theme = 'light' | 'dark'

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light')
  const setTheme = useCallback((t: Theme) => {
    document.documentElement.classList.toggle('dark', t === 'dark')
    try { localStorage.setItem('ep-theme', t) } catch { /* private mode */ }
    setThemeState(t)
    window.dispatchEvent(new CustomEvent('ep-theme', { detail: t }))
  }, [])
  useEffect(() => {
    const h = (e: Event) => setThemeState((e as CustomEvent<Theme>).detail)
    window.addEventListener('ep-theme', h)
    return () => window.removeEventListener('ep-theme', h)
  }, [])
  return [theme, setTheme]
}

// ------------------------------------------------------------------ experience: simple (beginners) or advanced (analysts)
export type Experience = 'simple' | 'advanced'

/** App-wide Simple / Advanced switch. Stored per browser; every page reads the same value, so switching never
 *  loses the company or page you are on. */
export function useExperience(): [Experience, (e: Experience) => void] {
  const read = (): Experience => { try { return (localStorage.getItem('ep-experience') as Experience) || 'simple' } catch { return 'simple' } }
  const [exp, setExp] = useState<Experience>(read)
  const set = useCallback((e: Experience) => {
    try { localStorage.setItem('ep-experience', e) } catch { /* private mode */ }
    setExp(e)
    window.dispatchEvent(new CustomEvent('ep-experience', { detail: e }))
  }, [])
  useEffect(() => {
    const h = (e: Event) => setExp((e as CustomEvent<Experience>).detail)
    window.addEventListener('ep-experience', h)
    return () => window.removeEventListener('ep-experience', h)
  }, [])
  return [exp, set]
}

// ------------------------------------------------------------------ live-style quote stream (WebSocket)
type StreamState = { quotes: Record<string, Quote>; market?: MarketStatus; connected: boolean; updatedAt?: number }

/** Subscribes to /api/ws/quotes. Reconnects with exponential backoff; quotes keep their provider status label. */
export function useQuoteStream(symbols: string[]): StreamState {
  const [state, setState] = useState<StreamState>({ quotes: {}, connected: false })
  const key = [...new Set(symbols)].sort().join(',')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!key) return
    let stopped = false
    let attempt = 0
    let timer: number | undefined
    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/api/ws/quotes`)
      wsRef.current = ws
      ws.onopen = () => {
        attempt = 0
        ws.send(JSON.stringify({ subscribe: key.split(',') }))
        setState((s) => ({ ...s, connected: true }))
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          // the server sends a full snapshot first, then only the quotes that changed
          if (msg.type === 'quotes') setState((s) => ({ quotes: { ...s.quotes, ...msg.quotes }, market: msg.market, connected: true, updatedAt: Date.now() }))
        } catch { /* ignore malformed frame */ }
      }
      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }))
        if (!stopped) timer = window.setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt++))
      }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => {
      stopped = true
      window.clearTimeout(timer)
      wsRef.current?.close()
    }
  }, [key])
  return state
}

// ------------------------------------------------------------------ keyboard shortcuts
export function useHotkey(match: (e: KeyboardEvent) => boolean, handler: (e: KeyboardEvent) => void) {
  const h = useRef(handler)
  h.current = handler
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if (match(e)) h.current(e)
    }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}

export function useDebounced<T>(value: T, ms = 200): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms)
    return () => window.clearTimeout(t)
  }, [value, ms])
  return v
}

// ------------------------------------------------------------------ user
export interface MeResponse { user: User; prefs: Record<string, unknown>; unread: number }

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api.get<MeResponse>('/me'), staleTime: 60_000 })
}

export function useInvalidate() {
  const qc = useQueryClient()
  return (...keys: string[]) => keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
}
