import React, { useState } from 'react'
import BatchList from './BatchList'
import BatchGallery from './BatchGallery'
import ImageGrid from './ImageGrid'
import { useGallery } from '../contexts/AppContext'
import '../styles/GalleryTab.css'

const GalleryTab: React.FC = () => {
  const { images, batches, loadingImages, loadingBatches, fetchImages, fetchBatches } = useGallery()
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)

  const handleSelectBatch = (batchId: string): void => {
    setSelectedBatchId(batchId)
  }

  const handleBackToList = (): void => {
    setSelectedBatchId(null)
    void fetchBatches()
  }

  return (
    <div className="gallery-tab">
      {selectedBatchId ? (
        <BatchGallery batchId={selectedBatchId} onBack={handleBackToList} />
      ) : (
        <>
          <section className="gallery-section">
            <h2>🖼️ Recent Images</h2>
            <ImageGrid
              images={images}
              onRefresh={fetchImages}
              loading={loadingImages}
            />
          </section>

          <section className="gallery-section">
            <h2>📁 Albums</h2>
            <BatchList
              batches={batches}
              onSelectBatch={handleSelectBatch}
              loading={loadingBatches}
            />
          </section>
        </>
      )}
    </div>
  )
}

export default GalleryTab
