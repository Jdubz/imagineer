import { useCallback, memo } from 'react'
import type { GeneratedImage, NsfwPreference } from '../../types/models'
import { resolveImageSources, preloadImage } from '../../lib/imageSources'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

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
      className={cn(
        'relative overflow-hidden rounded-lg border border-border shadow-sm transition-all hover:scale-[1.02] hover:shadow-md',
        className
      )}
      onMouseEnter={handlePreload}
    >
      <picture className="block w-full">
        {thumbnail.endsWith('.webp') && <source srcSet={srcSet} type="image/webp" />}
        <img
          src={thumbnail}
          srcSet={srcSet}
          sizes={sizes}
          alt={alt || image.filename}
          loading="lazy"
          decoding="async"
          onClick={handleClick}
          className={cn(
            'h-[250px] w-full bg-gradient-to-br from-muted to-border object-cover transition-all md:h-[200px]',
            onImageClick && 'cursor-pointer hover:opacity-90',
            shouldBlur && 'blur-[14px]'
          )}
        />
      </picture>

      {/* Blur overlay */}
      {shouldBlur && (
        <div
          className="pointer-events-none absolute inset-0 z-[2] flex items-center justify-center bg-gradient-to-br from-black/45 to-black/60 text-white"
          aria-label="NSFW content blurred"
        >
          <span className="rounded-full border border-white/40 bg-black/50 px-3 py-1.5 text-sm font-semibold uppercase tracking-wide">
            Blurred
          </span>
        </div>
      )}

      {/* NSFW Badge */}
      {isNsfw && showNsfwBadge && (
        <Badge
          variant="destructive"
          className="absolute right-2 top-2 z-[2] px-1.5 py-0.5 text-[0.7rem] font-bold shadow-md"
          aria-label="NSFW content"
        >
          18+
        </Badge>
      )}

      {/* Label Badge */}
      {hasLabels && showLabelBadge && (
        <Badge
          className="absolute bottom-2 right-2 z-[2] flex items-center gap-1 bg-foreground/70 px-1.5 py-0.5 text-[0.7rem] text-background shadow-md"
          aria-label={`${labelCount} labels`}
          title={`${labelCount} label(s)`}
        >
          🏷️
          {labelCount > 1 && <span className="text-[0.65rem] font-bold">{labelCount}</span>}
        </Badge>
      )}

      {/* Prompt (optional) */}
      {showPrompt && image.metadata?.prompt && (
        <div className="bg-background p-2 text-xs leading-snug text-muted-foreground">
          <p className="overflow-hidden text-ellipsis whitespace-nowrap">
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
