import React, { useState, useCallback, memo } from 'react'
import { logger } from '../lib/logger'
import { api } from '../lib/api'
import { ApiError } from '../lib/api'
import { useToast } from '../hooks/use-toast'
import { useAdaptivePolling } from '../hooks/useAdaptivePolling'
import type { JobsResponse } from '../types/models'
import '../styles/QueueTab.css'
import { Button } from '@/components/ui/button'
import { RotateCw } from 'lucide-react'

const QueueTab: React.FC = memo(() => {
  const { toast } = useToast()
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [authError, setAuthError] = useState<boolean>(false)

  const fetchQueueData = useCallback(async (): Promise<JobsResponse> => {
    try {
      const data = await api.jobs.getAll()
      setAuthError(false)  // Clear auth error on successful fetch
      return data
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        // Admin authentication required
        setAuthError(true)
        logger.warn('Queue access requires admin authentication')
        throw error
      }
      logger.error('Failed to fetch queue data:', error)
      toast({ title: 'Error', description: 'Failed to load job queue', variant: 'destructive' })
      throw error
    }
  }, [toast])

  // Adaptive polling: fast when jobs running, slow when idle
  const queueData = useAdaptivePolling(fetchQueueData, {
    activeInterval: 2000,   // 2s when job is running (1,800 req/hour)
    mediumInterval: 10000,  // 10s when jobs queued (360 req/hour - 80% reduction)
    baseInterval: 30000,    // 30s when idle (120 req/hour - 93% reduction)
    enabled: autoRefresh,
    pauseWhenHidden: true,
    getActivityLevel: (data) => {
      // Fast polling when a job is currently running
      if (data?.current) return 'active'
      // Medium polling when jobs are queued
      if (data?.queue && data.queue.length > 0) return 'medium'
      // Slow polling when completely idle
      return 'idle'
    },
  })

  const formatDate = useCallback((dateString?: string | null): string => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString()
  }, [])

  const formatDuration = useCallback((startTime?: string | null, endTime?: string | null): string => {
    if (!startTime || !endTime) return '-'
    const start = new Date(startTime)
    const end = new Date(endTime)
    const seconds = Math.floor((end.getTime() - start.getTime()) / 1000)
    return `${seconds}s`
  }, [])

  const getStatusBadge = useCallback((status: string): JSX.Element => {
    const statusClass = `status-badge status-${status}`
    return <span className={statusClass}>{status}</span>
  }, [])

  const handleAutoRefreshChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setAutoRefresh(e.target.checked)
  }, [])

  const handleRefresh = useCallback(() => {
    void fetchQueueData()
  }, [fetchQueueData])

  if (authError) {
    return (
      <div className="queue-tab">
        <div className="auth-error-banner">
          <h3>🔒 Admin Authentication Required</h3>
          <p>The job queue requires admin privileges to view. Please sign in with an admin account.</p>
          <Button onClick={handleRefresh} variant="outline">
            <RotateCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (!queueData) {
    return <div className="queue-tab loading">Loading queue data...</div>
  }

  return (
    <div className="queue-tab">
      <div className="queue-header">
        <h2>Job Queue</h2>
        <div className="queue-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={handleAutoRefreshChange}
            />
            Auto-refresh
          </label>
          <Button onClick={handleRefresh} variant="outline">
            <RotateCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Current Job */}
      <section className="queue-section">
        <h3>Currently Running</h3>
        {queueData.current ? (
          <div className="job-card current-job">
            <div className="job-header">
              <span className="job-id">Job #{queueData.current.id}</span>
              {getStatusBadge('running')}
            </div>
            <div className="job-details">
              <div className="job-field">
                <strong>Prompt:</strong>
                <span>{queueData.current.prompt}</span>
              </div>
              {queueData.current.lora_paths && queueData.current.lora_paths.length > 0 && (
                <div className="job-field">
                  <strong>LoRAs:</strong>
                  <span>{queueData.current.lora_paths.length} loaded</span>
                </div>
              )}
              <div className="job-field">
                <strong>Started:</strong>
                <span>{formatDate(queueData.current.started_at)}</span>
              </div>
              <div className="job-field">
                <strong>Settings:</strong>
                <span>
                  {queueData.current.width}×{queueData.current.height}, {queueData.current.steps} steps
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">No job currently running</div>
        )}
      </section>

      {/* Queued Jobs */}
      <section className="queue-section">
        <h3>
          Queued Jobs
          {queueData.queue && queueData.queue.length > 0 && (
            <span className="count-badge">{queueData.queue.length}</span>
          )}
        </h3>
        {queueData.queue && queueData.queue.length > 0 ? (
          <div className="job-list">
            {queueData.queue.map((job, index) => (
              <div key={job.id} className="job-card queued-job">
                <div className="job-header">
                  <span className="job-id">
                    #{index + 1} - Job #{job.id}
                  </span>
                  {getStatusBadge('queued')}
                </div>
                <div className="job-details">
                  <div className="job-field">
                    <strong>Prompt:</strong>
                    <span>{job.prompt}</span>
                  </div>
                  {job.lora_paths && job.lora_paths.length > 0 && (
                    <div className="job-field">
                      <strong>LoRAs:</strong>
                      <span>{job.lora_paths.length} loaded</span>
                    </div>
                  )}
                  <div className="job-field">
                    <strong>Submitted:</strong>
                    <span>{formatDate(job.submitted_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No jobs in queue</div>
        )}
      </section>

      {/* Job History */}
      <section className="queue-section">
        <h3>
          Recent History
          {queueData.history && queueData.history.length > 0 && (
            <span className="count-badge">{queueData.history.length}</span>
          )}
        </h3>
        {queueData.history && queueData.history.length > 0 ? (
          <div className="job-list history-list">
            {queueData.history.slice(0, 10).map((job) => (
              <div key={`${job.id}-${job.completed_at}`} className={`job-card history-job status-${job.status}`}>
                <div className="job-header">
                  <span className="job-id">Job #{job.id}</span>
                  {getStatusBadge(job.status)}
                  <span className="job-duration">
                    {formatDuration(job.started_at, job.completed_at)}
                  </span>
                </div>
                <div className="job-details">
                  <div className="job-field">
                    <strong>Prompt:</strong>
                    <span>{job.prompt}</span>
                  </div>
                  {job.status === 'completed' && (job.output_filename || job.output_path) && (
                    <div className="job-field">
                      <strong>Output:</strong>
                      <span className="output-path">
                        {job.output_filename || job.output_path?.split('/').pop() || 'completed'}
                      </span>
                    </div>
                  )}
                  {job.error && (
                    <div className="job-field error">
                      <strong>Error:</strong>
                      <span>{job.error}</span>
                    </div>
                  )}
                  <div className="job-field">
                    <strong>Completed:</strong>
                    <span>{formatDate(job.completed_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No completed jobs yet</div>
        )}
      </section>
    </div>
  )
})

QueueTab.displayName = 'QueueTab'

export default QueueTab
