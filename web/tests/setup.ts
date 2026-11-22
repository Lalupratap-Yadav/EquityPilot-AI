import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => cleanup())

// jsdom lacks a few browser APIs the app touches
if (!window.matchMedia) {
  window.matchMedia = (q: string) => ({ matches: false, media: q, onchange: null, addListener: () => {}, removeListener: () => {},
    addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false }) as MediaQueryList
}
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || function () {}
class RO { observe() {} unobserve() {} disconnect() {} }
;(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver ??= RO
class FakeWS {
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((e: unknown) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(public url: string) {}
  send() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
}
vi.stubGlobal('WebSocket', FakeWS)
