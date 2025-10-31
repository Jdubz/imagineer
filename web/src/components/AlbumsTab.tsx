import React, { useState, useCallback, useMemo, memo } from 'react'
import '../styles/AlbumsTab.css'
import LabelingPanel from './LabelingPanel'
import { logger } from '../lib/logger'
import { resolveImageSources, preloadImage } from '../lib/imageSources'
import { api, type GenerateBatchParams, type GenerateBatchSuccess } from '../lib/api'
import { useToast } from '../hooks/useToast'
import { useAbortableEffect } from '../hooks/useAbortableEffect'
import { useAlbumDetailState } from '../hooks/useAlbumDetailState'
import type { Album as SharedAlbum, Label, LabelAnalytics, GeneratedImage } from '../types/models'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface AlbumImage {
  id: number
  filename: string
  thumbnail_path?: string | null
  is_nsfw?: boolean
  labels?: Label[]
  label_count?: number
  manual_label_count?: number
}

type Album = SharedAlbum & {
  images?: AlbumImage[]
}

interface AlbumsTabProps {
  isAdmin: boolean
}

interface RawLabel {
  id: number | string
  image_id: number | string
  label_text: string
  label_type?: string | null
  confidence?: number | null
  source_model?: string | null
  source_prompt?: string | null
  created_by?: string | null
  created_at?: string | null
}

interface RawAlbumImage {
  id: number | string
  filename: string
  thumbnail_path?: string | null
  is_nsfw?: boolean
  labels?: RawLabel[]
  label_count?: number
  manual_label_count?: number
}

interface RawAlbum {
  id: number | string
  name: string
  description?: string
  album_type?: string
  image_count?: number
  images?: RawAlbumImage[]
  created_at?: string
  updated_at?: string
  is_set_template?: boolean
  csv_data?: string
  base_prompt?: string
  prompt_template?: string
  style_suffix?: string
  example_theme?: string
  lora_config?: string
  template_item_count?: number
  generation_prompt?: string
  generation_config?: string
}

type AlbumFilter = 'all' | 'sets' | 'regular'

