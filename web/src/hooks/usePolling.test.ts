import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePolling } from './usePolling'
import { logger } from '../lib/logger'

const flushMicrotasks = async () => {
  await act(async () => {
    await Promise.resolve()
  })
}

const advanceTimers = async (ms: number) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('calls the callback on the configured static interval', async () => {
    const callback = vi.fn()

    renderHook(() => usePolling(callback, { interval: 1000 }))

    expect(callback).not.toHaveBeenCalled()

    await advanceTimers(1000)
    expect(callback).toHaveBeenCalledTimes(1)

    await advanceTimers(1000)
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('runs immediately when runImmediately is enabled', async () => {
    const callback = vi.fn()

    renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        runImmediately: true,
      }),
    )

    await flushMicrotasks()
    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('respects the enabled flag', async () => {
    const callback = vi.fn()
    let enabled = false

    const { rerender } = renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        enabled,
      }),
    )

    await advanceTimers(1000)
    expect(callback).not.toHaveBeenCalled()

    enabled = true
    rerender()

    await advanceTimers(1000)
    expect(callback).toHaveBeenCalledTimes(1)

    enabled = false
    rerender()

    await advanceTimers(5000)
    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('cleans up timers on unmount', () => {
    const callback = vi.fn()
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')

    const { unmount } = renderHook(() => usePolling(callback, { interval: 1000 }))

    unmount()

    expect(clearTimeoutSpy).toHaveBeenCalled()
  })

  it('supports swapping callbacks without leaking timers', async () => {
    const callbackA = vi.fn()
    const callbackB = vi.fn()

    const { rerender } = renderHook(
      ({ cb }) => usePolling(cb, { interval: 1000 }),
      { initialProps: { cb: callbackA } },
    )

    await advanceTimers(1000)
    expect(callbackA).toHaveBeenCalledTimes(1)
    expect(callbackB).not.toHaveBeenCalled()

    rerender({ cb: callbackB })

    await advanceTimers(1000)
    expect(callbackA).toHaveBeenCalledTimes(1)
    expect(callbackB).toHaveBeenCalledTimes(1)
  })

  it('restarts timers when the interval changes', async () => {
    const callback = vi.fn()
    let interval = 1000

    const { rerender } = renderHook(() => usePolling(callback, { interval }))

    await advanceTimers(1000)
    expect(callback).toHaveBeenCalledTimes(1)

    interval = 500
    rerender()

    await advanceTimers(500)
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('awaits async callbacks before scheduling the next poll', async () => {
    const asyncCallback = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100))
    })

    renderHook(() => usePolling(asyncCallback, { interval: 1000 }))

    await advanceTimers(1000)
    expect(asyncCallback).toHaveBeenCalledTimes(1)

    await advanceTimers(100)

    await advanceTimers(1000)
    expect(asyncCallback).toHaveBeenCalledTimes(2)
  })

  describe('adaptive mode', () => {
    it('returns latest data and adapts intervals to activity level', async () => {
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout')
      const fetchMock = vi
        .fn<[], Promise<{ level: 'active' | 'medium' | 'idle' }>>()
        .mockResolvedValueOnce({ level: 'active' })
        .mockResolvedValueOnce({ level: 'medium' })
        .mockResolvedValueOnce({ level: 'idle' })

      const { result } = renderHook(() =>
        usePolling(fetchMock, {
          activeInterval: 1000,
          mediumInterval: 3000,
          idleInterval: 5000,
          getActivityLevel: (data) => data?.level ?? 'idle',
          pauseWhenHidden: false,
        }),
      )

      await flushMicrotasks()
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(result.current).toEqual({ level: 'active' })
      expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 1000)

      await advanceTimers(1000)
      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(result.current).toEqual({ level: 'medium' })
      expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 3000)

      await advanceTimers(3000)
      expect(fetchMock).toHaveBeenCalledTimes(3)
      expect(result.current).toEqual({ level: 'idle' })
      expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 5000)
    })

    it('falls back to the idle interval after an error', async () => {
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout')
      vi.spyOn(logger, 'error').mockImplementation(() => {})
      const error = new Error('boom')

      const fetchMock = vi
        .fn<[], Promise<{ level: 'active' | 'medium' | 'idle' }>>()
        .mockRejectedValueOnce(error)
        .mockResolvedValueOnce({ level: 'idle' })

      renderHook(() =>
        usePolling(fetchMock, {
          activeInterval: 1000,
          mediumInterval: 3000,
          idleInterval: 5000,
          getActivityLevel: (data) => data?.level ?? 'idle',
        }),
      )

      await flushMicrotasks()
      expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 5000)

      await advanceTimers(5000)
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })
  })

  describe('page visibility handling', () => {
    let visibilityState: DocumentVisibilityState
    let listeners: Array<() => void>

    beforeEach(() => {
      visibilityState = 'visible'
      listeners = []

      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => visibilityState,
      })

      const originalAddEventListener = document.addEventListener.bind(document)
      vi.spyOn(document, 'addEventListener').mockImplementation((event, handler) => {
        if (event === 'visibilitychange' && typeof handler === 'function') {
          listeners.push(handler as () => void)
        }
        return originalAddEventListener(event, handler as EventListener)
      })
    })

    it('pauses polling while hidden', async () => {
      const callback = vi.fn()

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: true,
        }),
      )

      await advanceTimers(1000)
      expect(callback).toHaveBeenCalledTimes(1)

      visibilityState = 'hidden'
      listeners.forEach((listener) => listener())

      await advanceTimers(5000)
      expect(callback).toHaveBeenCalledTimes(1)
    })

    it('resumes polling when visible again', async () => {
      const callback = vi.fn()

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: true,
        }),
      )

      await advanceTimers(1000)
      expect(callback).toHaveBeenCalledTimes(1)

      visibilityState = 'hidden'
      listeners.forEach((listener) => listener())

      visibilityState = 'visible'
      listeners.forEach((listener) => listener())

      await advanceTimers(1000)
      expect(callback).toHaveBeenCalledTimes(2)
    })

    it('keeps polling when pauseWhenHidden is false', async () => {
      const callback = vi.fn()

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: false,
        }),
      )

      await advanceTimers(1000)
      expect(callback).toHaveBeenCalledTimes(1)

      visibilityState = 'hidden'
      listeners.forEach((listener) => listener())

      await advanceTimers(1000)
      expect(callback).toHaveBeenCalledTimes(2)
    })
  })
})
