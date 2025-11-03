import { ApiError } from './api'

/**
 * Format an API error message for user display (without trace ID)
 *
 * @param error - The error to format (ApiError or generic Error)
 * @param fallbackMessage - Message to use if error has no message
 * @returns Formatted error message
 */
export function formatErrorMessage(error: unknown, fallbackMessage = 'An error occurred'): string {
  if (error instanceof ApiError) {
    let message = error.message || fallbackMessage

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
 * Extract detailed error information for bug reporting
 *
 * @param error - The error to extract data from
 * @param context - Additional context (e.g., "Failed to load album")
 * @returns Object with error details for bug report
 */
export function extractErrorDetails(
  error: unknown,
  context?: string
): {
  message: string
  traceId?: string
  status?: number
  response?: unknown
  stack?: string
  context?: string
} {
  const details: ReturnType<typeof extractErrorDetails> = {
    message: formatErrorMessage(error, 'Unknown error'),
  }

  if (context) {
    details.context = context
  }

  if (error instanceof ApiError) {
    details.traceId = error.traceId
    details.status = error.status
    details.response = error.response
    details.stack = error.stack
  } else if (error instanceof Error) {
    details.stack = error.stack
  }

  return details
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

/**
 * Format error description for toast with trace ID on separate line
 *
 * @param error - The error to format
 * @param context - Additional context message
 * @returns Formatted description string
 */
export function formatErrorToastDescription(error: unknown, context?: string): string {
  const message = formatErrorMessage(error, context || 'An error occurred')
  const traceId = getTraceId(error)

  if (traceId) {
    return `${message}\n\nTrace ID: ${traceId}`
  }

  return message
}
