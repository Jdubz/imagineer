import React, { useEffect, useRef, useState } from 'react'
import { logger } from '../lib/logger'
import { getApiUrl } from '../lib/apiConfig'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tag } from 'lucide-react'

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
        const response = await fetch(getApiUrl(`/api/labeling/tasks/${id}`), {
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

      const response = await fetch(getApiUrl(endpoint), {
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
      <div className="absolute left-2 bottom-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void startLabeling()}
          disabled={isRunning}
          title={isRunning ? 'Labeling in progress' : 'Label this image'}
        >
          <Tag className="h-3 w-3 mr-1" />
          {isRunning ? 'Labeling…' : 'Label image'}
        </Button>
        {statusMessage && (
          <p className="text-xs text-muted-foreground mt-1">{statusMessage}</p>
        )}
      </div>
    )
  }

  return (
    <div className="bg-muted border border-border rounded-lg p-4 mt-4 max-w-[420px]">
      <h3 className="m-0 mb-2 text-foreground text-lg">🏷️ AI Labeling</h3>
      <p className="m-0 text-muted-foreground text-sm">
        Trigger Claude to caption, tag, and classify {targetLabel}.
      </p>

      <div className="flex items-center gap-3 mt-4 flex-wrap">
        <Button
          onClick={() => void startLabeling()}
          disabled={isRunning}
        >
          <Tag className="h-4 w-4 mr-2" />
          {isRunning ? 'Labeling…' : 'Start Labeling'}
        </Button>
        {taskId && (
          <Badge variant="secondary" className="font-mono text-xs" aria-live="polite">
            Task ID: {taskId}
          </Badge>
        )}
      </div>

      <div className="mt-4">
        <Progress value={progress} className="w-full h-2.5" />
        {statusMessage && (
          <p className="mt-2 m-0 text-foreground text-sm">{statusMessage}</p>
        )}
      </div>
    </div>
  )
}

export default LabelingPanel
