import React from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Bug } from 'lucide-react'

const BugReportButton: React.FC = () => {
  const { openBugReport } = useBugReporter()
  const { user } = useAuth()

  // Only show for admin users
  if (user?.role !== 'admin') {
    return null
  }

  return (
    <Button
      type="button"
      variant="secondary"
      onClick={() => openBugReport()}
      aria-label="Report a bug (Ctrl+Shift+B)"
      title="Report a bug (Ctrl+Shift+B)"
    >
      <Bug className="h-4 w-4 mr-2" />
      Report Bug
    </Button>
  )
}

export default BugReportButton
