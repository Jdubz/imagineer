import { Component, ReactNode, ErrorInfo } from 'react'
import { logger } from '../lib/logger'
import { Button } from '@/components/ui/button'
import { RotateCw, RefreshCw, Home, Bug } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  /**
   * Optional fallback component to render instead of the default error UI
   */
  fallback?: ReactNode
  /**
   * Optional callback when an error is caught
   */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  /**
   * Optional name for this boundary (for logging context)
   */
  boundaryName?: string
  /**
   * Whether to show the "Report Bug" button (admin only)
   */
  showReportBugButton?: boolean
  /**
   * Callback when "Report Bug" button is clicked
   */
  onReportBug?: (error: Error, errorInfo: ErrorInfo | null, boundaryName?: string) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Error Boundary component to catch and handle React component errors
 *
 * Features:
 * - Catches errors in child component tree
 * - Prevents entire app crash
 * - Provides user-friendly error UI with recovery options
 * - Logs errors for debugging
 * - Shows stack traces in development mode
 *
 * @example
 * ```tsx
 * <ErrorBoundary boundaryName="AlbumsTab">
 *   <AlbumsTab />
 * </ErrorBoundary>
 * ```
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  /**
   * Update state so the next render shows the fallback UI
   */
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    }
  }

  /**
   * Log the error to our error reporting service
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const { boundaryName, onError } = this.props

    // Log error with context
    logger.error('React Error Boundary caught an error', error, {
      boundaryName: boundaryName || 'Unknown',
      componentStack: errorInfo.componentStack,
    })

    // Update state with error info for display
    this.setState({
      errorInfo,
    })

    // Call optional error callback
    if (onError) {
      onError(error, errorInfo)
    }
  }

  /**
   * Reset error boundary state
   */
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  /**
   * Reload the page to recover from error
   */
  handleReload = (): void => {
    window.location.reload()
  }

  /**
   * Navigate to home page
   */
  handleGoHome = (): void => {
    window.location.href = '/'
  }

  /**
   * Report bug with error details
   */
  handleReportBug = (): void => {
    const { onReportBug, boundaryName } = this.props
    const { error, errorInfo } = this.state

    if (onReportBug && error) {
      onReportBug(error, errorInfo, boundaryName)
    }
  }

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state
    const { children, fallback, boundaryName, showReportBugButton } = this.props

    if (hasError && error) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback
      }

      // Default error UI
      const isDevelopment = import.meta.env.MODE === 'development'

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-icon">⚠️</div>

            <h1 className="error-title">Oops! Something went wrong</h1>

            <p className="error-message">
              {boundaryName
                ? `An error occurred in ${boundaryName}. Don't worry, your other tabs are still working.`
                : 'An unexpected error occurred. The rest of the app should still work normally.'}
            </p>

            <div className="error-actions">
              <Button
                onClick={this.handleReset}
                type="button"
              >
                <RotateCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button
                variant="outline"
                onClick={this.handleReload}
                type="button"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Reload Page
              </Button>
              <Button
                variant="outline"
                onClick={this.handleGoHome}
                type="button"
              >
                <Home className="h-4 w-4 mr-2" />
                Go Home
              </Button>
              {showReportBugButton && (
                <Button
                  variant="secondary"
                  onClick={this.handleReportBug}
                  type="button"
                  title="Report this error to the development team"
                >
                  <Bug className="h-4 w-4 mr-2" />
                  Report Bug
                </Button>
              )}
            </div>

            {isDevelopment && (
              <details className="error-details">
                <summary>Error Details (Development Only)</summary>
                <div className="error-stack">
                  <h3>Error:</h3>
                  <pre>{error.toString()}</pre>

                  {error.stack && (
                    <>
                      <h3>Stack Trace:</h3>
                      <pre>{error.stack}</pre>
                    </>
                  )}

                  {errorInfo?.componentStack && (
                    <>
                      <h3>Component Stack:</h3>
                      <pre>{errorInfo.componentStack}</pre>
                    </>
                  )}
                </div>
              </details>
            )}

            <p className="error-footer">
              If this problem persists, please contact support with the error details above.
            </p>
          </div>
        </div>
      )
    }

    return children
  }
}

export default ErrorBoundary
