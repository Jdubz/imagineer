import React, { useState, useEffect, useMemo } from 'react'
import FocusLock from 'react-focus-lock'
import { SkeletonImageCard } from './Skeleton'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'

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

      {selectedImage && (
        <div className="modal" onClick={closeModal}>
          <FocusLock returnFocus>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close" onClick={closeModal} aria-label="Close modal">×</button>

            {selectedImageSources && (
              <img
                src={selectedImageSources.full}
                srcSet={selectedImageSources.srcSet}
                sizes="100vw"
                alt={selectedImageSources.alt || 'Generated image'}
                loading="eager"
                decoding="async"
              />
            )}

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

              {selectedImage.created && (
                <div className="detail-item">
                  <strong>Created:</strong> {new Date(selectedImage.created).toLocaleString()}
                </div>
              )}
            </div>
            </div>
          </FocusLock>
        </div>
      )}
    </div>
  )
}

export default ImageGrid
