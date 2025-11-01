import React, { useMemo, useState, useEffect, useCallback, memo } from 'react'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import ImageCard from './common/ImageCard'
import { useApp } from '../contexts/AppContext'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface ImageGalleryProps {
  images?: GeneratedImage[]
}

const ImageGallery: React.FC<ImageGalleryProps> = memo(({ images = [] }) => {
  const { nsfwEnabled } = useApp()
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
              hideNsfw={nsfwEnabled}
              onImageClick={openModal}
              showNsfwBadge={true}
              showLabelBadge={false}
              className="gallery-image-card"
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
