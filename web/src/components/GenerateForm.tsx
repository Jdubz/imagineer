import React, { useState } from 'react'
import { logger } from '../lib/logger'
import type { Config, GenerateParams } from '../types/models'
import {
  validateForm,
  generateFormSchema,
} from '../lib/validation'

interface GenerateFormProps {
  onGenerate: (params: GenerateParams) => void
  onGenerateBatch?: () => void
  loading: boolean
  config: Config | null
  isAdmin: boolean
}

const GenerateForm: React.FC<GenerateFormProps> = ({ onGenerate, loading, config }) => {
  const [prompt, setPrompt] = useState<string>('')
  const [steps, setSteps] = useState<number>(config?.generation?.steps || 30)
  const [guidanceScale, setGuidanceScale] = useState<number>(config?.generation?.guidance_scale || 7.5)
  const [seed, setSeed] = useState<string>('')
  const [useRandomSeed, setUseRandomSeed] = useState<boolean>(true)

  // Validation error state
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
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
  }

  const generateRandomSeed = (): void => {
    const randomSeed = Math.floor(Math.random() * 2147483647)
    setSeed(randomSeed.toString())
    setUseRandomSeed(false)
  }

  return (
    <div className="generate-form">
      <h2>Generate Single Image</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
              setPrompt(e.target.value)
              // Clear error on change
              if (validationErrors.prompt) {
                const newErrors = { ...validationErrors }
                delete newErrors.prompt
                setValidationErrors(newErrors)
              }
            }}
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
            <label htmlFor="steps">
              Steps: {steps}
              <span className="tooltip">?
                <span className="tooltip-text">
                  Number of denoising iterations. More steps = more refined image but slower.
                  <br/>• 20-25: Fast, decent quality
                  <br/>• 30-40: Balanced (recommended)
                  <br/>• 50+: Diminishing returns
                </span>
              </span>
            </label>
            <input
              type="range"
              id="steps"
              min="10"
              max="75"
              step="5"
              value={steps}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSteps(parseInt(e.target.value))}
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
            <label htmlFor="guidance">
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
            </label>
            <input
              type="range"
              id="guidance"
              min="1"
              max="20"
              step="0.5"
              value={guidanceScale}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGuidanceScale(parseFloat(e.target.value))}
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
          <label htmlFor="seed">
            Seed (Optional)
            <span className="tooltip">?
              <span className="tooltip-text">
                Random seed for reproducibility. Same seed + prompt = same image.
                <br/>• Leave as "Random" for different results each time
                <br/>• Set a specific number to reproduce an image
                <br/>• Range: 0 to 2,147,483,647
              </span>
            </span>
          </label>
          <div className="seed-controls">
            <div className="seed-toggle">
              <label className="toggle-option">
                <input
                  type="radio"
                  name="seed-mode"
                  checked={useRandomSeed}
                  onChange={() => {
                    setUseRandomSeed(true)
                    setSeed('')
                  }}
                  disabled={loading}
                />
                <span>Random</span>
              </label>
              <label className="toggle-option">
                <input
                  type="radio"
                  name="seed-mode"
                  checked={!useRandomSeed}
                  onChange={() => setUseRandomSeed(false)}
                  disabled={loading}
                />
                <span>Fixed</span>
              </label>
            </div>
            <input
              type="number"
              id="seed"
              value={seed}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSeed(e.target.value)}
              placeholder="Enter seed or generate random"
              min="0"
              max="2147483647"
              disabled={loading || useRandomSeed}
              className="seed-input"
            />
            <button
              type="button"
              onClick={generateRandomSeed}
              disabled={loading}
              className="generate-seed-btn"
              title="Generate random seed"
              aria-label="Generate random seed"
            >
              🎲
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? 'Generating...' : 'Generate Image'}
        </button>

        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>Generating your image... This may take 10-30 seconds</p>
          </div>
        )}
      </form>

      <div className="form-divider"></div>

      <div className="info-box">
        <h3>🎨 Generate Multiple Images from Templates</h3>
        <p>
          To generate complete sets of themed images (card decks, tarot, zodiac, etc.):
        </p>
        <ol>
          <li>Go to the <strong>Albums</strong> tab</li>
          <li>Filter by <strong>Set Templates</strong></li>
          <li>Click <strong>Generate Batch</strong> on any template</li>
          <li>Enter your art style theme</li>
          <li>Watch your complete themed collection generate!</li>
        </ol>
        <p className="info-note">
          <strong>Note:</strong> Set templates automatically create albums where all generated images are organized together.
        </p>
      </div>
    </div>
  )
}

export default GenerateForm
