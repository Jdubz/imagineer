import React, { useState, useCallback, memo } from 'react'
import { logger } from '../lib/logger'
import type { Config, GenerateParams } from '../types/models'
import {
  validateForm,
  generateFormSchema,
} from '../lib/validation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Shuffle } from 'lucide-react'

interface GenerateFormProps {
  onGenerate: (params: GenerateParams) => void
  loading: boolean
  config: Config | null
  isAdmin: boolean
}

const GenerateForm: React.FC<GenerateFormProps> = memo(({ onGenerate, loading, config }) => {
  // Single image generation state
  const [prompt, setPrompt] = useState<string>('')
  const [steps, setSteps] = useState<number>(config?.generation?.steps || 30)
  const [guidanceScale, setGuidanceScale] = useState<number>(config?.generation?.guidance_scale || 7.5)
  const [seed, setSeed] = useState<string>('')
  const [useRandomSeed, setUseRandomSeed] = useState<boolean>(true)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

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

      <Card>
        <CardHeader>
          <CardTitle>🎨 Batch Generation from Templates</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p>
            Generate complete sets of themed images using pre-configured templates.
          </p>
          <p className="text-sm text-muted-foreground">
            Visit the <strong>Templates</strong> tab to browse available templates and start batch generation.
          </p>
          <Button asChild variant="outline" className="w-full">
            <a href="/batch-templates">
              Go to Templates →
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
})

GenerateForm.displayName = 'GenerateForm'

export default GenerateForm
