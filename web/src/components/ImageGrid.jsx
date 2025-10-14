import React, { useState } from 'react'

function ImageGrid({ images, onRefresh }) {
  const [selectedImage, setSelectedImage] = useState(null)

  const openModal = (image) => {
    setSelectedImage(image)
  }

  const closeModal = () => {
    setSelectedImage(null)
  }

  return (
    <div className="image-grid-container">
      <div className="grid-header">
        <h2>Generated Images ({images.length})</h2>
        <button onClick={onRefresh} className="refresh-btn">
          Refresh
        </button>
      </div>

      {images.length === 0 ? (
        <div className="no-images">
          <p>No images generated yet.</p>
          <p>Use the form above to create your first image!</p>
        </div>
      ) : (
        <div className="image-grid">
          {images.map((image, index) => (
            <div
              key={index}
              className="image-card"
              onClick={() => openModal(image)}
            >
              <img
                src={`/api/outputs/${image.filename}`}
                alt={image.metadata?.prompt || 'Generated image'}
              />
              <div className="image-overlay">
                <p className="image-prompt">
                  {image.metadata?.prompt?.substring(0, 60)}
                  {image.metadata?.prompt?.length > 60 ? '...' : ''}
                </p>
                <p className="image-date">
                  {new Date(image.created).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedImage && (
        <div className="modal" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>×</button>

            <img
              src={`/api/outputs/${selectedImage.filename}`}
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

export default ImageGrid
