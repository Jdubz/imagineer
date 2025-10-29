import React, { useState, useEffect } from 'react'
import { logger } from '../lib/logger'
import '../styles/LorasTab.css'

interface LoraModel {
  folder: string
  filename: string
  format?: string
  default_weight?: number
  has_preview: boolean
  organized_at?: string
}

interface LorasResponse {
  loras: LoraModel[]
}

const LorasTab: React.FC = () => {
  const [loras, setLoras] = useState<LoraModel[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLora, setSelectedLora] = useState<LoraModel | null>(null)

  useEffect(() => {
    fetchLoras()
  }, [])

  const fetchLoras = async (): Promise<void> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/loras')
      if (!response.ok) {
        throw new Error('Failed to fetch LoRAs')
      }
      const data: LorasResponse = await response.json()
      setLoras(data.loras || [])
    } catch (err) {
      logger.error('Failed to fetch LoRAs:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleLoraClick = (lora: LoraModel): void => {
    setSelectedLora(selectedLora?.folder === lora.folder ? null : lora)
  }

  if (loading) {
    return (
      <div className="loras-tab">
        <div className="loras-loading">
          <p>Loading LoRAs...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="loras-tab">
        <div className="loras-error">
          <p>❌ {error}</p>
          <button onClick={fetchLoras} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="loras-tab">
      <div className="loras-header">
        <h2>🎨 LoRA Models</h2>
        <div className="loras-stats">
          <span className="stat">{loras.length} models</span>
          <button onClick={fetchLoras} className="refresh-button" title="Refresh">
            🔄
          </button>
        </div>
      </div>

      {loras.length === 0 ? (
        <div className="loras-empty">
          <p>No LoRAs found. Add .safetensors files to the LoRA directory.</p>
        </div>
      ) : (
        <div className="loras-list">
          {loras.map((lora) => (
            <div
              key={lora.folder}
              className={`lora-item ${selectedLora?.folder === lora.folder ? 'selected' : ''}`}
              onClick={() => handleLoraClick(lora)}
            >
              <div className="lora-item-content">
                {lora.has_preview ? (
                  <div className="lora-thumbnail">
                    <img
                      src={`/api/loras/${lora.folder}/preview`}
                      alt={lora.filename}
                      loading="lazy"
                    />
                  </div>
                ) : (
                  <div className="lora-thumbnail lora-no-thumbnail">
                    <span>🎨</span>
                  </div>
                )}

                <div className="lora-main-info">
                  <h3 className="lora-title" title={lora.filename}>
                    {lora.folder.replace(/_/g, ' ')}
                  </h3>
                  <div className="lora-subtitle">
                    <span className="lora-filename">{lora.filename}</span>
                  </div>
                </div>

                <div className="lora-badges">
                  <span className="badge badge-format">{lora.format || 'SD1.5'}</span>
                  {lora.default_weight && (
                    <span className="badge badge-weight">
                      Weight: {lora.default_weight}
                    </span>
                  )}
                  {lora.has_preview && (
                    <span className="badge badge-success">✓ Preview</span>
                  )}
                </div>
              </div>

              {selectedLora?.folder === lora.folder && (
                <div className="lora-expanded-details">
                  <div className="details-grid">
                    <div className="detail-item">
                      <span className="detail-label">Filename:</span>
                      <span className="detail-value">{lora.filename}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Folder:</span>
                      <span className="detail-value">{lora.folder}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Format:</span>
                      <span className="detail-value">{lora.format || 'SD1.5'}</span>
                    </div>
                    {lora.default_weight && (
                      <div className="detail-item">
                        <span className="detail-label">Default Weight:</span>
                        <span className="detail-value">{lora.default_weight}</span>
                      </div>
                    )}
                    {lora.organized_at && (
                      <div className="detail-item">
                        <span className="detail-label">Organized:</span>
                        <span className="detail-value">
                          {new Date(lora.organized_at).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default LorasTab
