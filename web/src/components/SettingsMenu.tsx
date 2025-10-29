import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import '../styles/SettingsMenu.css'

interface User {
  email: string
  role: string
}

interface SettingsMenuProps {
  user: User | null
  onLogout: () => void
  onNsfwToggle?: (enabled: boolean) => void
  nsfwEnabled?: boolean
}

/**
 * Settings menu with gear icon dropdown
 *
 * Features:
 * - User info display (email and role badge)
 * - NSFW filter toggle
 * - Bug report button (admin only)
 * - Logout button
 */
const SettingsMenu: React.FC<SettingsMenuProps> = ({
  user,
  onLogout,
  onNsfwToggle,
  nsfwEnabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const { openBugReport } = useBugReporter()

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Close on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const handleLogout = useCallback(() => {
    setIsOpen(false)
    onLogout()
  }, [onLogout])

  const handleBugReport = useCallback(() => {
    setIsOpen(false)
    openBugReport()
  }, [openBugReport])

  const handleNsfwToggle = useCallback(() => {
    if (onNsfwToggle) {
      onNsfwToggle(!nsfwEnabled)
    }
  }, [onNsfwToggle, nsfwEnabled])

  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const isAdmin = user?.role === 'admin'

  if (!user) {
    return null
  }

  return (
    <div className="settings-menu" ref={menuRef}>
      <button
        className="settings-trigger"
        onClick={toggleMenu}
        aria-label="Open settings menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
        type="button"
      >
        <svg
          className="settings-icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v6m0 6v10m-5-16.7l3 5.2m0 6.9-3 5.2m10-16.4-3 5.2m0 6.9 3 5.2m5-10.8-5.2-3m-6.9 0-5.2 3m16.4 10-5.2 3m-6.9 0-5.2-3" />
        </svg>
      </button>

      {isOpen && (
        <div className="settings-dropdown" role="menu">
          <div className="settings-header">
            <div className="settings-user-info">
              <div className="settings-user-email">{user.email}</div>
              <div className="settings-user-role">
                {isAdmin ? (
                  <>
                    <span className="role-icon">👑</span> Admin
                  </>
                ) : (
                  <>
                    <span className="role-icon">👁️</span> Viewer
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="settings-divider" />

          <div className="settings-options">
            {/* NSFW Filter Toggle */}
            <label className="settings-option settings-toggle" htmlFor="nsfw-filter">
              <span className="settings-option-label">Hide NSFW</span>
              <input
                id="nsfw-filter"
                type="checkbox"
                checked={nsfwEnabled}
                onChange={handleNsfwToggle}
                className="settings-checkbox"
              />
            </label>

            {/* Bug Report (Admin Only) */}
            {isAdmin && (
              <>
                <div className="settings-divider" />
                <button
                  className="settings-option settings-button"
                  onClick={handleBugReport}
                  type="button"
                  role="menuitem"
                >
                  <span className="settings-option-label">
                    <span className="bug-icon">🐞</span> Report Bug
                  </span>
                  <span className="settings-option-hint">Ctrl+Shift+B</span>
                </button>
              </>
            )}

            {/* Logout */}
            <div className="settings-divider" />
            <button
              className="settings-option settings-button"
              onClick={handleLogout}
              type="button"
              role="menuitem"
            >
              <span className="settings-option-label">Logout</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsMenu
