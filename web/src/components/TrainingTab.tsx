import React, { useState, useEffect, useCallback, useRef } from 'react'
import { logger } from '../lib/logger'
import { usePolling } from '../hooks/usePolling'
import '../styles/TrainingTab.css'
import type { TrainingJob, JobStatus } from '../types/models'

// Helper function to clamp progress values between 0 and 100
const clampProgress = (value: number | null | undefined): number => {
  if (typeof value !== 'number') return 0
  return Math.min(100, Math.max(0, value))
}

interface TrainingAlbum {
  id: string
  name: string
  image_count: number
}

interface TrainingConfig {
  steps: number
  rank: number
  learning_rate: number
  batch_size: number
}

interface TrainingFormData {
  name: string
  description: string
  album_ids: string[]
  config: TrainingConfig
}

interface TrainingRunsResponse {
  training_runs: TrainingJob[]
}

interface AlbumsResponse {
  albums: TrainingAlbum[]
}

interface TrainingLogResponse {
  training_run_id: number
  status: JobStatus
  progress: number
  error_message?: string | null
  log_path: string
  log_available: boolean
  logs: string
}

interface TrainingTabProps {
  isAdmin?: boolean
}

interface TrainingLogState {
  runId: string | null
  content: string
  status: JobStatus | null
  logAvailable: boolean
  logPath: string
  loading: boolean
  error: string | null
}

type TrainingConfigDetails = Partial<TrainingConfig> & {
  album_ids?: Array<string | number>
  [key: string]: unknown
}

type CopyField = 'dataset' | 'output' | 'checkpoint'

type CopyFeedback = {
  runId: string
  field: CopyField
} | null

const parseTrainingConfig = (
  config: TrainingJob['training_config'],
): TrainingConfigDetails | undefined => {
  if (!config) return undefined

  if (typeof config === 'string') {
    try {
      const parsed = JSON.parse(config)
      return parsed && typeof parsed === 'object' ? (parsed as TrainingConfigDetails) : undefined
    } catch {
      return undefined
    }
  }

  if (typeof config === 'object') {
    return config as TrainingConfigDetails
  }

  return undefined
}

