import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Edit2, Save, X, Trash2, Loader2, ImageIcon, FolderOpen } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { useToast } from '../hooks/use-toast'
import { useErrorToast } from '../hooks/use-error-toast'
import { api } from '../lib/api'
import { logger } from '../lib/logger'
import type { Album, GeneratedImage } from '../types/models'

interface AlbumDetailPageProps {
  isAdmin: boolean
}

const AlbumDetailPage: React.FC<AlbumDetailPageProps> = ({ isAdmin }) => {
  const { albumId } = useParams<{ albumId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { showErrorToast } = useErrorToast()

  const [album, setAlbum] = useState<Album | null>(null)
  const [images, setImages] = useState<GeneratedImage[]>([])
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editedName, setEditedName] = useState('')
  const [editedDescription, setEditedDescription] = useState('')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const fetchAlbumDetails = useCallback(async () => {
    if (!albumId) return

    setLoading(true)
    try {
      const albumData = await api.albums.getById(Number(albumId))
      setAlbum(albumData)
      setEditedName(albumData.name)
      setEditedDescription(albumData.description || '')

      // Album API returns images as part of the album response
      if (albumData.images) {
        setImages(albumData.images)
      }
    } catch (error) {
      logger.error('Failed to fetch album details:', error)
      showErrorToast({
        title: 'Album Load Failed',
        context: 'Failed to load album details',
        error,
      })
    } finally {
      setLoading(false)
    }
  }, [albumId, showErrorToast])

  useEffect(() => {
    void fetchAlbumDetails()
  }, [fetchAlbumDetails])

  const handleSave = useCallback(async () => {
    if (!album) return

    setIsSaving(true)
    try {
      await api.albums.update(album.id, {
        name: editedName,
        description: editedDescription
      })

      setAlbum({ ...album, name: editedName, description: editedDescription })
      setIsEditing(false)

      toast({
        title: 'Success',
        description: 'Album updated successfully'
      })
    } catch (error) {
      logger.error('Failed to update album:', error)
      showErrorToast({
        context: 'Failed to update album',
        error,
      })
    } finally {
      setIsSaving(false)
    }
  }, [album, editedName, editedDescription, toast, showErrorToast])

  const handleDelete = useCallback(async () => {
    if (!album) return

    setIsDeleting(true)
    try {
      await api.albums.delete(album.id)

      toast({
        title: 'Success',
        description: 'Album deleted successfully'
      })

      navigate('/albums')
    } catch (error) {
      logger.error('Failed to delete album:', error)
      showErrorToast({
        context: 'Failed to delete album',
        error,
      })
      setIsDeleting(false)
    }
  }, [album, navigate, toast, showErrorToast])

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center gap-4 py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading album...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!album) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">Album not found</p>
            <Button onClick={() => navigate('/albums')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Albums
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Back Button */}
      <Button
        onClick={() => navigate('/albums')}
        variant="ghost"
        className="w-fit"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Albums
      </Button>

      {/* Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <FolderOpen className="h-6 w-6 text-primary" />

                {isEditing ? (
                  <Input
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    className="max-w-md"
                    disabled={isSaving}
                  />
                ) : (
                  <CardTitle className="text-2xl">{album.name}</CardTitle>
                )}

                {album.is_set_template && (
                  <Badge variant="secondary">Set Template</Badge>
                )}
                {album.album_type && (
                  <Badge variant="outline" className="capitalize">
                    {album.album_type}
                  </Badge>
                )}
              </div>

              {isEditing ? (
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={editedDescription}
                    onChange={(e) => setEditedDescription(e.target.value)}
                    placeholder="Album description"
                    rows={3}
                    disabled={isSaving}
                  />
                </div>
              ) : (
                <CardDescription className="text-base">
                  {album.description || 'No description'}
                </CardDescription>
              )}
            </div>

            {isAdmin && (
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <Button onClick={handleSave} size="sm" disabled={isSaving}>
                      <Save className="h-4 w-4 mr-2" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      onClick={() => {
                        setIsEditing(false)
                        setEditedName(album.name)
                        setEditedDescription(album.description || '')
                      }}
                      variant="outline"
                      size="sm"
                      disabled={isSaving}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </>
                ) : (
                  <>
                    <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
                      <Edit2 className="h-4 w-4 mr-2" />
                      Edit
                    </Button>
                    <Button
                      onClick={() => setShowDeleteDialog(true)}
                      variant="destructive"
                      size="sm"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Images</p>
              <p className="text-2xl font-semibold">{album.image_count || 0}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="text-sm font-medium">
                {album.created_at ? new Date(album.created_at).toLocaleDateString() : 'N/A'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Updated</p>
              <p className="text-sm font-medium">
                {album.updated_at ? new Date(album.updated_at).toLocaleDateString() : 'N/A'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">ID</p>
              <p className="text-sm font-mono">{album.id}</p>
            </div>
          </div>

          {/* Template Configuration */}
          {album.is_set_template && (
            <div className="border-t pt-4 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Badge variant="secondary">Template Configuration</Badge>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {album.template_item_count !== undefined && (
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Template Items</p>
                    <p className="font-medium">{album.template_item_count}</p>
                  </div>
                )}
                {album.example_theme && (
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Example Theme</p>
                    <p className="font-medium">{album.example_theme}</p>
                  </div>
                )}
                {album.base_prompt && (
                  <div className="space-y-1 md:col-span-2">
                    <p className="text-sm text-muted-foreground">Base Prompt</p>
                    <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">{album.base_prompt}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Images Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="h-5 w-5" />
            Images ({images.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {images.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <ImageIcon className="h-12 w-12 mx-auto mb-4 opacity-20" />
              <p>No images in this album</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {images.map((image) => (
                <Link
                  key={image.id}
                  to={`/image/${image.id}`}
                  className="group relative aspect-square rounded-lg overflow-hidden bg-muted hover:ring-2 hover:ring-primary transition-all"
                >
                  <img
                    src={image.thumbnail_url || image.download_url}
                    alt={image.filename}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-2">
                    <p className="text-white text-xs text-center line-clamp-2">
                      {image.filename}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Album?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{album.name}"? This action cannot be undone.
              {album.image_count && album.image_count > 0 && (
                <span className="block mt-2 font-semibold">
                  This will affect {album.image_count} image(s).
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Album'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default AlbumDetailPage
