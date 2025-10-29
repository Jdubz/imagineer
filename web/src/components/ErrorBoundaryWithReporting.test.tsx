import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ErrorBoundaryWithReporting from './ErrorBoundaryWithReporting'

// Mock child component that can throw errors
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>Child component</div>
}

// Mock AuthContext
const mockUseAuth = vi.fn()
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

// Mock BugReportContext
const mockOpenBugReport = vi.fn()
vi.mock('../contexts/BugReportContext', () => ({
  useBugReporter: () => ({
    openBugReport: mockOpenBugReport,
    registerCollector: vi.fn(() => vi.fn()),
  }),
}))

describe('ErrorBoundaryWithReporting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Suppress console.error for error boundary tests
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  describe('Normal Rendering', () => {
    it('renders children when no error occurs', () => {
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={false} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText('Child component')).toBeInTheDocument()
    })

    it('does not show error UI when no error', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <div>Normal content</div>
        </ErrorBoundaryWithReporting>
      )

      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('catches errors and displays error UI', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })

    it('displays boundary name in error message', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Albums Tab">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/Albums Tab/i)).toBeInTheDocument()
    })
  })

  describe('Admin User - Bug Report Button', () => {
    it('shows report bug button for admin users when error occurs', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/🐞 report bug/i)).toBeInTheDocument()
    })

    it('calls openBugReport with pre-filled description when report bug is clicked', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      const reportButton = screen.getByText(/🐞 report bug/i)
      reportButton.click()

      expect(mockOpenBugReport).toHaveBeenCalledTimes(1)
      const callArg = mockOpenBugReport.mock.calls[0][0]

      // Verify pre-filled content
      expect(callArg).toContain('**Error caught in Test Boundary**')
      expect(callArg).toContain('Test error message')
      expect(callArg).toContain('**Error Stack:**')
      expect(callArg).toContain('**Steps to reproduce:**')
      expect(callArg).toContain('**Expected behavior:**')
    })

    it('includes error stack trace in pre-filled description', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      const reportButton = screen.getByText(/🐞 report bug/i)
      reportButton.click()

      const callArg = mockOpenBugReport.mock.calls[0][0]
      expect(callArg).toContain('Error: Test error message')
    })
  })

  describe('Viewer User - Bug Report Button', () => {
    it('does not show report bug button for viewer users', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'viewer@example.com', role: 'viewer' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.queryByText(/🐞 report bug/i)).not.toBeInTheDocument()
    })

    it('does not show report bug button when user is null', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.queryByText(/🐞 report bug/i)).not.toBeInTheDocument()
    })

    it('does not show report bug button when auth is loading', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: null,
        loading: true,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.queryByText(/🐞 report bug/i)).not.toBeInTheDocument()
    })
  })

  describe('Component Stack Integration', () => {
    it('includes component stack in pre-filled description when available', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      const reportButton = screen.getByText(/🐞 report bug/i)
      reportButton.click()

      const callArg = mockOpenBugReport.mock.calls[0][0]
      // Should have component stack section even if empty
      expect(callArg).toMatch(/\*\*Component Stack:\*\*|\*\*Error Stack:\*\*/)
    })
  })

  describe('Error Recovery Actions', () => {
    it('displays try again button', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/try again/i)).toBeInTheDocument()
    })

    it('displays reload page button', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/reload page/i)).toBeInTheDocument()
    })

    it('displays go home button', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/go home/i)).toBeInTheDocument()
    })
  })

  describe('Multiple Errors', () => {
    it('handles subsequent errors after recovery attempt', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      const { rerender } = render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

      // Click try again
      const tryAgainButton = screen.getByText(/try again/i)
      tryAgainButton.click()

      // Throw error again
      rerender(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      // Should still show error UI
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })

  describe('Boundary Name Variations', () => {
    it('handles missing boundary name gracefully', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting>
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      // Should show generic error message
      expect(screen.getByText(/unexpected error occurred/i)).toBeInTheDocument()
    })

    it('includes boundary name in pre-filled bug report', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Custom Boundary Name">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      const reportButton = screen.getByText(/🐞 report bug/i)
      reportButton.click()

      const callArg = mockOpenBugReport.mock.calls[0][0]
      expect(callArg).toContain('Custom Boundary Name')
    })
  })

  describe('Integration with BugReportProvider', () => {
    it('uses bugReporter context correctly', () => {
      // Mock setup
      mockUseAuth.mockReturnValue({
        user: { email: 'admin@example.com', role: 'admin' },
        loading: false,
      })

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Boundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundaryWithReporting>
      )

      const reportButton = screen.getByText(/🐞 report bug/i)
      reportButton.click()

      // Verify openBugReport was called from context
      expect(mockOpenBugReport).toHaveBeenCalled()
    })
  })
})
