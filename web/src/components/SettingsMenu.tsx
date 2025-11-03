import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import type { AuthStatus } from '../types/shared'
import type { NsfwPreference } from '@/types/models'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings, Bug, LogOut } from 'lucide-react'

interface SettingsMenuProps {
  user: AuthStatus | null
  onLogout: () => void
  onNsfwChange?: (preference: NsfwPreference) => void
  nsfwPreference?: NsfwPreference
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
  onNsfwChange,
  nsfwPreference = 'show',
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

  const handleNsfwChange = useCallback(
    (value: NsfwPreference) => {
      if (onNsfwChange) {
        onNsfwChange(value)
      }
    },
    [onNsfwChange],
  )

  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const isAdmin = user?.role === 'admin'

  if (!user) {
    return null
  }

  return (
    <div className="settings-menu" ref={menuRef}>
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleMenu}
        aria-label="Open settings menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
        type="button"
      >
        <Settings className="h-5 w-5" />
      </Button>

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
            {/* NSFW Preference */}
            <div className="settings-option settings-select">
              <div className="settings-option-text">
                <span className="settings-option-label">NSFW Content</span>
                <span className="settings-option-description">
                  Choose how NSFW images appear in galleries.
                </span>
              </div>
              <Select value={nsfwPreference} onValueChange={(value) => handleNsfwChange(value as NsfwPreference)}>
                <SelectTrigger className="settings-select-trigger" aria-label="NSFW preference">
                  <SelectValue placeholder="Select preference" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="show">Show</SelectItem>
                  <SelectItem value="blur">Blur</SelectItem>
                  <SelectItem value="hide">Hide</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Bug Report (Admin Only) */}
            {isAdmin && (
              <>
                <div className="settings-divider" />
                <Button
                  variant="ghost"
                  className="settings-option settings-button w-full justify-between"
                  onClick={handleBugReport}
                  type="button"
                  role="menuitem"
                >
                  <span className="settings-option-label">
                    <Bug className="h-4 w-4 inline mr-2" />
                    Report Bug
                  </span>
                  <span className="settings-option-hint">Ctrl+Shift+B</span>
                </Button>
              </>
            )}

            {/* Logout */}
            <div className="settings-divider" />
            <Button
              variant="ghost"
              className="settings-option settings-button w-full justify-start"
              onClick={handleLogout}
              type="button"
              role="menuitem"
            >
              <LogOut className="h-4 w-4 mr-2" />
              <span className="settings-option-label">Logout</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsMenu
