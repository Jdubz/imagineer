import React, { useMemo, useState, useEffect, useCallback, memo } from 'react'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface ImageGalleryProps {
  images?: GeneratedImage[]
}

// Memoized image card component to prevent unnecessary re-renders
interface ImageCardProps {
  image: GeneratedImage
  imageKey: string
  onOpen: (image: GeneratedImage) => void
}

const ImageCard = memo<ImageCardProps>(({ image, imageKey, onOpen }) => {
  const { thumbnail, full, alt, srcSet } = resolveImageSources(image)

  const handlePreload = useCallback(() => {
    preloadImage(full)
  }, [full])

  const handleClick = useCallback(() => {
    onOpen(image)
  }, [image, onOpen])

  return (
    <div key={imageKey} className="image-item" onMouseEnter={handlePreload}>
      <picture>
        {thumbnail.endsWith('.webp') && <source srcSet={srcSet} type="image/webp" />}
        <img
          src={thumbnail}
          srcSet={srcSet}
          sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw"
          alt={alt || image.filename}
          loading="lazy"
          decoding="async"
          onClick={handleClick}
          className="gallery-image"
        />
      </picture>
      <div className="image-prompt">
        {image.metadata?.prompt ? (
          <p>
            {image.metadata.prompt.length > 50
              ? `${image.metadata.prompt.substring(0, 50)}...`
              : image.metadata.prompt}
          </p>
        ) : null}
      </div>
    </div>
  )
})

ImageCard.displayName = 'ImageCard'

const ImageGallery: React.FC<ImageGalleryProps> = memo(({ images = [] }) => {
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null)
  const selectedSources = useMemo(
    () => (selectedImage ? resolveImageSources(selectedImage) : null),
    [selectedImage]
  )

  useEffect(() => {
    if (selectedSources?.full) {
      preloadImage(selectedSources.full)
    }
  }, [selectedSources?.full])

  const openModal = useCallback((image: GeneratedImage): void => {
    setSelectedImage(image)
  }, [])

  const closeModal = useCallback((): void => {
    setSelectedImage(null)
  }, [])

  if (images.length === 0) {
    return (
      <div className="image-gallery">
        <p>No images yet</p>
      </div>
    )
  }

  return (
    <div className="image-gallery">
      <div className="image-grid">
        {images.map((image, index) => {
          const imageKey = image.filename ?? (image.id ? `image-${image.id}` : `${index}`)
          return (
            <ImageCard
              key={imageKey}
              image={image}
              imageKey={imageKey}
              onOpen={openModal}
            />
          )
        })}
      </div>

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedSources && (
            <img
              src={selectedSources.full}
              srcSet={selectedSources.srcSet}
              sizes="90vw"
              alt={selectedSources.alt || (selectedImage?.filename ?? 'Generated image')}
              loading="eager"
              decoding="async"
              className="w-full rounded-md"
            />
          )}

          {selectedImage?.metadata && (
            <div className="space-y-2 text-sm">
              {selectedImage.metadata.prompt && (
                <div className="space-y-1">
                  <strong className="font-semibold">Prompt:</strong>
                  <p className="text-muted-foreground">{selectedImage.metadata.prompt}</p>
                </div>
              )}
              {selectedImage.metadata.seed && (
                <p><strong>Seed:</strong> {selectedImage.metadata.seed}</p>
              )}
              {selectedImage.metadata.steps && (
                <p><strong>Steps:</strong> {selectedImage.metadata.steps}</p>
              )}
              {selectedImage.metadata.guidance_scale && (
                <p><strong>Guidance Scale:</strong> {selectedImage.metadata.guidance_scale}</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
})

ImageGallery.displayName = 'ImageGallery'

export default ImageGallery
