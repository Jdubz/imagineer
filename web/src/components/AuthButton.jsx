import React, { useState, useEffect } from 'react'
import '../styles/AuthButton.css'

function AuthButton({ onAuthChange }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    void checkAuth()
  }, [])

  useEffect(() => {
    if (!loading && typeof onAuthChange === 'function') {
      onAuthChange(user)
    }
  }, [user, loading, onAuthChange])

  const checkAuth = async () => {
    try {
      const response = await fetch('/auth/me', {
        credentials: 'include'
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

      const data = await response.json()

      if (response.ok && data?.authenticated) {
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

  const handleLogin = () => {
    window.location.href = '/auth/login'
  }

  const handleLogout = async () => {
    try {
      const response = await fetch('/auth/logout', {
        credentials: 'include'
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
        <button onClick={handleLogin} className="auth-button auth-button--primary">
          {primaryLabel}
        </button>
        {user && (
          <button onClick={handleLogout} className="auth-button auth-button--secondary">
            Log Out
          </button>
        )}
      </div>
      {error && <div className="auth-error">{error}</div>}
    </div>
  )
}

export default AuthButton
