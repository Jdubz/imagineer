import React, { useState } from 'react'
import BatchList from './BatchList'
import BatchGallery from './BatchGallery'
import ImageGrid from './ImageGrid'
import type { BatchSummary, GeneratedImage } from '../types/models'
import '../styles/GalleryTab.css'

interface GalleryTabProps {
  batches: BatchSummary[]
  images: GeneratedImage[]
  onRefreshImages: () => Promise<void>
  onRefreshBatches: () => Promise<void>
  loadingImages?: boolean
  loadingBatches?: boolean
}

const GalleryTab: React.FC<GalleryTabProps> = ({
  batches,
  images,
  onRefreshImages,
  onRefreshBatches,
  loadingImages = false,
  loadingBatches = false,
}) => {
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)

  const handleSelectBatch = (batchId: string): void => {
    setSelectedBatchId(batchId)
  }

  const handleBackToList = (): void => {
    setSelectedBatchId(null)
    void onRefreshBatches()
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
              onRefresh={onRefreshImages}
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
