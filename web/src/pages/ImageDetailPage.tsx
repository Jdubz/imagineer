import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Edit2, Save, X, Trash2, Loader2, Download, FolderOpen, Calendar, Hash, Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { useToast } from '../hooks/use-toast'
import { api } from '../lib/api'
import { logger } from '../lib/logger'
import { formatErrorMessage } from '../lib/errorUtils'
import type { GeneratedImage } from '../types/models'

interface ImageDetailPageProps {
  isAdmin: boolean
}

const ImageDetailPage: React.FC<ImageDetailPageProps> = ({ isAdmin }) => {
  const { imageId } = useParams<{ imageId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [image, setImage] = useState<GeneratedImage | null>(null)
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editedPrompt, setEditedPrompt] = useState('')
  const [editedNegativePrompt, setEditedNegativePrompt] = useState('')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const fetchImageDetails = useCallback(async () => {
    if (!imageId) return

    setLoading(true)
    try {
      const imageData = await api.images.getById(Number(imageId))
      setImage(imageData)
      setEditedPrompt(imageData.prompt || '')
      setEditedNegativePrompt(imageData.negative_prompt || '')
    } catch (error: unknown) {
      logger.error('Failed to fetch image details:', error)
      toast({
        title: 'Error',
        description: formatErrorMessage(error, 'Failed to load image'),
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }, [imageId, toast])

  useEffect(() => {
    void fetchImageDetails()
  }, [fetchImageDetails])

  const handleSave = useCallback(async () => {
    if (!image) return

    if (!image.id) return

    setIsSaving(true)
    try {
      await api.images.update(image.id, {
        prompt: editedPrompt,
        negative_prompt: editedNegativePrompt
      })

      setImage({
        ...image,
        prompt: editedPrompt,
        negative_prompt: editedNegativePrompt
      })
      setIsEditing(false)

      toast({
        title: 'Success',
        description: 'Image updated successfully'
      })
    } catch (error: unknown) {
      logger.error('Failed to update image:', error)
      toast({
        title: 'Error',
        description: formatErrorMessage(error, 'Failed to update image'),
        variant: 'destructive'
      })
    } finally {
      setIsSaving(false)
    }
  }, [image, editedPrompt, editedNegativePrompt, toast])

  const handleDelete = useCallback(async () => {
    if (!image || !image.id) return

    setIsDeleting(true)
    try {
      await api.images.delete(image.id)

      toast({
        title: 'Success',
        description: 'Image deleted successfully'
      })

      navigate('/gallery')
    } catch (error: unknown) {
      logger.error('Failed to delete image:', error)
      toast({
        title: 'Error',
        description: formatErrorMessage(error, 'Failed to delete image'),
        variant: 'destructive'
      })
      setIsDeleting(false)
    }
  }, [image, navigate, toast])

  const handleDownload = useCallback(() => {
    if (!image || !image.download_url) return

    const link = document.createElement('a')
    link.href = image.download_url
    link.download = image.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [image])

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center gap-4 py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading image...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!image) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">Image not found</p>
            <Button onClick={() => navigate('/gallery')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Gallery
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
        onClick={() => navigate(-1)}
        variant="ghost"
        className="w-fit"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Image Display */}
        <Card className="lg:sticky lg:top-6 lg:self-start">
          <CardContent className="pt-6">
            <div className="aspect-square w-full rounded-lg overflow-hidden bg-muted">
              <img
                src={image.download_url}
                alt={image.filename}
                className="w-full h-full object-contain"
              />
            </div>
            <div className="mt-4 flex items-center gap-2">
              <Button onClick={handleDownload} className="flex-1">
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
              {isAdmin && (
                <Button
                  onClick={() => setShowDeleteDialog(true)}
                  variant="destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Image Details */}
        <div className="space-y-6">
          {/* Header Card */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-xl truncate">{image.filename}</CardTitle>
                  <CardDescription className="flex items-center gap-2 mt-2">
                    <Calendar className="h-4 w-4" />
                    {image.created_at ? new Date(image.created_at).toLocaleString() : 'Unknown date'}
                  </CardDescription>
                </div>

                {isAdmin && !isEditing && (
                  <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
                    <Edit2 className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Status Badges */}
              <div className="flex flex-wrap gap-2">
                {image.is_public !== undefined && (
                  <Badge variant={image.is_public ? 'default' : 'secondary'}>
                    {image.is_public ? 'Public' : 'Private'}
                  </Badge>
                )}
                {image.is_nsfw && (
                  <Badge variant="destructive">NSFW</Badge>
                )}
                <Badge variant="outline">
                  <Hash className="h-3 w-3 mr-1" />
                  ID: {image.id}
                </Badge>
              </div>

              {/* Album Link */}
              {image.album_id && (
                <div className="pt-2 border-t">
                  <Label className="text-sm text-muted-foreground mb-2 block">Album</Label>
                  <Link to={`/albums/${image.album_id}`}>
                    <Button variant="outline" size="sm">
                      <FolderOpen className="h-4 w-4 mr-2" />
                      View Album
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Generation Parameters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Generation Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {image.width && image.height && (
                  <div className="space-y-1">
                    <Label className="text-sm text-muted-foreground">Dimensions</Label>
                    <p className="font-medium">{image.width} × {image.height}</p>
                  </div>
                )}
                {image.steps !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm text-muted-foreground">Steps</Label>
                    <p className="font-medium">{image.steps}</p>
                  </div>
                )}
                {image.guidance_scale !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm text-muted-foreground">Guidance Scale</Label>
                    <p className="font-medium">{image.guidance_scale}</p>
                  </div>
                )}
                {image.seed !== undefined && image.seed !== null && (
                  <div className="space-y-1">
                    <Label className="text-sm text-muted-foreground">Seed</Label>
                    <p className="font-mono text-sm">{image.seed}</p>
                  </div>
                )}
              </div>

              {/* LoRA Configuration */}
              {image.lora_config && (
                <div className="space-y-2 pt-2 border-t">
                  <Label className="text-sm text-muted-foreground">LoRA Configuration</Label>
                  <pre className="text-xs font-mono bg-muted p-3 rounded-md overflow-x-auto">
                    {JSON.stringify(JSON.parse(image.lora_config), null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Prompts Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Prompts</CardTitle>
                {isAdmin && isEditing && (
                  <div className="flex items-center gap-2">
                    <Button onClick={handleSave} size="sm" disabled={isSaving}>
                      <Save className="h-4 w-4 mr-2" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      onClick={() => {
                        setIsEditing(false)
                        setEditedPrompt(image.prompt || '')
                        setEditedNegativePrompt(image.negative_prompt || '')
                      }}
                      variant="outline"
                      size="sm"
                      disabled={isSaving}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Positive Prompt */}
              <div className="space-y-2">
                <Label htmlFor="prompt">Prompt</Label>
                {isEditing ? (
                  <Textarea
                    id="prompt"
                    value={editedPrompt}
                    onChange={(e) => setEditedPrompt(e.target.value)}
                    rows={4}
                    disabled={isSaving}
                    className="font-mono text-sm"
                  />
                ) : (
                  <p className="text-sm bg-muted p-3 rounded-md whitespace-pre-wrap">
                    {image.prompt || 'No prompt'}
                  </p>
                )}
              </div>

              {/* Negative Prompt */}
              <div className="space-y-2">
                <Label htmlFor="negative-prompt">Negative Prompt</Label>
                {isEditing ? (
                  <Textarea
                    id="negative-prompt"
                    value={editedNegativePrompt}
                    onChange={(e) => setEditedNegativePrompt(e.target.value)}
                    rows={4}
                    disabled={isSaving}
                    className="font-mono text-sm"
                  />
                ) : (
                  <p className="text-sm bg-muted p-3 rounded-md whitespace-pre-wrap">
                    {image.negative_prompt || 'No negative prompt'}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Image?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{image.filename}"? This action cannot be undone.
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
                'Delete Image'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default ImageDetailPage
