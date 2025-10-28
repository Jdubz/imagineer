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
}

const GalleryTab: React.FC<GalleryTabProps> = ({
  batches,
  images,
  onRefreshImages,
  onRefreshBatches,
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
