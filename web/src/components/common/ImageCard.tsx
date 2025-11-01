import { useCallback, memo } from 'react'
import type { GeneratedImage, NsfwPreference } from '../../types/models'
import { resolveImageSources, preloadImage } from '../../lib/imageSources'
import '../../styles/ImageCard.css'

export interface ImageCardProps {
  /**
   * The image data to display
   */
  image: GeneratedImage

  /**
   * How NSFW images should be handled (`show`, `blur`, or `hide`)
   * @default 'hide'
   */
  nsfwPreference?: NsfwPreference

  /**
   * Callback when image is clicked
   */
  onImageClick?: (image: GeneratedImage) => void

  /**
   * Number of labels on this image (for badge)
   */
  labelCount?: number

  /**
   * Whether to show the NSFW badge (18+) on NSFW images
   * @default true
   */
  showNsfwBadge?: boolean

  /**
   * Whether to show the label badge (🏷️) when labels exist
   * @default true
   */
  showLabelBadge?: boolean

  /**
   * Whether to show the prompt below the image
   * @default true
   */
  showPrompt?: boolean

  /**
   * Additional CSS classes to apply to the card container
   */
  className?: string

  /**
   * Custom sizes attribute for responsive images
   * @default "(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw"
   */
  sizes?: string
}

/**
 * Common reusable image card component with NSFW filtering and badges
 *
 * Features:
 * - NSFW handling (hide or blur NSFW images based on preference)
 * - NSFW badge (18+) display
 * - Label badge (🏷️) display
 * - Responsive images with srcSet
 * - Lazy loading
 * - Hover preloading
 * - Optional prompt display
 * - Configurable click handler
 *
 * @example
 * ```tsx
 * <ImageCard
 *   image={image}
 *   nsfwPreference={nsfwPreference}
 *   onImageClick={handleOpenModal}
 *   labelCount={image.labels?.length}
 * />
 * ```
 */
const ImageCard = memo<ImageCardProps>(({
  image,
  nsfwPreference = 'hide',
  onImageClick,
  labelCount = 0,
  showNsfwBadge = true,
  showLabelBadge = true,
  showPrompt = true,
  className = '',
  sizes = '(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw',
}) => {
  const { thumbnail, full, alt, srcSet } = resolveImageSources(image)

  const handlePreload = useCallback(() => {
    preloadImage(full)
  }, [full])

  const handleClick = useCallback(() => {
    if (onImageClick) {
      onImageClick(image)
    }
  }, [image, onImageClick])

  const hasLabels = labelCount > 0
  const isNsfw = image.is_nsfw === true

  const shouldHide = nsfwPreference === 'hide' && isNsfw
  const shouldBlur = nsfwPreference === 'blur' && isNsfw

  if (shouldHide) {
    return null
  }

  return (
    <div
      className={`image-card ${isNsfw ? 'nsfw' : ''} ${shouldBlur ? 'nsfw-blurred' : ''} ${className}`}
      onMouseEnter={handlePreload}
    >
      <picture className="image-picture">
        {thumbnail.endsWith('.webp') && <source srcSet={srcSet} type="image/webp" />}
        <img
          src={thumbnail}
          srcSet={srcSet}
          sizes={sizes}
          alt={alt || image.filename}
          loading="lazy"
          decoding="async"
          onClick={handleClick}
          className={`image-thumbnail ${onImageClick ? 'clickable' : ''} ${shouldBlur ? 'blurred' : ''}`}
        />
      </picture>

      {/* Blur overlay */}
      {shouldBlur && (
        <div className="nsfw-blur-overlay" aria-label="NSFW content blurred">
          <span className="nsfw-blur-label">Blurred</span>
        </div>
      )}

      {/* NSFW Badge */}
      {isNsfw && showNsfwBadge && (
        <div className="nsfw-badge" aria-label="NSFW content">
          18+
        </div>
      )}

      {/* Label Badge */}
      {hasLabels && showLabelBadge && (
        <div className="label-badge" aria-label={`${labelCount} labels`} title={`${labelCount} label(s)`}>
          🏷️
          {labelCount > 1 && <span className="label-count">{labelCount}</span>}
        </div>
      )}

      {/* Prompt (optional) */}
      {showPrompt && image.metadata?.prompt && (
        <div className="image-prompt">
          <p>
            {image.metadata.prompt.length > 50
              ? `${image.metadata.prompt.substring(0, 50)}...`
              : image.metadata.prompt}
          </p>
        </div>
      )}
    </div>
  )
})

ImageCard.displayName = 'ImageCard'

export default ImageCard
