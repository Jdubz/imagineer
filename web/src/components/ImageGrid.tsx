import React, { useState, useEffect, useMemo } from 'react'
import { SkeletonImageCard } from './Skeleton'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface ImageGridProps {
  images: GeneratedImage[]
  onRefresh: () => Promise<void>
  loading?: boolean
}

const ImageGrid: React.FC<ImageGridProps> = ({ images, onRefresh, loading = false }) => {
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set())
  const selectedImageSources = useMemo(
    () => (selectedImage ? resolveImageSources(selectedImage) : null),
    [selectedImage]
  )

  const handleRefresh = async (): Promise<void> => {
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setIsRefreshing(false)
    }
  }

  const openModal = (image: GeneratedImage): void => {
    setSelectedImage(image)
  }

  const closeModal = (): void => {
    setSelectedImage(null)
  }

  const handleImageLoad = (filename: string): void => {
    setLoadedImages((prev) => new Set(prev).add(filename))
  }

  useEffect(() => {
    if (selectedImageSources?.full) {
      preloadImage(selectedImageSources.full)
    }
  }, [selectedImageSources?.full])

  return (
    <div className="image-grid-container">
      <div className="grid-header">
        <h2>Generated Images ({loading ? '...' : images.length})</h2>
        <button
          onClick={handleRefresh}
          className="refresh-btn"
          disabled={isRefreshing || loading}
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {loading ? (
        <div className="image-grid">
          {Array.from({ length: 8 }).map((_, index) => (
            <SkeletonImageCard key={index} />
          ))}
        </div>
      ) : images.length === 0 ? (
        <div className="no-images">
          <p>No images generated yet.</p>
          <p>Use the form above to create your first image!</p>
        </div>
      ) : (
        <div className="image-grid">
          {images.map((image) => {
            const { thumbnail, full, alt, srcSet } = resolveImageSources(image)
            const imageKey = image.filename ?? (image.id ? `image-${image.id}` : thumbnail)

            return (
              <div
                key={imageKey}
                className="image-card"
                onClick={() => openModal(image)}
                onMouseEnter={() => preloadImage(full)}
                onFocus={() => preloadImage(full)}
              >
                <picture className="image-picture">
                  {thumbnail.endsWith('.webp') && (
                    <source srcSet={srcSet} type="image/webp" />
                  )}
                  <img
                    src={thumbnail}
                    srcSet={srcSet}
                    sizes="(min-width: 1280px) 25vw, (min-width: 768px) 33vw, 100vw"
                    alt={alt || 'Generated image'}
                    loading="lazy"
                    decoding="async"
                    className={`preview-image ${loadedImages.has(imageKey) ? 'loaded' : 'loading'}`}
                    onLoad={() => handleImageLoad(imageKey)}
                  />
                </picture>
                <div className="image-overlay">
                  <p className="image-prompt">
                    {image.metadata?.prompt?.substring(0, 60)}
                    {image.metadata?.prompt && image.metadata.prompt.length > 60 ? '...' : ''}
                  </p>
                  {image.created && (
                    <p className="image-date">
                      {new Date(image.created).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedImageSources && (
            <img
              src={selectedImageSources.full}
              srcSet={selectedImageSources.srcSet}
              sizes="100vw"
              alt={selectedImageSources.alt || 'Generated image'}
              loading="eager"
              decoding="async"
              className="w-full rounded-md"
            />
          )}

          {selectedImage && (
            <div className="space-y-3">
              {selectedImage.metadata?.prompt && (
                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Prompt:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.metadata.prompt}</p>
                </div>
              )}

              {selectedImage.metadata?.negative_prompt && (
                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Negative Prompt:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.metadata.negative_prompt}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-sm">
                {selectedImage.metadata?.seed && (
                  <div>
                    <strong>Seed:</strong> {selectedImage.metadata.seed}
                  </div>
                )}

                {selectedImage.metadata?.steps && (
                  <div>
                    <strong>Steps:</strong> {selectedImage.metadata.steps}
                  </div>
                )}

                {selectedImage.metadata?.guidance_scale && (
                  <div>
                    <strong>Guidance:</strong> {selectedImage.metadata.guidance_scale}
                  </div>
                )}

                {selectedImage.metadata?.width && selectedImage.metadata?.height && (
                  <div>
                    <strong>Size:</strong> {selectedImage.metadata.width}x{selectedImage.metadata.height}
                  </div>
                )}
              </div>

              <div className="text-sm">
                <strong>Filename:</strong> {selectedImage.filename}
              </div>

              {selectedImage.created && (
                <div className="text-sm">
                  <strong>Created:</strong> {new Date(selectedImage.created).toLocaleString()}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ImageGrid
