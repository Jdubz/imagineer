import { useCallback } from 'react'
import { useToast } from './use-toast'
import { useBugReporter } from '../contexts/BugReportContext'
import { ToastAction } from '../components/ui/toast'
import { extractErrorDetails, formatErrorToastDescription } from '../lib/errorUtils'

export interface ErrorToastOptions {
  title?: string
  context?: string
  error: unknown
}

/**
 * Hook for showing error toasts with optional "Report Bug" button
 * that includes trace ID and error context
 */
export function useErrorToast() {
  const { toast } = useToast()
  const { openBugReport } = useBugReporter()

  const showErrorToast = useCallback(
    ({ title = 'Error', context, error }: ErrorToastOptions) => {
      const errorDetails = extractErrorDetails(error, context)
      const description = formatErrorToastDescription(error, context)

      // Build bug report description with all error details
      const bugReportDescription = [
        context || 'An error occurred',
        '',
        `Error: ${errorDetails.message}`,
        errorDetails.traceId ? `Trace ID: ${errorDetails.traceId}` : null,
        errorDetails.status ? `HTTP Status: ${errorDetails.status}` : null,
        '',
        'Stack Trace:',
        errorDetails.stack || 'No stack trace available',
        '',
        'Response Data:',
        errorDetails.response
          ? JSON.stringify(errorDetails.response, null, 2)
          : 'No response data',
      ]
        .filter(Boolean)
        .join('\n')

      toast({
        title,
        description,
        variant: 'destructive',
        action: (
          <ToastAction
            altText="Report this error"
            onClick={() => {
              openBugReport({ description: bugReportDescription })
            }}
          >
            Report Bug
          </ToastAction>
        ),
      })
    },
    [toast, openBugReport]
  )

  return { showErrorToast }
}
