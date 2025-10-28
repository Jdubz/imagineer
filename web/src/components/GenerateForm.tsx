import React, { useState, useEffect } from 'react'
import type { Config, GenerateParams, BatchGenerateParams } from '../types/models'

interface SetLoraConfig {
  folder: string
  weight: number
}

interface SetInfo {
  name: string
  description: string
  item_count: number
  example_theme?: string
}

interface AvailableSet {
  id: string
  name: string
}

interface LoraModel {
  folder: string
  filename: string
}

interface GenerateFormProps {
  onGenerate: (params: GenerateParams) => void
  onGenerateBatch: (params: BatchGenerateParams) => void
  loading: boolean
  config: Config | null
}

const GenerateForm: React.FC<GenerateFormProps> = ({ onGenerate, onGenerateBatch, loading, config }) => {
  const [prompt, setPrompt] = useState<string>('')
  const [steps, setSteps] = useState<number>(config?.generation?.steps || 30)
  const [guidanceScale, setGuidanceScale] = useState<number>(config?.generation?.guidance_scale || 7.5)
  const [seed, setSeed] = useState<string>('')
  const [useRandomSeed, setUseRandomSeed] = useState<boolean>(true)

  // Batch generation state
  const [availableSets, setAvailableSets] = useState<AvailableSet[]>([])
  const [selectedSet, setSelectedSet] = useState<string>('')
  const [userTheme, setUserTheme] = useState<string>('')
  const [selectedSetInfo, setSelectedSetInfo] = useState<SetInfo | null>(null)

  // LoRA configuration state
  const [setLoras, setSetLoras] = useState<SetLoraConfig[]>([])
  const [availableLoras, setAvailableLoras] = useState<LoraModel[]>([])
  const [showLoraConfig, setShowLoraConfig] = useState<boolean>(false)

  // Load available sets and LoRAs on mount
  useEffect(() => {
    fetchAvailableSets()
    fetchAvailableLoras()
  }, [])

  const fetchAvailableSets = async (): Promise<void> => {
    try {
      const response = await fetch('/api/sets')
      const data = await response.json()
      setAvailableSets(data.sets || [])
    } catch (error) {
      console.error('Failed to fetch sets:', error)
    }
  }

  const fetchAvailableLoras = async (): Promise<void> => {
    try {
      const response = await fetch('/api/loras')
      const data = await response.json()
      setAvailableLoras(data.loras || [])
    } catch (error) {
      console.error('Failed to fetch LoRAs:', error)
    }
  }

  const fetchRandomTheme = async (): Promise<void> => {
    try {
      const response = await fetch('/api/themes/random')
      const data = await response.json()
      setUserTheme(data.theme || '')
    } catch (error) {
      console.error('Failed to fetch random theme:', error)
    }
  }

  // When set selection changes, load set info and LoRAs
  useEffect(() => {
    if (selectedSet) {
      fetchSetInfo(selectedSet)
      fetchSetLoras(selectedSet)
    } else {
      setSelectedSetInfo(null)
      setSetLoras([])
    }
  }, [selectedSet])

  const fetchSetInfo = async (setName: string): Promise<void> => {
    try {
      const response = await fetch(`/api/sets/${setName}/info`)
      const data = await response.json()
      setSelectedSetInfo(data)
    } catch (error) {
      console.error('Failed to fetch set info:', error)
    }
  }

  const fetchSetLoras = async (setName: string): Promise<void> => {
    try {
      const response = await fetch(`/api/sets/${setName}/loras`)
      const data = await response.json()
      setSetLoras(data.loras || [])
    } catch (error) {
      console.error('Failed to fetch set LoRAs:', error)
    }
  }

  const updateSetLoras = async (setName: string, loras: SetLoraConfig[]): Promise<void> => {
    try {
      const response = await fetch(`/api/sets/${setName}/loras`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ loras })
      })
      const data = await response.json()
      if (data.success) {
        fetchSetLoras(setName)  // Refresh the list
      } else {
        console.error('Failed to update LoRAs:', data.error)
        alert(`Error: ${data.error}`)
      }
    } catch (error) {
      console.error('Failed to update set LoRAs:', error)
      alert('Failed to update LoRA configuration')
    }
  }

  const addLoraToSet = (loraFolder: string): void => {
    if (!selectedSet || !loraFolder) return

    // Check if already in set
    if (setLoras.some(l => l.folder === loraFolder)) {
      alert('This LoRA is already in the set')
      return
    }

    const updatedLoras = [
      ...setLoras,
      { folder: loraFolder, weight: 0.5 }
    ]

    updateSetLoras(selectedSet, updatedLoras)
  }

  const removeLoraFromSet = (loraFolder: string): void => {
    if (!selectedSet) return

    const updatedLoras = setLoras.filter(l => l.folder !== loraFolder)
    updateSetLoras(selectedSet, updatedLoras)
  }

  const updateLoraWeight = (loraFolder: string, newWeight: string): void => {
    if (!selectedSet) return

    const updatedLoras = setLoras.map(l =>
      l.folder === loraFolder ? { ...l, weight: parseFloat(newWeight) } : l
    )

    setSetLoras(updatedLoras)  // Update UI immediately
  }

  const saveLoraWeights = (): void => {
    if (!selectedSet) return
    updateSetLoras(selectedSet, setLoras)
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (prompt.trim()) {
      const params: GenerateParams = {
        prompt: prompt.trim(),
        steps,
        guidance_scale: guidanceScale
      }

      // Only include seed if user provided one
      if (!useRandomSeed && seed) {
        params.seed = parseInt(seed)
      }

      onGenerate(params)
      setPrompt('')
    }
  }

  const generateRandomSeed = (): void => {
    const randomSeed = Math.floor(Math.random() * 2147483647)
    setSeed(randomSeed.toString())
    setUseRandomSeed(false)
  }

  const handleBatchSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (selectedSet && userTheme.trim()) {
      const params: BatchGenerateParams = {
        set_name: selectedSet,
        user_theme: userTheme.trim(),
        steps,
        guidance_scale: guidanceScale
      }

      onGenerateBatch(params)
      setUserTheme('')
    }
  }

  return (
    <div className="generate-form">
      <h2>Generate Image</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setPrompt(e.target.value)}
            placeholder="Describe the image you want to generate..."
            rows={4}
            disabled={loading}
            required
          />
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

      <h2>Generate Set</h2>
      <form onSubmit={handleBatchSubmit} className="batch-form">
        <div className="form-group">
          <label htmlFor="set-select">
            Select Set
            <span className="tooltip">?
              <span className="tooltip-text">
                Choose a predefined set (e.g., card deck, tarot deck) to generate multiple images.
                <br/>Each item in the set will be styled with your art theme.
              </span>
            </span>
          </label>
          <select
            id="set-select"
            value={selectedSet}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedSet(e.target.value)}
            disabled={loading}
            required
          >
            <option value="">-- Select a set --</option>
            {availableSets.map((set) => (
              <option key={set.id} value={set.id}>
                {set.name}
              </option>
            ))}
          </select>
          {selectedSetInfo && (
            <p className="set-info">
              {selectedSetInfo.description} ({selectedSetInfo.item_count} items)
            </p>
          )}
        </div>

        {selectedSet && (
          <div className="form-group lora-config-section">
            <div className="lora-header">
              <label>
                LoRA Configuration
                <span className="tooltip">?
                  <span className="tooltip-text">
                    Configure which LoRAs to apply to this set and their influence weights.
                    <br/>• Weight 0.0 = No effect
                    <br/>• Weight 0.5 = Moderate effect (recommended)
                    <br/>• Weight 1.0 = Strong effect
                    <br/>• Weight 1.5+ = Very strong (may distort)
                  </span>
                </span>
              </label>
              <button
                type="button"
                onClick={() => setShowLoraConfig(!showLoraConfig)}
                className="toggle-lora-btn"
              >
                {showLoraConfig ? '▼ Hide' : '▶ Show'} LoRAs ({setLoras.length})
              </button>
            </div>

            {showLoraConfig && (
              <>
                {setLoras.length === 0 ? (
                  <p className="no-loras-message">No LoRAs configured for this set. Add one below.</p>
                ) : (
                  <div className="lora-list">
                    {setLoras.map((lora) => {
                      const loraInfo = availableLoras.find(l => l.folder === lora.folder)
                      return (
                        <div key={lora.folder} className="lora-item">
                          <div className="lora-info">
                            <span className="lora-name">{loraInfo?.filename || lora.folder}</span>
                          </div>
                          <div className="lora-controls">
                            <label htmlFor={`weight-${lora.folder}`} className="weight-label">
                              Weight: {lora.weight.toFixed(2)}
                            </label>
                            <input
                              type="range"
                              id={`weight-${lora.folder}`}
                              min="0"
                              max="2"
                              step="0.05"
                              value={lora.weight}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateLoraWeight(lora.folder, e.target.value)}
                              onMouseUp={saveLoraWeights}
                              onTouchEnd={saveLoraWeights}
                              className="weight-slider"
                              disabled={loading}
                            />
                            <button
                              type="button"
                              onClick={() => removeLoraFromSet(lora.folder)}
                              className="remove-lora-btn"
                              disabled={loading}
                              title="Remove LoRA"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}

                <div className="add-lora-section">
                  <label htmlFor="add-lora-select">Add LoRA:</label>
                  <select
                    id="add-lora-select"
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                      if (e.target.value) {
                        addLoraToSet(e.target.value)
                        e.target.value = ''  // Reset selection
                      }
                    }}
                    disabled={loading}
                    className="add-lora-select"
                  >
                    <option value="">-- Select LoRA to Add --</option>
                    {availableLoras
                      .filter(lora => !setLoras.some(sl => sl.folder === lora.folder))
                      .map(lora => (
                        <option key={lora.folder} value={lora.folder}>
                          {lora.filename || lora.folder}
                        </option>
                      ))}
                  </select>
                </div>
              </>
            )}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="user-theme">
            Art Style Theme
            <span className="tooltip">?
              <span className="tooltip-text">
                Describe the artistic style and atmosphere for your card set.
                <br/><br/>Examples:
                <br/>• "watercolor pastels with soft dreamy lighting"
                <br/>• "cyberpunk neon with dark urban background"
                <br/>• "vintage botanical illustrations"
                {selectedSetInfo?.example_theme && (
                  <>
                    <br/><br/>Suggestion for {selectedSetInfo.name}:
                    <br/>"{selectedSetInfo.example_theme}"
                  </>
                )}
              </span>
            </span>
          </label>
          <div className="theme-input-group">
            <textarea
              id="user-theme"
              value={userTheme}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setUserTheme(e.target.value)}
              placeholder="e.g., watercolor mystical forest, ethereal glowing light..."
              rows={3}
              disabled={loading}
              required
            />
            <button
              type="button"
              onClick={fetchRandomTheme}
              disabled={loading}
              className="random-theme-btn"
              title="Generate random theme"
            >
              🎲 Random Theme
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading || !selectedSet || !userTheme.trim()} className="batch-submit-btn">
          {loading ? 'Generating Set...' : 'Generate Complete Set'}
        </button>

        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>Queuing batch generation... This will create multiple jobs</p>
          </div>
        )}
      </form>
    </div>
  )
}

export default GenerateForm
