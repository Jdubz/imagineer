import React, { useContext } from 'react'
import { ToastContext } from '../contexts/ToastContext'
import '../styles/Toast.css'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'

/**
 * Toast notification component that displays success, error, warning, and info messages.
 *
 * Features:
 * - Auto-dismisses after configurable duration
 * - Manual dismiss via close button
 * - Different visual styles for each type
 * - Slide-in animation
 * - Accessible with ARIA attributes
 */
const ToastContainer: React.FC = () => {
  const context = useContext(ToastContext)

  if (!context) {
    throw new Error('ToastContainer must be used within ToastProvider')
  }

  const { toasts, removeToast } = context

  const getIcon = (type: string): string => {
    switch (type) {
      case 'success':
        return '✓'
      case 'error':
        return '✕'
      case 'warning':
        return '⚠'
      case 'info':
        return 'ℹ'
      default:
        return 'ℹ'
    }
  }

  return (
    <div className="toast-container" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}`}
          role="alert"
          aria-live="assertive"
        >
          <div className="toast-icon">{getIcon(toast.type)}</div>
          <div className="toast-message">{toast.message}</div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => removeToast(toast.id)}
            aria-label="Close notification"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
    </div>
  )
}

export default ToastContainer
