import React, { memo, useCallback, useState } from 'react'
import { logger } from '../lib/logger'
import { api } from '../lib/api'
import { useAdaptivePolling } from '../hooks/useAdaptivePolling'
import type { JobsResponse } from '../types/models'
import { formatErrorMessage, isAuthError } from '../lib/errorUtils'
import Spinner from './Spinner'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { RotateCw } from 'lucide-react'
import { useToast } from '../hooks/use-toast'

const STATUS_STYLES: Record<string, string> = {
  running: 'bg-emerald-500 text-emerald-50',
  queued: 'bg-amber-500 text-amber-50',
  completed: 'bg-emerald-500 text-emerald-50',
  failed: 'bg-rose-500 text-rose-50',
  cancelled: 'bg-muted text-muted-foreground',
}

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span
    className={cn(
      'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize',
      STATUS_STYLES[status] ?? 'bg-muted text-foreground',
    )}
  >
    {status.replace(/_/g, ' ')}
  </span>
)

const QueueTab: React.FC = memo(() => {
  const { toast } = useToast()
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [authError, setAuthError] = useState(false)

  const fetchQueueData = useCallback(async (): Promise<JobsResponse> => {
    try {
      const data = await api.jobs.getAll()
      setAuthError(false)
      return data
    } catch (error) {
      if (isAuthError(error)) {
        setAuthError(true)
        logger.warn('Queue access requires admin authentication')
        return { current: null, queue: [], history: [] }
      }
      logger.error('Failed to fetch queue data:', error)
      const errorMessage = formatErrorMessage(error, 'Failed to load job queue')
      toast({ title: 'Error loading queue', description: errorMessage, variant: 'destructive' })
      return { current: null, queue: [], history: [] }
    }
  }, [toast])

  const queueData = useAdaptivePolling(fetchQueueData, {
    activeInterval: 2000,
    mediumInterval: 10000,
    baseInterval: 30000,
    enabled: autoRefresh,
    pauseWhenHidden: true,
    getActivityLevel: (data) => {
      if (data?.current) return 'active'
      if (data?.queue && data.queue.length > 0) return 'medium'
      return 'idle'
    },
  })

  const formatDate = useCallback((dateString?: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString()
  }, [])

  const formatDuration = useCallback((startTime?: string | null, endTime?: string | null) => {
    if (!startTime || !endTime) return '-'
    const start = new Date(startTime)
    const end = new Date(endTime)
    const seconds = Math.floor((end.getTime() - start.getTime()) / 1000)
    return `${seconds}s`
  }, [])

  const handleRefresh = useCallback(() => {
    void fetchQueueData()
  }, [fetchQueueData])

  if (authError) {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader className="space-y-3">
            <CardTitle className="flex items-center gap-2 text-destructive">
              <span role="img" aria-label="Locked">
                🔒
              </span>
              Admin authentication required
            </CardTitle>
            <CardDescription>
              The job queue is restricted to administrators. Sign in with an admin account and try again.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleRefresh} variant="outline">
              <RotateCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!queueData) {
    return (
      <div className="flex min-h-[240px] w-full items-center justify-center py-16">
        <Spinner size="large" message="Loading queue data..." />
      </div>
    )
  }

  const queuedJobs = queueData.queue ?? []
  const historyJobs = queueData.history ?? []

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Job Queue</h2>
          <p className="text-sm text-muted-foreground">
            Monitor the real-time generation pipeline, view queued tasks, and audit recent history.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 accent-primary"
              checked={autoRefresh}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) => setAutoRefresh(event.target.checked)}
            />
            Auto-refresh
          </label>
          <Button variant="outline" onClick={handleRefresh}>
            <RotateCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Currently running</CardTitle>
            {queueData.current ? <StatusBadge status="running" /> : null}
          </CardHeader>
          <CardContent>
            {queueData.current ? (
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="font-medium text-foreground">Prompt</p>
                    <p>{queueData.current.prompt}</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Started</p>
                    <p>{formatDate(queueData.current.started_at)}</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Settings</p>
                    <p>
                      {queueData.current.width}×{queueData.current.height}, {queueData.current.steps} steps
                    </p>
                  </div>
                  {queueData.current.lora_paths && queueData.current.lora_paths.length > 0 ? (
                    <div>
                      <p className="font-medium text-foreground">LoRAs</p>
                      <p>{queueData.current.lora_paths.length} loaded</p>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No job currently running.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <CardTitle>Queued jobs</CardTitle>
              <CardDescription>Jobs waiting to be processed.</CardDescription>
            </div>
            {queuedJobs.length > 0 ? (
              <span className="inline-flex min-w-[2.5rem] items-center justify-center rounded-full bg-primary px-2 py-1 text-xs font-semibold text-primary-foreground">
                {queuedJobs.length}
              </span>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-3">
            {queuedJobs.length > 0 ? (
              queuedJobs.map((job, index) => (
                <div
                  key={job.id}
                  className="rounded-lg border border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-semibold text-foreground">
                      #{index + 1} · Job {job.id}
                    </span>
                    <StatusBadge status="queued" />
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div>
                      <p className="font-medium text-foreground">Prompt</p>
                      <p>{job.prompt}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground">Submitted</p>
                      <p>{formatDate(job.submitted_at)}</p>
                    </div>
                    {job.lora_paths && job.lora_paths.length > 0 ? (
                      <div>
                        <p className="font-medium text-foreground">LoRAs</p>
                        <p>{job.lora_paths.length} loaded</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No jobs in queue.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <CardTitle>Recent history</CardTitle>
              <CardDescription>The last 10 completed or failed jobs.</CardDescription>
            </div>
            {historyJobs.length > 0 ? (
              <span className="inline-flex min-w-[2.5rem] items-center justify-center rounded-full bg-primary px-2 py-1 text-xs font-semibold text-primary-foreground">
                {historyJobs.length}
              </span>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-3">
            {historyJobs.length > 0 ? (
              historyJobs.slice(0, 10).map((job) => (
                <div
                  key={`${job.id}-${job.completed_at ?? job.status}`}
                  className="rounded-lg border border-border/60 bg-muted/10 p-4 text-sm text-muted-foreground"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-semibold text-foreground">Job {job.id}</span>
                    <StatusBadge status={job.status} />
                    <span className="text-xs text-muted-foreground">
                      {formatDuration(job.started_at, job.completed_at)}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div>
                      <p className="font-medium text-foreground">Prompt</p>
                      <p>{job.prompt}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground">Completed</p>
                      <p>{formatDate(job.completed_at)}</p>
                    </div>
                    {job.status === 'completed' && (job.output_filename || job.output_path) ? (
                      <div>
                        <p className="font-medium text-foreground">Output</p>
                        <p>{job.output_filename || job.output_path?.split('/').pop() || 'completed'}</p>
                      </div>
                    ) : null}
                    {job.error ? (
                      <div className="sm:col-span-2">
                        <p className="font-medium text-foreground">Error</p>
                        <p className="text-destructive">{job.error}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No completed jobs yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
})

QueueTab.displayName = 'QueueTab'

export default QueueTab
