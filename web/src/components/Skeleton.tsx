import React from 'react'
import { Skeleton as ShadcnSkeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface SkeletonProps {
  variant?: 'text' | 'rectangular' | 'circular' | 'image-card'
  width?: string | number
  height?: string | number
  count?: number
  className?: string
}

/**
 * Reusable skeleton placeholder component
 * Shows animated placeholder for content that's loading
 */
const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  count = 1,
  className = '',
}) => {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  }

  const variantClasses = {
    text: 'h-4 mb-2 rounded',
    rectangular: 'rounded-lg',
    circular: 'rounded-full',
    'image-card': 'aspect-square',
  }

  const skeletonElement = (index: number) => (
    <ShadcnSkeleton
      key={index}
      className={cn(variantClasses[variant], className)}
      style={style}
      aria-label="Loading content"
      role="status"
    />
  )

  if (count === 1) {
    return skeletonElement(0)
  }

  return (
    <>
      {Array.from({ length: count }).map((_, index) => skeletonElement(index))}
    </>
  )
}

/**
 * Pre-configured skeleton for image grid cards
 */
export const SkeletonImageCard: React.FC = () => (
  <div className="bg-card border border-border rounded-lg overflow-hidden p-0">
    <Skeleton variant="rectangular" width="100%" height="200px" />
    <div className="p-4 flex flex-col gap-2">
      <Skeleton variant="text" width="90%" />
      <Skeleton variant="text" width="60%" />
    </div>
  </div>
)

/**
 * Pre-configured skeleton for batch list items
 */
export const SkeletonBatchItem: React.FC = () => (
  <div className="flex gap-4 p-4 bg-card border border-border rounded-lg mb-2">
    <Skeleton variant="rectangular" width="80px" height="80px" />
    <div className="flex-1 flex flex-col gap-2">
      <Skeleton variant="text" width="200px" />
      <Skeleton variant="text" width="150px" />
      <Skeleton variant="text" width="100px" />
    </div>
  </div>
)

export default Skeleton
