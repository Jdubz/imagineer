import React, { useMemo, useState, useEffect } from 'react'
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

const ImageGallery: React.FC<ImageGalleryProps> = ({ images = [] }) => {
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

  if (images.length === 0) {
    return (
      <div className="image-gallery">
        <p>No images yet</p>
      </div>
    )
  }

  const openModal = (image: GeneratedImage): void => {
    setSelectedImage(image)
  }

  const closeModal = (): void => {
    setSelectedImage(null)
  }

  return (
    <div className="image-gallery">
      <div className="image-grid">
        {images.map((image, index) => {
          const { thumbnail, full, alt, srcSet } = resolveImageSources(image)
          const imageKey = image.filename ?? (image.id ? `image-${image.id}` : `${index}`)

          return (
            <div key={imageKey} className="image-item" onMouseEnter={() => preloadImage(full)}>
              <picture>
                {thumbnail.endsWith('.webp') && <source srcSet={srcSet} type="image/webp" />}
                <img
                  src={thumbnail}
                  srcSet={srcSet}
                  sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw"
                  alt={alt || image.filename}
                  loading="lazy"
                  decoding="async"
                  onClick={() => openModal(image)}
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
}

export default ImageGallery
