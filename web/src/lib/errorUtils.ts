import { ApiError } from './api'

/**
 * Format an API error message with trace ID for user display
 *
 * @param error - The error to format (ApiError or generic Error)
 * @param fallbackMessage - Message to use if error has no message
 * @returns Formatted error message with trace ID if available
 */
export function formatErrorMessage(error: unknown, fallbackMessage = 'An error occurred'): string {
  if (error instanceof ApiError) {
    let message = error.message || fallbackMessage

    // Add trace ID if available (for support/debugging)
    if (error.traceId) {
      message += ` (Trace ID: ${error.traceId})`
    }

    // Add retry-after hint if present
    if (error.retryAfter) {
      message += ` Please retry after ${error.retryAfter} seconds.`
    }

    return message
  }

  if (error instanceof Error) {
    return error.message || fallbackMessage
  }

  return fallbackMessage
}

/**
 * Get trace ID from an error if it's an ApiError
 *
 * @param error - The error to extract trace ID from
 * @returns The trace ID or undefined
 */
export function getTraceId(error: unknown): string | undefined {
  return error instanceof ApiError ? error.traceId : undefined
}

/**
 * Get retry-after seconds from an error if it's an ApiError
 *
 * @param error - The error to extract retry-after from
 * @returns The retry-after seconds or undefined
 */
export function getRetryAfter(error: unknown): number | undefined {
  return error instanceof ApiError ? error.retryAfter : undefined
}

/**
 * Check if error is an auth error (401 or 403)
 *
 * @param error - The error to check
 * @returns True if error is 401 or 403
 */
export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

/**
 * Check if error is a rate limit error (429)
 *
 * @param error - The error to check
 * @returns True if error is 429
 */
export function isRateLimitError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 429
}
