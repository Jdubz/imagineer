import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, cleanup } from '@testing-library/react'
import { useAbortableEffect } from './useAbortableEffect'

describe('useAbortableEffect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('provides an AbortSignal to the effect', () => {
    const effect = vi.fn()

    renderHook(() => useAbortableEffect(effect, []))

    expect(effect).toHaveBeenCalledTimes(1)
    expect(effect).toHaveBeenCalledWith(expect.any(AbortSignal))
  })

  it('aborts the signal when unmounted', () => {
    let capturedSignal: AbortSignal | null = null
    const effect = vi.fn((signal: AbortSignal) => {
      capturedSignal = signal
    })

    const { unmount } = renderHook(() => useAbortableEffect(effect, []))

    expect(capturedSignal).not.toBeNull()
    expect(capturedSignal?.aborted).toBe(false)

    unmount()

    expect(capturedSignal?.aborted).toBe(true)
  })

  it('aborts the signal when dependencies change', () => {
    let firstSignal: AbortSignal | null = null
    let secondSignal: AbortSignal | null = null
    let callCount = 0

    const effect = vi.fn((signal: AbortSignal) => {
      if (callCount === 0) {
        firstSignal = signal
      } else {
        secondSignal = signal
      }
      callCount++
    })

    const { rerender } = renderHook(({ dep }) => useAbortableEffect(effect, [dep]), {
      initialProps: { dep: 1 },
    })

    expect(firstSignal).not.toBeNull()
    expect(firstSignal?.aborted).toBe(false)

    rerender({ dep: 2 })

    expect(firstSignal?.aborted).toBe(true)
    expect(secondSignal).not.toBeNull()
    expect(secondSignal?.aborted).toBe(false)
  })

  it('calls cleanup function from effect when unmounted', () => {
    const cleanup = vi.fn()
    const effect = vi.fn(() => cleanup)

    const { unmount } = renderHook(() => useAbortableEffect(effect, []))

    expect(cleanup).not.toHaveBeenCalled()

    unmount()

    expect(cleanup).toHaveBeenCalledTimes(1)
  })

  it('handles fetch cancellation gracefully', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
    })

    global.fetch = fetchMock

    let abortError: Error | null = null

    const effect = (signal: AbortSignal) => {
      const fetchData = async () => {
        try {
          await fetch('/api/test', { signal })
        } catch (error) {
          if (error instanceof Error && error.name === 'AbortError') {
            abortError = error
          }
        }
      }

      void fetchData()
    }

    const { unmount } = renderHook(() => useAbortableEffect(effect, []))

    unmount()

    // The fetch should have been called with an aborted signal
    expect(fetchMock).toHaveBeenCalledWith('/api/test', {
      signal: expect.any(AbortSignal),
    })

    // The signal should be aborted
    const callArgs = fetchMock.mock.calls[0]
    const signal = callArgs[1].signal as AbortSignal
    expect(signal.aborted).toBe(true)
  })

  it('does not call cleanup if effect does not return a function', () => {
    const effect = vi.fn(() => undefined)

    const { unmount } = renderHook(() => useAbortableEffect(effect, []))

    expect(() => unmount()).not.toThrow()
  })

  it('runs effect on every dependency change', () => {
    const effect = vi.fn()

    const { rerender } = renderHook(({ deps }) => useAbortableEffect(effect, deps), {
      initialProps: { deps: [1, 2] },
    })

    expect(effect).toHaveBeenCalledTimes(1)

    rerender({ deps: [1, 3] })
    expect(effect).toHaveBeenCalledTimes(2)

    rerender({ deps: [2, 3] })
    expect(effect).toHaveBeenCalledTimes(3)
  })
})
