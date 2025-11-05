/* eslint-disable @typescript-eslint/require-await, @typescript-eslint/unbound-method, @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor, renderHook, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AuthProvider, useAuth } from './AuthContext'
import type { AuthStatus } from '../types/shared'
import type { ReactElement } from 'react'

// Mock logger
vi.mock('../lib/logger', () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
}))

describe('AuthContext', () => {
  let defaultFetchMock: ReturnType<typeof vi.fn>
  const renderWithProvider = async (ui: ReactElement) => {
    let result: ReturnType<typeof render>
    await act(async () => {
      result = render(ui)
    })
    return result!
  }

  const renderAuthHook = async () => {
    let hookResult: ReturnType<typeof renderHook>
    await act(async () => {
      hookResult = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })
    })
    return hookResult!
  }

  beforeEach(() => {
    vi.clearAllMocks()
    defaultFetchMock = vi.fn().mockResolvedValue({ status: 204 })
    vi.stubGlobal('fetch', defaultFetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  describe('AuthProvider', () => {
    it('renders children', async () => {
      const { getByText } = await renderWithProvider(
        <AuthProvider>
          <div>Test Child</div>
        </AuthProvider>
      )

      expect(getByText('Test Child')).toBeInTheDocument()
      await waitFor(() => {
        expect(defaultFetchMock).toHaveBeenCalled()
      })
    })

    it('initializes with loading state', async () => {
      const TestComponent = () => {
        const { loading } = useAuth()
        return <div>{loading ? 'Loading' : 'Not Loading'}</div>
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockReturnValue(new Promise(() => {}))

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(getByText('Loading')).toBeInTheDocument()
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })
    })

    it('calls checkAuth on mount', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        status: 204,
      })
      vi.stubGlobal('fetch', mockFetch)

      await renderWithProvider(
        <AuthProvider>
          <div>Test</div>
        </AuthProvider>
      )

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/auth/me'),
          expect.objectContaining({
            credentials: 'include',
          }),
        )
      })
    })

    it('sets loading to false after checkAuth completes', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 204,
      })

      const TestComponent = () => {
        const { loading } = useAuth()
        return <div>{loading ? 'Loading' : 'Not Loading'}</div>
      }

      const { getByText } = await renderWithProvider(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(getByText('Not Loading')).toBeInTheDocument()
      })
    })
  })

  describe('useAuth hook', () => {
    it('returns context value when used inside provider', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 204,
      })

      const { result } = await renderAuthHook()

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current).toHaveProperty('user')
      expect(result.current).toHaveProperty('loading')
      expect(result.current).toHaveProperty('checkAuth')
      expect(result.current).toHaveProperty('logout')
      expect(result.current).toHaveProperty('setUser')
    })

    it('throws error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        renderHook(() => useAuth())
      }).toThrow('useAuth must be used within AuthProvider')

      consoleErrorSpy.mockRestore()
    })
  })

  describe('checkAuth', () => {
    it('sets user when authenticated', async () => {
      const mockUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => mockUser,
      })

      const { result } = await renderAuthHook()

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toEqual(mockUser)
    })

    it('sets user to null on 204 No Content', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 204,
      })

      const { result } = await renderAuthHook()

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null on 401 Unauthorized', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 401,
      })

      const { result } = await renderAuthHook()

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null on 403 Forbidden', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 403,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null when response is not JSON', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'text/html' : null),
        },
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null when content-type header is missing', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: () => null,
        },
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null when authenticated is false', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({ authenticated: false }),
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null when response is not ok', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({ authenticated: true, email: 'test@example.com', role: 'admin' }),
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('handles network errors gracefully', async () => {
      const mockError = new Error('Network error')
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockRejectedValue(mockError)

      const { logger } = await import('../lib/logger')

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      // The error is logged twice: once in apiRequest, once in checkAuth
      expect(logger.error).toHaveBeenCalled()
      expect(logger.error).toHaveBeenCalledWith('Failed to check auth', expect.any(Error))
    })

    it('handles JSON parsing errors gracefully', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })

      const { logger } = await import('../lib/logger')

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(logger.error).toHaveBeenCalled()
    })

    it('can be called manually after mount', async () => {
      let callCount = 0
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockImplementation(() => {
        callCount++
        return Promise.resolve({ status: 204 })
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(callCount).toBe(1)

      // Call checkAuth manually
      await act(async () => {
        await result.current.checkAuth()
      })

      expect(callCount).toBe(2)
    })
  })

  describe('logout', () => {
    it('clears user on successful logout', async () => {
      const mockUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      // First call for checkAuth (on mount)
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => mockUser,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
      })

      // Mock logout call
      const mockLogoutFetch1 = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
      })
      vi.stubGlobal('fetch', mockLogoutFetch1)

      await act(async () => {
        await result.current.logout()
      })

      await waitFor(() => {
        expect(result.current.user).toBeNull()
      })
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/logout'),
        {
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        },
      )
    })

    it('throws error on failed logout', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValueOnce({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Mock failed logout
      const mockLogoutFetch2 = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      })
      vi.stubGlobal('fetch', mockLogoutFetch2)

      await expect(
        act(async () => {
          await result.current.logout()
        })
      ).rejects.toThrow('Internal Server Error')
    })

    it('logs error on logout failure', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)

      // Initial checkAuth on mount
      mockFetch.mockResolvedValueOnce({
        status: 204,
      })

      const { logger } = await import('../lib/logger')

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const logoutError = new Error('Logout failed')
      // Logout call that will fail
      mockFetch.mockRejectedValueOnce(logoutError)
      // Any subsequent calls (e.g. checkAuth after error) return 204
      // This prevents race conditions where checkAuth is called after logout fails
      mockFetch.mockResolvedValue({
        status: 204,
      })

      let logoutFailed = false
      try {
        await act(async () => {
          await result.current.logout()
        })
      } catch (error) {
        logoutFailed = true
        expect(error).toBe(logoutError)
      }

      expect(logoutFailed).toBe(true)
      // Verify logger.error was called with the logout error at some point
      expect(logger.error).toHaveBeenCalledWith('Failed to logout', logoutError)
    })

    it('handles logout response without text method', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValueOnce({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Mock logout with response that has no text method
      const mockLogoutFetch3 = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: undefined,
      })
      vi.stubGlobal('fetch', mockLogoutFetch3)

      await expect(
        act(async () => {
          await result.current.logout()
        })
      ).rejects.toThrow('Unexpected logout response')
    })
  })

  describe('setUser', () => {
    it('directly updates user state', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()

      const newUser: AuthStatus = {
        authenticated: true,
        email: 'viewer@example.com',
        role: 'viewer',
      }

      act(() => {
        result.current.setUser(newUser)
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(newUser)
      })
    })

    it('can set user to null', async () => {
      const mockUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => mockUser,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
      })

      act(() => {
        result.current.setUser(null)
      })

      await waitFor(() => {
        expect(result.current.user).toBeNull()
      })
    })
  })

  describe('Loading State Management', () => {
    it('maintains loading state during checkAuth', async () => {
      let resolveAuth: (value: any) => void = () => {}
      const authPromise = new Promise((resolve) => {
        resolveAuth = resolve
      })

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockReturnValue(authPromise)

      const loadingStates: boolean[] = []

      const TestComponent = () => {
        const { loading } = useAuth()
        loadingStates.push(loading)
        return <div>{loading ? 'Loading' : 'Done'}</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      // Should start with loading=true
      expect(loadingStates[0]).toBe(true)

      // Resolve the auth promise
      resolveAuth({ status: 204 })

      await waitFor(() => {
        expect(loadingStates[loadingStates.length - 1]).toBe(false)
      })
    })

    it('sets loading to false even when checkAuth fails', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })
  })

  describe('Multiple User Roles', () => {
    it('handles admin user correctly', async () => {
      const adminUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => adminUser,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user?.role).toBe('admin')
      })
    })

    it('handles viewer user correctly', async () => {
      const viewerUser: AuthStatus = {
        authenticated: true,
        email: 'viewer@example.com',
        role: 'viewer',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => viewerUser,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user?.role).toBe('viewer')
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles rapid checkAuth calls', async () => {
      let fetchCount = 0
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockImplementation(() => {
        fetchCount++
        return Promise.resolve({ status: 204 })
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      // Wait for initial checkAuth
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const initialCount = fetchCount

      // Call checkAuth multiple times rapidly
      await Promise.all([
        result.current.checkAuth(),
        result.current.checkAuth(),
        result.current.checkAuth(),
      ])

      // Should have called fetch 3 more times (beyond initial)
      expect(fetchCount).toBe(initialCount + 3)
    })

    it('handles user state transitions', async () => {
      const adminUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => adminUser,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(adminUser)
      })

      // Transition to viewer
      const viewerUser: AuthStatus = {
        authenticated: true,
        email: 'viewer@example.com',
        role: 'viewer',
      }

      act(() => {
        result.current.setUser(viewerUser)
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(viewerUser)
      })

      // Transition to null
      act(() => {
        result.current.setUser(null)
      })

      await waitFor(() => {
        expect(result.current.user).toBeNull()
      })
    })

    it('preserves callback references with useCallback', async () => {
      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        status: 204,
      })

      const { result, rerender } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const firstCheckAuth = result.current.checkAuth
      const firstLogout = result.current.logout

      // Rerender
      rerender()

      // Callbacks should be stable
      expect(result.current.checkAuth).toBe(firstCheckAuth)
      expect(result.current.logout).toBe(firstLogout)
    })
  })

  describe('Integration with Components', () => {
    it('provides auth state to nested components', async () => {
      const mockUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => mockUser,
      })

      const NestedComponent = () => {
        const { user } = useAuth()
        return <div>{user ? user.email : 'Not logged in'}</div>
      }

      const { getByText } = render(
        <AuthProvider>
          <NestedComponent />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(getByText('admin@example.com')).toBeInTheDocument()
      })
    })

    it('allows multiple components to access auth state', async () => {
      const mockUser: AuthStatus = {
        authenticated: true,
        email: 'admin@example.com',
        role: 'admin',
      }

      const mockFetch = vi.fn()
      vi.stubGlobal('fetch', mockFetch)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => mockUser,
      })

      const EmailDisplay = () => {
        const { user } = useAuth()
        return <div data-testid="email">{user?.email}</div>
      }

      const RoleDisplay = () => {
        const { user } = useAuth()
        return <div data-testid="role">{user?.role}</div>
      }

      const { getByTestId } = render(
        <AuthProvider>
          <EmailDisplay />
          <RoleDisplay />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(getByTestId('email')).toHaveTextContent('admin@example.com')
        expect(getByTestId('role')).toHaveTextContent('admin')
      })
    })
  })
})
