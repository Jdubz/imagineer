import React, { useState, useEffect, useCallback } from 'react'
import { Wand2, Loader2, Layers, Info } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { useToast } from '../hooks/use-toast'
import { useErrorToast } from '../hooks/use-error-toast'
import { api } from '../lib/api'
import { logger } from '../lib/logger'
import type { BatchTemplate, BatchGenerateParams } from '../types/models'

interface BatchTemplatesPageProps {
  isAdmin: boolean
}

const BatchTemplatesPage: React.FC<BatchTemplatesPageProps> = ({ isAdmin }) => {
  const { toast } = useToast()
  const { showErrorToast } = useErrorToast()

  const [templates, setTemplates] = useState<BatchTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<BatchTemplate | null>(null)
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Form state
  const [albumName, setAlbumName] = useState('')
  const [userTheme, setUserTheme] = useState('')
  const [steps, setSteps] = useState<number | ''>('')
  const [seed, setSeed] = useState<number | ''>('')
  const [guidanceScale, setGuidanceScale] = useState<number | ''>('')

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const templatesData = await api.batchTemplates.getAll()
      setTemplates(templatesData)
    } catch (error) {
      logger.error('Failed to fetch batch templates:', error)
      showErrorToast({
        title: 'Templates Load Failed',
        context: 'Failed to load batch templates',
        error,
      })
    } finally {
      setLoading(false)
    }
  }, [showErrorToast])

  useEffect(() => {
    void fetchTemplates()
  }, [fetchTemplates])

  const handleOpenGenerateDialog = useCallback((template: BatchTemplate) => {
    setSelectedTemplate(template)
    setAlbumName('')
    setUserTheme(template.example_theme || '')
    setSteps('')
    setSeed('')
    setGuidanceScale('')
    setShowAdvanced(false)
    setShowGenerateDialog(true)
  }, [])

  const pollRunProgress = useCallback(
    (templateId: number, runId: number, albumName: string) => {
      let progressToast: ReturnType<typeof toast> | null = null
      let pollCount = 0
      const maxPolls = 120 // 10 minutes max (5 sec intervals)

      const poll = async () => {
        try {
          pollCount++
          const run = await api.batchTemplates.getRunStatus(templateId, runId)

          const progress = run.completed_items || 0
          const failed = run.failed_items || 0
          const total = run.total_items || 0
          const percentComplete = total > 0 ? Math.round((progress / total) * 100) : 0

          // Update or create progress toast
          if (!progressToast) {
            progressToast = toast({
              title: 'Generating...',
              description: `${progress}/${total} images complete (${percentComplete}%)${
                failed > 0 ? ` - ${failed} failed` : ''
              }`,
              duration: Infinity,
            })
          } else {
            toast({
              title: 'Generating...',
              description: `${progress}/${total} images complete (${percentComplete}%)${
                failed > 0 ? ` - ${failed} failed` : ''
              }`,
              duration: Infinity,
            })
          }

          // Check if complete
          if (run.status === 'completed' || run.status === 'failed') {
            if (run.status === 'completed') {
              toast({
                title: 'Batch Complete!',
                description: `Album "${albumName}" created with ${progress} images${
                  run.album_id ? `. View in Albums tab.` : ''
                }`,
              })
            } else {
              toast({
                title: 'Batch Failed',
                description: run.error_message || 'All generation jobs failed',
                variant: 'destructive',
              })
            }
            return // Stop polling
          }

          // Continue polling if not complete and haven't exceeded max
          if (pollCount < maxPolls) {
            setTimeout(poll, 5000) // Poll every 5 seconds
          }
        } catch (error) {
          logger.error('Failed to poll run status:', error)
          // Stop polling on error
        }
      }

      // Start polling
      void poll()
    },
    [toast]
  )

  const handleGenerate = useCallback(async () => {
    if (!selectedTemplate || !albumName || !userTheme) {
      toast({
        title: 'Missing Fields',
        description: 'Please provide both album name and theme',
        variant: 'destructive',
      })
      return
    }

    setIsGenerating(true)
    try {
      const params: BatchGenerateParams = {
        album_name: albumName,
        user_theme: userTheme,
      }

      // Add optional parameters if provided
      if (steps !== '') params.steps = Number(steps)
      if (seed !== '') params.seed = Number(seed)
      if (guidanceScale !== '') params.guidance_scale = Number(guidanceScale)

      const response = await api.batchTemplates.generate(selectedTemplate.id, params)

      toast({
        title: 'Batch Generation Started',
        description: `Queued ${response.run.total_items} images for generation. Album: ${response.run.album_name}`,
      })

      setShowGenerateDialog(false)
      setSelectedTemplate(null)

      // Start polling for progress
      pollRunProgress(selectedTemplate.id, response.run.id, response.run.album_name)
    } catch (error) {
      logger.error('Failed to generate batch:', error)
      showErrorToast({
        title: 'Generation Failed',
        context: 'Failed to start batch generation',
        error,
      })
    } finally {
      setIsGenerating(false)
    }
  }, [selectedTemplate, albumName, userTheme, steps, seed, guidanceScale, toast, showErrorToast, pollRunProgress])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Batch Templates</h1>
          <p className="text-muted-foreground mt-1">
            Generate collections of themed images from pre-configured templates
          </p>
        </div>
        {isAdmin && (
          <Button variant="outline" disabled>
            <Layers className="h-4 w-4 mr-2" />
            New Template
          </Button>
        )}
      </div>

      {templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Layers className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground text-center">
              No batch templates available
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <Card key={template.id} className="flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  {template.name}
                </CardTitle>
                {template.description && (
                  <CardDescription>{template.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="flex-1 space-y-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-muted-foreground">Items</p>
                    <p className="font-medium">{template.template_item_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Dimensions</p>
                    <p className="font-medium">
                      {template.width}×{template.height}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">LoRAs</p>
                    <p className="font-medium">{template.lora_count}</p>
                  </div>
                </div>

                {template.example_theme && (
                  <div className="pt-2 border-t">
                    <div className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                      <div className="text-sm">
                        <p className="text-muted-foreground mb-1">Example theme:</p>
                        <p className="italic">{template.example_theme}</p>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  onClick={() => handleOpenGenerateDialog(template)}
                >
                  <Wand2 className="h-4 w-4 mr-2" />
                  Generate Batch
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Generate Dialog */}
      <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Generate: {selectedTemplate?.name}</DialogTitle>
            <DialogDescription>
              Create a themed collection of {selectedTemplate?.template_item_count} images
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="album-name">Album Name *</Label>
              <Input
                id="album-name"
                placeholder="My Custom Cards"
                value={albumName}
                onChange={(e) => setAlbumName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="user-theme">Theme *</Label>
              <Textarea
                id="user-theme"
                placeholder="steampunk aesthetic with brass gears and Victorian industrial design..."
                value={userTheme}
                onChange={(e) => setUserTheme(e.target.value)}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Describe the style, mood, or aesthetic you want
              </p>
            </div>

            <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-full">
                  <span>{showAdvanced ? '▼' : '▶'} Advanced Options</span>
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4 pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="steps">Steps</Label>
                    <Input
                      id="steps"
                      type="number"
                      placeholder="25"
                      value={steps}
                      onChange={(e) => setSteps(e.target.value ? Number(e.target.value) : '')}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="seed">Seed</Label>
                    <Input
                      id="seed"
                      type="number"
                      placeholder="Random"
                      value={seed}
                      onChange={(e) => setSeed(e.target.value ? Number(e.target.value) : '')}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="guidance">Guidance Scale</Label>
                  <Input
                    id="guidance"
                    type="number"
                    step="0.1"
                    placeholder="7.5"
                    value={guidanceScale}
                    onChange={(e) => setGuidanceScale(e.target.value ? Number(e.target.value) : '')}
                  />
                </div>
              </CollapsibleContent>
            </Collapsible>

            {selectedTemplate && (
              <div className="bg-muted p-3 rounded-md text-sm">
                <p className="text-muted-foreground">
                  Will generate <strong>{selectedTemplate.template_item_count} images</strong> at{' '}
                  <strong>
                    {selectedTemplate.width}×{selectedTemplate.height}
                  </strong>
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGenerateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleGenerate} disabled={isGenerating || !albumName || !userTheme}>
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 className="h-4 w-4 mr-2" />
                  Generate Batch
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default BatchTemplatesPage
