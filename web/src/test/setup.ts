import '@testing-library/jest-dom'
import { afterEach, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Clear all mocks before each test to prevent state leakage
beforeEach(() => {
  vi.clearAllMocks()
})

// Cleanup after each test to ensure test isolation
afterEach(() => {
  cleanup()

  // Clear storage to prevent state leakage between tests
  localStorage.clear()
  sessionStorage.clear()

  // Clear any pending timers
  vi.clearAllTimers()

  // Reset document state
  document.body.innerHTML = ''

  // Clear any custom attributes that might have been added
  document.documentElement.removeAttribute('class')
  document.documentElement.removeAttribute('style')
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
