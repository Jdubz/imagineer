import React, { useState } from 'react'

function ImageGallery({ images = [] }) {
  const [selectedImage, setSelectedImage] = useState(null)

  if (images.length === 0) {
    return (
      <div className="image-gallery">
        <p>No images yet</p>
      </div>
    )
  }

  const openModal = (image) => {
    setSelectedImage(image)
  }

  const closeModal = () => {
    setSelectedImage(null)
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      closeModal()
    }
  }

  return (
    <div className="image-gallery">
      <div className="image-grid">
        {images.map((image, index) => (
          <div key={index} className="image-item">
            <img
              src={`/api${image.path}`}
              alt={image.metadata?.prompt || image.filename}
              loading="lazy"
              onClick={() => openModal(image)}
              className="gallery-image"
            />
            <div className="image-prompt">
              {image.metadata?.prompt ? (
                <p>{image.metadata.prompt.length > 50 
                  ? `${image.metadata.prompt.substring(0, 50)}...` 
                  : image.metadata.prompt}</p>
              ) : null}
            </div>
          </div>
        ))}
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
            <img 
              src={`/api${selectedImage.path}`} 
              alt={selectedImage.metadata?.prompt || selectedImage.filename}
              className="modal-image"
            />
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