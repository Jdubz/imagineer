import React from 'react'
import '../styles/Skeleton.css'

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

  const skeletonElement = (index: number) => (
    <div
      key={index}
      className={`skeleton skeleton-${variant} ${className}`}
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
  <div className="skeleton-image-card">
    <Skeleton variant="rectangular" width="100%" height="200px" />
    <div className="skeleton-image-card-text">
      <Skeleton variant="text" width="90%" />
      <Skeleton variant="text" width="60%" />
    </div>
  </div>
)

/**
 * Pre-configured skeleton for batch list items
 */
export const SkeletonBatchItem: React.FC = () => (
  <div className="skeleton-batch-item">
    <Skeleton variant="rectangular" width="80px" height="80px" />
    <div className="skeleton-batch-item-content">
      <Skeleton variant="text" width="200px" />
      <Skeleton variant="text" width="150px" />
      <Skeleton variant="text" width="100px" />
    </div>
  </div>
)

export default Skeleton
