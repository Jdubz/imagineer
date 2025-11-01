import React, { useState, useEffect, useCallback, useMemo, memo } from 'react'
import { logger } from '../lib/logger'
import type { GeneratedImage, ImageMetadata } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface BatchImage {
  filename: string
  relative_path: string
  created: string
  metadata?: ImageMetadata
}

interface BatchData {
  batch_id: string
  image_count: number
  images?: BatchImage[]
}

interface BatchGalleryProps {
  batchId: string
  onBack: () => void
}

// Memoized batch image card component
interface BatchImageCardProps {
  image: BatchImage
  imageKey: string
  onOpen: (image: BatchImage) => void
  onImageLoad: (path: string) => void
  isLoaded: boolean
}

const BatchImageCard = memo<BatchImageCardProps>(({ image, imageKey, onOpen, onImageLoad, isLoaded }) => {
  const generatedImage: GeneratedImage = useMemo(() => ({
    filename: image.filename,
    relative_path: image.relative_path,
    metadata: image.metadata,
    download_url: `/api/outputs/${image.relative_path}`,
  }), [image])

  const { thumbnail, full, alt, srcSet } = useMemo(() =>
    resolveImageSources(generatedImage, {
      fallbackAlt: image.metadata?.prompt || 'Generated image',
    }),
    [generatedImage, image.metadata?.prompt]
  )

  const handleClick = useCallback(() => {
    onOpen(image)
  }, [image, onOpen])

  const handlePreload = useCallback(() => {
    preloadImage(full)
  }, [full])

  const handleLoad = useCallback(() => {
    onImageLoad(image.relative_path)
  }, [image.relative_path, onImageLoad])

  return (
    <div
      key={imageKey}
      className="image-card"
      onClick={handleClick}
      onMouseEnter={handlePreload}
      onFocus={handlePreload}
    >
      <picture className="image-picture">
        {thumbnail.endsWith('.webp') && (
          <source srcSet={srcSet} type="image/webp" />
        )}
        <img
          src={thumbnail}
          srcSet={srcSet}
          sizes="(min-width: 1280px) 25vw, (min-width: 768px) 33vw, 100vw"
          alt={alt}
          loading="lazy"
          decoding="async"
          className={`preview-image ${isLoaded ? 'loaded' : 'loading'}`}
          onLoad={handleLoad}
        />
      </picture>
      <div className="image-info">
        <p className="image-prompt">{image.metadata?.prompt || 'No prompt'}</p>
        {image.metadata && (
          <div className="image-metadata">
            <span>Steps: {image.metadata.steps}</span>
            {image.metadata.seed && <span>Seed: {image.metadata.seed}</span>}
          </div>
        )}
      </div>
    </div>
  )
})

BatchImageCard.displayName = 'BatchImageCard'

const BatchGallery: React.FC<BatchGalleryProps> = memo(({ batchId, onBack }) => {
  const [batch, setBatch] = useState<BatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedImage, setSelectedImage] = useState<BatchImage | null>(null)
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set())

  const selectedGeneratedImage = useMemo<GeneratedImage | null>(() => {
    if (!selectedImage) {
      return null
    }

    return {
      filename: selectedImage.filename,
      relative_path: selectedImage.relative_path,
      metadata: selectedImage.metadata,
      download_url: `/api/outputs/${selectedImage.relative_path}`,
    }
  }, [selectedImage])

  const selectedAlt = selectedImage?.metadata?.prompt || 'Generated image'

  const selectedImageSources = useMemo(
    () =>
      selectedGeneratedImage
        ? resolveImageSources(selectedGeneratedImage, { fallbackAlt: selectedAlt })
        : null,
    [selectedGeneratedImage, selectedAlt]
  )

  useEffect(() => {
    if (selectedImageSources?.full) {
      preloadImage(selectedImageSources.full)
    }
  }, [selectedImageSources?.full])

  const fetchBatch = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/batches/${batchId}`)
      const data = await response.json()
      setBatch(data)
    } catch (error) {
      logger.error('Failed to fetch batch:', error)
    } finally {
      setLoading(false)
    }
  }, [batchId])

  useEffect(() => {
    void fetchBatch()
  }, [fetchBatch])

  const openModal = useCallback((image: BatchImage): void => {
    setSelectedImage(image)
  }, [])

  const closeModal = useCallback((): void => {
    setSelectedImage(null)
  }, [])

  const handleImageLoad = useCallback((filename: string): void => {
    setLoadedImages((prev) => new Set(prev).add(filename))
  }, [])

  if (loading) {
    return (
      <div className="batch-gallery">
        <div className="loading-indicator" role="status" aria-live="polite" aria-atomic="true">
          <div className="spinner"></div>
          <p>Loading batch...</p>
        </div>
      </div>
    )
  }

  if (!batch) {
    return (
      <div className="batch-gallery">
        <button onClick={onBack} className="back-button">← Back to Gallery</button>
        <p>Batch not found</p>
      </div>
    )
  }

  return (
    <div className="batch-gallery">
      <div className="batch-header">
        <button onClick={onBack} className="back-button">← Back to Gallery</button>
        <h2>{batch.batch_id}</h2>
        <p className="batch-info">{batch.image_count} images</p>
      </div>

      <div className="image-grid">
        {batch.images && batch.images.length > 0 ? (
          batch.images.map((image, index) => {
            const imageKey = image.filename || image.relative_path || String(index)
            return (
              <BatchImageCard
                key={imageKey}
                image={image}
                imageKey={imageKey}
                onOpen={openModal}
                onImageLoad={handleImageLoad}
                isLoaded={loadedImages.has(image.relative_path)}
              />
            )
          })
        ) : (
          <p>No images in this batch yet</p>
        )}
      </div>

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedImageSources && (
            <img
              src={selectedImageSources.full}
              srcSet={selectedImageSources.srcSet}
              sizes="90vw"
              alt={selectedImageSources.alt}
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

              <div className="text-sm">
                <strong>Created:</strong> {new Date(selectedImage.created).toLocaleString()}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
})

BatchGallery.displayName = 'BatchGallery'

export default BatchGallery
