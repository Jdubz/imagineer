import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AuthButton from './AuthButton'

const createResponse = (data = {}, init = {}) =>
  Promise.resolve({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: () => Promise.resolve(data)
  })

describe('AuthButton', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = originalFetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('renders viewer button for unauthenticated users', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      createResponse({
        authenticated: false
      })
    )

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument()
  })

  it('shows admin label and logout button for admins', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        createResponse({
          authenticated: true,
          role: 'admin'
        })
      )
      .mockImplementationOnce(() =>
        createResponse({}, { status: 200 })
      )

    globalThis.fetch = fetchMock

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /admin/i })).toBeInTheDocument()
    })

    const logoutButton = screen.getByRole('button', { name: /log out/i })
    await user.click(logoutButton)

    expect(fetchMock).toHaveBeenCalledWith('/auth/logout', expect.any(Object))
  })

  it('surface errors when auth check fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'))

    render(<AuthButton />)

    await waitFor(() => {
      expect(
        screen.getByText(/unable to verify authentication status/i)
      ).toBeInTheDocument()
    })
    // Button should still default to viewer state
    expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
  })
})
