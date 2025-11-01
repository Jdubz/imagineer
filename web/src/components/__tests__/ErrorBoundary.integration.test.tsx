/**
 * ErrorBoundary Integration Tests
 *
 * Tests that verify ErrorBoundary correctly catches errors,
 * displays fallback UI, and integrates with bug reporting.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorBoundary from '../ErrorBoundary'

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>No error</div>
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error for these tests since we expect errors
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  describe('Error Catching', () => {
    it('should catch errors from child components', () => {
      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })

    it('should display error UI when error is caught', () => {
      render(
        <ErrorBoundary boundaryName="TestBoundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      expect(screen.getByText(/TestBoundary/i)).toBeInTheDocument()
    })

    it('should render children normally when no error', () => {
      render(
        <ErrorBoundary boundaryName="Test">
          <div>Normal content</div>
        </ErrorBoundary>
      )

      expect(screen.getByText('Normal content')).toBeInTheDocument()
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Error UI Elements', () => {
    it('should display boundary name in error message', () => {
      render(
        <ErrorBoundary boundaryName="Albums Tab">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText(/Albums Tab/)).toBeInTheDocument()
    })

    it('should display Try Again button', () => {
      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('should display Reload Page button', () => {
      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument()
    })

    it('should display Go Home button', () => {
      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /go home/i })).toBeInTheDocument()
    })
  })

  describe('Recovery Actions', () => {
    it('should reload page when Reload button is clicked', async () => {
      const user = userEvent.setup()
      const reloadSpy = vi.fn()
      Object.defineProperty(window, 'location', {
        value: { reload: reloadSpy },
        writable: true,
      })

      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const reloadButton = screen.getByRole('button', { name: /reload page/i })
      await user.click(reloadButton)

      expect(reloadSpy).toHaveBeenCalled()
    })

    it('should navigate home when Go Home is clicked', async () => {
      const user = userEvent.setup()
      const hrefSetter = vi.fn()
      let currentHref = '/'
      Object.defineProperty(window, 'location', {
        value: {
          get href() { return currentHref },
          set href(value: string) {
            currentHref = value
            hrefSetter(value)
          }
        },
        writable: true,
      })

      render(
        <ErrorBoundary boundaryName="Test">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const homeButton = screen.getByRole('button', { name: /go home/i })
      await user.click(homeButton)

      expect(hrefSetter).toHaveBeenCalledWith('/')
    })
  })

  describe('Custom Fallback', () => {
    it('should render custom fallback when provided', () => {
      const CustomFallback = <div>Custom error UI</div>

      render(
        <ErrorBoundary boundaryName="Test" fallback={CustomFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText('Custom error UI')).toBeInTheDocument()
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Error Callback', () => {
    it('should call onError callback when error is caught', () => {
      const onErrorMock = vi.fn()

      render(
        <ErrorBoundary boundaryName="Test" onError={onErrorMock}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(onErrorMock).toHaveBeenCalled()
      expect(onErrorMock).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      )
    })
  })

  describe('Bug Report Integration', () => {
    it('should show Report Bug button when showReportBugButton is true', () => {
      render(
        <ErrorBoundary boundaryName="Test" showReportBugButton={true}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /report bug/i })).toBeInTheDocument()
    })

    it('should not show Report Bug button when showReportBugButton is false', () => {
      render(
        <ErrorBoundary boundaryName="Test" showReportBugButton={false}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.queryByRole('button', { name: /report bug/i })).not.toBeInTheDocument()
    })

    it('should call onReportBug when Report Bug is clicked', async () => {
      const user = userEvent.setup()
      const onReportBugMock = vi.fn()

      render(
        <ErrorBoundary
          boundaryName="Test"
          showReportBugButton={true}
          onReportBug={onReportBugMock}
        >
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const reportButton = screen.getByRole('button', { name: /report bug/i })
      await user.click(reportButton)

      expect(onReportBugMock).toHaveBeenCalled()
      expect(onReportBugMock).toHaveBeenCalledWith(
        expect.any(Error),
        expect.any(Object),
        'Test'
      )
    })
  })

  describe('Multiple Error Boundaries', () => {
    it('should only affect its own boundary when error occurs', () => {
      render(
        <div>
          <ErrorBoundary boundaryName="Boundary 1">
            <div>Content 1 - No error</div>
          </ErrorBoundary>
          <ErrorBoundary boundaryName="Boundary 2">
            <ThrowError shouldThrow={true} />
          </ErrorBoundary>
        </div>
      )

      // First boundary should show content
      expect(screen.getByText('Content 1 - No error')).toBeInTheDocument()

      // Second boundary should show error
      expect(screen.getByText(/Boundary 2/)).toBeInTheDocument()
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })
})
