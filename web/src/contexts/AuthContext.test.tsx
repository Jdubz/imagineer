import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor, renderHook } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AuthProvider, useAuth } from './AuthContext'
import type { AuthStatus } from '../types/shared'

// Mock logger
vi.mock('../lib/logger', () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
}))

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  describe('AuthProvider', () => {
    it('renders children', () => {
      const { getByText } = render(
        <AuthProvider>
          <div>Test Child</div>
        </AuthProvider>
      )

      expect(getByText('Test Child')).toBeInTheDocument()
    })

    it('initializes with loading state', () => {
      const TestComponent = () => {
        const { loading } = useAuth()
        return <div>{loading ? 'Loading' : 'Not Loading'}</div>
      }

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
        status: 204,
      })

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(getByText('Loading')).toBeInTheDocument()
    })

    it('calls checkAuth on mount', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        status: 204,
      })
      vi.stubGlobal('fetch', mockFetch)

      render(
        <AuthProvider>
          <div>Test</div>
        </AuthProvider>
      )

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/auth/me', {
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        })
      })
    })

    it('sets loading to false after checkAuth completes', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
        status: 204,
      })

      const TestComponent = () => {
        const { loading } = useAuth()
        return <div>{loading ? 'Loading' : 'Not Loading'}</div>
      }

      const { getByText } = render(
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toEqual(mockUser)
    })

    it('sets user to null on 204 No Content', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null on 401 Unauthorized', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
        status: 401,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
    })

    it('sets user to null on 403 Forbidden', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockRejectedValue(mockError)

      const { logger } = await import('../lib/logger')

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(logger.error).toHaveBeenCalledWith('Failed to check auth', mockError)
    })

    it('handles JSON parsing errors gracefully', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockImplementation(() => {
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
      await result.current.checkAuth()

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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
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
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
        ok: true,
        status: 200,
      })

      await result.current.logout()

      expect(result.current.user).toBeNull()
      expect(fetch).toHaveBeenCalledWith('/api/auth/logout', {
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      })
    })

    it('throws error on failed logout', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Mock failed logout
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      })

      await expect(result.current.logout()).rejects.toThrow('Internal Server Error')
    })

    it('logs error on logout failure', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
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
      vi.stubGlobal('fetch', vi.fn()).mockRejectedValueOnce(logoutError)

      await expect(result.current.logout()).rejects.toThrow('Logout failed')
      expect(logger.error).toHaveBeenCalledWith('Failed to logout', logoutError)
    })

    it('handles logout response without text method', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
        status: 204,
      })

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Mock logout with response that has no text method
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: undefined,
      })

      await expect(result.current.logout()).rejects.toThrow('Unexpected logout response')
    })
  })

  describe('setUser', () => {
    it('directly updates user state', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      result.current.setUser(newUser)

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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      result.current.setUser(null)

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

      vi.stubGlobal('fetch', vi.fn()).mockReturnValue(authPromise)

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
      vi.stubGlobal('fetch', vi.fn()).mockRejectedValue(new Error('Network error'))

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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
      vi.stubGlobal('fetch', vi.fn()).mockImplementation(() => {
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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      result.current.setUser(viewerUser)

      await waitFor(() => {
        expect(result.current.user).toEqual(viewerUser)
      })

      // Transition to null
      result.current.setUser(null)

      await waitFor(() => {
        expect(result.current.user).toBeNull()
      })
    })

    it('preserves callback references with useCallback', async () => {
      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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

      vi.stubGlobal('fetch', vi.fn()).mockResolvedValue({
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
