import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock ResizeObserver (used by Radix UI Dialog)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined, // deprecated
    removeListener: () => undefined, // deprecated
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => true,
  }),
})

// Mock html2canvas to avoid CSS parsing errors in tests
vi.mock('html2canvas', () => ({
  default: vi.fn(() => {
    // Create a minimal mock canvas with toDataURL support
    const canvas = document.createElement('canvas')
    canvas.width = 100
    canvas.height = 100
    // Mock toDataURL to return a minimal valid data URL
    canvas.toDataURL = vi.fn(() => 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    return Promise.resolve(canvas)
  }),
}))

const resolveRequestUrl = (input: RequestInfo | URL): string => {
  if (typeof input === 'string') {
    return input
  }

  if (input instanceof URL) {
    return input.toString()
  }

  if (typeof Request !== 'undefined' && input instanceof Request) {
    return input.url
  }

  if (typeof input === 'object' && input && 'url' in input && typeof (input as { url: unknown }).url === 'string') {
    return (input as { url: string }).url
  }

  return ''
}

const toNormalizedPath = (value: string): string => {
  if (!value) {
    return value
  }

  if (value.startsWith('http://') || value.startsWith('https://')) {
    try {
      const parsed = new URL(value)
      return `${parsed.pathname}${parsed.search}`
    } catch {
      return value
    }
  }

  return value
}

const jsonResponse = (data: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(data), {
    status: init.status ?? 200,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })

const DEFAULT_API_RESPONSES: Record<string, () => Response> = {
  '/api/config': () =>
    jsonResponse({
      generation: {
        steps: 30,
        guidance_scale: 7.5,
      },
    }),
  '/api/images': () =>
    jsonResponse({
      images: [],
      total: 0,
      page: 1,
      per_page: 60,
      pages: 0,
    }),
  '/api/batches': () => jsonResponse({ batches: [] }),
  '/api/loras': () => jsonResponse({ loras: [] }),
  '/api/sets': () => jsonResponse({ sets: [] }),
  '/api/themes/random': () => jsonResponse({ theme: '' }),
  '/api/auth/me': () => jsonResponse({ authenticated: false }),
}

const fallbackOrigin =
  (typeof window !== 'undefined' && window.location ? window.location.origin : undefined) ??
  (import.meta.env?.VITE_TEST_BASE_URL as string | undefined) ??
  'http://localhost'

const realFetch = globalThis.fetch?.bind(globalThis)

globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const requestUrl = resolveRequestUrl(input)
  const normalized = toNormalizedPath(requestUrl)

  const handler = DEFAULT_API_RESPONSES[normalized]
  if (handler) {
    return handler()
  }

  if (realFetch) {
    const absolute =
      normalized.startsWith('http://') || normalized.startsWith('https://')
        ? requestUrl
        : new URL(normalized || requestUrl, fallbackOrigin).toString()

    return realFetch(absolute, init)
  }

  return jsonResponse({})
}) as typeof fetch

if (typeof window !== 'undefined') {
  window.fetch = globalThis.fetch
}
