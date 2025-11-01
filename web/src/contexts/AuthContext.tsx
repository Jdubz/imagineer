import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { logger } from '../lib/logger'
import { api, ApiError } from '../lib/api'
import { isAuthError } from '../lib/errorUtils'
import type { AuthStatus } from '../types/shared'

interface AuthContextValue {
  user: AuthStatus | null
  loading: boolean
  checkAuth: () => Promise<void>
  logout: () => Promise<void>
  setUser: (user: AuthStatus | null) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = useCallback(async (): Promise<void> => {
    try {
      // Use the api.auth.checkAuth method which validates with AuthStatusSchema
      const data = await api.auth.checkAuth()

      if (data?.authenticated) {
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      // Handle auth errors (401/403) gracefully
      if (isAuthError(error)) {
        setUser(null)
        return
      }
      logger.error('Failed to check auth', error as Error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch('/api/auth/logout', {
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      })

      if (!response.ok) {
        const message =
          typeof response.text === 'function'
            ? await response.text()
            : 'Unexpected logout response'
        throw new Error(message)
      }

      setUser(null)
    } catch (error) {
      logger.error('Failed to logout', error as Error)
      throw error
    }
  }, [])

  // Check auth on mount
  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  const value: AuthContextValue = {
    user,
    loading,
    checkAuth,
    logout,
    setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
