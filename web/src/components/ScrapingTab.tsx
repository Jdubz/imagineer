import React, { useState, useEffect, useCallback } from 'react'
import '../styles/ScrapingTab.css'
import type { ScrapingJob } from '../types/models'

// Helper function to clamp progress values between 0 and 100
const clampProgress = (value: number | null | undefined): number | undefined => {
  return typeof value === 'number' ? Math.min(100, Math.max(0, value)) : undefined
}

const formatGigabytes = (value?: number | null): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'N/A'
  }
  const fractionDigits = value < 10 ? 1 : 0
  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: 1,
  })} GB`
}

interface StorageStats {
  path: string
  total_gb?: number
  used_gb?: number
  free_gb?: number
  free_percent?: number | null
  error?: string
}

interface ScrapingStats {
  total_jobs: number
  total_images_scraped: number
  recent_jobs: number
  storage?: StorageStats
}

interface ScrapingJobsResponse {
  jobs: ScrapingJob[]
}

interface ScrapingTabProps {
  isAdmin?: boolean
}

const ScrapingTab: React.FC<ScrapingTabProps> = ({ isAdmin = false }) => {
  const [scrapeJobs, setScrapeJobs] = useState<ScrapingJob[]>([])
  const [showStartDialog, setShowStartDialog] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<ScrapingStats | null>(null)

  const fetchJobs = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch('/api/scraping/jobs', {
        credentials: 'include',
      })
      if (response.ok) {
        const data: ScrapingJobsResponse = await response.json()
        setScrapeJobs(data.jobs || [])
        setError(null)
      } else if (response.status === 401 || response.status === 403) {
        setScrapeJobs([])
        setError('You need admin access to view scrape jobs.')
      } else {
        setError('Failed to fetch scrape jobs')
      }
    } catch (err) {
      setError('Error fetching scrape jobs')
      console.error('Error fetching jobs:', err)
    }
  }, [isAdmin])

  const fetchStats = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch('/api/scraping/stats', {
        credentials: 'include',
      })
      if (response.ok) {
        const data: ScrapingStats = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
    }
  }, [isAdmin])

  useEffect(() => {
    if (!isAdmin) {
      return
    }

    fetchJobs().catch((err) => console.error('Error refreshing jobs:', err))
    fetchStats().catch((err) => console.error('Error refreshing stats:', err))

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchJobs().catch((err) => console.error('Error refreshing jobs:', err))
      fetchStats().catch((err) => console.error('Error refreshing stats:', err))
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchJobs, fetchStats, isAdmin])

  const startScrape = async (url: string, name: string, description: string, depth: number, maxImages: number): Promise<void> => {
    if (!isAdmin) return
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/scraping/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          url,
          name,
          description,
          depth,
          max_images: maxImages
        })
      })

      if (response.ok) {
        await response.json() // Consume response
        await fetchJobs()
        setShowStartDialog(false)
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to start scrape job')
      }
    } catch (err) {
      setError('Error starting scrape job')
      console.error('Error starting scrape:', err)
    } finally {
      setLoading(false)
    }
  }

  const cancelJob = async (jobId: string): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch(`/api/scraping/jobs/${jobId}/cancel`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        await fetchJobs()
      } else {
        setError('Failed to cancel job')
      }
    } catch (err) {
      setError('Error cancelling job')
      console.error('Error cancelling job:', err)
    }
  }

  const cleanupJob = async (jobId: string): Promise<void> => {
    if (!isAdmin) return
    try {
      const response = await fetch(`/api/scraping/jobs/${jobId}/cleanup`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        await fetchJobs()
      } else {
        setError('Failed to cleanup job')
      }
    } catch (err) {
      setError('Error cleaning up job')
      console.error('Error cleaning up job:', err)
    }
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending': return '#f39c12'
      case 'running': return '#3498db'
      case 'completed': return '#27ae60'
      case 'failed': return '#e74c3c'
      case 'cancelled': return '#95a5a6'
      case 'cleaned_up': return '#7f8c8d'
      default: return '#95a5a6'
    }
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  if (!isAdmin) {
    return (
      <div className="scraping-tab">
        <div className="scraping-access-message">
          <h2>Web Scraping</h2>
          <p>Admin access required to manage scraping jobs.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="scraping-tab">
      <div className="scraping-header">
        <h2>Web Scraping</h2>
        {isAdmin && (
          <button
            className="start-scrape-btn"
            onClick={() => setShowStartDialog(true)}
            disabled={loading}
          >
            {loading ? 'Starting...' : 'Start New Scrape'}
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {stats && (
        <div className="scraping-stats">
          <div className="stat-card">
            <h3>Total Jobs</h3>
            <span className="stat-number">{stats.total_jobs}</span>
          </div>
          <div className="stat-card">
            <h3>Images Scraped</h3>
            <span className="stat-number">{stats.total_images_scraped}</span>
          </div>
          <div className="stat-card">
            <h3>Recent Jobs (7 days)</h3>
            <span className="stat-number">{stats.recent_jobs}</span>
          </div>
          {stats.storage && (
            <div className="stat-card storage-card">
              <h3>Storage Free</h3>
              <span className="stat-number">{formatGigabytes(stats.storage.free_gb)}</span>
              {stats.storage.error ? (
                <div className="storage-error">{stats.storage.error}</div>
              ) : (
                <>
                  <div className="storage-details">
                    {formatGigabytes(stats.storage.used_gb)} used · {formatGigabytes(stats.storage.total_gb)} total
                  </div>
                  {typeof stats.storage.free_percent === 'number' && (
                    <div className="storage-details">
                      {stats.storage.free_percent.toFixed(1)}% free
                    </div>
                  )}
                </>
              )}
              <div className="storage-path">{stats.storage.path}</div>
            </div>
          )}
        </div>
      )}

      <div className="scrape-jobs-list">
        {scrapeJobs.length === 0 ? (
          <div className="no-jobs">
            <p>No scrape jobs found. Start a new scrape to begin collecting training data.</p>
          </div>
        ) : (
          scrapeJobs.map(job => {
            const runtime = job.runtime ?? {}
            const jobUrl = job.url ?? job.source_url ?? 'Unknown URL'
            const outputDir = job.output_dir ?? job.output_directory
            const progressPercent = clampProgress(job.progress) ?? clampProgress(runtime.progress)
            const progressMessage = job.progress_message ?? runtime.last_message ?? ''

            return (
              <div key={job.id} className={`scrape-job-card status-${job.status}`}>
                <div className="job-header">
                  <h3>{jobUrl}</h3>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(job.status) }}
                  >
                    {job.status}
                  </span>
                </div>

                <div className="job-details">
                  <div className="detail">
                    <strong>URL:</strong>
                    <a
                      href={jobUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="job-url"
                    >
                      {jobUrl}
                    </a>
                  </div>

                  {outputDir && (
                    <div className="detail">
                      <strong>Output Directory:</strong>
                      <span>{outputDir}</span>
                    </div>
                  )}

                  {job.status === 'running' && (
                    <div className="progress-section">
                      {progressPercent !== undefined && (
                        <div className="progress-bar">
                          <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
                        </div>
                      )}
                      {(runtime.stage || progressMessage) && (
                        <div className="runtime-stage">
                          {runtime.stage && (
                            <strong>{runtime.stage.charAt(0).toUpperCase() + runtime.stage.slice(1)}</strong>
                          )}
                          {progressMessage && (
                            <span className="runtime-message">
                              {runtime.stage ? ' · ' : ''}
                              {progressMessage}
                            </span>
                          )}
                        </div>
                      )}
                      {(runtime.discovered != null || runtime.downloaded != null) && (
                        <div className="runtime-metrics">
                          {runtime.discovered != null && (
                            <span>Links discovered: {runtime.discovered}</span>
                          )}
                          {runtime.downloaded != null && (
                            <span>Images downloaded: {runtime.downloaded}</span>
                          )}
                        </div>
                      )}
                      {job.images_scraped != null && job.images_scraped > 0 && (
                        <div className="stats">
                          <span>Images scraped: {job.images_scraped}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {job.status === 'completed' && job.images_scraped != null && (
                    <div className="completion-stats">
                      <div className="success-message">
                        ✓ Successfully scraped {job.images_scraped} images
                      </div>
                      {outputDir && (
                        <div className="output-info">
                          Output: {outputDir}
                        </div>
                      )}
                    </div>
                  )}

                  {job.status === 'failed' && job.error && (
                    <div className="error-details">
                      <strong>Error:</strong>
                      <span className="error-text">{job.error}</span>
                    </div>
                  )}

                  <div className="job-meta">
                    <div className="meta-item">
                      <strong>Created:</strong> {formatDate(job.created_at)}
                    </div>
                    {job.completed_at && (
                      <div className="meta-item">
                        <strong>Completed:</strong> {formatDate(job.completed_at)}
                      </div>
                    )}
                    {runtime.updated_at && (
                      <div className="meta-item">
                        <strong>Updated:</strong> {formatDate(runtime.updated_at)}
                      </div>
                    )}
                  </div>
                </div>

                {isAdmin && (
                  <div className="job-actions">
                    {job.status === 'running' && (
                      <button
                        className="cancel-btn"
                        onClick={() => cancelJob(job.id)}
                      >
                        Cancel
                      </button>
                    )}
                    {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                      <button
                        className="cleanup-btn"
                        onClick={() => cleanupJob(job.id)}
                      >
                        Cleanup
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {showStartDialog && (
        <StartScrapeDialog
          onClose={() => setShowStartDialog(false)}
          onSubmit={startScrape}
          loading={loading}
        />
      )}
    </div>
  )
}

interface StartScrapeDialogProps {
  onClose: () => void
  onSubmit: (url: string, name: string, description: string, depth: number, maxImages: number) => void
  loading: boolean
}

const StartScrapeDialog: React.FC<StartScrapeDialogProps> = ({ onClose, onSubmit, loading }) => {
  const [url, setUrl] = useState<string>('')
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [depth, setDepth] = useState<number>(3)
  const [maxImages, setMaxImages] = useState<number>(1000)

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (!url) return

    const jobName = name || `Scrape ${url}`
    const jobDescription = description || `Web scraping job for ${url}`

    onSubmit(url, jobName, jobDescription, depth, maxImages)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
        <h2>Start Web Scrape</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="url">URL to Scrape *</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
              placeholder="https://example.com/gallery"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="name">Job Name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              placeholder="Auto-generated from URL"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
              placeholder="Optional description for this scraping job"
              rows={3}
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="depth">Max Depth</label>
              <input
                id="depth"
                type="number"
                value={depth}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDepth(parseInt(e.target.value))}
                min="1"
                max="10"
                disabled={loading}
              />
              <small>How many links deep to follow (1-10)</small>
            </div>

            <div className="form-group">
              <label htmlFor="maxImages">Max Images</label>
              <input
                id="maxImages"
                type="number"
                value={maxImages}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMaxImages(parseInt(e.target.value))}
                min="1"
                max="10000"
                disabled={loading}
              />
              <small>Maximum images to download (1-10000)</small>
            </div>
          </div>

          <div className="dialog-actions">
            <button
              type="submit"
              className="submit-btn"
              disabled={loading || !url}
            >
              {loading ? 'Starting...' : 'Start Scrape'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ScrapingTab
