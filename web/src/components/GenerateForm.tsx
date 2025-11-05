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
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { FormField } from '@/components/form'
import { cn } from '@/lib/utils'
import { Shuffle, Info } from 'lucide-react'

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
    <div className="space-y-6">
      <Card>
        <CardHeader className="space-y-1">
          <CardTitle>Generate Single Image</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <FormField
              label={(
                <span className="flex items-center gap-2">
                  Prompt
                  <span className="text-xs font-normal text-muted-foreground">required</span>
                </span>
              )}
              htmlFor="prompt"
              description="Describe the image you want Imagineer to create."
              error={validationErrors.prompt}
            >
              <Textarea
                id="prompt"
                value={prompt}
                onChange={handlePromptChange}
                placeholder="Describe the image you want to generate..."
                rows={4}
                disabled={loading}
                required
                className="min-h-[120px]"
              />
            </FormField>

            <div className="grid gap-6 md:grid-cols-2">
              <FormField
                label={(
                  <span className="flex items-center gap-2">
                    Steps
                    <span className="text-xs font-normal text-muted-foreground">{steps}</span>
                    <span
                      className="text-muted-foreground"
                      title="Higher steps refine the result but take longer to render."
                    >
                      <Info className="h-4 w-4" aria-hidden="true" />
                    </span>
                  </span>
                )}
                description="20–40 steps balance speed and quality for most prompts."
              >
                <input
                  type="range"
                  id="steps"
                  min="10"
                  max="75"
                  step="5"
                  value={steps}
                  onChange={handleStepsChange}
                  disabled={loading}
                  className="range-input"
                />
                <div className="mt-2 flex justify-between text-[0.7rem] uppercase tracking-wide text-muted-foreground">
                  <span>10</span>
                  <span>Fast</span>
                  <span>Quality</span>
                  <span>75</span>
                </div>
              </FormField>

              <FormField
                label={(
                  <span className="flex items-center gap-2">
                    Guidance Scale
                    <span className="text-xs font-normal text-muted-foreground">{guidanceScale}</span>
                    <span
                      className="text-muted-foreground"
                      title="Higher guidance keeps the output closer to your prompt."
                    >
                      <Info className="h-4 w-4" aria-hidden="true" />
                    </span>
                  </span>
                )}
                description="Lower values encourage exploration; higher values follow the prompt strictly."
              >
                <input
                  type="range"
                  id="guidance"
                  min="1"
                  max="20"
                  step="0.5"
                  value={guidanceScale}
                  onChange={handleGuidanceChange}
                  disabled={loading}
                  className="range-input"
                />
                <div className="mt-2 flex justify-between text-[0.7rem] uppercase tracking-wide text-muted-foreground">
                  <span>1</span>
                  <span>Creative</span>
                  <span>Strict</span>
                  <span>20</span>
                </div>
              </FormField>
            </div>

            <FormField
              label={(
                <span className="flex items-center gap-2">
                  Seed
                  <span className="text-xs font-normal text-muted-foreground">optional</span>
                </span>
              )}
              description="Use a fixed seed to reproduce results or stay random for fresh variations."
            >
              <div className="space-y-3">
                <div className="inline-flex items-center rounded-full border border-border bg-muted/40 p-1 text-xs font-medium shadow-sm">
                  <button
                    type="button"
                    onClick={handleSeedModeRandom}
                    disabled={loading}
                    className={cn(
                      'rounded-full px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
                      useRandomSeed
                        ? 'bg-background text-foreground shadow'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    Random
                  </button>
                  <button
                    type="button"
                    onClick={handleSeedModeFixed}
                    disabled={loading}
                    className={cn(
                      'rounded-full px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
                      !useRandomSeed
                        ? 'bg-background text-foreground shadow'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    Fixed
                  </button>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Input
                    type="number"
                    id="seed"
                    value={seed}
                    onChange={handleSeedChange}
                    placeholder="Enter a specific seed"
                    min="0"
                    max="2147483647"
                    disabled={loading || useRandomSeed}
                    className="sm:max-w-[200px]"
                  />
                  <Button
                    type="button"
                    onClick={generateRandomSeed}
                    disabled={loading}
                    variant="secondary"
                    size="sm"
                  >
                    <Shuffle className="mr-2 h-4 w-4" />
                    Randomize
                  </Button>
                </div>
              </div>
            </FormField>

            <Button
              type="submit"
              disabled={loading || !prompt.trim()}
              size="lg"
              className="w-full"
            >
              {loading ? 'Generating…' : 'Generate Image'}
            </Button>

            {loading ? (
              <p className="text-center text-sm text-muted-foreground">
                Generating your image… This may take up to 30 seconds.
              </p>
            ) : null}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="space-y-1">
          <CardTitle>🎨 Batch Generation from Templates</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>Generate complete sets of themed images using pre-configured templates.</p>
          <p>Visit the <strong>Templates</strong> tab to browse available options and start batch jobs.</p>
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <a href="/batch-templates">Go to Templates →</a>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
})

GenerateForm.displayName = 'GenerateForm'

export default GenerateForm
