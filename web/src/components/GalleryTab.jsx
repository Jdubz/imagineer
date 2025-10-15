import React, { useState } from 'react'
import BatchList from './BatchList'
import ImageGrid from './ImageGrid'
import BatchGallery from './BatchGallery'
import '../styles/GalleryTab.css'

function GalleryTab({ batches, images, onRefreshImages, onRefreshBatches }) {
  const [selectedBatchId, setSelectedBatchId] = useState(null)

  const handleSelectBatch = (batchId) => {
    setSelectedBatchId(batchId)
  }

  const handleBackToList = () => {
    setSelectedBatchId(null)
    onRefreshBatches() // Refresh batches when going back
  }

  return (
    <div className="gallery-tab">
      {selectedBatchId ? (
        <BatchGallery batchId={selectedBatchId} onBack={handleBackToList} />
      ) : (
        <>
          <section className="gallery-section">
            <h2>📁 Batch Sets</h2>
            <BatchList batches={batches} onSelectBatch={handleSelectBatch} />
          </section>

          <section className="gallery-section">
            <h2>🖼️ Recent Images</h2>
            <ImageGrid images={images} onRefresh={onRefreshImages} />
          </section>
        </>
      )}
    </div>
  )
}

export default GalleryTab
