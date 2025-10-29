import React from 'react'
import { useBugReporter } from '../contexts/BugReportContext'

const BugReportButton: React.FC = () => {
  const { openBugReport } = useBugReporter()

  return (
    <button
      type="button"
      className="bug-report-trigger"
      onClick={() => openBugReport()}
      aria-label="Report a bug"
    >
      🐞 Report Bug
    </button>
  )
}

export default BugReportButton
