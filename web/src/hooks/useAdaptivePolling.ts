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

  const savedCallback = useRef(callback);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isVisibleRef = useRef(true);
  const currentIntervalRef = useRef<number>(baseInterval);
  const enabledRef = useRef(enabled);

  // Update refs on each render
  useEffect(() => {
    savedCallback.current = callback;
    enabledRef.current = enabled;
  }, [callback, enabled]);

  // Polling function that schedules the next poll
  const scheduleNextPoll = useCallback((interval: number): void => {
    // Clear any existing timeout
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    // Only schedule if enabled and visible
    if (!enabledRef.current || (pauseWhenHidden && !isVisibleRef.current)) {
      return;
    }

    timeoutRef.current = setTimeout(() => {
      // Execute the callback and schedule next poll
      void (async () => {
        try {
          const result = await savedCallback.current();
          setData(result);

          // Determine activity level and get next interval
          const activityLevel = getActivityLevel(result);
          const nextInterval =
            activityLevel === 'active' ? activeInterval :
            activityLevel === 'medium' ? mediumInterval :
            baseInterval;

          currentIntervalRef.current = nextInterval;

          // Schedule next poll with the new interval
          if (enabledRef.current && (!pauseWhenHidden || isVisibleRef.current)) {
            scheduleNextPoll(nextInterval);
          }
        } catch (error) {
          // On error, keep existing data and slow down polling
          logger.error('Adaptive polling error:', error as Error);
          currentIntervalRef.current = baseInterval;

          // Schedule next poll with base interval
          if (enabledRef.current && (!pauseWhenHidden || isVisibleRef.current)) {
            scheduleNextPoll(baseInterval);
          }
        }
      })();
    }, interval);
  }, [getActivityLevel, activeInterval, mediumInterval, baseInterval, pauseWhenHidden]);

  // Handle visibility changes
  useEffect(() => {
    if (!pauseWhenHidden) return;

    const handleVisibilityChange = (): void => {
      const isVisible = document.visibilityState === 'visible';
      isVisibleRef.current = isVisible;

      // If page becomes visible, fetch immediately and restart polling
      if (isVisible && enabled) {
        void (async () => {
          try {
            const result = await savedCallback.current();
            setData(result);

            // Determine activity level and get next interval
            const activityLevel = getActivityLevel(result);
            const nextInterval =
              activityLevel === 'active' ? activeInterval :
              activityLevel === 'medium' ? mediumInterval :
              baseInterval;

            currentIntervalRef.current = nextInterval;
            scheduleNextPoll(nextInterval);
          } catch (error) {
            logger.error('Adaptive polling error:', error as Error);
            currentIntervalRef.current = baseInterval;
            scheduleNextPoll(baseInterval);
          }
        })();
      }
      // If page becomes hidden, clear the timeout
      else if (!isVisible && timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [pauseWhenHidden, enabled, getActivityLevel, activeInterval, mediumInterval, baseInterval, scheduleNextPoll]);

  // Initial fetch and setup effect
  useEffect(() => {
    if (!enabled) {
      // Clear any pending timeout if disabled
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      return;
    }

    // Initial fetch
    void (async () => {
      try {
        const result = await savedCallback.current();
        setData(result);

        // Determine activity level and start polling
        const activityLevel = getActivityLevel(result);
        const nextInterval =
          activityLevel === 'active' ? activeInterval :
          activityLevel === 'medium' ? mediumInterval :
          baseInterval;

        currentIntervalRef.current = nextInterval;
        scheduleNextPoll(nextInterval);
      } catch (error) {
        logger.error('Adaptive polling error:', error as Error);
        currentIntervalRef.current = baseInterval;
        scheduleNextPoll(baseInterval);
      }
    })();

    // Cleanup function - critical for preventing memory leaks
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return data;
}
