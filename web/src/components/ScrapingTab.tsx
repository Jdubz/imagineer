import React, { useState, useEffect, useCallback } from 'react'
import { logger } from '../lib/logger'
import { usePolling } from '../hooks/usePolling'
import type { ScrapingJob, ScrapingStats } from '../types/models'
import { validateForm, scrapeFormSchema } from '../lib/validation'
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
import { FormField } from '@/components/form'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Plus, StopCircle, Trash2, X } from 'lucide-react'
import { useToast } from '../hooks/use-toast'
import { api, ApiError } from '@/lib/api'
import { formatErrorMessage } from '@/lib/errorUtils'
import { clampPercent, formatGigabytes, getJobStatusColor } from '@/lib/adminJobs'
import { cn } from '@/lib/utils'

interface ScrapingTabProps {
  isAdmin?: boolean
}

const ScrapingTab: React.FC<ScrapingTabProps> = ({ isAdmin = false }) => {
  const { toast } = useToast()
  const [scrapeJobs, setScrapeJobs] = useState<ScrapingJob[]>([])
  const [showStartDialog, setShowStartDialog] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<ScrapingStats | null>(null)

  const fetchJobs = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const jobs = await api.scraping.getJobs()
      setScrapeJobs(jobs)
      setError(null)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setScrapeJobs([])
        setError('You need admin access to view scrape jobs.')
        return
      }

      const message = formatErrorMessage(err, 'Error fetching scrape jobs')
      setError(message)
      toast({
        variant: 'destructive',
        title: 'Failed to load scrape jobs',
        description: message,
      })
      logger.error('Error fetching jobs:', err)
    }
  }, [isAdmin, toast])

  const fetchStats = useCallback(async (): Promise<void> => {
    if (!isAdmin) return
    try {
      const data = await api.scraping.getStats()
      setStats(data)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setStats(null)
        setError((prev) => prev ?? 'You need admin access to view scrape stats.')
        return
      }

      const message = formatErrorMessage(err, 'Error fetching scrape stats')
      setError((prev) => prev ?? message)
      toast({
        variant: 'destructive',
        title: 'Failed to load scraping metrics',
        description: message,
      })
      logger.error('Error fetching stats:', err)
    }
  }, [isAdmin, toast])

  useEffect(() => {
    if (!isAdmin) return

    fetchJobs().catch((err) => logger.error('Error refreshing jobs:', err))
    fetchStats().catch((err) => logger.error('Error refreshing stats:', err))
  }, [fetchJobs, fetchStats, isAdmin])

  const refreshData = useCallback(async () => {
    await Promise.all([
      fetchJobs().catch((err) => logger.error('Error refreshing jobs:', err)),
      fetchStats().catch((err) => logger.error('Error refreshing stats:', err)),
    ])
  }, [fetchJobs, fetchStats])

  usePolling(refreshData, {
    interval: 5000,
    enabled: isAdmin,
    pauseWhenHidden: true,
  })

  const startScrape = async (
    url: string,
    name: string,
    description: string,
    depth: number,
    maxImages: number,
  ): Promise<void> => {
    if (!isAdmin) return

    setLoading(true)
    setError(null)

    try {
      await api.scraping.startJob({
        url,
        name,
        description,
        depth,
        max_images: maxImages,
      })

      const jobLabel = name || url
      toast({
        title: 'Scrape job started',
        description: `Queued ${jobLabel}.`,
      })

      await Promise.all([fetchJobs(), fetchStats()])
      setShowStartDialog(false)
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to start scrape job')
      setError(message)
      toast({
        variant: 'destructive',
        title: 'Failed to start scrape job',
        description: message,
      })
      logger.error('Error starting scrape:', err)
    } finally {
      setLoading(false)
    }
  }

  const cancelJob = async (jobId: string): Promise<void> => {
    if (!isAdmin) return
    try {
      await api.scraping.cancelJob(jobId)
      await fetchJobs()
      toast({
        title: 'Scrape job cancelled',
        description: 'The job was cancelled successfully.',
      })
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to cancel job')
      setError((prev) => prev ?? message)
      toast({
        variant: 'destructive',
        title: 'Failed to cancel job',
        description: message,
      })
      logger.error('Error cancelling job:', err)
    }
  }

  const cleanupJob = async (jobId: string): Promise<void> => {
    if (!isAdmin) return
    try {
      await api.scraping.cleanupJob(jobId)
      await fetchJobs()
      toast({
        title: 'Scrape job cleaned up',
        description: 'Outputs removed from the worker host.',
      })
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to clean up job')
      setError((prev) => prev ?? message)
      toast({
        variant: 'destructive',
        title: 'Failed to clean up job',
        description: message,
      })
      logger.error('Error cleaning up job:', err)
    }
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>Web Scraping</CardTitle>
            <CardDescription>
              Admin access is required to review or manage scraping jobs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Contact an administrator if you need permission to launch scraping runs or review
              telemetry.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Web Scraping</h2>
          <p className="text-sm text-muted-foreground">
            Launch new scraping jobs and monitor progress, storage usage, and recent activity.
          </p>
        </div>
        <Button onClick={() => setShowStartDialog(true)} disabled={loading}>
          <Plus className="mr-2 h-4 w-4" />
          {loading ? 'Starting…' : 'Start New Scrape'}
        </Button>
      </div>

      {error ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {stats ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Total Jobs</CardTitle>
              <CardDescription>All scrape jobs recorded</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-3xl font-semibold text-foreground">{stats.total_jobs}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Images Scraped</CardTitle>
              <CardDescription>Cumulative images downloaded</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-3xl font-semibold text-foreground">{stats.total_images_scraped}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Recent Jobs (7 days)</CardTitle>
              <CardDescription>Activity in the past week</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-3xl font-semibold text-foreground">{stats.recent_jobs}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Storage Free</CardTitle>
              <CardDescription>Scraper output volume</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 pt-0 text-sm">
              {stats.storage ? (
                stats.storage.error ? (
                  <p className="font-medium text-destructive">{stats.storage.error}</p>
                ) : (
                  <>
                    <p className="text-lg font-semibold text-foreground">
                      {formatGigabytes(stats.storage.free_gb)} free
                    </p>
                    <p className="text-muted-foreground">
                      {formatGigabytes(stats.storage.used_gb)} used · {formatGigabytes(stats.storage.total_gb)} total
                    </p>
                    {typeof stats.storage.free_percent === 'number' ? (
                      <p className="text-muted-foreground">
                        {stats.storage.free_percent.toFixed(1)}% free
                      </p>
                    ) : null}
                    <p className="truncate text-xs text-muted-foreground">{stats.storage.path}</p>
                  </>
                )
              ) : (
                <p className="text-muted-foreground">No storage telemetry available.</p>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      <div className="grid gap-4">
        {scrapeJobs.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center text-muted-foreground">
              No scrape jobs found. Start a new scrape to begin collecting training data.
            </CardContent>
          </Card>
        ) : (
          scrapeJobs.map((job) => {
            const runtime = job.runtime ?? {}
            const jobUrl = job.url ?? job.source_url ?? 'Unknown URL'
            const outputDir = job.output_dir ?? job.output_directory
            const progressPercent = clampPercent(job.progress) ?? clampPercent(runtime.progress)
            const progressMessage = job.progress_message ?? runtime.last_message ?? ''
            const statusColor = getJobStatusColor(job.status)

            return (
              <Card
                key={job.id}
                className={cn('border border-border/60', 'border-l-4')}
                style={{ borderLeftColor: statusColor }}
              >
                <CardHeader className="gap-4 border-b border-border/60 bg-muted/40 pb-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-2">
                    <CardTitle className="text-lg font-semibold leading-tight text-foreground">
                      {jobUrl}
                    </CardTitle>
                    <a
                      href={jobUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-sm font-medium text-primary underline underline-offset-4"
                    >
                      {jobUrl}
                    </a>
                    {outputDir ? (
                      <p className="text-xs text-muted-foreground">Output: {outputDir}</p>
                    ) : null}
                  </div>
                  <span
                    className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white"
                    style={{ backgroundColor: statusColor }}
                  >
                    {job.status?.replace(/_/g, ' ') ?? 'unknown'}
                  </span>
                </CardHeader>

                <CardContent className="space-y-4 pt-4 text-sm">
                  {job.status === 'running' ? (
                    <div className="space-y-3">
                      {progressPercent !== undefined ? (
                        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${progressPercent}%` }}
                            role="progressbar"
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={progressPercent}
                          />
                        </div>
                      ) : null}
                      {runtime.stage || progressMessage ? (
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-muted-foreground">
                          {runtime.stage ? (
                            <span className="font-medium text-foreground">
                              {runtime.stage.charAt(0).toUpperCase() + runtime.stage.slice(1)}
                            </span>
                          ) : null}
                          {progressMessage ? <span>{progressMessage}</span> : null}
                        </div>
                      ) : null}
                      {runtime.discovered != null || runtime.downloaded != null ? (
                        <div className="flex flex-wrap gap-4 text-muted-foreground">
                          {runtime.discovered != null ? (
                            <span>Links discovered: {runtime.discovered}</span>
                          ) : null}
                          {runtime.downloaded != null ? (
                            <span>Images downloaded: {runtime.downloaded}</span>
                          ) : null}
                        </div>
                      ) : null}
                      {job.images_scraped != null && job.images_scraped > 0 ? (
                        <div className="text-muted-foreground">Images scraped: {job.images_scraped}</div>
                      ) : null}
                    </div>
                  ) : null}

                  {job.status === 'completed' && job.images_scraped != null ? (
                    <div className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700">
                      ✓ Successfully scraped {job.images_scraped} images
                    </div>
                  ) : null}

                  {job.status === 'failed' && job.error ? (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-destructive">
                      <span className="font-semibold">Error:</span> {job.error}
                    </div>
                  ) : null}

                  <div className="grid gap-4 text-sm text-muted-foreground md:grid-cols-3">
                    <div className="space-y-1">
                      <p className="font-medium text-foreground">Created</p>
                      <p>{formatDate(job.created_at)}</p>
                    </div>
                    {job.completed_at ? (
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">Completed</p>
                        <p>{formatDate(job.completed_at)}</p>
                      </div>
                    ) : null}
                    {runtime.updated_at ? (
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">Updated</p>
                        <p>{formatDate(runtime.updated_at)}</p>
                      </div>
                    ) : null}
                  </div>
                </CardContent>

                <CardFooter className="flex flex-wrap gap-2">
                  {job.status === 'running' ? (
                    <Button variant="destructive" onClick={() => cancelJob(job.id)}>
                      <StopCircle className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  ) : null}
                  {job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled' ? (
                    <Button variant="outline" onClick={() => cleanupJob(job.id)}>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Cleanup
                    </Button>
                  ) : null}
                </CardFooter>
              </Card>
            )
          })
        )}
      </div>

      <Dialog open={showStartDialog} onOpenChange={setShowStartDialog}>
        <StartScrapeDialog
          isOpen={showStartDialog}
          onClose={() => setShowStartDialog(false)}
          onSubmit={startScrape}
          loading={loading}
        />
      </Dialog>
    </div>
  )
}

interface StartScrapeDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (
    url: string,
    name: string,
    description: string,
    depth: number,
    maxImages: number,
  ) => void
  loading: boolean
}

const StartScrapeDialog: React.FC<StartScrapeDialogProps> = ({ isOpen, onClose, onSubmit, loading }) => {
  const [url, setUrl] = useState<string>('')
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [depthValue, setDepthValue] = useState<string>('3')
  const [maxImagesValue, setMaxImagesValue] = useState<string>('1000')
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (isOpen) {
      setUrl('')
      setName('')
      setDescription('')
      setDepthValue('3')
      setMaxImagesValue('1000')
      setValidationErrors({})
    }
  }, [isOpen])

  const clearValidationError = useCallback((field: string) => {
    setValidationErrors((prev) => {
      if (!prev[field]) {
        return prev
      }
      const next = { ...prev }
      delete next[field]
      return next
    })
  }, [])

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    setValidationErrors({})

    const jobName = name || `Scrape ${url}`
    const jobDescription = description || `Web scraping job for ${url}`

    const depthNumber = depthValue.trim() === '' ? Number.NaN : Number(depthValue)
    const maxImagesNumber = maxImagesValue.trim() === '' ? Number.NaN : Number(maxImagesValue)

    const formData = {
      url: url.trim(),
      name: jobName,
      description: jobDescription,
      depth: depthNumber,
      maxImages: maxImagesNumber,
    }

    const validation = validateForm(scrapeFormSchema, formData)

    if (!validation.success) {
      setValidationErrors(validation.errors)
      logger.warn('Scrape form validation failed:', validation.errors)
      return
    }

    onSubmit(
      validation.data.url,
      validation.data.name || jobName,
      validation.data.description || jobDescription,
      validation.data.depth,
      validation.data.maxImages,
    )
  }

  return (
    <DialogContent className="max-w-xl">
      <DialogHeader>
        <DialogTitle>Start Web Scrape</DialogTitle>
        <DialogDescription>
          Provide a target URL and optional context. Defaults will be generated when fields are left blank.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-6">
          <FormField
            label="URL to Scrape"
            htmlFor="scrape-url"
            error={validationErrors.url}
            description="The starting URL for the crawler."
          >
            <Input
              id="scrape-url"
              type="url"
              value={url}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                setUrl(event.target.value)
                clearValidationError('url')
              }}
              placeholder="https://example.com/gallery"
              required
              disabled={loading}
              aria-invalid={Boolean(validationErrors.url)}
              className={cn(
                validationErrors.url ? 'border-destructive focus-visible:ring-destructive' : '',
              )}
            />
          </FormField>

          <div className="grid gap-6 sm:grid-cols-2">
            <FormField
              label="Job Name"
              htmlFor="scrape-name"
              description="Defaults to the URL when blank."
            >
              <Input
                id="scrape-name"
                type="text"
                value={name}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => setName(event.target.value)}
                placeholder="Auto-generated from URL"
                disabled={loading}
              />
            </FormField>

            <FormField label="Max Depth" htmlFor="scrape-depth" error={validationErrors.depth}>
              <Input
                id="scrape-depth"
                type="number"
                inputMode="numeric"
                min={1}
                max={10}
                step={1}
                value={depthValue}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setDepthValue(event.target.value)
                  clearValidationError('depth')
                }}
                disabled={loading}
                aria-invalid={Boolean(validationErrors.depth)}
                className={cn(
                  validationErrors.depth ? 'border-destructive focus-visible:ring-destructive' : '',
                )}
              />
              <p className="text-xs text-muted-foreground">How many links deep to follow (1-10).</p>
            </FormField>
          </div>

          <FormField label="Description" htmlFor="scrape-description">
            <Textarea
              id="scrape-description"
              value={description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(event.target.value)}
              placeholder="Optional description for this scraping job"
              rows={3}
              disabled={loading}
            />
          </FormField>

          <FormField label="Max Images" htmlFor="scrape-max-images" error={validationErrors.maxImages}>
            <Input
              id="scrape-max-images"
              type="number"
              inputMode="numeric"
              min={1}
              max={10000}
              step={1}
              value={maxImagesValue}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                setMaxImagesValue(event.target.value)
                clearValidationError('maxImages')
              }}
              disabled={loading}
              aria-invalid={Boolean(validationErrors.maxImages)}
              className={cn(
                validationErrors.maxImages ? 'border-destructive focus-visible:ring-destructive' : '',
              )}
            />
            <p className="text-xs text-muted-foreground">Maximum images to download (1-10,000).</p>
          </FormField>
        </div>

        <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button type="submit" disabled={loading || !url}>
            <Plus className="mr-2 h-4 w-4" />
            {loading ? 'Starting…' : 'Start Scrape'}
          </Button>
          <Button type="button" onClick={onClose} disabled={loading} variant="outline">
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}

export default ScrapingTab
