import React, { useState, useEffect, useCallback, useMemo, memo } from 'react'
import { logger } from '../lib/logger'
import { api } from '../lib/api'
import { useToast } from '../hooks/use-toast'
import { useErrorToast } from '../hooks/use-error-toast'
import type { Config, GenerateParams, Album } from '../types/models'
import {
  validateForm,
  generateFormSchema,
  themeSchema,
} from '../lib/validation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Shuffle } from 'lucide-react'

interface GenerateFormProps {
  onGenerate: (params: GenerateParams) => void
  loading: boolean
  config: Config | null
  isAdmin: boolean
}

const GenerateForm: React.FC<GenerateFormProps> = memo(({ onGenerate, loading, config, isAdmin }) => {
  const { toast } = useToast()
  const { showErrorToast } = useErrorToast()
  // Single image generation state
  const [prompt, setPrompt] = useState<string>('')
  const [steps, setSteps] = useState<number>(config?.generation?.steps || 30)
  const [guidanceScale, setGuidanceScale] = useState<number>(config?.generation?.guidance_scale || 7.5)
  const [seed, setSeed] = useState<string>('')
  const [useRandomSeed, setUseRandomSeed] = useState<boolean>(true)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  // Batch generation state
  const [templates, setTemplates] = useState<Album[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(undefined)
  const [batchTheme, setBatchTheme] = useState<string>('')
  const [batchSteps, setBatchSteps] = useState<string>('')
  const [batchSeed, setBatchSeed] = useState<string>('')
  const [loadingTemplates, setLoadingTemplates] = useState<boolean>(false)
  const [submittingBatch, setSubmittingBatch] = useState<boolean>(false)
  const [batchValidationErrors, setBatchValidationErrors] = useState<Record<string, string>>({})

  const fetchTemplates = useCallback(async (): Promise<void> => {
    setLoadingTemplates(true)
    try {
      const albums = await api.albums.getAll()
      const templateAlbums = albums.filter(album => album.is_set_template === true)
      setTemplates(templateAlbums)
    } catch (error) {
      logger.error('Failed to fetch templates:', error)
      showErrorToast({
        title: 'Template Load Error',
        context: 'Failed to load batch templates',
        error,
      })
    } finally {
      setLoadingTemplates(false)
    }
  }, [showErrorToast])

  // Load templates on mount
  useEffect(() => {
    if (isAdmin) {
      fetchTemplates()
    }
  }, [isAdmin, fetchTemplates])

  const handleSubmit = useCallback((e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    setValidationErrors({}) // Clear previous errors

    // Prepare data for validation
    const formData = {
      prompt: prompt.trim(),
      steps,
      guidance_scale: guidanceScale,
      seed: !useRandomSeed && seed ? parseInt(seed) : undefined,
    }

    // Validate form data
    const validation = validateForm(generateFormSchema, formData)

    if (!validation.success) {
      setValidationErrors(validation.errors)
      logger.warn('Form validation failed:', validation.errors)
      return
    }

    // Validation passed, submit the form
    const params: GenerateParams = {
      prompt: validation.data.prompt,
      steps: validation.data.steps,
      guidance_scale: validation.data.guidance_scale,
    }

    // Only include seed if user provided one
    if (validation.data.seed !== undefined) {
      params.seed = validation.data.seed
    }

    onGenerate(params)
    setPrompt('')
    setValidationErrors({}) // Clear errors on successful submission
  }, [prompt, steps, guidanceScale, useRandomSeed, seed, onGenerate])

  const generateRandomSeed = useCallback((): void => {
    const randomSeed = Math.floor(Math.random() * 2147483647)
    setSeed(randomSeed.toString())
    setUseRandomSeed(false)
  }, [])

  const handleBatchSubmit = useCallback(async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setBatchValidationErrors({})

    if (!selectedTemplate) {
      toast({ title: 'Error', description: 'Please select a template', variant: 'destructive' })
      return
    }

    // Validate theme
    const themeValidation = validateForm(themeSchema, batchTheme.trim())
    if (!themeValidation.success) {
      setBatchValidationErrors(themeValidation.errors)
      return
    }

    setSubmittingBatch(true)

    try {
      const params: {
        user_theme: string
        steps?: number
        seed?: number
      } = {
        user_theme: batchTheme.trim(),
      }

      if (batchSteps) {
        const stepsNum = parseInt(batchSteps, 10)
        if (!isNaN(stepsNum)) params.steps = stepsNum
      }

      if (batchSeed) {
        const seedNum = parseInt(batchSeed, 10)
        if (!isNaN(seedNum)) params.seed = seedNum
      }

      const result = await api.albums.generateBatch(selectedTemplate, params)

      if (result.success) {
        const template = templates.find(t => t.id === selectedTemplate)
        toast({ title: 'Success', description: `Batch generation started! ${template?.template_item_count || 0} jobs queued.` })
        setBatchTheme('')
        setBatchSteps('')
        setBatchSeed('')
      } else {
        showErrorToast({
          title: 'Batch Generation Failed',
          context: 'Failed to start batch generation',
          error: new Error(result.error || 'Failed to start batch generation'),
        })
      }
    } catch (error) {
      logger.error('Failed to generate batch:', error)
      showErrorToast({
        title: 'Batch Generation Error',
        context: 'Error starting batch generation',
        error,
      })
    } finally {
      setSubmittingBatch(false)
    }
  }, [selectedTemplate, batchTheme, batchSteps, batchSeed, templates, toast, showErrorToast])

  // Memoize onChange handlers to prevent re-renders
  const handlePromptChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(e.target.value)
    if (validationErrors.prompt) {
      setValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors.prompt
        return newErrors
      })
    }
  }, [validationErrors.prompt])

  const handleStepsChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSteps(parseInt(e.target.value))
  }, [])

  const handleGuidanceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setGuidanceScale(parseFloat(e.target.value))
  }, [])

  const handleSeedModeRandom = useCallback(() => {
    setUseRandomSeed(true)
    setSeed('')
  }, [])

  const handleSeedModeFixed = useCallback(() => {
    setUseRandomSeed(false)
  }, [])

  const handleSeedChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSeed(e.target.value)
  }, [])

  const handleTemplateChange = useCallback((value: string) => {
    setSelectedTemplate(value)
  }, [])

  const handleBatchThemeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setBatchTheme(e.target.value)
    if (batchValidationErrors.theme) {
      setBatchValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors.theme
        return newErrors
      })
    }
  }, [batchValidationErrors.theme])

  const handleBatchStepsChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setBatchSteps(e.target.value)
  }, [])

  const handleBatchSeedChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setBatchSeed(e.target.value)
  }, [])

  // Memoize selected template example
  const selectedTemplateExample = useMemo(() => {
    return selectedTemplate
      ? templates.find(t => t.id === selectedTemplate)?.example_theme || 'Choose a template to see example'
      : 'Choose a template to see example'
  }, [selectedTemplate, templates])

  return (
    <div className="generate-form">
      <Card>
        <CardHeader>
          <CardTitle>Generate Single Image</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
        <div className="form-group">
          <Label htmlFor="prompt">Prompt</Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={handlePromptChange}
            placeholder="Describe the image you want to generate..."
            rows={4}
            disabled={loading}
            required
            className={validationErrors.prompt ? 'error' : ''}
          />
          {validationErrors.prompt && (
            <span className="error-message">{validationErrors.prompt}</span>
          )}
        </div>

        <div className="controls-grid">
          <div className="form-group">
            <Label htmlFor="steps">
              Steps: {steps}
              <span className="tooltip">?
                <span className="tooltip-text">
                  Number of denoising iterations. More steps = more refined image but slower.
                  <br/>• 20-25: Fast, decent quality
                  <br/>• 30-40: Balanced (recommended)
                  <br/>• 50+: Diminishing returns
                </span>
              </span>
            </Label>
            <input
              type="range"
              id="steps"
              min="10"
              max="75"
              step="5"
              value={steps}
              onChange={handleStepsChange}
              disabled={loading}
            />
            <div className="range-labels">
              <span>10</span>
              <span>Fast</span>
              <span>Quality</span>
              <span>75</span>
            </div>
          </div>

          <div className="form-group">
            <Label htmlFor="guidance">
              Guidance Scale: {guidanceScale}
              <span className="tooltip">?
                <span className="tooltip-text">
                  How closely the model follows your prompt.
                  <br/>• 1-5: Creative, loose interpretation
                  <br/>• 7-10: Balanced
                  <br/>• 10-15: Strong adherence
                  <br/>• 15-20: Very strict (may reduce quality)
                </span>
              </span>
            </Label>
            <input
              type="range"
              id="guidance"
              min="1"
              max="20"
              step="0.5"
              value={guidanceScale}
              onChange={handleGuidanceChange}
              disabled={loading}
            />
            <div className="range-labels">
              <span>1</span>
              <span>Creative</span>
              <span>Strict</span>
              <span>20</span>
            </div>
          </div>
        </div>

        <div className="form-group seed-group">
          <Label htmlFor="seed">
            Seed (Optional)
            <span className="tooltip">?
              <span className="tooltip-text">
                Random seed for reproducibility. Same seed + prompt = same image.
                <br/>• Leave as "Random" for different results each time
                <br/>• Set a specific number to reproduce an image
                <br/>• Range: 0 to 2,147,483,647
              </span>
            </span>
          </Label>
          <div className="seed-controls">
            <div className="seed-toggle">
              <label className="toggle-option">
                <input
                  type="radio"
                  name="seed-mode"
                  checked={useRandomSeed}
                  onChange={handleSeedModeRandom}
                  disabled={loading}
                />
                <span>Random</span>
              </label>
              <label className="toggle-option">
                <input
                  type="radio"
                  name="seed-mode"
                  checked={!useRandomSeed}
                  onChange={handleSeedModeFixed}
                  disabled={loading}
                />
                <span>Fixed</span>
              </label>
            </div>
            <Input
              type="number"
              id="seed"
              value={seed}
              onChange={handleSeedChange}
              placeholder="Enter seed or generate random"
              min="0"
              max="2147483647"
              disabled={loading || useRandomSeed}
              className="seed-input"
            />
            <Button
              type="button"
              onClick={generateRandomSeed}
              disabled={loading}
              size="icon"
              variant="secondary"
              title="Generate random seed"
              aria-label="Generate random seed"
            >
              <Shuffle className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <Button
          type="submit"
          disabled={loading || !prompt.trim()}
          size="lg"
          className="w-full"
        >
          {loading ? 'Generating...' : 'Generate Image'}
        </Button>

        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>Generating your image... This may take 10-30 seconds</p>
          </div>
        )}
          </form>
        </CardContent>
      </Card>

      <div className="form-divider"></div>

      {isAdmin ? (
        <Card>
          <CardHeader>
            <CardTitle>Generate Batch from Template</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleBatchSubmit} className="batch-generate-form">
            <div className="form-group">
              <Label htmlFor="template">Select Template</Label>
              <Select
                value={selectedTemplate ?? undefined}
                onValueChange={handleTemplateChange}
                disabled={loadingTemplates || submittingBatch}
                required
              >
                <SelectTrigger id="template">
                  <SelectValue placeholder="-- Choose a template --" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map(template => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name} ({template.template_item_count || 0} items)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {loadingTemplates && <span className="loading-text">Loading templates...</span>}
              {templates.length === 0 && !loadingTemplates && (
                <span className="info-text">No templates available. Create one in the Albums tab.</span>
              )}
            </div>

            <div className="form-group">
              <Label htmlFor="batch-theme">Art Style Theme</Label>
              <Input
                id="batch-theme"
                type="text"
                value={batchTheme}
                onChange={handleBatchThemeChange}
                placeholder="e.g., gothic style with ravens and purple tones"
                disabled={submittingBatch}
                required
                className={batchValidationErrors.theme ? 'error' : ''}
              />
              {batchValidationErrors.theme && (
                <span className="error-message">{batchValidationErrors.theme}</span>
              )}
              {selectedTemplate && (
                <span className="info-text">
                  Example: {selectedTemplateExample}
                </span>
              )}
            </div>

            <div className="controls-grid">
              <div className="form-group">
                <Label htmlFor="batch-steps">Steps (Optional)</Label>
                <Input
                  type="number"
                  id="batch-steps"
                  value={batchSteps}
                  onChange={handleBatchStepsChange}
                  placeholder="Leave empty for template default"
                  min="1"
                  max="150"
                  disabled={submittingBatch}
                />
              </div>

              <div className="form-group">
                <Label htmlFor="batch-seed">Seed (Optional)</Label>
                <Input
                  type="number"
                  id="batch-seed"
                  value={batchSeed}
                  onChange={handleBatchSeedChange}
                  placeholder="Random seed for reproducibility"
                  min="0"
                  max="2147483647"
                  disabled={submittingBatch}
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={submittingBatch || !selectedTemplate || !batchTheme.trim()}
              size="lg"
              variant="secondary"
              className="w-full"
            >
              {submittingBatch ? 'Starting Batch...' : 'Generate Batch'}
            </Button>

            {submittingBatch && (
              <div className="loading-indicator">
                <div className="spinner"></div>
                <p>Queuing batch generation jobs...</p>
              </div>
            )}
            </form>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>🎨 Batch Generation from Templates</CardTitle>
          </CardHeader>
          <CardContent>
            <p>
              Admin users can generate complete sets of themed images from templates.
              Batch generation is available in the <strong>Albums</strong> tab.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
})

GenerateForm.displayName = 'GenerateForm'

export default GenerateForm
