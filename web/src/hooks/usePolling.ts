import { useEffect, useRef, useCallback, useState } from "react"
import { logger } from "../lib/logger"

type ActivityLevel = "active" | "medium" | "idle"

interface BasePollingOptions {
  enabled?: boolean
  pauseWhenHidden?: boolean
  runImmediately?: boolean
}

interface StaticPollingOptions extends BasePollingOptions {
  interval: number
}

interface AdaptivePollingOptions<T> extends BasePollingOptions {
  idleInterval?: number
  baseInterval?: number
  mediumInterval?: number
  activeInterval?: number
  getActivityLevel: (data: T | null) => ActivityLevel
}

type UsePollingOptions<T> = StaticPollingOptions | AdaptivePollingOptions<T>

function isAdaptiveOptions<T>(options: UsePollingOptions<T>): options is AdaptivePollingOptions<T> {
  return typeof (options as AdaptivePollingOptions<T>).getActivityLevel === "function"
}

export function usePolling(callback: () => void | Promise<void>, options: StaticPollingOptions): void
export function usePolling<T>(callback: () => Promise<T>, options: AdaptivePollingOptions<T>): T | null
export function usePolling<T>(
  callback: (() => void | Promise<void>) | (() => Promise<T>),
  options: UsePollingOptions<T>,
): T | null | void {
  const isAdaptive = isAdaptiveOptions(options)

  const {
    enabled = true,
    pauseWhenHidden = true,
    runImmediately: runImmediatelyOption,
  } = options

  const idleInterval = isAdaptive ? options.idleInterval ?? options.baseInterval ?? 30_000 : undefined
  const mediumInterval = isAdaptive ? options.mediumInterval ?? 10_000 : undefined
  const activeInterval = isAdaptive ? options.activeInterval ?? 2_000 : undefined
  const staticInterval = !isAdaptive ? options.interval : undefined

  if (!isAdaptive && typeof staticInterval !== "number") {
    if (process.env.NODE_ENV !== "production") {
      logger.warn(
        "usePolling: interval is required when adaptive options are not provided. Defaulting to 30000ms.",
      )
    }
  }

  const resolvedStaticInterval = staticInterval ?? 30_000
  const effectiveRunImmediately = runImmediatelyOption ?? isAdaptive

  const savedCallback = useRef(callback)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isVisibleRef = useRef(true)
  const enabledRef = useRef(enabled)
  const dataRef = useRef<T | null>(null)

  const [data, setData] = useState<T | null>(null)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  const clearTimer = useCallback(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  const scheduleNext = useCallback(
    (delay: number) => {
      clearTimer()

      if (!enabledRef.current || (pauseWhenHidden && !isVisibleRef.current)) {
        return
      }

      timeoutRef.current = setTimeout(() => {
        void runPollRef.current?.()
      }, delay)
    },
    [clearTimer, pauseWhenHidden],
  )

  const runPollRef = useRef<() => Promise<void>>()

  const runPoll = useCallback(async () => {
    if (!enabledRef.current) {
      return
    }

    try {
      const result = await savedCallback.current()
      let nextInterval: number

      if (isAdaptive) {
        const typedResult = ((result ?? null) as T | null)
        dataRef.current = typedResult
        setData(typedResult)

        const activityLevel = options.getActivityLevel(typedResult)
        nextInterval =
          activityLevel === "active"
            ? activeInterval ?? 2_000
            : activityLevel === "medium"
              ? mediumInterval ?? 10_000
              : idleInterval ?? 30_000
      } else {
        nextInterval = resolvedStaticInterval
      }

      scheduleNext(nextInterval)
    } catch (error) {
      if (isAdaptive) {
        logger.error("Adaptive polling error:", error as Error)
      }

      const fallbackInterval = isAdaptive ? idleInterval ?? 30_000 : resolvedStaticInterval
      scheduleNext(fallbackInterval)
    }
  }, [isAdaptive, options, activeInterval, mediumInterval, idleInterval, resolvedStaticInterval, scheduleNext])

  useEffect(() => {
    runPollRef.current = runPoll
  }, [runPoll])

  useEffect(() => {
    if (!pauseWhenHidden) {
      return undefined
    }

    const handleVisibilityChange = (): void => {
      const isVisible = document.visibilityState === "visible"
      isVisibleRef.current = isVisible

      if (isVisible && enabledRef.current) {
        if (effectiveRunImmediately || isAdaptive) {
          void runPollRef.current?.()
        } else {
          scheduleNext(resolvedStaticInterval)
        }
      } else if (!isVisible) {
        clearTimer()
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [pauseWhenHidden, effectiveRunImmediately, isAdaptive, resolvedStaticInterval, scheduleNext, clearTimer])

  useEffect(() => {
    if (!enabled) {
      clearTimer()
      return undefined
    }

    if (effectiveRunImmediately) {
      void runPollRef.current?.()
    } else {
      const initialDelay = isAdaptive ? idleInterval ?? 30_000 : resolvedStaticInterval
      scheduleNext(initialDelay)
    }

    return () => {
      clearTimer()
    }
  }, [enabled, effectiveRunImmediately, isAdaptive, idleInterval, resolvedStaticInterval, scheduleNext, clearTimer])

  return isAdaptive ? data : undefined
}

/**
 * Hook for conditionally pausing all effects when page is hidden
 * Useful for pausing animations, expensive computations, etc.
 *
 * @returns boolean indicating if page is currently visible
 */
export function usePageVisibility(): boolean {
  const [isVisible, setIsVisible] = useState(
    typeof document !== "undefined"
      ? document.visibilityState === "visible"
      : true,
  )

  useEffect(() => {
    const handleVisibilityChange = (): void => {
      setIsVisible(document.visibilityState === "visible")
    }

    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [])

  return isVisible
}
