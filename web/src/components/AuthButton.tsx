import React, { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { logger } from '../lib/logger'
import type { AuthStatus } from '../types/shared'
import '../styles/AuthButton.css'

interface AuthButtonProps {
  onAuthChange?: (user: AuthStatus | null) => void
}

export const buildLoginState = (
  location: Pick<Location, 'pathname' | 'search' | 'hash' | 'origin'>,
): string => {
  const pathPart = location.pathname.startsWith('/')
    ? location.pathname
    : `/${location.pathname}`
  const rawState = `${pathPart}${location.search}${location.hash}` || '/'

  try {
    const parsed = new URL(rawState, location.origin)
    if (parsed.origin === location.origin) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}` || '/'
    }
  } catch {
    // Ignore parsing errors and fall back to root
  }

  return '/'
}

const AuthButton: React.FC<AuthButtonProps> = ({ onAuthChange }) => {
  const [user, setUser] = useState<AuthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const popupRef = useRef<Window | null>(null)
  const popupTimerRef = useRef<number | null>(null)
  const pollCountRef = useRef(0)
  const authCheckInFlightRef = useRef(false)

  const clearPopupTimer = useCallback((): void => {
    if (popupTimerRef.current != null) {
      window.clearInterval(popupTimerRef.current)
      popupTimerRef.current = null
    }
    pollCountRef.current = 0
  }, [])

  const closeAuthWindow = useCallback(
    (reason?: 'success' | 'closed' | 'cancelled'): void => {
      clearPopupTimer()

      const popupWindow = popupRef.current
      popupRef.current = null

      if (popupWindow && !popupWindow.closed) {
        try {
          popupWindow.close()
        } catch (err) {
          logger.warn?.('Unable to close OAuth popup', err)
        }
      }

      setIsAuthModalOpen(false)

      if (reason === 'cancelled') {
        setError('Login was cancelled. You can try again when you are ready.')
      }
    },
    [clearPopupTimer],
  )

  const checkAuth = useCallback(async (): Promise<void> => {
    if (authCheckInFlightRef.current) {
      return
    }

    authCheckInFlightRef.current = true

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
      logger.error('Failed to check auth:', err)
      setUser(null)
      setError('Unable to verify authentication status. Please try again.')
    } finally {
      authCheckInFlightRef.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (!loading && typeof onAuthChange === 'function') {
      onAuthChange(user)
    }
  }, [user, loading, onAuthChange])

  useEffect(() => {
    if (!loading && user?.authenticated) {
      closeAuthWindow('success')
    }
  }, [loading, user?.authenticated, closeAuthWindow])

  useEffect(() => {
    return () => {
      closeAuthWindow()
    }
  }, [closeAuthWindow])

  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent): void => {
      if (event.origin !== window.location.origin) {
        return
      }

      const payload =
        typeof event.data === 'object' && event.data !== null
          ? (event.data as { type?: string })
          : null

      if (payload?.type === 'imagineer-auth-success') {
        closeAuthWindow('success')
        void checkAuth()
      }
    }

    window.addEventListener('message', handleAuthMessage)

    return () => {
      window.removeEventListener('message', handleAuthMessage)
    }
  }, [checkAuth, closeAuthWindow])

  const handleLogin = (): void => {
    closeAuthWindow()

    const sanitizedState = buildLoginState(window.location)

    // Force HTTPS in production, use current origin in development
    let origin = window.location.origin
    if (import.meta.env.PROD && origin.startsWith('http://')) {
      origin = origin.replace('http://', 'https://')
    }

    const loginUrl = new URL('/api/auth/login', origin)
    loginUrl.searchParams.set('state', sanitizedState)

    const popup = window.open(loginUrl.toString(), 'oauth', 'width=500,height=700')

    if (popup) {
      popupRef.current = popup
      popup.focus?.()
      pollCountRef.current = 0
      setIsAuthModalOpen(true)

      popupTimerRef.current = window.setInterval(() => {
        const activePopup = popupRef.current
        if (!activePopup || activePopup.closed) {
          closeAuthWindow('closed')
          void checkAuth()
          return
        }

        pollCountRef.current += 1
        if (pollCountRef.current % 6 === 0) {
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
      logger.error('Failed to logout:', err)
      setError('Failed to log out. Please retry.')
    }
  }

  if (loading) {
    return null
  }

  const authModal = isAuthModalOpen
    ? createPortal(
        <div className="auth-modal-backdrop" role="presentation">
          <div
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-modal-title"
          >
            <h2 id="auth-modal-title">Complete Google Sign-In</h2>
            <p className="auth-modal-message">
              Finish signing in with Google in the window that just opened. This dialog will close
              automatically once we confirm your account.
            </p>
            <div className="auth-modal-actions">
              <button
                type="button"
                className="auth-modal-button"
                onClick={() => {
                  closeAuthWindow('cancelled')
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )
    : null

  const primaryLabel = user?.role === 'admin' ? 'Admin' : 'Viewer'

  return (
    <>
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
      {authModal}
    </>
  )
}

export default AuthButton
