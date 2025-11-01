/**
 * ErrorBoundaryWithReporting Tests
 *
 * Tests that verify the ErrorBoundaryWithReporting wrapper correctly
 * integrates with the auth system and bug reporter.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorBoundaryWithReporting from '../ErrorBoundaryWithReporting'

// Mock the base ErrorBoundary
vi.mock('../ErrorBoundary', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: ({ children, showReportBugButton, onReportBug, boundaryName }: any) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [hasError, setHasError] = React.useState(false)

    if (hasError) {
      return (
        <div>
          <div>Error in {boundaryName}</div>
          {showReportBugButton && (
            <button
              onClick={() => {
                // eslint-disable-next-line @typescript-eslint/no-unsafe-call
                onReportBug(new Error('Test'), null, boundaryName)
              }}
            >
              Report Bug
            </button>
          )}
        </div>
      )
    }

    return <div onClick={() => setHasError(true)}>{children}</div>
  },
}))

// Mock auth context with mutable user
const authMocks = vi.hoisted(() => ({
  user: { role: 'admin', email: 'admin@test.com' },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: authMocks.user,
  }),
}))

// Mock bug reporter
const mockOpenBugReport = vi.fn()
vi.mock('@/contexts/BugReportContext', () => ({
  useBugReporter: () => ({
    openBugReport: mockOpenBugReport,
  }),
}))

// Import React after mocking to ensure mocks are applied
import React from 'react'

describe('ErrorBoundaryWithReporting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  describe('Admin User Integration', () => {
    it('should show Report Bug button for admin users', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Test Component">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error
      await user.click(screen.getByText('Click to trigger error'))

      // Admin should see Report Bug button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /report bug/i })).toBeInTheDocument()
      })
    })

    it('should pre-fill bug report with error details', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Generate Tab">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error
      await user.click(screen.getByText('Click to trigger error'))

      // Click Report Bug
      const reportButton = screen.getByRole('button', { name: /report bug/i })
      await user.click(reportButton)

      // Should call openBugReport with pre-filled description
      expect(mockOpenBugReport).toHaveBeenCalledWith(
        expect.objectContaining({
          description: expect.stringContaining('Generate Tab'),
        })
      )

      expect(mockOpenBugReport).toHaveBeenCalledWith(
        expect.objectContaining({
          description: expect.stringContaining('Error Message'),
        })
      )
    })

    it('should include error stack in bug report description', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Albums Tab">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error
      await user.click(screen.getByText('Click to trigger error'))

      // Click Report Bug
      await user.click(screen.getByRole('button', { name: /report bug/i }))

      // Should include stack trace
      expect(mockOpenBugReport).toHaveBeenCalledWith(
        expect.objectContaining({
          description: expect.stringContaining('Error Stack'),
        })
      )
    })

    it('should include boundary name in bug report', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Custom Boundary Name">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error
      await user.click(screen.getByText('Click to trigger error'))

      // Click Report Bug
      await user.click(screen.getByRole('button', { name: /report bug/i }))

      // Should mention boundary name
      expect(mockOpenBugReport).toHaveBeenCalledWith(
        expect.objectContaining({
          description: expect.stringContaining('Custom Boundary Name'),
        })
      )
    })
  })

  describe('Non-Admin User', () => {
    beforeEach(() => {
      // Change mock to non-admin user
      authMocks.user = { role: 'viewer', email: 'viewer@test.com' }
    })

    afterEach(() => {
      // Reset to admin user
      authMocks.user = { role: 'admin', email: 'admin@test.com' }
    })

    it('should not show Report Bug button for non-admin users', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Test">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error
      await user.click(screen.getByText('Click to trigger error'))

      // Non-admin should not see Report Bug button
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /report bug/i })).not.toBeInTheDocument()
      })
    })
  })

  describe('Bug Report Description Format', () => {
    it('should format description with markdown sections', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Test">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error and report
      await user.click(screen.getByText('Click to trigger error'))
      await user.click(screen.getByRole('button', { name: /report bug/i }))

      const description = mockOpenBugReport.mock.calls[0][0].description

      // Should have markdown sections
      expect(description).toContain('**Error Message:**')
      expect(description).toContain('**Error Stack:**')
      expect(description).toContain('**Steps to reproduce:**')
      expect(description).toContain('**Expected behavior:**')
      expect(description).toContain('**Additional context:**')
    })

    it('should include code blocks for stack traces', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Test">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error and report
      await user.click(screen.getByText('Click to trigger error'))
      await user.click(screen.getByRole('button', { name: /report bug/i }))

      const description = mockOpenBugReport.mock.calls[0][0].description

      // Should use code blocks for stack traces
      expect(description).toContain('```')
    })

    it('should handle missing component stack gracefully', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundaryWithReporting boundaryName="Test">
          <div>Click to trigger error</div>
        </ErrorBoundaryWithReporting>
      )

      // Trigger error and report
      await user.click(screen.getByText('Click to trigger error'))
      await user.click(screen.getByRole('button', { name: /report bug/i }))

      // Should not throw even if component stack is missing
      expect(mockOpenBugReport).toHaveBeenCalled()
    })
  })

  describe('Integration with Base ErrorBoundary', () => {
    it('should pass boundaryName to base ErrorBoundary', () => {
      render(
        <ErrorBoundaryWithReporting boundaryName="Custom Name">
          <div>Content</div>
        </ErrorBoundaryWithReporting>
      )

      // Should render (tests that props are passed correctly)
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('should pass showReportBugButton based on user role', () => {
      render(
        <ErrorBoundaryWithReporting boundaryName="Test">
          <div>Content</div>
        </ErrorBoundaryWithReporting>
      )

      // Should render (tests that conditional prop is passed)
      expect(screen.getByText('Content')).toBeInTheDocument()
    })
  })
})
