import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import SettingsMenu from './SettingsMenu'
import { BugReportProvider } from '../contexts/BugReportContext'

// Mock BugReportContext
vi.mock('../contexts/BugReportContext', () => ({
  useBugReporter: () => ({
    openBugReport: vi.fn(),
    registerCollector: vi.fn(() => vi.fn()),
  }),
  BugReportProvider: ({ children }: { children: React.ReactNode }) => children,
}))

describe('SettingsMenu', () => {
  const mockUser = {
    email: 'admin@example.com', authenticated: true,
    role: 'admin',
  }

  const mockViewerUser = {
    email: 'viewer@example.com', authenticated: true,
    role: 'viewer',
  }

  const mockOnLogout = vi.fn()
  const mockOnNsfwToggle = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders settings trigger button', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      expect(trigger).toBeInTheDocument()
    })

    it('does not render when user is null', () => {
      const { container } = render(
        <SettingsMenu
          user={null}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('shows dropdown when trigger is clicked', async () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      await waitFor(() => {
        expect(screen.getByText(mockUser.email)).toBeInTheDocument()
      })
    })
  })

  describe('User Info Display', () => {
    it('displays admin user email and role badge', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(mockUser.email)).toBeInTheDocument()
      expect(screen.getByText(/admin/i)).toBeInTheDocument()
      expect(screen.getByText('👑')).toBeInTheDocument()
    })

    it('displays viewer user email and role badge', () => {
      render(
        <SettingsMenu
          user={mockViewerUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(mockViewerUser.email)).toBeInTheDocument()
      expect(screen.getByText(/viewer/i)).toBeInTheDocument()
      expect(screen.getByText('👁️')).toBeInTheDocument()
    })
  })

  describe('NSFW Toggle', () => {
    it('renders NSFW toggle checkbox', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          onNsfwToggle={mockOnNsfwToggle}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const checkbox = screen.getByRole('checkbox', { name: /hide nsfw/i })
      expect(checkbox).toBeInTheDocument()
      expect(checkbox).not.toBeChecked()
    })

    it('reflects nsfwEnabled state', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          onNsfwToggle={mockOnNsfwToggle}
          nsfwEnabled={true}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const checkbox = screen.getByRole('checkbox', { name: /hide nsfw/i })
      expect(checkbox).toBeChecked()
    })

    it('calls onNsfwToggle when checkbox is clicked', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          onNsfwToggle={mockOnNsfwToggle}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const checkbox = screen.getByRole('checkbox', { name: /hide nsfw/i })
      fireEvent.click(checkbox)

      expect(mockOnNsfwToggle).toHaveBeenCalledWith(true)
    })
  })

  describe('Bug Report Button', () => {
    it('shows bug report button for admin users', () => {
      render(
        <BugReportProvider>
          <SettingsMenu
            user={mockUser}
            onLogout={mockOnLogout}
            nsfwEnabled={false}
          />
        </BugReportProvider>
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(/report bug/i)).toBeInTheDocument()
      expect(screen.getByText(/ctrl\+shift\+b/i)).toBeInTheDocument()
    })

    it('hides bug report button for viewer users', () => {
      render(
        <BugReportProvider>
          <SettingsMenu
            user={mockViewerUser}
            onLogout={mockOnLogout}
            nsfwEnabled={false}
          />
        </BugReportProvider>
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.queryByText(/report bug/i)).not.toBeInTheDocument()
    })
  })

  describe('Logout Button', () => {
    it('renders logout button', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(/logout/i)).toBeInTheDocument()
    })

    it('calls onLogout and closes menu when logout is clicked', async () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const logoutButton = screen.getByText(/logout/i)
      fireEvent.click(logoutButton)

      expect(mockOnLogout).toHaveBeenCalled()

      // Menu should close
      await waitFor(() => {
        expect(screen.queryByText(mockUser.email)).not.toBeInTheDocument()
      })
    })
  })

  describe('Menu Interactions', () => {
    it('closes menu when clicking outside', async () => {
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <SettingsMenu
            user={mockUser}
            onLogout={mockOnLogout}
            nsfwEnabled={false}
          />
        </div>
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(mockUser.email)).toBeInTheDocument()

      // Click outside
      const outside = screen.getByTestId('outside')
      fireEvent.mouseDown(outside)

      await waitFor(() => {
        expect(screen.queryByText(mockUser.email)).not.toBeInTheDocument()
      })
    })

    it('closes menu when pressing Escape', async () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      expect(screen.getByText(mockUser.email)).toBeInTheDocument()

      // Press Escape
      fireEvent.keyDown(document, { key: 'Escape' })

      await waitFor(() => {
        expect(screen.queryByText(mockUser.email)).not.toBeInTheDocument()
      })
    })

    it('toggles menu open/closed on multiple clicks', async () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      const trigger = screen.getByRole('button', { name: /open settings menu/i })

      // First click - open
      fireEvent.click(trigger)
      expect(screen.getByText(mockUser.email)).toBeInTheDocument()

      // Second click - close
      fireEvent.click(trigger)
      await waitFor(() => {
        expect(screen.queryByText(mockUser.email)).not.toBeInTheDocument()
      })

      // Third click - open again
      fireEvent.click(trigger)
      expect(screen.getByText(mockUser.email)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes on trigger', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      expect(trigger).toHaveAttribute('aria-expanded', 'false')
      expect(trigger).toHaveAttribute('aria-haspopup', 'true')

      // Open menu
      fireEvent.click(trigger)
      expect(trigger).toHaveAttribute('aria-expanded', 'true')
    })

    it('has proper role on dropdown menu', () => {
      render(
        <SettingsMenu
          user={mockUser}
          onLogout={mockOnLogout}
          nsfwEnabled={false}
        />
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const menu = screen.getByRole('menu')
      expect(menu).toBeInTheDocument()
    })

    it('has proper role on menu items', () => {
      render(
        <BugReportProvider>
          <SettingsMenu
            user={mockUser}
            onLogout={mockOnLogout}
            nsfwEnabled={false}
          />
        </BugReportProvider>
      )

      // Open dropdown
      const trigger = screen.getByRole('button', { name: /open settings menu/i })
      fireEvent.click(trigger)

      const bugReportButton = screen.getByRole('menuitem', { name: /report bug/i })
      const logoutButton = screen.getByRole('menuitem', { name: /logout/i })

      expect(bugReportButton).toBeInTheDocument()
      expect(logoutButton).toBeInTheDocument()
    })
  })
})
