import React, { useState, useEffect } from 'react'
import '../styles/AlbumsTab.css'

function AlbumsTab({ isAdmin }) {
  const [albums, setAlbums] = useState([])
  const [selectedAlbum, setSelectedAlbum] = useState(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAlbums()
  }, [])

  const fetchAlbums = async () => {
    try {
      const response = await fetch('/api/albums')
      const data = await response.json()
      setAlbums(data.albums || data) // Handle both array and object responses
    } catch (error) {
      console.error('Failed to fetch albums:', error)
    }
  }

  const selectAlbum = async (albumId) => {
    try {
      const response = await fetch(`/api/albums/${albumId}`)
      const data = await response.json()
      setSelectedAlbum(data)
    } catch (error) {
      console.error('Failed to fetch album details:', error)
    }
  }

  const createAlbum = async (name, description, albumType = 'manual') => {
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
        const error = await response.json()
        alert('Failed to create album: ' + error.error)
      }
    } catch (error) {
      console.error('Failed to create album:', error)
      alert('Error creating album')
    }
  }

  const deleteAlbum = async (albumId) => {
    if (!isAdmin) return

    if (!window.confirm('Are you sure you want to delete this album?')) return

    try {
      const response = await fetch(`/api/albums/${albumId}`, {
        method: 'DELETE',
        credentials: 'include'
      })

      if (response.ok) {
        fetchAlbums()
        if (selectedAlbum && selectedAlbum.id === albumId) {
          setSelectedAlbum(null)
        }
      } else {
        const error = await response.json()
        alert('Failed to delete album: ' + error.error)
      }
    } catch (error) {
      console.error('Failed to delete album:', error)
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
                    onClick={(e) => {
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

function AlbumDetailView({ album, onBack, isAdmin, onDelete }) {
  const [images, setImages] = useState(album.images || [])
  const [selectedImages, setSelectedImages] = useState([])
  const [nsfwSetting, setNsfwSetting] = useState('blur') // 'hide', 'blur', 'show'

  const toggleImageSelection = (imageId) => {
    if (!isAdmin) return

    if (selectedImages.includes(imageId)) {
      setSelectedImages(selectedImages.filter(id => id !== imageId))
    } else {
      setSelectedImages([...selectedImages, imageId])
    }
  }

  const removeSelectedImages = async () => {
    if (!isAdmin) return

    for (const imageId of selectedImages) {
      try {
        await fetch(`/api/albums/${album.id}/images/${imageId}`, {
          method: 'DELETE',
          credentials: 'include'
        })
      } catch (error) {
        console.error(`Failed to remove image ${imageId}:`, error)
      }
    }

    setImages(images.filter(img => !selectedImages.includes(img.id)))
    setSelectedImages([])
  }

  return (
    <div className="album-detail">
      <div className="album-detail-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <h2>{album.name}</h2>

        <div className="nsfw-filter">
          <label>NSFW:</label>
          <select value={nsfwSetting} onChange={e => setNsfwSetting(e.target.value)}>
            <option value="hide">Hide</option>
            <option value="blur">Blur</option>
            <option value="show">Show</option>
          </select>
        </div>

        {isAdmin && selectedImages.length > 0 && (
          <button 
            className="remove-images-btn"
            onClick={removeSelectedImages}
          >
            Remove {selectedImages.length} images
          </button>
        )}
      </div>

      <div className="album-description">
        <p>{album.description || 'No description'}</p>
      </div>

      <div className="album-images-grid">
        {images.map(image => (
          <div
            key={image.id}
            className={`image-card ${image.is_nsfw ? 'nsfw' : ''} ${nsfwSetting}`}
            onClick={() => isAdmin && toggleImageSelection(image.id)}
          >
            {isAdmin && (
              <input
                type="checkbox"
                checked={selectedImages.includes(image.id)}
                onChange={() => toggleImageSelection(image.id)}
                className="image-checkbox"
              />
            )}

            <img
              src={`/api/images/${image.id}/thumbnail`}
              alt={image.filename}
              className={image.is_nsfw && nsfwSetting === 'blur' ? 'blurred' : ''}
            />

            {image.is_nsfw && (
              <div className="nsfw-badge">18+</div>
            )}

            {image.labels && image.labels.length > 0 && (
              <div className="has-labels-badge">🏷️</div>
            )}
          </div>
        ))}
      </div>

      {images.length === 0 && (
        <div className="empty-album">
          <p>This album is empty.</p>
        </div>
      )}
    </div>
  )
}

function CreateAlbumDialog({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [albumType, setAlbumType] = useState('manual')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim()) return

    onCreate(name.trim(), description.trim(), albumType)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={e => e.stopPropagation()}>
        <h2>Create Album</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Album Name:</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Enter album name"
              required
            />
          </div>

          <div className="form-group">
            <label>Description:</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Enter album description (optional)"
              rows="3"
            />
          </div>

          <div className="form-group">
            <label>Album Type:</label>
            <select value={albumType} onChange={e => setAlbumType(e.target.value)}>
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
