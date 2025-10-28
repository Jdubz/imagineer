import React, { useState, useEffect } from 'react'
import type { AuthStatus } from '../types/shared'
import '../styles/AuthButton.css'

interface AuthButtonProps {
  onAuthChange?: (user: AuthStatus | null) => void
}

const AuthButton: React.FC<AuthButtonProps> = ({ onAuthChange }) => {
  const [user, setUser] = useState<AuthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void checkAuth()
  }, [])

  useEffect(() => {
    if (!loading && typeof onAuthChange === 'function') {
      onAuthChange(user)
    }
  }, [user, loading, onAuthChange])

  const checkAuth = async (): Promise<void> => {
    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include',
        headers: {
          Accept: 'application/json'
        }
      })
      const contentType = response.headers?.get?.('content-type') ?? ''

      if (response.status === 204) {
        setUser(null)
        setError(null)
        return
      }

      if (!contentType.includes('application/json')) {
        if (response.status === 401 || response.status === 403) {
          setUser(null)
          setError(null)
          return
        }

        if (typeof response.text === 'function') {
          const preview = (await response.text()).slice(0, 120)
          throw new Error(
            `Unexpected auth response format (${response.status}): ${preview}`
          )
        }

        throw new Error(`Unexpected auth response format (${response.status})`)
      }

      const data: AuthStatus = await response.json()

      if (!response.ok) {
        const backendMessage =
          typeof data?.message === 'string'
            ? data.message
            : typeof data?.error === 'string'
              ? data.error
              : 'Unable to verify authentication status. Please try again.'
        setUser(null)
        setError(backendMessage)
        return
      }

      if (data?.authenticated) {
        setUser(data)
        setError(null)
      } else {
        setUser(null)
        setError(null)
      }
    } catch (err) {
      console.error('Failed to check auth:', err)
      setUser(null)
      setError('Unable to verify authentication status. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = (): void => {
    const currentLocation = window.location.pathname + window.location.search + window.location.hash
    const nextParam = encodeURIComponent(currentLocation || '/')
    const loginUrl = new URL('/api/auth/login', window.location.origin)
    loginUrl.searchParams.set('state', nextParam)

    const popup = window.open(loginUrl.toString(), 'oauth', 'width=500,height=700')

    if (popup) {
      const timer = window.setInterval(() => {
        if (popup.closed) {
          window.clearInterval(timer)
          void checkAuth()
        }
      }, 500)
    } else {
      window.location.href = loginUrl.toString()
    }
  }

  const handleLogout = async (): Promise<void> => {
    try {
      const response = await fetch('/api/auth/logout', {
        credentials: 'include',
        headers: {
          Accept: 'application/json'
        }
      })
      if (!response.ok) {
        const message = typeof response.text === 'function'
          ? await response.text()
          : 'Unexpected logout response'
        throw new Error(message)
      }
      setUser(null)
      setError(null)
    } catch (err) {
      console.error('Failed to logout:', err)
      setError('Failed to log out. Please retry.')
    }
  }

  if (loading) {
    return null
  }

  const primaryLabel = user?.role === 'admin' ? 'Admin' : 'Viewer'

  return (
    <div className="auth-button-container">
      <div className="auth-actions">
        <button type="button" onClick={handleLogin} className="auth-button auth-button--primary">
          {primaryLabel}
        </button>
        {user && (
          <button
            type="button"
            onClick={handleLogout}
            className="auth-button auth-button--secondary"
          >
            Log Out
          </button>
        )}
      </div>
      {error && <div className="auth-error">{error}</div>}
    </div>
  )
}

export default AuthButton
