import { useEffect, useRef, useCallback, useState } from 'react';

interface UsePollingOptions {
  /**
   * Polling interval in milliseconds
   */
  interval: number;

  /**
   * Whether polling should be active
   * @default true
   */
  enabled?: boolean;

  /**
   * Whether to pause polling when the page/tab is not visible
   * Uses the Page Visibility API to detect visibility changes
   * @default true
   */
  pauseWhenHidden?: boolean;

  /**
   * Whether to execute the callback immediately on mount
   * @default false
   */
  runImmediately?: boolean;
}

/**
 * Custom hook for polling with proper cleanup and memory leak prevention
 *
 * Features:
 * - Automatic cleanup on unmount
 * - Pauses when tab is hidden (Page Visibility API)
 * - Stable interval reference (no memory leaks from dependency changes)
 * - Can be enabled/disabled dynamically
 *
 * @param callback - Function to call on each poll. Should be wrapped in useCallback.
 * @param options - Polling configuration options
 *
 * @example
 * ```tsx
 * const fetchData = useCallback(async () => {
 *   const data = await fetch('/api/data');
 *   setData(data);
 * }, []);
 *
 * usePolling(fetchData, { interval: 5000, pauseWhenHidden: true });
 * ```
 */
export function usePolling(
  callback: () => void | Promise<void>,
  options: UsePollingOptions
): void {
  const {
    interval,
    enabled = true,
    pauseWhenHidden = true,
    runImmediately = false,
  } = options;

  // Store callback in ref to avoid recreating interval on every callback change
  const savedCallback = useRef(callback);
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isVisibleRef = useRef(true);

  // Update saved callback on each render
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Start polling function
  const startPolling = useCallback((): void => {
    // Clear any existing interval
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
    }

    // Only start if enabled and (not checking visibility OR page is visible)
    if (!enabled || (pauseWhenHidden && !isVisibleRef.current)) {
      return;
    }

    // Set up the interval
    intervalRef.current = setInterval(() => {
      // Double-check visibility before executing
      if (!pauseWhenHidden || isVisibleRef.current) {
        void savedCallback.current();
      }
    }, interval);
  }, [enabled, interval, pauseWhenHidden]);

  // Handle visibility changes
  useEffect(() => {
    if (!pauseWhenHidden) return;

    const handleVisibilityChange = (): void => {
      const isVisible = document.visibilityState === 'visible';
      isVisibleRef.current = isVisible;

      // If page becomes visible, restart polling immediately
      if (isVisible && enabled && intervalRef.current === null) {
        startPolling();
      }
      // If page becomes hidden, clear the interval
      else if (!isVisible && intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [pauseWhenHidden, enabled, interval, startPolling]);

  // Main polling effect
  useEffect(() => {
    // Run immediately if requested
    if (runImmediately && enabled) {
      void savedCallback.current();
    }

    // Start polling
    startPolling();

    // Cleanup function - critical for preventing memory leaks
    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, interval, runImmediately, startPolling]);
}

/**
 * Hook for conditionally pausing all effects when page is hidden
 * Useful for pausing animations, expensive computations, etc.
 *
 * @returns boolean indicating if page is currently visible
 */
export function usePageVisibility(): boolean {
  const [isVisible, setIsVisible] = useState(
    typeof document !== 'undefined'
      ? document.visibilityState === 'visible'
      : true
  );

  useEffect(() => {
    const handleVisibilityChange = (): void => {
      setIsVisible(document.visibilityState === 'visible');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return isVisible;
}
