import React, { useState, useEffect, useCallback } from 'react'
import { logger } from '../lib/logger'
import { api, ApiError } from '../lib/api'
import { formatErrorMessage, isAuthError } from '../lib/errorUtils'
import '../styles/LorasTab.css'
import { Button } from '@/components/ui/button'
import { RotateCw } from 'lucide-react'

interface LoraModel {
  folder: string
  filename: string
  format?: string
  default_weight?: number
  has_preview?: boolean
  organized_at?: string
}

const LorasTab: React.FC = () => {
  const [loras, setLoras] = useState<LoraModel[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLora, setSelectedLora] = useState<LoraModel | null>(null)

  const fetchLoras = useCallback(async (): Promise<void> => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.loras.getAll()
      setLoras(data || [])
    } catch (err) {
      if (isAuthError(err)) {
        logger.warn('LoRA catalogue requires admin authentication')
        setError('Admin authentication required to view available LoRAs.')
        return
      }
      logger.error('Failed to fetch LoRAs:', err)
      const errorMessage = formatErrorMessage(err, 'Failed to fetch LoRAs')
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchLoras()
  }, [fetchLoras])

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
          <Button onClick={fetchLoras} variant="outline">
            <RotateCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
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
          <Button onClick={fetchLoras} variant="ghost" size="icon" title="Refresh">
            <RotateCw className="h-4 w-4" />
          </Button>
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
