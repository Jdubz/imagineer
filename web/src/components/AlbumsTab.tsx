import React, { useState, useEffect } from 'react'
import '../styles/AlbumsTab.css'
import LabelingPanel from './LabelingPanel'
import { logger } from '../lib/logger'
import { useAlbumDetailState } from '../hooks/useAlbumDetailState'
import type { Label, LabelAnalytics } from '../types/models'

interface AlbumImage {
  id: number
  filename: string
  thumbnail_path?: string | null
  is_nsfw?: boolean
  labels?: Label[]
  label_count?: number
  manual_label_count?: number
}

interface Album {
  id: string
  name: string
  description?: string
  image_count: number
  album_type?: string
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
}

const AlbumsTab: React.FC<AlbumsTabProps> = ({ isAdmin }) => {
  const [albums, setAlbums] = useState<Album[]>([])
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState<boolean>(false)
  const [albumAnalytics, setAlbumAnalytics] = useState<LabelAnalytics | null>(null)

  useEffect(() => {
    fetchAlbums()
  }, [])

  const fetchAlbums = async (): Promise<void> => {
    try {
      const response = await fetch('/api/albums')
      const data = await response.json()
      const rawAlbums = data.albums || data
      const normalizedAlbums = Array.isArray(rawAlbums)
        ? rawAlbums.map((album: Album & { id: string | number }) => ({
            ...album,
            id: String(album.id),
          }))
        : []
      setAlbums(normalizedAlbums)
    } catch (error) {
      logger.error('Failed to fetch albums:', error)
    }
  }

  const fetchAlbumAnalytics = async (albumId: string): Promise<LabelAnalytics | null> => {
    if (!isAdmin) return null

    try {
      const response = await fetch(`/api/albums/${albumId}/labeling/analytics`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch analytics (status ${response.status})`)
      }

      const analytics = (await response.json()) as LabelAnalytics
      setAlbumAnalytics(analytics)
      return analytics
    } catch (error) {
      logger.error('Failed to fetch album analytics:', error)
      setAlbumAnalytics(null)
      return null
    }
  }

  const loadAlbum = async (albumId: string): Promise<Album | null> => {
    try {
      const includeParam = isAdmin ? '?include_labels=1' : ''
      const response = await fetch(`/api/albums/${albumId}${includeParam}`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch album (status ${response.status})`)
      }

      const data = (await response.json()) as RawAlbum

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
      logger.error('Failed to fetch album details:', error)
      setAlbumAnalytics(null)
      return null
    }
  }

  const selectAlbum = async (albumId: string): Promise<void> => {
    await loadAlbum(albumId)
  }

  const createAlbum = async (name: string, description: string, albumType = 'manual'): Promise<void> => {
    if (!isAdmin) return

    try {
      const response = await fetch('/api/albums', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name,
          description,
          album_type: albumType,
          is_public: true
        })
      })

      if (response.ok) {
        fetchAlbums()
        setShowCreateDialog(false)
      } else {
        const error = (await response.json()) as { error?: string }
        alert('Failed to create album: ' + (error.error ?? 'Unknown error'))
      }
    } catch (error) {
      logger.error('Failed to create album:', error)
      alert('Error creating album')
    }
  }

  const deleteAlbum = async (albumId: string): Promise<void> => {
    if (!isAdmin) return

    if (!window.confirm('Are you sure you want to delete this album?')) return

    try {
      const response = await fetch(`/api/albums/${albumId}`, {
        method: 'DELETE',
        credentials: 'include'
      })

      if (response.ok) {
        fetchAlbums()
        if (selectedAlbum?.id === albumId) {
          setSelectedAlbum(null)
          setAlbumAnalytics(null)
        }
      } else {
        const error = await response.json()
        alert('Failed to delete album: ' + error.error)
      }
    } catch (error) {
      logger.error('Failed to delete album:', error)
      alert('Error deleting album')
    }
  }

  if (selectedAlbum) {
    return (
      <AlbumDetailView
        album={selectedAlbum}
        onBack={() => setSelectedAlbum(null)}
        isAdmin={isAdmin}
        onDelete={deleteAlbum}
        onRefresh={() => loadAlbum(String(selectedAlbum.id))}
        analytics={albumAnalytics}
        onRefreshAnalytics={async () => {
          await fetchAlbumAnalytics(String(selectedAlbum.id))
        }}
      />
    )
  }

  return (
    <div className="albums-tab">
      <div className="albums-header">
        <h2>Albums</h2>
        {isAdmin && (
          <button
            className="create-album-btn"
            onClick={() => setShowCreateDialog(true)}
          >
            Create Album
          </button>
        )}
      </div>

      <div className="albums-grid">
        {albums.map(album => (
          <div
            key={album.id}
            className="album-card"
            onClick={() => selectAlbum(album.id)}
          >
            <div className="album-cover">
              {album.images && album.images.length > 0 ? (
                <img
                  src={`/api/images/${album.images[0].id}/thumbnail`}
                  alt={album.name}
                />
              ) : (
                <div className="album-placeholder">
                  {album.image_count || 0} images
                </div>
              )}
            </div>

            <div className="album-info">
              <h3>{album.name}</h3>
              <p>{album.description || 'No description'}</p>
              <div className="album-meta">
                <span>{album.image_count || 0} images</span>
                <span className="album-type">{album.album_type || 'manual'}</span>
                {isAdmin && (
                  <button
                    className="delete-album-btn"
                    onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                      e.stopPropagation()
                      deleteAlbum(album.id)
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {albums.length === 0 && (
        <div className="empty-state">
          <p>No albums yet. {isAdmin ? 'Create your first album!' : 'Albums will appear here.'}</p>
        </div>
      )}

      {showCreateDialog && (
        <CreateAlbumDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={createAlbum}
        />
      )}
    </div>
  )
}

interface AlbumDetailViewProps {
  album: Album
  onBack: () => void
  isAdmin: boolean
  onDelete: (albumId: string) => void
  onRefresh: () => Promise<Album | null>
  analytics: LabelAnalytics | null
  onRefreshAnalytics: () => Promise<void>
}

const AlbumDetailView: React.FC<AlbumDetailViewProps> = ({
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
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              actions.setNsfwSetting(e.target.value as 'hide' | 'blur' | 'show')
            }
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
            onComplete={async () => {
              await onRefresh()
              await onRefreshAnalytics()
            }}
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

          return (
            <div
              key={image.id}
              className={`image-card ${image.is_nsfw ? 'nsfw' : ''} ${nsfwSetting}`}
              onClick={() => isAdmin && actions.toggleImageSelection(image.id)}
            >
              {isAdmin && (
                <input
                  type="checkbox"
                  checked={selectedImages.has(imageKey)}
                  onChange={() => actions.toggleImageSelection(image.id)}
                  className="image-checkbox"
                />
              )}

              <img
                src={`/api/images/${image.id}/thumbnail`}
                alt={image.filename}
                className={image.is_nsfw && nsfwSetting === 'blur' ? 'blurred' : ''}
              />

              {image.is_nsfw && <div className="nsfw-badge">18+</div>}

              {labels.length > 0 && <div className="has-labels-badge">🏷️</div>}

              {isAdmin && (
                <>
                  <LabelingPanel
                    imageId={image.id}
                    onComplete={async () => {
                      await onRefresh()
                      await onRefreshAnalytics()
                    }}
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
                                      onClick={() => actions.startEditingLabel(image.id, label)}
                                      disabled={state.loadingStates.editingLabel}
                                    >
                                      Edit
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => actions.deleteLabel(image.id, label.id)}
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
                      onSubmit={(event) => {
                        event.preventDefault()
                        void actions.addLabel(image.id)
                      }}
                    >
                      <input
                        type="text"
                        placeholder="Add manual tag"
                        value={inputValue}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                          actions.updateLabelInput(image.id, e.target.value)
                        }
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
}

interface CreateAlbumDialogProps {
  onClose: () => void
  onCreate: (name: string, description: string, albumType: string) => void
}

const CreateAlbumDialog: React.FC<CreateAlbumDialogProps> = ({ onClose, onCreate }) => {
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [albumType, setAlbumType] = useState<string>('manual')

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (!name.trim()) return

    onCreate(name.trim(), description.trim(), albumType)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
        <h2>Create Album</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="album-name">Album Name:</label>
            <input
              id="album-name"
              type="text"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              placeholder="Enter album name"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="album-description">Description:</label>
            <textarea
              id="album-description"
              value={description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
              placeholder="Enter album description (optional)"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="album-type">Album Type:</label>
            <select id="album-type" value={albumType} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setAlbumType(e.target.value)}>
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
}

export default AlbumsTab
