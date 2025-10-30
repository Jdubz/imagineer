import React, { useState, useEffect, useCallback } from 'react'
import { logger } from '../lib/logger'
import type { ImageMetadata } from '../types/models'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
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

const BatchGallery: React.FC<BatchGalleryProps> = ({ batchId, onBack }) => {
  const [batch, setBatch] = useState<BatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedImage, setSelectedImage] = useState<BatchImage | null>(null)
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set())

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

  const openModal = (image: BatchImage): void => {
    setSelectedImage(image)
  }

  const closeModal = (): void => {
    setSelectedImage(null)
  }

  const handleImageLoad = (filename: string): void => {
    setLoadedImages((prev) => new Set(prev).add(filename))
  }

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
        <Button onClick={onBack} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Gallery
        </Button>
        <p>Batch not found</p>
      </div>
    )
  }

  return (
    <div className="batch-gallery">
      <div className="batch-header">
        <Button onClick={onBack} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Gallery
        </Button>
        <h2>{batch.batch_id}</h2>
        <p className="batch-info">{batch.image_count} images</p>
      </div>

      <div className="image-grid">
        {batch.images && batch.images.length > 0 ? (
          batch.images.map((image, index) => (
            <div
              key={index}
              className="image-card"
              onClick={() => openModal(image)}
            >
              <img
                src={`/api/outputs/${image.relative_path}`}
                alt={image.metadata?.prompt || 'Generated image'}
                loading="lazy"
                className={loadedImages.has(image.relative_path) ? 'loaded' : 'loading'}
                onLoad={() => handleImageLoad(image.relative_path)}
              />
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
          ))
        ) : (
          <p>No images in this batch yet</p>
        )}
      </div>

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>
          {selectedImage && (
            <div className="space-y-4">
              <img
                src={`/api/outputs/${selectedImage.relative_path}`}
                alt={selectedImage.metadata?.prompt || 'Generated image'}
                loading="eager"
                className="w-full rounded-md"
              />

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

                <div className="grid grid-cols-2 gap-3">
                  {selectedImage.metadata?.seed && (
                    <div className="space-y-1">
                      <strong className="text-sm font-semibold">Seed:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.seed}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.steps && (
                    <div className="space-y-1">
                      <strong className="text-sm font-semibold">Steps:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.steps}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.guidance_scale && (
                    <div className="space-y-1">
                      <strong className="text-sm font-semibold">Guidance:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.guidance_scale}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.width && selectedImage.metadata?.height && (
                    <div className="space-y-1">
                      <strong className="text-sm font-semibold">Size:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.width}x{selectedImage.metadata.height}</p>
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Filename:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.filename}</p>
                </div>

                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Created:</strong>
                  <p className="text-sm text-muted-foreground">{new Date(selectedImage.created).toLocaleString()}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default BatchGallery
