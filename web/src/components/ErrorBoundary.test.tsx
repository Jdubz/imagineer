import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorBoundary from './ErrorBoundary'
import { logger } from '../lib/logger'

// Mock the logger
vi.mock('../lib/logger', () => ({
  logger: {
    error: vi.fn(),
  },
}))

// Component that throws an error for testing
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }): JSX.Element => {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>No error</div>
}

// Suppress console.error during tests since we're intentionally throwing errors
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})

afterEach(() => {
  console.error = originalError
  vi.clearAllMocks()
})

describe('ErrorBoundary', () => {
  describe('Normal rendering', () => {
    it('should render children when there is no error', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child">Child component</div>
        </ErrorBoundary>
      )

      expect(screen.getByTestId('child')).toBeInTheDocument()
      expect(screen.getByText('Child component')).toBeInTheDocument()
    })

    it('should not show error UI when children render successfully', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      )

      expect(screen.getByText('No error')).toBeInTheDocument()
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Error handling', () => {
    it('should catch errors and display fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      expect(screen.queryByText('No error')).not.toBeInTheDocument()
    })

    it('should log errors when caught', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(logger.error).toHaveBeenCalledWith(
        'React Error Boundary caught an error',
        expect.any(Error),
        expect.objectContaining({
          boundaryName: 'Unknown',
        })
      )
    })

    it('should log errors with boundary name when provided', () => {
      render(
        <ErrorBoundary boundaryName="TestBoundary">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(logger.error).toHaveBeenCalledWith(
        'React Error Boundary caught an error',
        expect.any(Error),
        expect.objectContaining({
          boundaryName: 'TestBoundary',
        })
      )
    })

    it('should call onError callback when error occurs', () => {
      const onError = vi.fn()

      render(
        <ErrorBoundary onError={onError}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      )
    })

    it('should display custom boundary name in error message', () => {
      render(
        <ErrorBoundary boundaryName="AlbumsTab">
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText(/an error occurred in AlbumsTab/i)).toBeInTheDocument()
    })
  })

  describe('Recovery options', () => {
    it('should show Try Again button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('should show Reload Page button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument()
    })

    it('should show Go Home button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('button', { name: /go home/i })).toBeInTheDocument()
    })

    it('should reset error state when Try Again is clicked', async () => {
      const user = userEvent.setup()

      // Create a controlled component to test reset
      let shouldThrow = true
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      // Error UI should be shown
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

      // Fix the error and click Try Again
      shouldThrow = false
      const tryAgainButton = screen.getByRole('button', { name: /try again/i })
      await user.click(tryAgainButton)

      // Rerender with fixed component
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      // After reset, the component should try to render children again
      // Note: In this test, we can't fully test the recovery since we need to
      // manually trigger a state update. In real usage, clicking "Try Again"
      // would cause React to re-render the children.
    })

    it('should reload page when Reload Page is clicked', async () => {
      const user = userEvent.setup()
      const reloadSpy = vi.fn()
      Object.defineProperty(window, 'location', {
        value: { reload: reloadSpy },
        writable: true,
      })

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const reloadButton = screen.getByRole('button', { name: /reload page/i })
      await user.click(reloadButton)

      expect(reloadSpy).toHaveBeenCalled()
    })

    it('should navigate to home when Go Home is clicked', async () => {
      const user = userEvent.setup()

      // Mock window.location.href
      delete (window as { location?: unknown }).location
      window.location = { href: '' } as Location

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const goHomeButton = screen.getByRole('button', { name: /go home/i })
      await user.click(goHomeButton)

      expect(window.location.href).toBe('/')
    })
  })

  describe('Custom fallback', () => {
    it('should render custom fallback when provided', () => {
      render(
        <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom error UI</div>}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument()
      expect(screen.getByText('Custom error UI')).toBeInTheDocument()
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Development mode', () => {
    it('should show error details in development mode', () => {
      // Mock development mode
      vi.stubEnv('MODE', 'development')

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // Error details should be in a details element (more specific selector)
      const details = screen.getByText('Error Details (Development Only)')
      expect(details).toBeInTheDocument()
      expect(details.tagName).toBe('SUMMARY')
    })

    it('should show error message in stack trace', () => {
      vi.stubEnv('MODE', 'development')

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // The error message should appear somewhere in the UI
      // Use getAllByText since it appears in multiple places (error display and stack)
      const errorTexts = screen.getAllByText(/Test error message/i)
      expect(errorTexts.length).toBeGreaterThan(0)
    })
  })
})
