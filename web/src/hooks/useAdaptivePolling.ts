import { useEffect, useRef, useCallback, useState } from 'react';
import { logger } from '../lib/logger';

interface UseAdaptivePollingOptions<T> {
  /**
   * Base polling interval in milliseconds (used when idle)
   * @default 30000 (30 seconds)
   */
  baseInterval?: number;

  /**
   * Fast polling interval in milliseconds (used when activity detected)
   * @default 2000 (2 seconds)
   */
  activeInterval?: number;

  /**
   * Medium polling interval in milliseconds (used when some activity)
   * @default 10000 (10 seconds)
   */
  mediumInterval?: number;

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
   * Function to determine activity level from the polled data
   * Returns:
   * - 'active': Use activeInterval (fast polling)
   * - 'medium': Use mediumInterval (medium polling)
   * - 'idle': Use baseInterval (slow polling)
   *
   * @param data - The data returned from the last poll
   * @returns Activity level
   */
  getActivityLevel: (data: T | null) => 'active' | 'medium' | 'idle';
}

/**
 * Custom hook for adaptive polling that adjusts interval based on activity
 *
 * Features:
 * - Automatic cleanup on unmount
 * - Pauses when tab is hidden (Page Visibility API)
 * - Adaptive intervals based on activity level
 * - Reduces requests by up to 90% during idle periods
 * - Can be enabled/disabled dynamically
 *
 * @param callback - Async function to call on each poll. Should return data.
 * @param options - Adaptive polling configuration options
 *
 * @example
 * ```tsx
 * const fetchQueue = useCallback(async () => {
 *   const data = await api.jobs.getAll();
 *   return data;
 * }, []);
 *
 * const queueData = useAdaptivePolling(fetchQueue, {
 *   activeInterval: 2000,    // 2s when jobs running
 *   mediumInterval: 10000,   // 10s when jobs queued
 *   baseInterval: 30000,     // 30s when idle
 *   getActivityLevel: (data) => {
 *     if (data?.current) return 'active';
 *     if (data?.queue?.length) return 'medium';
 *     return 'idle';
 *   }
 * });
 * ```
 */
export function useAdaptivePolling<T>(
  callback: () => Promise<T>,
  options: UseAdaptivePollingOptions<T>
): T | null {
  const {
    baseInterval = 30000,
    activeInterval = 2000,
    mediumInterval = 10000,
    enabled = true,
    pauseWhenHidden = true,
    getActivityLevel,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [currentInterval, setCurrentInterval] = useState(baseInterval);

  const savedCallback = useRef(callback);
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isVisibleRef = useRef(true);
  const lastActivityLevel = useRef<'active' | 'medium' | 'idle'>('idle');

  // Update saved callback on each render
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Execute callback and update data
  const executeCallback = useCallback(async (): Promise<void> => {
    try {
      const result = await savedCallback.current();
      setData(result);

      // Determine activity level and adjust interval
      const activityLevel = getActivityLevel(result);

      // Only update interval if activity level changed
      if (activityLevel !== lastActivityLevel.current) {
        lastActivityLevel.current = activityLevel;

        const newInterval =
          activityLevel === 'active' ? activeInterval :
          activityLevel === 'medium' ? mediumInterval :
          baseInterval;

        setCurrentInterval(newInterval);
      }
    } catch (error) {
      // On error, keep existing data and slow down polling
      logger.error('Adaptive polling error:', error as Error);
      setCurrentInterval(baseInterval);
    }
  }, [getActivityLevel, activeInterval, mediumInterval, baseInterval]);

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

    // Set up the interval with current interval
    intervalRef.current = setInterval(() => {
      // Double-check visibility before executing
      if (!pauseWhenHidden || isVisibleRef.current) {
        void executeCallback();
      }
    }, currentInterval);
  }, [enabled, currentInterval, pauseWhenHidden, executeCallback]);

  // Handle visibility changes
  useEffect(() => {
    if (!pauseWhenHidden) return;

    const handleVisibilityChange = (): void => {
      const isVisible = document.visibilityState === 'visible';
      isVisibleRef.current = isVisible;

      // If page becomes visible, fetch immediately and restart polling
      if (isVisible && enabled) {
        void executeCallback();
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
  }, [pauseWhenHidden, enabled, executeCallback, startPolling]);

  // Initial fetch effect - only run once on mount or when enabled changes
  useEffect(() => {
    if (enabled) {
      void executeCallback();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Main polling effect - restart when interval changes
  useEffect(() => {
    // Start polling
    startPolling();

    // Cleanup function - critical for preventing memory leaks
    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [currentInterval, startPolling]);

  return data;
}
