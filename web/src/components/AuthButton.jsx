import React, { useState, useEffect } from 'react'
import '../styles/AuthButton.css'

function AuthButton() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const response = await fetch('/auth/me', {
        credentials: 'include'
      })
      const data = await response.json()

      if (data.authenticated) {
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Failed to check auth:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = () => {
    // Redirect to backend OAuth login
    window.location.href = '/auth/login'
  }

  const handleLogout = async () => {
    try {
      await fetch('/auth/logout', {
        credentials: 'include'
      })
      setUser(null)
    } catch (error) {
      console.error('Failed to logout:', error)
    }
  }

  if (loading) {
    return null
  }

  return (
    <div className="auth-button-container">
      {user ? (
        <div className="auth-user-info">
          <span className="auth-role-badge">{user.role}</span>
          <button onClick={handleLogout} className="auth-button">
            Log Out
          </button>
        </div>
      ) : (
        <button onClick={handleLogin} className="auth-button">
          Log In
        </button>
      )}
    </div>
  )
}

export default AuthButton
