import React, { useEffect, useRef, useState } from 'react'
import { logger } from '../lib/logger'
import '../styles/LabelingPanel.css'

type Identifier = number | string

interface LabelingPanelProps {
  albumId?: Identifier
  imageId?: Identifier
  onComplete?: () => Promise<void> | void
  variant?: 'default' | 'compact'
}

interface TaskStatus {
  state?: string
  result?: {
    current?: number
    total?: number
    message?: string
    [key: string]: unknown
  }
  [key: string]: unknown
}

type ProgressSnapshot = {
  current?: number
  total?: number
  message?: string
}

const normalizeProgress = (value: unknown): ProgressSnapshot | undefined => {
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return {
      current: typeof record.current === 'number' ? record.current : undefined,
      total: typeof record.total === 'number' ? record.total : undefined,
      message: typeof record.message === 'string' ? record.message : undefined,
    }
  }

  return undefined
}

const LabelingPanel: React.FC<LabelingPanelProps> = ({
  albumId,
  imageId,
  onComplete,
  variant = 'default'
}) => {
  const [isRunning, setIsRunning] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [taskId, setTaskId] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const targetLabel = imageId ? `image #${imageId}` : `album #${albumId}`

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current)
      }
    }
  }, [])

  const resetState = (): void => {
    setIsRunning(false)
    setProgress(0)
    setTaskId(null)
    if (pollRef.current) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const handleError = (message: string): void => {
    setStatusMessage(message)
    resetState()
  }

  const startPolling = (id: string): void => {
    pollRef.current = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/labeling/tasks/${id}`, {
          credentials: 'include'
        })

        if (!response.ok) {
          throw new Error('Failed to fetch task status')
        }

        const data: TaskStatus = await response.json()
        const taskState = data.state ?? 'PENDING'

        if (taskState === 'SUCCESS') {
          setStatusMessage('Labeling complete!')
          setProgress(100)
          if (pollRef.current) {
            window.clearInterval(pollRef.current)
            pollRef.current = null
          }

          if (onComplete) {
            try {
              await onComplete()
            } catch (error) {
              logger.error('Labeling onComplete handler failed:', error)
            }
          }

          setTimeout(() => {
            setStatusMessage('')
            resetState()
          }, 1500)
        } else if (taskState === 'FAILURE') {
          const failureMessage =
            (data.result && typeof data.result === 'object' && 'message' in data.result
              ? String(data.result.message)
              : 'Labeling failed')
          handleError(failureMessage)
        } else if (taskState === 'PROGRESS') {
          const progressSnapshot =
            normalizeProgress(data.progress) ?? normalizeProgress(data.result) ?? {}
          const { current, total, message } = progressSnapshot
          if (typeof current === 'number' && typeof total === 'number' && total > 0) {
            setProgress(Math.min(100, Math.round((current / total) * 100)))
            setStatusMessage(`Labeled ${current} of ${total} images...`)
          } else if (message) {
            setStatusMessage(String(message))
          } else {
            setStatusMessage('Labeling in progress...')
          }
        } else {
          setStatusMessage(`Status: ${taskState}`)
        }
      } catch (error) {
        logger.error('Polling error:', error)
        handleError('Failed to poll labeling status')
      }
    }, 2000)
  }

  const startLabeling = async (): Promise<void> => {
    if (isRunning) return

    if (!albumId && !imageId) {
      handleError('Missing album or image identifier')
      return
    }

    setIsRunning(true)
    setStatusMessage('Starting labeling...')
    setProgress(0)

    try {
      const endpoint = imageId
        ? `/api/labeling/image/${imageId}`
        : `/api/labeling/album/${albumId}`

      const payload = {
        prompt_type: 'sd_training',
        ...(albumId ? { force: false } : {})
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      })

      const data = await response.json().catch(() => ({}))

      if (response.status === 202 && data.task_id) {
        setTaskId(data.task_id)
        setStatusMessage('Labeling queued...')
        startPolling(data.task_id)
      } else if (response.ok) {
        setStatusMessage('Labeling complete!')
        setProgress(100)
        if (onComplete) {
          await Promise.resolve(onComplete())
        }
        setTimeout(() => {
          setStatusMessage('')
          resetState()
        }, 1500)
      } else {
        const errorMessage = typeof data.error === 'string' ? data.error : 'Labeling failed'
        handleError(errorMessage)
      }
    } catch (error) {
      logger.error('Labeling request failed:', error)
      handleError('Failed to start labeling task')
    }
  }

  if (variant === 'compact') {
    return (
      <div className="labeling-panel compact">
        <button
          className="labeling-trigger"
          onClick={() => void startLabeling()}
          disabled={isRunning}
          title={isRunning ? 'Labeling in progress' : 'Label this image'}
        >
          {isRunning ? 'Labeling…' : 'Label image'}
        </button>
        {statusMessage && <p className="status-text">{statusMessage}</p>}
      </div>
    )
  }

  return (
    <div className="labeling-panel">
      <h3>🏷️ AI Labeling</h3>
      <p className="help-text">
        Trigger Claude to caption, tag, and classify {targetLabel}.
      </p>

      <div className="labeling-actions">
        <button
          className="labeling-button"
          onClick={() => void startLabeling()}
          disabled={isRunning}
        >
          {isRunning ? 'Labeling…' : 'Start Labeling'}
        </button>
        {taskId && (
          <span className="task-id" aria-live="polite">
            Task ID: {taskId}
          </span>
        )}
      </div>

      <div className="labeling-progress">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        {statusMessage && <p className="status-text">{statusMessage}</p>}
      </div>
    </div>
  )
}

export default LabelingPanel
