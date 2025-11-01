import React, { useState, useEffect, useCallback, useMemo, memo } from 'react'
import { logger } from '../lib/logger'
import type { GeneratedImage, ImageMetadata } from '../types/models'
import ImageCard from './common/ImageCard'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import { api } from '@/lib/api'
import { useApp } from '../contexts/AppContext'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import '../styles/ImageCard.css'

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

const isBatchImageNsfw = (image: BatchImage): boolean =>
  image.metadata?.nsfw === true ||
  image.metadata?.is_nsfw === true ||
  (image as { is_nsfw?: boolean }).is_nsfw === true

const toGeneratedImage = (image: BatchImage): GeneratedImage => ({
  filename: image.filename,
  relative_path: image.relative_path,
  metadata: image.metadata,
  download_url: `/api/outputs/${image.relative_path}`,
  created: image.created,
  is_nsfw: isBatchImageNsfw(image),
})

const renderFooter = (image: BatchImage) => {
  const prompt = image.metadata?.prompt ?? ''
  const hasPrompt = prompt.length > 0
  const truncatedPrompt = hasPrompt && prompt.length > 60 ? `${prompt.substring(0, 60)}...` : prompt
  const steps = image.metadata?.steps
  const seed = image.metadata?.seed
  const hasMeta = steps != null || seed != null

  if (!hasPrompt && !hasMeta) {
    return null
  }

  return (
    <div className="gallery-card-footer">
      {hasPrompt && (
        <p className="gallery-card-prompt" title={prompt}>
          {truncatedPrompt}
        </p>
      )}
      {hasMeta && (
        <div className="gallery-card-meta">
          {steps != null && <span>Steps: {steps}</span>}
          {seed != null && <span>Seed: {seed}</span>}
        </div>
      )}
    </div>
  )
}

const BatchGallery: React.FC<BatchGalleryProps> = memo(({ batchId, onBack }) => {
  const [batch, setBatch] = useState<BatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedImage, setSelectedImage] = useState<BatchImage | null>(null)
  const { nsfwPreference } = useApp()

  const selectedGeneratedImage = useMemo<GeneratedImage | null>(() => {
    if (!selectedImage) {
      return null
    }

    return toGeneratedImage(selectedImage)
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
      const data = await api.batches.getById(batchId)
      setBatch(data)
    } catch (error) {
      logger.error('Failed to fetch batch:', error as Error)
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
            const isNsfw = isBatchImageNsfw(image)
            if (isNsfw && nsfwPreference === 'hide') {
              return null
            }

            const generatedImage = toGeneratedImage(image)
            const labelCount = generatedImage.labels?.length ?? 0

            return (
              <div key={imageKey} className="gallery-grid-item">
                <ImageCard
                  image={generatedImage}
                  nsfwPreference={nsfwPreference}
                  onImageClick={() => openModal(image)}
                  showPrompt={false}
                  labelCount={labelCount}
                  showLabelBadge={labelCount > 0}
                />
                {renderFooter(image)}
              </div>
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
