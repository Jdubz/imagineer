import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SpinnerProps {
  size?: 'small' | 'medium' | 'large'
  message?: string
  className?: string
}

const sizeClasses = {
  small: 'h-6 w-6',
  medium: 'h-10 w-10',
  large: 'h-16 w-16',
}

/**
 * Reusable loading spinner component
 * Shows an animated spinner with optional message
 */
const Spinner: React.FC<SpinnerProps> = ({ size = 'medium', message, className }) => {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-4 p-8', className)}>
      <Loader2
        className={cn('animate-spin text-primary', sizeClasses[size])}
        aria-label="Loading"
        role="status"
      />
      {message && <p className="text-center text-sm text-muted-foreground">{message}</p>}
    </div>
  )
}

export default Spinner