const TrainingTab: React.FC<TrainingTabProps> = ({ isAdmin = false }) => {
  const [trainingRuns, setTrainingRuns] = useState<TrainingJob[]>([])
  const [albums, setAlbums] = useState<TrainingAlbum[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState<boolean>(false)
  const [logState, setLogState] = useState<TrainingLogState>({
    runId: null,
    content: '',
    status: null,
    logAvailable: false,
    logPath: '',
    loading: false,
    error: null,
  })
  const copyTimeoutRef = useRef<number | null>(null)
  const [copyFeedback, setCopyFeedback] = useState<CopyFeedback>(null)

  // Form state for creating training runs
  const [formData, setFormData] = useState<TrainingFormData>({
    name: '',
    description: '',
    album_ids: [],
    config: {
      steps: 1000,
      rank: 4,
      learning_rate: 0.0001,
      batch_size: 1
    }
  })

  const fetchTrainingRuns = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      setLoading(true)
      const response = await fetch('/api/training', {
        credentials: 'include',
      })
      const data: TrainingRunsResponse = await response.json()
      setTrainingRuns(data.training_runs || [])
    } catch (err) {
      setError('Failed to fetch training runs')
      logger.error('Error fetching training runs:', err)
    } finally {
      setLoading(false)
    }
  }, [isAdmin])

  const fetchAlbums = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch('/api/training/albums', {
        credentials: 'include',
      })
      const data: AlbumsResponse = await response.json()
      setAlbums(data.albums || [])
    } catch (err) {
      logger.error('Error fetching albums:', err)
    }
  }, [isAdmin])

  // Initial fetch on mount
  useEffect(() => {
    if (!isAdmin) {
      setLoading(false)
      return
    }
    fetchTrainingRuns().catch((err) => logger.error('Error refreshing runs:', err))
    fetchAlbums().catch((err) => logger.error('Error refreshing albums:', err))
  }, [fetchAlbums, fetchTrainingRuns, isAdmin])

  const fetchTrainingLogs = useCallback(async (runId: string | number): Promise<void> => {
    const runIdStr = String(runId)
    setLogState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetch(`/api/training/${runIdStr}/logs?tail=500`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch logs (status ${response.status})`)
      }

      const data: TrainingLogResponse = await response.json()
      setLogState((prev) => ({
        ...prev,
        runId: runIdStr,
        loading: false,
        content: data.logs ?? '',
        status: data.status,
        logAvailable: data.log_available,
        logPath: data.log_path,
        error: null,
      }))

      // Stop polling if training is complete
      if (!['running', 'queued'].includes(data.status)) {
        setLogState((prev) => ({ ...prev, runId: null }))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load logs'
      setLogState((prev) => ({ ...prev, loading: false, error: message }))
    }
  }, [])

  const openLogViewer = useCallback(
    (runId: string | number) => {
      const runIdStr = String(runId)
      setLogState({
        runId: runIdStr,
        content: '',
        status: null,
        logAvailable: false,
        logPath: '',
        loading: true,
        error: null,
      })
      fetchTrainingLogs(runIdStr).catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load logs'
        setLogState((prev) => ({ ...prev, loading: false, error: message }))
      })
    },
    [fetchTrainingLogs],
  )

  // Polling for training logs with proper cleanup
  const pollLogs = useCallback(async () => {
    if (logState.runId) {
      await fetchTrainingLogs(logState.runId).catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load logs'
        setLogState((prev) => ({ ...prev, loading: false, error: message }))
      })
    }
  }, [logState.runId, fetchTrainingLogs])

  usePolling(pollLogs, {
    interval: 5000,
    enabled: logState.runId !== null,
    pauseWhenHidden: true,
  })
  useEffect(
    () => () => {
      if (copyTimeoutRef.current) {
        window.clearTimeout(copyTimeoutRef.current)
      }
    },
    [],
  )

  const closeLogViewer = useCallback(() => {
    // Setting runId to null will automatically stop the polling
    setLogState({
      runId: null,
      content: '',
      status: null,
      logAvailable: false,
      logPath: '',
      loading: false,
      error: null,
    })
  }, [])

  const handleCopy = useCallback(
    (value: string, runId: number | string, field: CopyField) => {
      if (!value) return
      const runIdStr = String(runId)
      const fallbackCopy = () => {
        const textarea = document.createElement('textarea')
        textarea.value = value
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        try {
          document.execCommand('copy')
        } finally {
          document.body.removeChild(textarea)
        }
      }

      if (navigator?.clipboard?.writeText) {
        navigator.clipboard.writeText(value).catch(fallbackCopy)
      } else {
        fallbackCopy()
      }

      if (copyTimeoutRef.current) {
        window.clearTimeout(copyTimeoutRef.current)
      }

      setCopyFeedback({ runId: runIdStr, field })
      copyTimeoutRef.current = window.setTimeout(() => {
        setCopyFeedback(null)
        copyTimeoutRef.current = null
      }, 2000)
    },
    [],
  )

  const handleCreateTraining = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    if (!isAdmin) return

    try {
      const response = await fetch('/api/training', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData),
      })

      if (response.ok) {
        setShowCreateDialog(false)
        setFormData({
          name: '',
          description: '',
          album_ids: [],
          config: {
            steps: 1000,
            rank: 4,
            learning_rate: 0.0001,
            batch_size: 1
          }
        })
        fetchTrainingRuns()
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to create training run')
      }
    } catch (err) {
      setError('Failed to create training run')
      logger.error('Error creating training run:', err)
    }
  }

  const handleStartTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch(`/api/training/${String(runId)}/start`, {
        method: 'POST',
        credentials: 'include',
      })

      if (response.ok) {
        fetchTrainingRuns()
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to start training')
      }
    } catch (err) {
      setError('Failed to start training')
      logger.error('Error starting training:', err)
    }
  }

  const handleCancelTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch(`/api/training/${String(runId)}/cancel`, {
        method: 'POST',
        credentials: 'include',
      })

      if (response.ok) {
        fetchTrainingRuns()
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to cancel training')
      }
    } catch (err) {
      setError('Failed to cancel training')
      logger.error('Error cancelling training:', err)
    }
  }

  const handleCleanupTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch(`/api/training/${String(runId)}/cleanup`, {
        method: 'POST',
        credentials: 'include',
      })

      if (response.ok) {
        fetchTrainingRuns()
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to cleanup training')
      }
    } catch (err) {
      setError('Failed to cleanup training')
      logger.error('Error cleaning up training:', err)
    }
  }

  const getStatusColor = (status: JobStatus): string => {
    switch (status) {
      case 'completed': return '#4CAF50'
      case 'running': return '#2196F3'
      case 'failed': return '#F44336'
      case 'cancelled': return '#FF9800'
      case 'queued': return '#FFC107'
      default: return '#9E9E9E'
    }
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  if (!isAdmin) {
    return (
      <div className="training-tab">
        <div className="training-access-message">
          <h2>LoRA Training</h2>
          <p>Sign in with an admin account to manage training runs.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="training-tab">
        <div className="loading">Loading training runs...</div>
      </div>
    )
  }

  return (
    <div className="training-tab">
      <div className="training-header">
        <h2>LoRA Training Pipeline</h2>
        {isAdmin && (
          <button
            className="create-button"
            onClick={() => setShowCreateDialog(true)}
          >
            Create Training Run
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="training-runs">
        {trainingRuns.length === 0 ? (
          <div className="no-runs">
            <p>No training runs found. {isAdmin && 'Create your first training run to get started!'}</p>
          </div>
        ) : (
          trainingRuns.map((run) => {
            const config = parseTrainingConfig(run.training_config)
            const maybeAlbumIds = Array.isArray(config?.album_ids) ? config?.album_ids : undefined
            const runIdStr = String(run.id)
            const errorMessage = run.error_message ?? run.error ?? null
            const progressPercent = clampProgress(run.progress)

            return (
              <div key={run.id} className="training-run-card">
                <div className="run-header">
                  <h3>{run.name || `Training run ${runIdStr}`}</h3>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(run.status) }}
                  >
                    {run.status.toUpperCase()}
                  </span>
                </div>

                {run.description && (
                  <p className="run-description">{run.description}</p>
                )}

                <div className="run-details">
                  <div className="detail-item">
                    <strong>Progress:</strong> {progressPercent}%
                  </div>
                  <div className="detail-item">
                    <strong>Created:</strong> {formatDate(run.created_at)}
                  </div>
                  {run.started_at && (
                    <div className="detail-item">
                      <strong>Started:</strong> {formatDate(run.started_at)}
                    </div>
                  )}
                  {run.completed_at && (
                    <div className="detail-item">
                      <strong>Completed:</strong> {formatDate(run.completed_at)}
                    </div>
                  )}
                </div>

                {run.status === 'running' && typeof run.progress === 'number' && (
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${progressPercent}%` }}
                    ></div>
                  </div>
                )}

                <div className="asset-section">
                  <div className="asset-item">
                    <div className="asset-header">
                      <strong>Dataset directory</strong>
                      <button
                        type="button"
                        className="copy-button"
                        onClick={() => handleCopy(run.dataset_path ?? '', run.id, 'dataset')}
                      >
                        Copy
                      </button>
                      {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'dataset' && (
                        <span className="copy-feedback">Copied!</span>
                      )}
                    </div>
                    <code>{run.dataset_path || 'Unavailable'}</code>
                  </div>

                  <div className="asset-item">
                    <div className="asset-header">
                      <strong>Output directory</strong>
                      <button
                        type="button"
                        className="copy-button"
                        onClick={() => handleCopy(run.output_path ?? '', run.id, 'output')}
                      >
                        Copy
                      </button>
                      {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'output' && (
                        <span className="copy-feedback">Copied!</span>
                      )}
                    </div>
                    <code>{run.output_path || 'Unavailable'}</code>
                  </div>

                  <div className="asset-item">
                    <div className="asset-header">
                      <strong>Final checkpoint</strong>
                      {run.final_checkpoint && (
                        <>
                          <button
                            type="button"
                            className="copy-button"
                            onClick={() => handleCopy(run.final_checkpoint || '', run.id, 'checkpoint')}
                          >
                            Copy
                          </button>
                          {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'checkpoint' && (
                            <span className="copy-feedback">Copied!</span>
                          )}
                        </>
                      )}
                    </div>
                    <code>{run.final_checkpoint ?? 'Generated after completion'}</code>
                  </div>

                  {config && (
                    <div className="asset-item">
                      <div className="asset-header">
                        <strong>Training configuration</strong>
                      </div>
                      <div className="config-summary">
                        {typeof config.steps === 'number' && <span>Steps: {config.steps}</span>}
                        {typeof config.rank === 'number' && <span>Rank: {config.rank}</span>}
                        {typeof config.learning_rate === 'number' && (
                          <span>Learning rate: {config.learning_rate}</span>
                        )}
                        {typeof config.batch_size === 'number' && <span>Batch size: {config.batch_size}</span>}
                        {maybeAlbumIds && maybeAlbumIds.length > 0 && (
                          <span>Albums: {maybeAlbumIds.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {errorMessage && (
                  <div className="error-details">
                    <strong>Error:</strong> {errorMessage}
                  </div>
                )}

                {isAdmin && (
                  <div className="run-actions">
                    {run.status === 'queued' && (
                      <button
                        className="action-button start"
                        onClick={() => handleStartTraining(run.id)}
                      >
                        Start Training
                      </button>
                    )}

                    {(run.status === 'queued' || run.status === 'running') && (
                      <button
                        className="action-button cancel"
                        onClick={() => handleCancelTraining(run.id)}
                      >
                        Cancel
                      </button>
                    )}

                    {(run.status === 'completed' || run.status === 'failed') && (
                      <button
                        className="action-button cleanup"
                        onClick={() => handleCleanupTraining(run.id)}
                      >
                        Cleanup
                      </button>
                    )}
                    <button
                      className="action-button logs"
                      onClick={() => openLogViewer(run.id)}
                    >
                      View Logs
                    </button>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Create Training Dialog */}
      {showCreateDialog && (
        <div className="dialog-overlay">
          <div className="dialog">
            <div className="dialog-header">
              <h3>Create Training Run</h3>
              <button
                className="close-button"
                onClick={() => setShowCreateDialog(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateTraining} className="training-form">
              <div className="form-group">
                <label htmlFor="name">Name *</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFormData({...formData, description: e.target.value})}
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Training Albums *</label>
                <div className="album-selection">
                  {albums.map((album) => (
                    <label key={album.id} className="album-checkbox">
                      <input
                        type="checkbox"
                        checked={formData.album_ids.includes(album.id)}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              album_ids: [...formData.album_ids, album.id]
                            })
                          } else {
                            setFormData({
                              ...formData,
                              album_ids: formData.album_ids.filter(id => id !== album.id)
                            })
                          }
                        }}
                      />
                      <span>{album.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="steps">Training Steps</label>
                <input
                  type="number"
                  id="steps"
                  value={formData.config.steps}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({
                    ...formData,
                    config: {...formData.config, steps: parseInt(e.target.value)}
                  })}
                  min="100"
                  max="10000"
                />
              </div>

              <div className="form-group">
                <label htmlFor="rank">LoRA Rank</label>
                <input
                  type="number"
                  id="rank"
                  value={formData.config.rank}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({
                    ...formData,
                    config: {...formData.config, rank: parseInt(e.target.value)}
                  })}
                  min="1"
                  max="64"
                />
              </div>

              <div className="form-group">
                <label htmlFor="learning_rate">Learning Rate</label>
                <input
                  type="number"
                  id="learning_rate"
                  value={formData.config.learning_rate}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({
                    ...formData,
                    config: {...formData.config, learning_rate: parseFloat(e.target.value)}
                  })}
                  step="0.0001"
                  min="0.0001"
                  max="0.01"
                />
              </div>

              <div className="form-group">
                <label htmlFor="batch_size">Batch Size</label>
                <input
                  type="number"
                  id="batch_size"
                  value={formData.config.batch_size}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({
                    ...formData,
                    config: {...formData.config, batch_size: parseInt(e.target.value)}
                  })}
                  min="1"
                  max="8"
                />
              </div>

              <div className="form-actions">
                <button type="button" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </button>
                <button type="submit" disabled={formData.album_ids.length === 0}>
                  Create Training Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {logState.runId && (
        <div className="dialog-overlay" role="dialog" aria-modal="true">
          <div className="dialog log-dialog">
            <div className="dialog-header">
              <h3>Training Logs</h3>
              <button className="close-button" onClick={closeLogViewer} aria-label="Close logs">
                ×
              </button>
            </div>

            <div className="log-meta">
              <div>
                <strong>Run ID:</strong> {logState.runId}
              </div>
              {logState.status && (
                <div>
                  <strong>Status:</strong> {logState.status.toUpperCase()}
                </div>
              )}
              {logState.logPath && (
                <div className="log-path">
                  <strong>Log file:</strong> {logState.logPath}
                </div>
              )}
            </div>

            <div className="log-body">
              {logState.loading ? (
                <div className="log-loading">Loading logs...</div>
              ) : logState.error ? (
                <div className="log-error">{logState.error}</div>
              ) : logState.logAvailable ? (
                <pre className="log-content">{logState.content || 'No log output yet.'}</pre>
              ) : (
                <div className="log-empty">Logs are not available yet for this run.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TrainingTab
