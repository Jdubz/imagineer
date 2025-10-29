import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePolling } from './usePolling';

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should call callback at specified interval', () => {
    const callback = vi.fn();
    const interval = 1000;

    renderHook(() => usePolling(callback, { interval }));

    // Should not be called immediately by default
    expect(callback).not.toHaveBeenCalled();

    // Advance time by interval
    vi.advanceTimersByTime(interval);
    expect(callback).toHaveBeenCalledTimes(1);

    // Advance again
    vi.advanceTimersByTime(interval);
    expect(callback).toHaveBeenCalledTimes(2);
  });

  it('should call callback immediately when runImmediately is true', () => {
    const callback = vi.fn();

    renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        runImmediately: true,
      })
    );

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should not poll when enabled is false', () => {
    const callback = vi.fn();

    renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        enabled: false,
      })
    );

    vi.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
  });

  it('should start polling when enabled changes to true', () => {
    const callback = vi.fn();
    let enabled = false;

    const { rerender } = renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        enabled,
      })
    );

    // Should not poll initially
    vi.advanceTimersByTime(1000);
    expect(callback).not.toHaveBeenCalled();

    // Enable polling
    enabled = true;
    rerender();

    // Should now poll
    vi.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should stop polling when enabled changes to false', () => {
    const callback = vi.fn();
    let enabled = true;

    const { rerender } = renderHook(() =>
      usePolling(callback, {
        interval: 1000,
        enabled,
      })
    );

    // Should poll initially
    vi.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(1);

    // Disable polling
    enabled = false;
    rerender();

    // Should not poll anymore
    vi.advanceTimersByTime(5000);
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should cleanup interval on unmount', () => {
    const callback = vi.fn();
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');

    const { unmount } = renderHook(() =>
      usePolling(callback, { interval: 1000 })
    );

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  it('should handle callback updates without creating memory leaks', () => {
    const callback1 = vi.fn(() => undefined)
    const callback2 = vi.fn(() => undefined)

    const { rerender } = renderHook(
      ({ cb }) => usePolling(cb, { interval: 1000 }),
      {
        initialProps: { cb: callback1 },
      }
    );

    // First callback should be called
    vi.advanceTimersByTime(1000);
    expect(callback1).toHaveBeenCalledTimes(1);
    expect(callback2).not.toHaveBeenCalled();

    // Change callback
    rerender({ cb: callback2 });

    // New callback should be called, old one should not be called again
    vi.advanceTimersByTime(1000);
    expect(callback1).toHaveBeenCalledTimes(1); // Still 1
    expect(callback2).toHaveBeenCalledTimes(1); // Now called
  });

  it('should restart interval when interval duration changes', () => {
    const callback = vi.fn();
    let interval = 1000;

    const { rerender } = renderHook(() => usePolling(callback, { interval }));

    vi.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(1);

    // Change interval
    interval = 500;
    rerender();

    // Should now use new interval
    vi.advanceTimersByTime(500);
    expect(callback).toHaveBeenCalledTimes(2);

    vi.advanceTimersByTime(500);
    expect(callback).toHaveBeenCalledTimes(3);
  });

  it('should handle async callbacks without errors', async () => {
    const asyncCallback = vi.fn(async (): Promise<void> => {
      await new Promise<void>((resolve) => setTimeout(resolve, 100));
    });

    renderHook(() => usePolling(asyncCallback, { interval: 1000 }));

    vi.advanceTimersByTime(1000);
    expect(asyncCallback).toHaveBeenCalledTimes(1);

    // Advance past async operation
    await vi.advanceTimersByTimeAsync(100);

    vi.advanceTimersByTime(1000);
    expect(asyncCallback).toHaveBeenCalledTimes(2);
  });

  describe('Page Visibility API', () => {
    let visibilityState: DocumentVisibilityState;
    let visibilityListeners: Array<() => void> = [];

    beforeEach(() => {
      visibilityState = 'visible';
      visibilityListeners = [];

      // Mock document.visibilityState
      Object.defineProperty(document, 'visibilityState', {
        get: () => visibilityState,
        configurable: true,
      });

      // Mock addEventListener for visibilitychange
      const originalAddEventListener = document.addEventListener.bind(document);
      vi.spyOn(document, 'addEventListener').mockImplementation((event, handler) => {
        if (event === 'visibilitychange' && typeof handler === 'function') {
          visibilityListeners.push(handler as () => void);
        }
        return originalAddEventListener(event, handler as EventListener);
      });
    });

    it('should pause polling when page is hidden', () => {
      const callback = vi.fn();

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: true,
        })
      );

      // Poll once while visible
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(1);

      // Hide page
      visibilityState = 'hidden';
      visibilityListeners.forEach((listener) => listener());

      // Should not poll while hidden
      vi.advanceTimersByTime(5000);
      expect(callback).toHaveBeenCalledTimes(1); // Still 1
    });

    it('should resume polling when page becomes visible again', () => {
      const callback = vi.fn();

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: true,
        })
      );

      // Poll once
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(1);

      // Hide page
      visibilityState = 'hidden';
      visibilityListeners.forEach((listener) => listener());

      // Show page again
      visibilityState = 'visible';
      visibilityListeners.forEach((listener) => listener());

      // Should resume polling
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(2);
    });

    it('should not pause when pauseWhenHidden is false', () => {
      const callback = vi.fn();

      renderHook(() =>
        usePolling(callback, {
          interval: 1000,
          pauseWhenHidden: false,
        })
      );

      // Poll once
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(1);

      // Hide page
      visibilityState = 'hidden';
      visibilityListeners.forEach((listener) => listener());

      // Should continue polling even when hidden
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(2);
    });
  });
});
