import React, { useState, useEffect } from 'react'

function GenerateForm({ onGenerate, onGenerateBatch, loading, config }) {
  const [prompt, setPrompt] = useState('')
  const [steps, setSteps] = useState(config?.generation?.steps || 30)
  const [guidanceScale, setGuidanceScale] = useState(config?.generation?.guidance_scale || 7.5)
  const [seed, setSeed] = useState('')
  const [useRandomSeed, setUseRandomSeed] = useState(true)

  // Batch generation state
  const [availableSets, setAvailableSets] = useState([])
  const [selectedSet, setSelectedSet] = useState('')
  const [userTheme, setUserTheme] = useState('')
  const [selectedSetInfo, setSelectedSetInfo] = useState(null)

  // Load available sets on mount
  useEffect(() => {
    fetchAvailableSets()
  }, [])

  const fetchAvailableSets = async () => {
    try {
      const response = await fetch('/api/sets')
      const data = await response.json()
      setAvailableSets(data.sets || [])
    } catch (error) {
      console.error('Failed to fetch sets:', error)
    }
  }

  const fetchRandomTheme = async () => {
    try {
      const response = await fetch('/api/themes/random')
      const data = await response.json()
      setUserTheme(data.theme || '')
    } catch (error) {
      console.error('Failed to fetch random theme:', error)
    }
  }

  // When set selection changes, load set info
  useEffect(() => {
    if (selectedSet) {
      fetchSetInfo(selectedSet)
    } else {
      setSelectedSetInfo(null)
    }
  }, [selectedSet])

  const fetchSetInfo = async (setName) => {
    try {
      const response = await fetch(`/api/sets/${setName}/info`)
      const data = await response.json()
      setSelectedSetInfo(data)
    } catch (error) {
      console.error('Failed to fetch set info:', error)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (prompt.trim()) {
      const params = {
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

  const generateRandomSeed = () => {
    const randomSeed = Math.floor(Math.random() * 2147483647)
    setSeed(randomSeed.toString())
    setUseRandomSeed(false)
  }

  const handleBatchSubmit = (e) => {
    e.preventDefault()
    if (selectedSet && userTheme.trim()) {
      const params = {
        set_name: selectedSet,
        user_theme: userTheme.trim(),
        steps,
        guidance_scale: guidanceScale
      }

      // Only include seed if user provided one
      if (!useRandomSeed && seed) {
        params.seed = parseInt(seed)
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
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the image you want to generate..."
            rows="4"
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
              onChange={(e) => setSteps(parseInt(e.target.value))}
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
              onChange={(e) => setGuidanceScale(parseFloat(e.target.value))}
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
              onChange={(e) => setSeed(e.target.value)}
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
            onChange={(e) => setSelectedSet(e.target.value)}
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
                {selectedSetInfo && selectedSetInfo.example_theme && (
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
              onChange={(e) => setUserTheme(e.target.value)}
              placeholder="e.g., watercolor mystical forest, ethereal glowing light..."
              rows="3"
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
