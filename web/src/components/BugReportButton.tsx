import React from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import { useAuth } from '../contexts/AuthContext'

const BugReportButton: React.FC = () => {
  const { openBugReport } = useBugReporter()
  const { user } = useAuth()

  // Only show for admin users
  if (user?.role !== 'admin') {
    return null
  }

  return (
    <button
      type="button"
      className="bug-report-trigger"
      onClick={() => openBugReport()}
      aria-label="Report a bug (Ctrl+Shift+B)"
      title="Report a bug (Ctrl+Shift+B)"
    >
      🐞 Report Bug
    </button>
  )
}

export default BugReportButton
