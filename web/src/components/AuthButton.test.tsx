import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AuthButton, { buildLoginState } from './AuthButton'

interface MockResponseInit {
  ok?: boolean
  status?: number
  headers?: Record<string, string>
  text?: string
}

interface MockResponse {
  ok: boolean
  status: number
  headers: { get: (name: string) => string | null }
  json: () => Promise<Record<string, unknown>>
  text: () => Promise<string>
}

const createResponse = (
  data: Record<string, unknown> = {},
  init: MockResponseInit = {},
): Promise<MockResponse> => {
  const headersInit = init.headers ?? { 'content-type': 'application/json' }
  const headerStore = new Map(
    Object.entries(headersInit).map(([key, value]) => [key.toLowerCase(), value]),
  )

  return Promise.resolve({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    headers: {
      get: (name: string) => headerStore.get(name.toLowerCase()) ?? null,
    },
    json: () => Promise.resolve(data),
    text: () =>
      Promise.resolve(typeof init.text === 'string' ? init.text : JSON.stringify(data)),
  })
}

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
        authenticated: false,
      }),
    )

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument()
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/auth/me',
      expect.objectContaining({
        credentials: 'include',
        headers: { Accept: 'application/json' },
      }),
    )
  })

  it('shows admin label and logout button for admins', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        createResponse({
          authenticated: true,
          role: 'admin',
        }),
      )
      .mockImplementationOnce(() => createResponse({}, { status: 200 }))

    globalThis.fetch = fetchMock

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /admin/i })).toBeInTheDocument()
    })

    const logoutButton = screen.getByRole('button', { name: /log out/i })
    await user.click(logoutButton)

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/auth/me',
      expect.objectContaining({
        credentials: 'include',
        headers: { Accept: 'application/json' },
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/auth/logout',
      expect.objectContaining({
        credentials: 'include',
        headers: { Accept: 'application/json' },
      }),
    )
  })

  it('surfaces errors when auth check fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'))

    render(<AuthButton />)

    await waitFor(() => {
      expect(
        screen.getByText(/unable to verify authentication status/i),
      ).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
  })

  it('handles non-json unauthorized responses gracefully', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      createResponse(
        {},
        {
          ok: false,
          status: 401,
          headers: { 'content-type': 'text/html' },
          text: '<!DOCTYPE html><html></html>',
        },
      ),
    )

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
    })
    expect(screen.queryByText(/unable to verify/i)).not.toBeInTheDocument()
  })

  it('shows backend-provided error message when auth check fails server-side', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      createResponse(
        {
          authenticated: false,
          error: 'AUTH_STATUS_ERROR',
          message: 'Failed to determine authentication status.'
        },
        {
          ok: false,
          status: 500
        }
      )
    )

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByText(/failed to determine authentication status/i)).toBeInTheDocument()
    })
  })

  it('opens OAuth popup with normalized state', async () => {
    window.history.replaceState({}, '', '/dashboard/view?tab=gallery#images')

    const fetchMock = vi.fn().mockResolvedValue(
      createResponse({
        authenticated: false,
      }),
    )
    globalThis.fetch = fetchMock

    let closedState = false
    const popupRef = {
      get closed() {
        return closedState
      }
    } as unknown as WindowProxy
    const openSpy = vi.spyOn(window, 'open').mockReturnValue(popupRef)

    render(<AuthButton />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
    })

    vi.useFakeTimers()
    try {
      fireEvent.click(screen.getByRole('button', { name: /viewer/i }))
      closedState = true
      vi.runOnlyPendingTimers()

      expect(openSpy).toHaveBeenCalledTimes(1)
      const loginUrl = new URL(openSpy.mock.calls[0][0] as string, window.location.origin)
      expect(loginUrl.pathname).toBe('/api/auth/login')
      expect(loginUrl.searchParams.get('state')).toBe('/dashboard/view?tab=gallery#images')
    } finally {
      openSpy.mockRestore()
      vi.useRealTimers()
    }
  })

  it('falls back to root state when location resolves outside origin', () => {
    const hostileLocation = {
      pathname: '//malicious.example.com/path',
      search: '?redirect=1',
      hash: '',
      origin: 'http://localhost:5173',
    }

    expect(buildLoginState(hostileLocation)).toBe('/')
  })
})
