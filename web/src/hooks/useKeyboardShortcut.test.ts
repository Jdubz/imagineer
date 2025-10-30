import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcut } from './useKeyboardShortcut'

describe('useKeyboardShortcut', () => {
  let mockCallback: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockCallback = vi.fn()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Functionality', () => {
    it('calls callback when correct key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when wrong key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'a' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })

    it('is case insensitive', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'B' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })
  })

  describe('Ctrl Key Modifier', () => {
    it('calls callback when Ctrl+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        ctrlKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('calls callback when Cmd+key is pressed (Mac)', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        metaKey: true, // Cmd key on Mac
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when key without Ctrl is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('Shift Key Modifier', () => {
    it('calls callback when Shift+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          shiftKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        shiftKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when key without Shift is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          shiftKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('Alt Key Modifier', () => {
    it('calls callback when Alt+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          altKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        altKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when key without Alt is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          altKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('Meta Key Modifier', () => {
    it('calls callback when Meta+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          metaKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        metaKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when key without Meta is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          metaKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('Multiple Modifiers', () => {
    it('calls callback when Ctrl+Shift+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          shiftKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        ctrlKey: true,
        shiftKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when only one modifier is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          shiftKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        ctrlKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })

    it('calls callback when Ctrl+Shift+Alt+key is pressed', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          shiftKey: true,
          altKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        ctrlKey: true,
        shiftKey: true,
        altKey: true,
      })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })
  })

  describe('Enabled/Disabled State', () => {
    it('calls callback when enabled is true', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          enabled: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('does not call callback when enabled is false', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          enabled: false,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })

    it('dynamically enables/disables based on enabled prop', () => {
      const { rerender } = renderHook(
        ({ enabled }) =>
          useKeyboardShortcut({
            key: 'b',
            enabled,
            callback: mockCallback,
          }),
        {
          initialProps: { enabled: false },
        }
      )

      // Disabled - should not call
      let event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)
      expect(mockCallback).not.toHaveBeenCalled()

      // Enable
      rerender({ enabled: true })

      // Enabled - should call
      event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)
      expect(mockCallback).toHaveBeenCalledTimes(1)
    })
  })

  describe('Ignores Input Fields', () => {
    it('does not call callback when typing in input field', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const input = document.createElement('input')
      document.body.appendChild(input)

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', { value: input, writable: false })
      input.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()

      document.body.removeChild(input)
    })

    it('does not call callback when typing in textarea', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const textarea = document.createElement('textarea')
      document.body.appendChild(textarea)

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', {
        value: textarea,
        writable: false,
      })
      textarea.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()

      document.body.removeChild(textarea)
    })

    it('does not call callback when typing in contenteditable', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const div = document.createElement('div')
      div.contentEditable = 'true'
      document.body.appendChild(div)

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', { value: div, writable: false })
      div.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()

      document.body.removeChild(div)
    })

    it('calls callback when event target is not an input field', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const div = document.createElement('div')
      document.body.appendChild(div)

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', { value: div, writable: false })
      div.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)

      document.body.removeChild(div)
    })
  })

  describe('Prevents Default Behavior', () => {
    it('prevents default when shortcut matches', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', {
        key: 'b',
        ctrlKey: true,
      })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')

      window.dispatchEvent(event)

      expect(preventDefaultSpy).toHaveBeenCalled()
    })

    it('does not prevent default when shortcut does not match', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'a' })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')

      window.dispatchEvent(event)

      expect(preventDefaultSpy).not.toHaveBeenCalled()
    })
  })

  describe('Cleanup', () => {
    it('removes event listener on unmount', () => {
      const { unmount } = renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      unmount()

      const event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)

      expect(mockCallback).not.toHaveBeenCalled()
    })

    it('updates callback when it changes', () => {
      const callback1 = vi.fn()
      const callback2 = vi.fn()

      const { rerender } = renderHook(
        ({ callback }) =>
          useKeyboardShortcut({
            key: 'b',
            callback,
          }),
        {
          initialProps: { callback: callback1 },
        }
      )

      // First callback
      let event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)
      expect(callback1).toHaveBeenCalledTimes(1)
      expect(callback2).not.toHaveBeenCalled()

      // Change callback
      rerender({ callback: callback2 })

      // Second callback
      event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)
      expect(callback1).toHaveBeenCalledTimes(1)
      expect(callback2).toHaveBeenCalledTimes(1)
    })
  })

  describe('Special Keys', () => {
    it('handles Enter key', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'Enter',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'Enter' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('handles Escape key', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'Escape',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: 'Escape' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })

    it('handles Space key', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: ' ',
          callback: mockCallback,
        })
      )

      const event = new KeyboardEvent('keydown', { key: ' ' })
      window.dispatchEvent(event)

      expect(mockCallback).toHaveBeenCalledTimes(1)
    })
  })

  describe('Edge Cases', () => {
    it('handles rapid key presses', () => {
      renderHook(() =>
        useKeyboardShortcut({
          key: 'b',
          callback: mockCallback,
        })
      )

      for (let i = 0; i < 10; i++) {
        const event = new KeyboardEvent('keydown', { key: 'b' })
        window.dispatchEvent(event)
      }

      expect(mockCallback).toHaveBeenCalledTimes(10)
    })

    it('handles multiple shortcuts on same key with different modifiers', () => {
      const callback1 = vi.fn()
      const callback2 = vi.fn()

      renderHook(() => {
        useKeyboardShortcut({
          key: 'b',
          callback: callback1,
        })
        useKeyboardShortcut({
          key: 'b',
          ctrlKey: true,
          callback: callback2,
        })
      })

      // Press 'b' without modifier
      let event = new KeyboardEvent('keydown', { key: 'b' })
      window.dispatchEvent(event)
      expect(callback1).toHaveBeenCalledTimes(1)
      expect(callback2).not.toHaveBeenCalled()

      // Press 'b' with Ctrl
      event = new KeyboardEvent('keydown', { key: 'b', ctrlKey: true })
      window.dispatchEvent(event)
      expect(callback1).toHaveBeenCalledTimes(1)
      expect(callback2).toHaveBeenCalledTimes(1)
    })
  })
})
