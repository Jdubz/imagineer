import React, { useMemo, useState, useEffect } from 'react'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'

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

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    if (e.target === e.currentTarget) {
      closeModal()
    }
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

      {selectedImage && (
        <div
          className="modal-backdrop"
          data-testid="modal-backdrop"
          onClick={handleBackdropClick}
        >
          <div className="modal-content" role="dialog" aria-modal="true">
            <button
              className="close-button"
              onClick={closeModal}
              aria-label="Close"
            >
              ×
            </button>
            {selectedSources && (
              <img
                src={selectedSources.full}
                srcSet={selectedSources.srcSet}
                sizes="90vw"
                alt={selectedSources.alt || selectedImage.filename}
                className="modal-image"
                loading="eager"
                decoding="async"
              />
            )}
            {selectedImage.metadata && (
              <div className="image-metadata">
                <h3>Image Details</h3>
                {selectedImage.metadata.prompt && (
                  <p><strong>Prompt:</strong> {selectedImage.metadata.prompt}</p>
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
          </div>
        </div>
      )}
    </div>
  )
}

export default ImageGallery
