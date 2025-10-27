import React, { useState, useEffect, useCallback } from 'react'
import '../styles/PasswordGate.css'

const AUTH_TOKEN_KEY = 'imagineer_auth_token'
const SESSION_EXPIRY_KEY = 'imagineer_session_expiry'
const SESSION_DURATION = 24 * 60 * 60 * 1000 // 24 hours in milliseconds

function PasswordGate({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const checkExistingSession = useCallback(() => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    const expiry = localStorage.getItem(SESSION_EXPIRY_KEY)

    if (token && expiry) {
      const expiryTime = parseInt(expiry, 10)
      const now = Date.now()

      if (now < expiryTime) {
        // Session is still valid
        setIsAuthenticated(true)
      } else {
        // Session expired, clear storage
        clearSession()
      }
    }

    setIsLoading(false)
  }, [])

  useEffect(() => {
    // Check if user has a valid session
    checkExistingSession()
  }, [checkExistingSession])

  const clearSession = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(SESSION_EXPIRY_KEY)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')

    // Get password from environment variable
    const correctPassword = import.meta.env.VITE_APP_PASSWORD || 'carnuvian'

    if (password === correctPassword) {
      // Generate a simple token (timestamp-based for this basic implementation)
      const token = btoa(`authenticated:${Date.now()}`)
      const expiry = Date.now() + SESSION_DURATION

      // Store in localStorage
      localStorage.setItem(AUTH_TOKEN_KEY, token)
      localStorage.setItem(SESSION_EXPIRY_KEY, expiry.toString())

      setIsAuthenticated(true)
      setPassword('')
    } else {
      setError('Incorrect password')
      setPassword('')
    }
  }

  const handleLogout = () => {
    clearSession()
    setIsAuthenticated(false)
    setPassword('')
  }

  // Show loading state while checking session
  if (isLoading) {
    return (
      <div className="password-gate">
        <div className="password-gate-container">
          <div className="password-gate-card">
            <h1>✨ Imagineer</h1>
            <p>Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="password-gate">
        <div className="password-gate-container">
          <div className="password-gate-card">
            <h1>✨ Imagineer</h1>
            <p className="subtitle">AI Image Generation Toolkit</p>

            <form onSubmit={handleSubmit} className="password-form">
              <div className="form-group">
                <label htmlFor="password">Enter Password</label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  autoFocus
                  autoComplete="current-password"
                />
              </div>

              {error && <div className="error-message">{error}</div>}

              <button type="submit" className="submit-button">
                Unlock
              </button>
            </form>

            <p className="footer-text">
              Protected Access • Session expires in 24 hours
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Render children with logout button if authenticated
  return (
    <>
      <div className="auth-status">
        <button onClick={handleLogout} className="logout-button" title="Logout">
          🚪 Logout
        </button>
      </div>
      {children}
    </>
  )
}

export default PasswordGate
