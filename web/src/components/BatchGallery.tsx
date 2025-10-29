import React, { useState, useEffect, useCallback } from 'react'
import { logger } from '../lib/logger'
import type { ImageMetadata } from '../types/models'

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

  // Add Escape key handler for modal
  useEffect(() => {
    if (!selectedImage) return

    const handleEscape = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        closeModal()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [selectedImage])

  if (loading) {
    return (
      <div className="batch-gallery">
        <div className="loading-indicator">
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

      {selectedImage && (
        <div className="modal" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal} aria-label="Close modal">×</button>

            <img
              src={`/api/outputs/${selectedImage.relative_path}`}
              alt={selectedImage.metadata?.prompt || 'Generated image'}
            />

            <div className="modal-info">
              <h3>Image Details</h3>

              {selectedImage.metadata?.prompt && (
                <div className="detail-item">
                  <strong>Prompt:</strong>
                  <p>{selectedImage.metadata.prompt}</p>
                </div>
              )}

              {selectedImage.metadata?.negative_prompt && (
                <div className="detail-item">
                  <strong>Negative Prompt:</strong>
                  <p>{selectedImage.metadata.negative_prompt}</p>
                </div>
              )}

              <div className="detail-grid">
                {selectedImage.metadata?.seed && (
                  <div className="detail-item">
                    <strong>Seed:</strong> {selectedImage.metadata.seed}
                  </div>
                )}

                {selectedImage.metadata?.steps && (
                  <div className="detail-item">
                    <strong>Steps:</strong> {selectedImage.metadata.steps}
                  </div>
                )}

                {selectedImage.metadata?.guidance_scale && (
                  <div className="detail-item">
                    <strong>Guidance:</strong> {selectedImage.metadata.guidance_scale}
                  </div>
                )}

                {selectedImage.metadata?.width && selectedImage.metadata?.height && (
                  <div className="detail-item">
                    <strong>Size:</strong> {selectedImage.metadata.width}x{selectedImage.metadata.height}
                  </div>
                )}
              </div>

              <div className="detail-item">
                <strong>Filename:</strong> {selectedImage.filename}
              </div>

              <div className="detail-item">
                <strong>Created:</strong> {new Date(selectedImage.created).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default BatchGallery
