import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import type { AuthStatus } from '../types/shared'
import type { NsfwPreference } from '@/types/models'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings, Bug, LogOut } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

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
  const menuRef = useRef<HTMLDivElement | null>(null)
  const { openBugReport } = useBugReporter()

  // Close menu when clicking outside
  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
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
    <div className="relative" ref={menuRef}>
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
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-border bg-popover p-4 shadow-lg focus:outline-none"
        >
          <div className="mb-3 space-y-1">
            <p className="text-sm font-medium text-foreground">{user.email}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant={isAdmin ? 'secondary' : 'outline'}>
                {isAdmin ? 'Admin' : 'Viewer'}
              </Badge>
              <span>{isAdmin ? 'Full access' : 'Read only access'}</span>
            </div>
          </div>

          <div className="my-3 h-px bg-border" />

          <div className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <span className="text-sm font-medium text-foreground">NSFW Content</span>
                <span className="block text-xs text-muted-foreground">
                  Choose how NSFW images appear in galleries.
                </span>
              </div>
              <Select
                value={nsfwPreference}
                onValueChange={(value) => handleNsfwChange(value as NsfwPreference)}
              >
                <SelectTrigger
                  aria-label="NSFW preference"
                  className="w-[150px] justify-between"
                >
                  <SelectValue placeholder="Select preference" />
                </SelectTrigger>
                <SelectContent align="end">
                  <SelectItem value="show">Show</SelectItem>
                  <SelectItem value="blur">Blur</SelectItem>
                  <SelectItem value="hide">Hide</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {isAdmin && (
              <Button
                variant="ghost"
                className="w-full justify-between"
                onClick={handleBugReport}
                type="button"
                role="menuitem"
              >
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Bug className="h-4 w-4" />
                  Report Bug
                </span>
                <span className="text-xs text-muted-foreground">Ctrl+Shift+B</span>
              </Button>
            )}

            <Button
              variant="ghost"
              className="w-full justify-start gap-2 text-destructive hover:text-destructive"
              onClick={handleLogout}
              type="button"
              role="menuitem"
            >
              <LogOut className="h-4 w-4" />
              <span className="text-sm font-medium">Logout</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsMenu
