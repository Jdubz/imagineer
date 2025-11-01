import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import SettingsMenu from './SettingsMenu'

vi.mock('../contexts/BugReportContext', () => ({
  useBugReporter: () => ({
    openBugReport: vi.fn(),
    registerCollector: vi.fn(() => vi.fn()),
  }),
}))

const adminUser = {
  email: 'admin@example.com',
  authenticated: true,
  role: 'admin',
} as const

const viewerUser = {
  email: 'viewer@example.com',
  authenticated: true,
  role: 'viewer',
} as const

describe('SettingsMenu', () => {
  const onLogout = vi.fn()
  const onNsfwChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the trigger button when a user is present', () => {
    render(
      <SettingsMenu
        user={adminUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    expect(screen.getByRole('button', { name: /open settings menu/i })).toBeInTheDocument()
  })

  it('returns null when no user is provided', () => {
    const { container } = render(
      <SettingsMenu user={null} onLogout={onLogout} onNsfwChange={onNsfwChange} />,
    )

    expect(container.firstChild).toBeNull()
  })

  it('opens the dropdown and displays user details on trigger click', () => {
    render(
      <SettingsMenu
        user={adminUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /open settings menu/i }))

    expect(screen.getByText(adminUser.email)).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('updates NSFW preference when a new option is selected', () => {
    render(
      <SettingsMenu
        user={adminUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /open settings menu/i }))
    const trigger = screen.getByRole('combobox', { name: /nsfw preference/i })
    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('option', { name: /hide/i }))

    expect(onNsfwChange).toHaveBeenCalledWith('hide')
  })

  it('shows the bug report action for admin users', () => {
    render(
      <SettingsMenu
        user={adminUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /open settings menu/i }))

    expect(screen.getByText(/report bug/i)).toBeInTheDocument()
  })

  it('hides the bug report action for viewer users', () => {
    render(
      <SettingsMenu
        user={viewerUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /open settings menu/i }))

    expect(screen.queryByText(/report bug/i)).not.toBeInTheDocument()
  })

  it('invokes onLogout when logout is clicked', () => {
    render(
      <SettingsMenu
        user={adminUser}
        onLogout={onLogout}
        onNsfwChange={onNsfwChange}
        nsfwPreference="show"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /open settings menu/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /logout/i }))

    expect(onLogout).toHaveBeenCalledTimes(1)
  })
})
