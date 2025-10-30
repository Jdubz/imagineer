import React, { useState } from 'react'
import { SkeletonImageCard } from './Skeleton'
import type { GeneratedImage } from '../types/models'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { RefreshCw } from 'lucide-react'

interface ImageGridProps {
  images: GeneratedImage[]
  onRefresh: () => Promise<void>
  loading?: boolean
}

const ImageGrid: React.FC<ImageGridProps> = ({ images, onRefresh, loading = false }) => {
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set())

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

  return (
    <Card>
      <CardHeader>
        <div className="grid-header">
          <CardTitle>Generated Images ({loading ? '...' : images.length})</CardTitle>
          <Button
            onClick={handleRefresh}
            variant="outline"
            disabled={isRefreshing || loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
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
            {images.map((image) => (
              <div
                key={image.filename}
                className="image-card"
                onClick={() => openModal(image)}
              >
                <img
                  src={`/api/outputs/${image.filename}`}
                  alt={image.metadata?.prompt || 'Generated image'}
                  loading="lazy"
                  className={loadedImages.has(image.filename) ? 'loaded' : 'loading'}
                  onLoad={() => handleImageLoad(image.filename)}
                />
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
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedImage && (
            <div className="space-y-4">
              <img
                src={`/api/outputs/${selectedImage.filename}`}
                alt={selectedImage.metadata?.prompt || 'Generated image'}
                loading="eager"
                className="w-full rounded-md"
              />

              <div className="space-y-3">
                {selectedImage.metadata?.prompt && (
                  <div className="space-y-1">
                    <strong className="text-sm font-medium">Prompt:</strong>
                    <p className="text-sm text-muted-foreground">{selectedImage.metadata.prompt}</p>
                  </div>
                )}

                {selectedImage.metadata?.negative_prompt && (
                  <div className="space-y-1">
                    <strong className="text-sm font-medium">Negative Prompt:</strong>
                    <p className="text-sm text-muted-foreground">{selectedImage.metadata.negative_prompt}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  {selectedImage.metadata?.seed && (
                    <div className="space-y-1">
                      <strong className="text-sm font-medium">Seed:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.seed}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.steps && (
                    <div className="space-y-1">
                      <strong className="text-sm font-medium">Steps:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.steps}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.guidance_scale && (
                    <div className="space-y-1">
                      <strong className="text-sm font-medium">Guidance:</strong>
                      <p className="text-sm text-muted-foreground">{selectedImage.metadata.guidance_scale}</p>
                    </div>
                  )}

                  {selectedImage.metadata?.width && selectedImage.metadata?.height && (
                    <div className="space-y-1">
                      <strong className="text-sm font-medium">Size:</strong>
                      <p className="text-sm text-muted-foreground">
                        {selectedImage.metadata.width}x{selectedImage.metadata.height}
                      </p>
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <strong className="text-sm font-medium">Filename:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.filename}</p>
                </div>

                {selectedImage.created && (
                  <div className="space-y-1">
                    <strong className="text-sm font-medium">Created:</strong>
                    <p className="text-sm text-muted-foreground">
                      {new Date(selectedImage.created).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}

export default ImageGrid
