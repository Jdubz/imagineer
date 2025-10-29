import React, { ReactNode } from 'react'
import { ErrorInfo } from 'react'
import ErrorBoundary from './ErrorBoundary'
import { useAuth } from '../contexts/AuthContext'
import { useBugReporter } from '../contexts/BugReportContext'

interface ErrorBoundaryWithReportingProps {
  children: ReactNode
  boundaryName?: string
}

/**
 * Wrapper component that adds bug reporting to ErrorBoundary for admin users
 *
 * Features:
 * - Automatically shows "Report Bug" button for admin users
 * - Pre-fills bug report with error details when clicked
 * - Passes through all ErrorBoundary props
 *
 * @example
 * ```tsx
 * <ErrorBoundaryWithReporting boundaryName="Generate Tab">
 *   <GenerateTab />
 * </ErrorBoundaryWithReporting>
 * ```
 */
const ErrorBoundaryWithReporting: React.FC<ErrorBoundaryWithReportingProps> = ({
  children,
  boundaryName,
}) => {
  const { user } = useAuth()
  const { openBugReport } = useBugReporter()

  const handleReportBug = (
    error: Error,
    errorInfo: ErrorInfo | null,
    boundary?: string
  ): void => {
    // Pre-fill the bug report description with error details
    const description = `**Error caught in ${boundary || 'Unknown Component'}**

**Error Message:**
${error.message}

**Error Stack:**
\`\`\`
${error.stack || 'No stack trace available'}
\`\`\`

${errorInfo?.componentStack ? `**Component Stack:**\n\`\`\`\n${errorInfo.componentStack}\n\`\`\`` : ''}

---

**Steps to reproduce:**
1.
2.
3.

**Expected behavior:**


**Additional context:**

`

    openBugReport(description)
  }

  return (
    <ErrorBoundary
      boundaryName={boundaryName}
      showReportBugButton={user?.role === 'admin'}
      onReportBug={handleReportBug}
    >
      {children}
    </ErrorBoundary>
  )
}

export default ErrorBoundaryWithReporting