const AlbumsTab: React.FC<AlbumsTabProps> = memo(({ isAdmin }) => {
  const toast = useToast()
  const [albums, setAlbums] = useState<Album[]>([])
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState<boolean>(false)
  const [albumAnalytics, setAlbumAnalytics] = useState<LabelAnalytics | null>(null)
  const [albumFilter, setAlbumFilter] = useState<AlbumFilter>('all')
  const [showBatchDialog, setShowBatchDialog] = useState<Album | null>(null)
  const [deleteConfirmAlbum, setDeleteConfirmAlbum] = useState<string | null>(null)

  const fetchAlbums = useCallback(async (signal?: AbortSignal): Promise<void> => {
    try {
      const rawAlbums = await api.albums.getAll(signal)
      const normalizedAlbums = Array.isArray(rawAlbums)
        ? rawAlbums.map((album: Album & { id: string | number }) => ({
            ...album,
            id: String(album.id),
          }))
        : []
      setAlbums(normalizedAlbums)
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      logger.error('Failed to fetch albums:', error)
    }
  }, [])

  useAbortableEffect((signal) => {
    void fetchAlbums(signal)
  }, [fetchAlbums])

  const fetchAlbumAnalytics = useCallback(async (albumId: string, signal?: AbortSignal): Promise<LabelAnalytics | null> => {
    if (!isAdmin) return null

    try {
      const analytics = await api.albums.getAnalytics(albumId, signal)
      setAlbumAnalytics(analytics)
      return analytics
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return null
      }
      logger.error('Failed to fetch album analytics:', error)
      setAlbumAnalytics(null)
      return null
    }
  }, [isAdmin])

  const loadAlbum = useCallback(async (albumId: string, signal?: AbortSignal): Promise<Album | null> => {
    try {
      const apiData = await api.albums.getById(albumId, isAdmin, signal)
      const data = apiData as RawAlbum

      const normalizedImages: AlbumImage[] = Array.isArray(data.images)
        ? data.images.map((image: RawAlbumImage) => {
            const rawLabels: RawLabel[] = Array.isArray(image.labels) ? image.labels : []
            const labels: Label[] = rawLabels.map((label) => ({
              id: Number(label.id),
              image_id: Number(label.image_id),
              label_text: label.label_text,
              confidence:
                label.confidence === null || typeof label.confidence === 'undefined'
                  ? null
                  : Number(label.confidence),
              label_type: label.label_type ?? null,
              source_model: label.source_model ?? null,
              source_prompt: label.source_prompt ?? null,
              created_by: label.created_by ?? null,
              created_at: label.created_at ?? null,
            }))

            return {
              id: typeof image.id === 'string' ? parseInt(image.id, 10) : image.id,
              filename: image.filename,
              thumbnail_path: image.thumbnail_path ?? null,
              is_nsfw: image.is_nsfw,
              labels,
              label_count:
                typeof image.label_count === 'number' ? image.label_count : labels.length,
              manual_label_count:
                typeof image.manual_label_count === 'number'
                  ? image.manual_label_count
                  : undefined,
            }
          })
        : []

      const normalizedAlbum: Album = {
        id: String(data.id),
        name: data.name,
        description: data.description,
        album_type: data.album_type,
        image_count: data.image_count ?? normalizedImages.length,
        created_at: data.created_at ?? '',
        updated_at: data.updated_at ?? '',
        is_set_template: data.is_set_template,
        csv_data: data.csv_data,
        base_prompt: data.base_prompt,
        prompt_template: data.prompt_template,
        style_suffix: data.style_suffix,
        example_theme: data.example_theme,
        lora_config: data.lora_config,
        template_item_count: data.template_item_count,
        generation_prompt: data.generation_prompt,
        generation_config: data.generation_config,
        images: normalizedImages,
      }

      setSelectedAlbum(normalizedAlbum)

      if (isAdmin) {
        await fetchAlbumAnalytics(String(data.id))
      } else {
        setAlbumAnalytics(null)
      }

      return normalizedAlbum
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return null
      }
      logger.error('Failed to fetch album details:', error)
      setAlbumAnalytics(null)
      return null
    }
  }, [isAdmin, fetchAlbumAnalytics])

  const selectAlbum = useCallback(async (albumId: string): Promise<void> => {
    await loadAlbum(albumId)
  }, [loadAlbum])

  const createAlbum = useCallback(async (name: string, description: string, albumType = 'manual'): Promise<void> => {
    if (!isAdmin) return

    try {
      const result = await api.albums.create(name, description, albumType)

      if (result.success) {
        toast.success('Album created successfully!')
        fetchAlbums()
        setShowCreateDialog(false)
      } else {
        toast.error('Failed to create album: ' + (result.error ?? 'Unknown error'))
      }
    } catch (error) {
      logger.error('Failed to create album:', error)
      toast.error('Error creating album')
    }
  }, [isAdmin, toast, fetchAlbums])

  const deleteAlbum = useCallback((albumId: string): void => {
    if (!isAdmin) return
    setDeleteConfirmAlbum(albumId)
  }, [isAdmin])

  const handleDeleteConfirm = useCallback(async (): Promise<void> => {
    if (!deleteConfirmAlbum) return

    try {
      const result = await api.albums.delete(deleteConfirmAlbum)

      if (result.success) {
        toast.success('Album deleted successfully')
        fetchAlbums()
        if (selectedAlbum?.id === deleteConfirmAlbum) {
          setSelectedAlbum(null)
          setAlbumAnalytics(null)
        }
      } else {
        toast.error('Failed to delete album: ' + (result.error ?? 'Unknown error'))
      }
    } catch (error) {
      logger.error('Failed to delete album:', error)
      toast.error('Error deleting album')
    } finally {
      setDeleteConfirmAlbum(null)
    }
  }, [deleteConfirmAlbum, toast, fetchAlbums, selectedAlbum])

  const handleBatchGenerate = useCallback((album: Album, event: React.MouseEvent): void => {
    event.stopPropagation()
    setShowBatchDialog(album)
  }, [])

  const filteredAlbums = useMemo(() => {
    return albums.filter((album) => {
      if (albumFilter === 'all') return true
      if (albumFilter === 'sets') return album.is_set_template === true
      if (albumFilter === 'regular') return !album.is_set_template
      return true
    })
  }, [albums, albumFilter])

  const handleFilterAll = useCallback(() => setAlbumFilter('all'), [])
  const handleFilterSets = useCallback(() => setAlbumFilter('sets'), [])
  const handleFilterRegular = useCallback(() => setAlbumFilter('regular'), [])
  const handleShowCreateDialog = useCallback(() => setShowCreateDialog(true), [])
  const handleCloseCreateDialog = useCallback(() => setShowCreateDialog(false), [])
  const handleCloseBatchDialog = useCallback(() => setShowBatchDialog(null), [])
  const handleBackToList = useCallback(() => setSelectedAlbum(null), [])

  const handleRefreshAlbum = useCallback(() => {
    if (!selectedAlbum) return Promise.resolve(null)
    return loadAlbum(String(selectedAlbum.id))
  }, [selectedAlbum, loadAlbum])

  const handleRefreshAnalytics = useCallback(async () => {
    if (!selectedAlbum) return
    await fetchAlbumAnalytics(String(selectedAlbum.id))
  }, [selectedAlbum, fetchAlbumAnalytics])

  const handleBatchSuccess = useCallback((result: GenerateBatchSuccess) => {
    setShowBatchDialog(null)
    const suffix = result.batchId ? ` (batch ${result.batchId})` : ''
    toast.success(`${result.message}${suffix}`)
  }, [toast])

  if (selectedAlbum) {
    return (
      <AlbumDetailView
        album={selectedAlbum}
        onBack={handleBackToList}
        isAdmin={isAdmin}
        onDelete={deleteAlbum}
        onRefresh={handleRefreshAlbum}
        analytics={albumAnalytics}
        onRefreshAnalytics={handleRefreshAnalytics}
      />
    )
  }

  return (
    <div className="albums-tab">
      <div className="albums-header">
        <h2>Albums</h2>
        <div className="albums-header-actions">
          <div className="album-filter-buttons">
            <button
              className={`filter-btn ${albumFilter === 'all' ? 'active' : ''}`}
              onClick={handleFilterAll}
            >
              All Albums
            </button>
            <button
              className={`filter-btn ${albumFilter === 'sets' ? 'active' : ''}`}
              onClick={handleFilterSets}
            >
              Set Templates
            </button>
            <button
              className={`filter-btn ${albumFilter === 'regular' ? 'active' : ''}`}
              onClick={handleFilterRegular}
            >
              Regular Albums
            </button>
          </div>
          {isAdmin && (
            <button
              className="create-album-btn"
              onClick={handleShowCreateDialog}
            >
              Create Album
            </button>
          )}
        </div>
      </div>

      <div className="albums-grid">
        {filteredAlbums.map(album => {
          const handleSelectAlbum = () => selectAlbum(album.id)
          const handleDeleteAlbum = (e: React.MouseEvent<HTMLButtonElement>) => {
            e.stopPropagation()
            deleteAlbum(album.id)
          }
          const handleBatchClick = (e: React.MouseEvent<HTMLButtonElement>) => handleBatchGenerate(album, e)
          const coverImage = album.images && album.images.length > 0 ? album.images[0] : null
          const coverGenerated: GeneratedImage | null = coverImage
            ? {
                id: coverImage.id,
                filename: coverImage.filename,
                thumbnail_url: `/api/images/${coverImage.id}/thumbnail`,
                download_url: `/api/images/${coverImage.id}/file`,
              }
            : null
          const coverSources = coverGenerated
            ? resolveImageSources(coverGenerated, { fallbackAlt: album.name })
            : null

          return (
            <div
              key={album.id}
              className="album-card"
              onClick={handleSelectAlbum}
            >
            <div
              className="album-cover"
              onMouseEnter={() => coverSources && preloadImage(coverSources.full)}
              onFocus={() => coverSources && preloadImage(coverSources.full)}
            >
              {coverSources ? (
                <picture>
                  {coverSources.thumbnail.endsWith('.webp') && (
                    <source srcSet={coverSources.srcSet} type="image/webp" />
                  )}
                  <img
                    src={coverSources.thumbnail}
                    srcSet={coverSources.srcSet}
                    sizes="(min-width: 1280px) 20vw, (min-width: 768px) 30vw, 100vw"
                    alt={coverSources.alt || album.name}
                    loading="lazy"
                    decoding="async"
                    className="album-cover-image blur-up"
                  />
                </picture>
              ) : (
                <div className="album-placeholder">
                  {album.image_count || 0} images
                </div>
              )}
            </div>

            <div className="album-info">
              <div className="album-title-row">
                <h3>{album.name}</h3>
                {album.is_set_template && (
                  <span className="set-template-badge">Set Template</span>
                )}
              </div>
              <p>{album.description || 'No description'}</p>
              {album.is_set_template && album.template_item_count && (
                <p className="template-info">{album.template_item_count} template items</p>
              )}
              <div className="album-meta">
                <span>{album.image_count || 0} images</span>
                <span className="album-type">{album.album_type || 'manual'}</span>
              </div>
              {isAdmin && (
                <div className="album-actions">
                  {album.is_set_template && (
                    <button
                      className="generate-batch-btn"
                      onClick={handleBatchClick}
                    >
                      Generate Batch
                    </button>
                  )}
                  <button
                    className="delete-album-btn"
                    onClick={handleDeleteAlbum}
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
          )
        })}
      </div>

      {filteredAlbums.length === 0 && albums.length > 0 && (
        <div className="empty-state">
          <p>No {albumFilter === 'sets' ? 'set template' : albumFilter === 'regular' ? 'regular' : ''} albums found.</p>
        </div>
      )}

      {albums.length === 0 && (
        <div className="empty-state">
          <p>No albums yet. {isAdmin ? 'Create your first album!' : 'Albums will appear here.'}</p>
        </div>
      )}

      {showCreateDialog && (
        <CreateAlbumDialog
          onClose={handleCloseCreateDialog}
          onCreate={createAlbum}
        />
      )}

      {showBatchDialog && (
        <BatchGenerateDialog
          album={showBatchDialog}
          onClose={handleCloseBatchDialog}
          onSuccess={handleBatchSuccess}
        />
      )}

      <AlertDialog open={!!deleteConfirmAlbum} onOpenChange={(open) => !open && setDeleteConfirmAlbum(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Album?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the album and all its images.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
})

AlbumsTab.displayName = 'AlbumsTab'

interface AlbumDetailViewProps {
  album: Album
  onBack: () => void
  isAdmin: boolean
  onDelete: (albumId: string) => void
  onRefresh: () => Promise<Album | null>
  analytics: LabelAnalytics | null
  onRefreshAnalytics: () => Promise<void>
}

const AlbumDetailView: React.FC<AlbumDetailViewProps> = memo(({
  album,
  onBack,
  isAdmin,
  onRefresh,
  analytics,
  onRefreshAnalytics,
}) => {
  // Use the custom hook for state management
  const { state, actions, isLoading } = useAlbumDetailState({
    albumId: album.id,
    initialImages: album.images || [],
    onRefresh,
    onRefreshAnalytics,
  })

  const { images, selectedImages, nsfwSetting, labelInputs, editingLabel, labelError } = state
  const [loadedImages, setLoadedImages] = useState<Set<number>>(new Set())

  const handleImageLoad = useCallback((imageId: number): void => {
    setLoadedImages((prev) => {
      const next = new Set(prev)
      next.add(imageId)
      return next
    })
  }, [])

  const handleNsfwChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    actions.setNsfwSetting(e.target.value as 'hide' | 'blur' | 'show')
  }, [actions])

  const handleLabelingComplete = useCallback(async () => {
    await onRefresh()
    await onRefreshAnalytics()
  }, [onRefresh, onRefreshAnalytics])

  return (
    <div className="album-detail">
      <div className="album-detail-header">
        <button className="back-btn" onClick={onBack}>
          ← Back
        </button>
        <h2>{album.name}</h2>

        <div className="nsfw-filter">
          <label>NSFW:</label>
          <select
            value={nsfwSetting}
            onChange={handleNsfwChange}
          >
            <option value="hide">Hide</option>
            <option value="blur">Blur</option>
            <option value="show">Show</option>
          </select>
        </div>

        {isAdmin && selectedImages.size > 0 && (
          <button className="remove-images-btn" onClick={actions.removeSelectedImages}>
            Remove {selectedImages.size} images
          </button>
        )}
      </div>

      {isAdmin && labelError && <div className="label-error">{labelError}</div>}

      {isAdmin && analytics && (
        <div className="album-analytics">
          <div className="analytics-cards">
            <div className="analytics-card">
              <span className="analytics-label">Images</span>
              <strong>{analytics.image_count}</strong>
            </div>
            <div className="analytics-card">
              <span className="analytics-label">Labeled</span>
              <strong>
                {analytics.images_with_labels}/{analytics.image_count}
              </strong>
              <small>{analytics.coverage.labels_percent}%</small>
            </div>
            <div className="analytics-card">
              <span className="analytics-label">Manual Coverage</span>
              <strong>{analytics.coverage.manual_percent}%</strong>
            </div>
            <div className="analytics-card">
              <span className="analytics-label">Avg. Labels/Image</span>
              <strong>{analytics.average_labels_per_image}</strong>
            </div>
            <div className="analytics-card">
              <span className="analytics-label">Unlabeled</span>
              <strong>{analytics.unlabeled_images}</strong>
            </div>
            {analytics.last_labeled_at && (
              <div className="analytics-card">
                <span className="analytics-label">Last Labeled</span>
                <strong>{new Date(analytics.last_labeled_at).toLocaleString()}</strong>
              </div>
            )}
          </div>

          {analytics.top_tags.length > 0 && (
            <div className="analytics-top-tags">
              <h4>Top Tags</h4>
              <ul>
                {analytics.top_tags.map((tag) => (
                  <li key={tag.label_text}>
                    <span>{tag.label_text}</span>
                    <span className="tag-count">{tag.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {isAdmin && (
        <div className="album-actions">
          <LabelingPanel
            albumId={album.id}
            onComplete={handleLabelingComplete}
          />
        </div>
      )}

      <div className="album-description">
        <p>{album.description || 'No description'}</p>
      </div>

      <div className="album-images-grid">
        {images.map((image) => {
          const labels = image.labels ?? []
          const imageKey = String(image.id)
          const inputValue = labelInputs[image.id] ?? ''
          const activeEdit =
            editingLabel && editingLabel.imageId === image.id ? editingLabel : null

          const handleImageClick = () => isAdmin && actions.toggleImageSelection(image.id)
          const handleToggleSelection = () => actions.toggleImageSelection(image.id)
          const handleImageLoaded = () => handleImageLoad(image.id)
          const handleAddLabelSubmit = (event: React.FormEvent<HTMLFormElement>) => {
            event.preventDefault()
            void actions.addLabel(image.id)
          }
          const handleUpdateLabelInput = (e: React.ChangeEvent<HTMLInputElement>) => {
            actions.updateLabelInput(image.id, e.target.value)
          }
          const generatedImage: GeneratedImage = {
            id: image.id,
            filename: image.filename,
            thumbnail_url: `/api/images/${image.id}/thumbnail`,
            download_url: `/api/images/${image.id}/file`,
            is_nsfw: image.is_nsfw,
          }
          const { thumbnail, full, alt, srcSet } = resolveImageSources(generatedImage, {
            fallbackAlt: image.filename,
          })

          return (
            <div
              key={image.id}
              className={`image-card ${image.is_nsfw ? 'nsfw' : ''} ${nsfwSetting}`}
              onClick={handleImageClick}
              onMouseEnter={() => preloadImage(full)}
              onFocus={() => preloadImage(full)}
            >
              {isAdmin && (
                <input
                  type="checkbox"
                  checked={selectedImages.has(imageKey)}
                  onChange={handleToggleSelection}
                  className="image-checkbox"
                />
              )}

              <picture className="image-picture">
                {thumbnail.endsWith('.webp') && (
                  <source srcSet={srcSet} type="image/webp" />
                )}
                <img
                  src={thumbnail}
                  srcSet={srcSet}
                  sizes="(min-width: 1280px) 20vw, (min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw"
                  alt={alt || image.filename}
                  loading="lazy"
                  decoding="async"
                  className={`preview-image ${loadedImages.has(image.id) ? 'loaded' : 'loading'} ${image.is_nsfw && nsfwSetting === 'blur' ? 'blurred' : ''}`}
                  onLoad={handleImageLoaded}
                />
              </picture>

              {image.is_nsfw && <div className="nsfw-badge">18+</div>}

              {labels.length > 0 && <div className="has-labels-badge">🏷️</div>}

              {isAdmin && (
                <>
                  <LabelingPanel
                    imageId={image.id}
                    onComplete={handleLabelingComplete}
                    variant="compact"
                  />

                  <div className="label-editor">
                    <div className="label-chip-list">
                      {labels.length === 0 && <span className="label-empty">No labels yet.</span>}
                      {labels.map((label) => {
                        const isEditing = activeEdit && activeEdit.labelId === label.id
                        const labelType = (label.label_type || 'unknown').toLowerCase()
                        const isCaption = labelType === 'caption'
                        const isDeletingThisLabel = isLoading.deletingLabel(image.id, label.id)

                        const handleStartEdit = () => actions.startEditingLabel(image.id, label)
                        const handleDeleteLabel = () => actions.deleteLabel(image.id, label.id)

                        return (
                          <div
                            key={label.id}
                            className={`label-chip label-type-${labelType} ${isEditing ? 'editing' : ''}`}
                          >
                            {isEditing ? (
                              <>
                                <input
                                  type="text"
                                  value={activeEdit?.value ?? ''}
                                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                    actions.updateEditingLabel(e.target.value)
                                  }
                                  disabled={state.loadingStates.editingLabel}
                                />
                                <div className="label-chip-actions">
                                  <button
                                    type="button"
                                    onClick={actions.saveEditedLabel}
                                    disabled={state.loadingStates.editingLabel || !(activeEdit?.value ?? '').trim()}
                                  >
                                    {state.loadingStates.editingLabel ? 'Saving...' : 'Save'}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={actions.cancelEditingLabel}
                                    disabled={state.loadingStates.editingLabel}
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </>
                            ) : (
                              <>
                                <span>{label.label_text}</span>
                                <div className="label-chip-actions">
                                  {!isCaption && (
                                    <button
                                      type="button"
                                      onClick={handleStartEdit}
                                      disabled={state.loadingStates.editingLabel}
                                    >
                                      Edit
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={handleDeleteLabel}
                                    disabled={isDeletingThisLabel}
                                  >
                                    {isDeletingThisLabel ? 'Removing...' : 'Remove'}
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        )
                      })}
                    </div>

                    <form
                      className="label-add-form"
                      onSubmit={handleAddLabelSubmit}
                    >
                      <input
                        type="text"
                        placeholder="Add manual tag"
                        value={inputValue}
                        onChange={handleUpdateLabelInput}
                        disabled={isLoading.addingLabel(image.id)}
                      />
                      <button
                        type="submit"
                        disabled={isLoading.addingLabel(image.id) || !inputValue.trim()}
                      >
                        {isLoading.addingLabel(image.id) ? 'Adding...' : 'Add'}
                      </button>
                    </form>
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>

      {images.length === 0 && (
        <div className="empty-album">
          <p>This album is empty.</p>
        </div>
      )}
    </div>
  )
})

AlbumDetailView.displayName = 'AlbumDetailView'

interface BatchGenerateDialogProps {
  album: Album
  onClose: () => void
  onSuccess: (result: GenerateBatchSuccess) => void
}

const BatchGenerateDialog: React.FC<BatchGenerateDialogProps> = memo(({ album, onClose, onSuccess }) => {
  const toast = useToast()
  const [userTheme, setUserTheme] = useState<string>('')
  const [steps, setSteps] = useState<string>('')
  const [seed, setSeed] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  const handleUserThemeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setUserTheme(e.target.value)
  }, [])

  const handleStepsChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSteps(e.target.value)
  }, [])

  const handleSeedChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSeed(e.target.value)
  }, [])

  const handleOverlayClick = useCallback(() => {
    onClose()
  }, [onClose])

  const handleDialogClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation()
  }, [])

  const handleSubmit = useCallback(async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    if (!userTheme.trim()) {
      toast.error('User theme is required')
      return
    }

    setIsSubmitting(true)

    try {
      const params: GenerateBatchParams = {
        user_theme: userTheme.trim(),
      }

      if (steps) {
        const stepsNum = parseInt(steps, 10)
        if (!isNaN(stepsNum)) params.steps = stepsNum
      }

      if (seed) {
        const seedNum = parseInt(seed, 10)
        if (!isNaN(seedNum)) params.seed = seedNum
      }

      const result = await api.albums.generateBatch(album.id, params)

      if (result.success) {
        onSuccess(result)
      } else {
        toast.error(result.error)
      }
    } catch (error) {
      logger.error('Failed to generate batch:', error)
      toast.error('Error starting batch generation')
    } finally {
      setIsSubmitting(false)
    }
  }, [userTheme, steps, seed, album.id, toast, onSuccess])

  return (
    <div className="dialog-overlay" onClick={handleOverlayClick}>
      <div className="dialog" onClick={handleDialogClick}>
        <h2>Generate Batch: {album.name}</h2>
        <p className="dialog-description">
          Generate {album.template_item_count || 0} images using this set template
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="user-theme">Art Style Theme (required):</label>
            <input
              id="user-theme"
              type="text"
              value={userTheme}
              onChange={handleUserThemeChange}
              placeholder={album.example_theme || "e.g., gothic style with ravens"}
              required
              disabled={isSubmitting}
            />
            {album.example_theme && (
              <small className="form-hint">Example: {album.example_theme}</small>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="steps">Steps (optional):</label>
            <input
              id="steps"
              type="number"
              value={steps}
              onChange={handleStepsChange}
              placeholder="Leave empty to use album defaults"
              min="1"
              max="150"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="seed">Seed (optional):</label>
            <input
              id="seed"
              type="number"
              value={seed}
              onChange={handleSeedChange}
              placeholder="Random seed for reproducibility"
              min="0"
              max="2147483647"
              disabled={isSubmitting}
            />
          </div>

          <div className="dialog-actions">
            <button type="submit" disabled={isSubmitting || !userTheme.trim()}>
              {isSubmitting ? 'Starting...' : 'Start Generation'}
            </button>
            <button type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
})

BatchGenerateDialog.displayName = 'BatchGenerateDialog'

interface CreateAlbumDialogProps {
  onClose: () => void
  onCreate: (name: string, description: string, albumType: string) => void
}

const CreateAlbumDialog: React.FC<CreateAlbumDialogProps> = memo(({ onClose, onCreate }) => {
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [albumType, setAlbumType] = useState<string>('manual')

  const handleNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setName(e.target.value)
  }, [])

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDescription(e.target.value)
  }, [])

  const handleAlbumTypeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setAlbumType(e.target.value)
  }, [])

  const handleOverlayClick = useCallback(() => {
    onClose()
  }, [onClose])

  const handleDialogClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation()
  }, [])

  const handleSubmit = useCallback((e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (!name.trim()) return

    onCreate(name.trim(), description.trim(), albumType)
  }, [name, description, albumType, onCreate])

  return (
    <div className="dialog-overlay" onClick={handleOverlayClick}>
      <div className="dialog" onClick={handleDialogClick}>
        <h2>Create Album</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="album-name">Album Name:</label>
            <input
              id="album-name"
              type="text"
              value={name}
              onChange={handleNameChange}
              placeholder="Enter album name"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="album-description">Description:</label>
            <textarea
              id="album-description"
              value={description}
              onChange={handleDescriptionChange}
              placeholder="Enter album description (optional)"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="album-type">Album Type:</label>
            <select id="album-type" value={albumType} onChange={handleAlbumTypeChange}>
              <option value="manual">Manual Collection</option>
              <option value="batch">Generated Batch</option>
              <option value="set">CSV Set</option>
            </select>
          </div>

          <div className="dialog-actions">
            <button type="submit">Create Album</button>
            <button type="button" onClick={onClose}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
})

CreateAlbumDialog.displayName = 'CreateAlbumDialog'

export default AlbumsTab
