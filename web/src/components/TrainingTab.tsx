import React, { useState, useEffect, useCallback, useRef } from 'react'
import { logger } from '../lib/logger'
import { usePolling } from '../hooks/usePolling'
import type { TrainingJob, JobStatus, TrainingAlbum } from '../types/models'
import Spinner from './Spinner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { FormField } from '@/components/form'
import { Plus, X, Play, StopCircle, Trash2, FileText, Copy } from 'lucide-react'
import { useToast } from '../hooks/use-toast'
import { api, ApiError } from '@/lib/api'
import { formatErrorMessage } from '@/lib/errorUtils'
import { clampPercentOrDefault, getJobStatusColor } from '@/lib/adminJobs'
import { cn } from '@/lib/utils'

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
  const { toast } = useToast()
  const notifyError = useCallback(
    (title: string, message: string) => {
      toast({
        variant: 'destructive',
        title,
        description: message,
      })
    },
    [toast],
  )
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
  const toggleAlbumSelection = useCallback((albumId: string | number) => {
    const id = String(albumId)
    setFormData((prev) => {
      const exists = prev.album_ids.includes(id)
      return {
        ...prev,
        album_ids: exists ? prev.album_ids.filter((value) => value !== id) : [...prev.album_ids, id],
      }
    })
  }, [])

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
      const runs = await api.training.getRuns()
      setTrainingRuns(runs)
      setError(null)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setTrainingRuns([])
        setError('Admin access required to manage training runs.')
      } else {
        const message = formatErrorMessage(err, 'Failed to fetch training runs')
        setError(message)
        notifyError('Failed to fetch training runs', message)
      }
      logger.error('Error fetching training runs:', err)
    } finally {
      setLoading(false)
    }
  }, [isAdmin, notifyError])

  const fetchAlbums = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const albumList = await api.training.getAlbums()
      setAlbums(albumList)
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
      const data = await api.training.getLogs(runIdStr, { tail: 500 })
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
      const message = formatErrorMessage(err, 'Failed to load logs')
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
      await api.training.createRun(formData)
      setShowCreateDialog(false)
      setFormData({
        name: '',
        description: '',
        album_ids: [],
        config: {
          steps: 1000,
          rank: 4,
          learning_rate: 0.0001,
          batch_size: 1,
        },
      })
      setError(null)
      toast({
        title: 'Training run created',
        description: formData.name
          ? `Queued "${formData.name}" for training.`
          : 'Queued new training run.',
      })
      await fetchTrainingRuns()
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to create training run')
      setError(message)
      notifyError('Failed to create training run', message)
      logger.error('Error creating training run:', err)
    }
  }

  const handleStartTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      await api.training.startRun(runId)
      await fetchTrainingRuns()
      toast({
        title: 'Training run started',
        description: `Run ${runId} is now running.`,
      })
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to start training')
      setError(message)
      notifyError('Failed to start training', message)
      logger.error('Error starting training:', err)
    }
  }

  const handleCancelTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      await api.training.cancelRun(runId)
      await fetchTrainingRuns()
      toast({
        title: 'Training run cancelled',
        description: `Run ${runId} has been cancelled.`,
      })
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to cancel training')
      setError(message)
      notifyError('Failed to cancel training', message)
      logger.error('Error cancelling training:', err)
    }
  }

  const handleCleanupTraining = async (runId: number | string): Promise<void> => {
    if (!isAdmin) return
    try {
      await api.training.cleanupRun(runId)
      await fetchTrainingRuns()
      toast({
        title: 'Training artifacts cleaned',
        description: `Removed artifacts for run ${runId}.`,
      })
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to cleanup training')
      setError(message)
      notifyError('Failed to clean up training', message)
      logger.error('Error cleaning up training:', err)
    }
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const logDialogOpen = logState.runId !== null

  if (!isAdmin) {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>LoRA Training</CardTitle>
            <CardDescription>Sign in with an admin account to manage training runs.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Contact an administrator if you need access to launch or monitor training jobs.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex min-h-[240px] w-full items-center justify-center py-16">
        <Spinner size="large" message="Loading training runs..." />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">LoRA Training Pipeline</h2>
          <p className="text-sm text-muted-foreground">
            Launch new LoRA training runs, monitor progress, and review generated artifacts.
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Training Run
        </Button>
      </div>

      {error ? (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>{error}</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
            className="text-destructive hover:text-destructive"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : null}

      <div className="grid gap-4">
        {trainingRuns.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center text-muted-foreground">
              No training runs found. Create your first training run to get started!
            </CardContent>
          </Card>
        ) : (
          trainingRuns.map((run) => {
            const config = parseTrainingConfig(run.training_config)
            const maybeAlbumIds = Array.isArray(config?.album_ids) ? config?.album_ids : undefined
            const runIdStr = String(run.id)
            const errorMessage = run.error_message ?? run.error ?? null
            const progressPercent = clampPercentOrDefault(run.progress)
            const statusColor = getJobStatusColor(run.status)

            return (
              <Card key={run.id} className="border border-border/60">
                <CardHeader className="gap-4 border-b border-border/60 bg-muted/40 pb-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-2">
                    <CardTitle className="text-lg font-semibold leading-tight text-foreground">
                      {run.name || `Training run ${runIdStr}`}
                    </CardTitle>
                    {run.description ? (
                      <CardDescription className="text-sm text-muted-foreground">
                        {run.description}
                      </CardDescription>
                    ) : null}
                  </div>
                  <span
                    className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white"
                    style={{ backgroundColor: statusColor }}
                  >
                    {run.status.replace(/_/g, ' ')}
                  </span>
                </CardHeader>

                <CardContent className="space-y-4 pt-4 text-sm">
                  <div className="grid gap-4 text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-1">
                      <p className="font-medium text-foreground">Progress</p>
                      <p>{progressPercent}%</p>
                    </div>
                    <div className="space-y-1">
                      <p className="font-medium text-foreground">Created</p>
                      <p>{formatDate(run.created_at)}</p>
                    </div>
                    {run.started_at ? (
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">Started</p>
                        <p>{formatDate(run.started_at)}</p>
                      </div>
                    ) : null}
                    {run.completed_at ? (
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">Completed</p>
                        <p>{formatDate(run.completed_at)}</p>
                      </div>
                    ) : null}
                  </div>

                  {run.status === 'running' ? (
                    <div className="space-y-2">
                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          role="progressbar"
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={progressPercent}
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>
                  ) : null}

                  <div className="space-y-3">
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-foreground">Dataset directory</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(run.dataset_path ?? '', run.id, 'dataset')}
                        >
                          <Copy className="mr-1 h-3 w-3" />
                          Copy
                        </Button>
                        {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'dataset' ? (
                          <span className="text-xs font-medium text-primary">Copied!</span>
                        ) : null}
                      </div>
                      <code className="mt-2 block break-all text-xs text-muted-foreground">
                        {run.dataset_path || 'Unavailable'}
                      </code>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-foreground">Output directory</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(run.output_path ?? '', run.id, 'output')}
                        >
                          <Copy className="mr-1 h-3 w-3" />
                          Copy
                        </Button>
                        {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'output' ? (
                          <span className="text-xs font-medium text-primary">Copied!</span>
                        ) : null}
                      </div>
                      <code className="mt-2 block break-all text-xs text-muted-foreground">
                        {run.output_path || 'Unavailable'}
                      </code>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-foreground">Final checkpoint</span>
                        {run.final_checkpoint ? (
                          <>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCopy(run.final_checkpoint ?? '', run.id, 'checkpoint')}
                            >
                              <Copy className="mr-1 h-3 w-3" />
                              Copy
                            </Button>
                            {copyFeedback?.runId === runIdStr && copyFeedback?.field === 'checkpoint' ? (
                              <span className="text-xs font-medium text-primary">Copied!</span>
                            ) : null}
                          </>
                        ) : null}
                      </div>
                      <code className="mt-2 block break-all text-xs text-muted-foreground">
                        {run.final_checkpoint ?? 'Generated after completion'}
                      </code>
                    </div>

                    {config ? (
                      <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                        <p className="font-semibold text-foreground">Training configuration</p>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
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
                    ) : null}
                  </div>

                  {errorMessage ? (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      <strong className="font-semibold">Error:</strong> {errorMessage}
                    </div>
                  ) : null}
                </CardContent>

                <CardFooter className="flex flex-wrap gap-2">
                  {run.status === 'queued' ? (
                    <Button onClick={() => handleStartTraining(run.id)}>
                      <Play className="mr-2 h-4 w-4" />
                      Start Training
                    </Button>
                  ) : null}

                  {(run.status === 'queued' || run.status === 'running') ? (
                    <Button variant="destructive" onClick={() => handleCancelTraining(run.id)}>
                      <StopCircle className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  ) : null}

                  {(run.status === 'completed' || run.status === 'failed') ? (
                    <Button variant="outline" onClick={() => handleCleanupTraining(run.id)}>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Cleanup
                    </Button>
                  ) : null}

                  <Button variant="outline" onClick={() => openLogViewer(run.id)}>
                    <FileText className="mr-2 h-4 w-4" />
                    View Logs
                  </Button>
                </CardFooter>
              </Card>
            )
          })
        )}
      </div>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Training Run</DialogTitle>
            <DialogDescription>
              Configure a new LoRA training job. All fields can be adjusted later if needed.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateTraining} className="space-y-6">
            <FormField
              label="Name"
              htmlFor="training-name"
              description="Human-friendly label for the run."
            >
              <Input
                id="training-name"
                value={formData.name}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setFormData((prev) => ({ ...prev, name: event.target.value }))
                }
                required
              />
            </FormField>

            <FormField label="Description" htmlFor="training-description">
              <Textarea
                id="training-description"
                rows={3}
                value={formData.description}
                onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setFormData((prev) => ({ ...prev, description: event.target.value }))
                }
              />
            </FormField>

            <FormField
              label="Training Albums"
              description={
                albums.length === 0
                  ? 'No training albums available yet.'
                  : 'Select one or more albums to use as the training dataset.'
              }
            >
              <div className="grid max-h-56 gap-2 overflow-y-auto pr-1">
                {albums.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Add albums before starting a training run.
                  </p>
                ) : (
                  albums.map((album) => {
                    const albumId = String(album.id)
                    const selected = formData.album_ids.includes(albumId)
                    return (
                      <label
                        key={albumId}
                        className={cn(
                          'flex items-center justify-between rounded-md border px-3 py-2 text-sm transition-colors',
                          selected ? 'border-primary bg-primary/10 text-foreground' : 'border-border bg-background',
                        )}
                      >
                        <span className="font-medium">{album.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {(album.image_count ?? 0).toLocaleString()} images
                          </span>
                          <input
                            type="checkbox"
                            className="h-4 w-4 accent-primary"
                            checked={selected}
                            onChange={() => toggleAlbumSelection(albumId)}
                          />
                        </div>
                      </label>
                    )
                  })
                )}
              </div>
            </FormField>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="Training Steps"
                htmlFor="training-steps"
                description="More steps yield higher quality but take longer."
              >
                <Input
                  id="training-steps"
                  type="number"
                  min={100}
                  max={10000}
                  value={formData.config.steps}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                    const next = Number.parseInt(event.target.value, 10)
                    setFormData((prev) => ({
                      ...prev,
                      config: {
                        ...prev.config,
                        steps: Number.isNaN(next) ? prev.config.steps : next,
                      },
                    }))
                  }}
                />
              </FormField>

              <FormField
                label="LoRA Rank"
                htmlFor="training-rank"
                description="Lower ranks train faster; higher ranks capture more detail."
              >
                <Input
                  id="training-rank"
                  type="number"
                  min={1}
                  max={64}
                  value={formData.config.rank}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                    const next = Number.parseInt(event.target.value, 10)
                    setFormData((prev) => ({
                      ...prev,
                      config: {
                        ...prev.config,
                        rank: Number.isNaN(next) ? prev.config.rank : next,
                      },
                    }))
                  }}
                />
              </FormField>

              <FormField label="Learning Rate" htmlFor="training-learning-rate">
                <Input
                  id="training-learning-rate"
                  type="number"
                  step="0.0001"
                  min="0.0001"
                  max="0.01"
                  value={formData.config.learning_rate}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                    const next = Number.parseFloat(event.target.value)
                    setFormData((prev) => ({
                      ...prev,
                      config: {
                        ...prev.config,
                        learning_rate: Number.isNaN(next) ? prev.config.learning_rate : next,
                      },
                    }))
                  }}
                />
              </FormField>

              <FormField label="Batch Size" htmlFor="training-batch-size">
                <Input
                  id="training-batch-size"
                  type="number"
                  min={1}
                  max={8}
                  value={formData.config.batch_size}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                    const next = Number.parseInt(event.target.value, 10)
                    setFormData((prev) => ({
                      ...prev,
                      config: {
                        ...prev.config,
                        batch_size: Number.isNaN(next) ? prev.config.batch_size : next,
                      },
                    }))
                  }}
                />
              </FormField>
            </div>

            <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
              <Button type="submit" disabled={formData.album_ids.length === 0}>
                <Plus className="mr-2 h-4 w-4" />
                Create Training Run
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={logDialogOpen} onOpenChange={(open) => { if (!open) closeLogViewer() }}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Training Logs</DialogTitle>
            <DialogDescription>
              {logState.runId ? `Most recent output for training run ${logState.runId}.` : 'No run selected.'}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            {logState.status ? (
              <span>
                <span className="font-medium text-foreground">Status:</span> {logState.status.toUpperCase()}
              </span>
            ) : null}
            {logState.logPath ? (
              <span className="break-all">
                <span className="font-medium text-foreground">Log file:</span> {logState.logPath}
              </span>
            ) : null}
          </div>
          <div className="max-h-[480px] overflow-y-auto rounded-md border border-border/60 bg-background p-4 text-xs leading-relaxed text-muted-foreground">
            {logState.loading ? (
              <Spinner size="small" message="Loading logs..." />
            ) : logState.error ? (
              <div className="text-destructive">{logState.error}</div>
            ) : logState.logAvailable ? (
              <pre className="whitespace-pre-wrap break-words font-mono text-xs text-foreground">
                {logState.content || 'No log output yet.'}
              </pre>
            ) : (
              <div>Logs are not available yet for this run.</div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeLogViewer}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default TrainingTab
