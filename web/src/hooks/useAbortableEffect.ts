import { useEffect, DependencyList } from 'react'

/**
 * Custom hook that provides an AbortController for effect cleanup.
 * Automatically aborts the signal when the effect is cleaned up.
 *
 * @param effect - Effect function that receives an AbortSignal
 * @param deps - Dependency array for the effect
 *
 * @example
 * ```tsx
 * useAbortableEffect((signal) => {
 *   const fetchData = async () => {
 *     try {
 *       const response = await fetch('/api/data', { signal })
 *       const data = await response.json()
 *       setState(data)
 *     } catch (error) {
 *       if (error.name === 'AbortError') {
 *         // Request was cancelled - this is expected behavior
 *         return
 *       }
 *       // Handle other errors
 *       console.error(error)
 *     }
 *   }
 *
 *   void fetchData()
 * }, [])
 * ```
 */
export const useAbortableEffect = (
  effect: (signal: AbortSignal) => void | (() => void),
  deps: DependencyList
): void => {
  useEffect(() => {
    const abortController = new AbortController()
    const cleanup = effect(abortController.signal)

    return () => {
      abortController.abort()
      if (cleanup) {
        cleanup()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
