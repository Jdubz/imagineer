import React, { useState } from 'react'
import { ImageIcon, FolderOpen } from 'lucide-react'
import BatchList from './BatchList'
import BatchGallery from './BatchGallery'
import ImageGrid from './ImageGrid'
import { useGallery } from '../contexts/AppContext'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

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
    <div className="flex flex-col gap-8">
      {selectedBatchId ? (
        <BatchGallery batchId={selectedBatchId} onBack={handleBackToList} />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ImageIcon className="h-5 w-5" />
                Recent Images
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ImageGrid
                images={images}
                onRefresh={fetchImages}
                loading={loadingImages}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                Albums
              </CardTitle>
            </CardHeader>
            <CardContent>
              <BatchList
                batches={batches}
                onSelectBatch={handleSelectBatch}
                loading={loadingBatches}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

export default GalleryTab
