import { useEffect } from 'react'

interface KeyboardShortcutOptions {
  /**
   * Key to listen for (e.g., 'b', 'Enter', 'Escape')
   */
  key: string

  /**
   * Whether Ctrl (Windows/Linux) or Cmd (Mac) key must be pressed
   */
  ctrlKey?: boolean

  /**
   * Whether Shift key must be pressed
   */
  shiftKey?: boolean

  /**
   * Whether Alt/Option key must be pressed
   */
  altKey?: boolean

  /**
   * Whether Meta (Cmd on Mac) key must be pressed
   */
  metaKey?: boolean

  /**
   * Whether the shortcut is enabled
   * Useful for conditional shortcuts (e.g., admin-only)
   */
  enabled?: boolean

  /**
   * Callback to execute when shortcut is triggered
   */
  callback: () => void
}

/**
 * Hook to register global keyboard shortcuts
 *
 * Features:
 * - Ignores shortcuts when typing in inputs/textareas
 * - Supports Ctrl/Cmd, Shift, Alt modifiers
 * - Can be conditionally enabled/disabled
 * - Automatically cleans up on unmount
 *
 * @example
 * ```tsx
 * // Register Ctrl+Shift+B shortcut (admin only)
 * useKeyboardShortcut({
 *   key: 'b',
 *   ctrlKey: true,
 *   shiftKey: true,
 *   enabled: isAdmin,
 *   callback: () => openBugReport()
 * })
 * ```
 */
export const useKeyboardShortcut = ({
  key,
  ctrlKey = false,
  shiftKey = false,
  altKey = false,
  metaKey = false,
  enabled = true,
  callback,
}: KeyboardShortcutOptions): void => {
  useEffect(() => {
    if (!enabled) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if typing in input/textarea/contenteditable
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable ||
        target.contentEditable === 'true'
      ) {
        return
      }

      // Check if all modifiers and key match
      // Use metaKey for Cmd on Mac, ctrlKey for Ctrl on Windows/Linux
      const isCtrlOrCmd = ctrlKey && (event.ctrlKey || event.metaKey)
      const isShift = shiftKey === event.shiftKey
      const isAlt = altKey === event.altKey
      const isMeta = metaKey === event.metaKey
      const isKey = event.key.toLowerCase() === key.toLowerCase()

      // If ctrlKey specified, check Ctrl or Cmd
      // If metaKey specified, check specifically Meta
      // Otherwise ensure no ctrl/meta keys are pressed
      const modifiersMatch =
        isKey &&
        isShift &&
        isAlt &&
        (ctrlKey ? isCtrlOrCmd : metaKey ? true : !event.ctrlKey && !event.metaKey) &&
        (metaKey ? isMeta : true)

      if (modifiersMatch) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [key, ctrlKey, shiftKey, altKey, metaKey, enabled, callback])
}
