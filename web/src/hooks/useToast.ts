import { useContext } from 'react'
import { ToastContext, ToastType } from '../contexts/ToastContext'

/**
 * Custom hook to access toast notification system.
 *
 * Usage:
 * ```tsx
 * const toast = useToast()
 *
 * toast.success('Image generated successfully!')
 * toast.error('Failed to generate image')
 * toast.warning('Queue is full')
 * toast.info('Processing request...')
 * ```
 *
 * @throws Error if used outside ToastProvider
 */
export const useToast = () => {
  const context = useContext(ToastContext)

  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }

  const { addToast } = context

  return {
    success: (message: string, duration?: number) => addToast(message, 'success', duration),
    error: (message: string, duration?: number) => addToast(message, 'error', duration),
    warning: (message: string, duration?: number) => addToast(message, 'warning', duration),
    info: (message: string, duration?: number) => addToast(message, 'info', duration),
    toast: (message: string, type: ToastType, duration?: number) => addToast(message, type, duration),
  }
}
