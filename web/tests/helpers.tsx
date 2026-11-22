import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { vi } from 'vitest'
import { ToastProvider } from '../src/components/ui'

export type Handler = unknown | ((url: URL, init?: RequestInit) => unknown)

/** Replace fetch with a fake API. Keys are path prefixes after /api (longest match wins); unknown paths return 404.
 * Returns the mock so tests can inspect which URLs were requested. */
export function mockApi(routes: Record<string, Handler>) {
  const keys = Object.keys(routes).sort((a, b) => b.length - a.length)
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const path = url.pathname.replace(/^\/api/, '') + url.search
    const key = keys.find((k) => path.startsWith(k))
    if (key === undefined) return new Response(JSON.stringify({ detail: 'Not found' }), { status: 404, headers: { 'content-type': 'application/json' } })
    const h = routes[key]
    const body = typeof h === 'function' ? (h as (u: URL, i?: RequestInit) => unknown)(url, init) : h
    if (body instanceof Response) return body
    return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export const requested = (fn: ReturnType<typeof mockApi>) => fn.mock.calls.map((c) => String(c[0]))

function Where() {
  const loc = useLocation()
  return <div data-testid="location">{loc.pathname + loc.search}</div>
}

export function renderPage(ui: ReactElement, { route = '/', path = '*' }: { route?: string; path?: string } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <ToastProvider>
          <Routes><Route path={path} element={<>{ui}<Where /></>} /></Routes>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
