import React, { useState, useEffect, useMemo } from 'react'
import { SkeletonImageCard } from './Skeleton'
import ImageCard from './common/ImageCard'
import type { GeneratedImage } from '../types/models'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import { useApp } from '../contexts/AppContext'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import '../styles/ImageCard.css'

interface ImageGridProps {
  images: GeneratedImage[]
  onRefresh: () => Promise<void>
  loading?: boolean
}

const ImageGrid: React.FC<ImageGridProps> = ({ images, onRefresh, loading = false }) => {
  const { nsfwPreference } = useApp()
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
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

  useEffect(() => {
    if (selectedImageSources?.full) {
      preloadImage(selectedImageSources.full)
    }
  }, [selectedImageSources?.full])

  const renderFooter = (image: GeneratedImage) => {
    const prompt = image.metadata?.prompt ?? ''
    const createdDate = image.created ? new Date(image.created).toLocaleDateString() : null
    const hasPrompt = prompt.length > 0
    const truncatedPrompt = hasPrompt && prompt.length > 60 ? `${prompt.substring(0, 60)}...` : prompt
    const metaItems = createdDate ? [createdDate] : []

    if (!hasPrompt && metaItems.length === 0) {
      return null
    }

    return (
      <div className="gallery-card-footer">
        {hasPrompt && (
          <p className="gallery-card-prompt" title={prompt}>
            {truncatedPrompt}
          </p>
        )}
        {metaItems.length > 0 && (
          <div className="gallery-card-meta">
            {metaItems.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

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
          {images.map((image, index) => {
            const isNsfw = image.is_nsfw === true
            if (isNsfw && nsfwPreference === 'hide') {
              return null
            }

            const imageKey =
              image.filename ??
              (image.id ? `image-${image.id}` : image.relative_path ?? image.thumbnail_url ?? `image-${index}`)
            const labelCount = image.labels?.length ?? 0

            return (
              <div key={imageKey} className="gallery-grid-item">
                <ImageCard
                  image={image}
                  nsfwPreference={nsfwPreference}
                  onImageClick={openModal}
                  labelCount={labelCount}
                  showLabelBadge={labelCount > 0}
                  showPrompt={false}
                />
                {renderFooter(image)}
              </div>
            )
          })}
        </div>
      )}

      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedImageSources && (
            <img
              src={selectedImageSources.full}
              srcSet={selectedImageSources.srcSet}
              sizes="100vw"
              alt={selectedImageSources.alt || 'Generated image'}
              loading="eager"
              decoding="async"
              className="w-full rounded-md"
            />
          )}

          {selectedImage && (
            <div className="space-y-3">
              {selectedImage.metadata?.prompt && (
                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Prompt:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.metadata.prompt}</p>
                </div>
              )}

              {selectedImage.metadata?.negative_prompt && (
                <div className="space-y-1">
                  <strong className="text-sm font-semibold">Negative Prompt:</strong>
                  <p className="text-sm text-muted-foreground">{selectedImage.metadata.negative_prompt}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-sm">
                {selectedImage.metadata?.seed && (
                  <div>
                    <strong>Seed:</strong> {selectedImage.metadata.seed}
                  </div>
                )}

                {selectedImage.metadata?.steps && (
                  <div>
                    <strong>Steps:</strong> {selectedImage.metadata.steps}
                  </div>
                )}

                {selectedImage.metadata?.guidance_scale && (
                  <div>
                    <strong>Guidance:</strong> {selectedImage.metadata.guidance_scale}
                  </div>
                )}

                {selectedImage.metadata?.width && selectedImage.metadata?.height && (
                  <div>
                    <strong>Size:</strong> {selectedImage.metadata.width}x{selectedImage.metadata.height}
                  </div>
                )}
              </div>

              <div className="text-sm">
                <strong>Filename:</strong> {selectedImage.filename}
              </div>

              {selectedImage.created && (
                <div className="text-sm">
                  <strong>Created:</strong> {new Date(selectedImage.created).toLocaleString()}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ImageGrid
