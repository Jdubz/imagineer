import React, { useState, useEffect, lazy, Suspense, useCallback, useRef } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import './styles/App.css'
import SkipNav from './components/SkipNav'
import Tabs from './components/Tabs'
import ErrorBoundaryWithReporting from './components/ErrorBoundaryWithReporting'
import ToastContainer from './components/Toast'
import Spinner from './components/Spinner'
import { ToastProvider } from './contexts/ToastContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { useToast } from './hooks/useToast'
import { useKeyboardShortcut } from './hooks/useKeyboardShortcut'
import { logger } from './lib/logger'
import { api } from './lib/api'
import { JobSchema } from './lib/schemas'
import type {
  Config,
  GeneratedImage,
  BatchSummary,
  Job,
  GenerateParams,
  Tab,
} from './types/models'
import { BugReportProvider, useBugReporter } from './contexts/BugReportContext'
import SettingsMenu from './components/SettingsMenu'
import BugReportButton from './components/BugReportButton'

// Lazy load tab components for code splitting
const GenerateTab = lazy(() => import('./components/GenerateTab'))
const GalleryTab = lazy(() => import('./components/GalleryTab'))
const AlbumsTab = lazy(() => import('./components/AlbumsTab'))
const ScrapingTab = lazy(() => import('./components/ScrapingTab'))
const TrainingTab = lazy(() => import('./components/TrainingTab'))
const LorasTab = lazy(() => import('./components/LorasTab'))
const QueueTab = lazy(() => import('./components/QueueTab'))

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

const AppContent: React.FC = () => {
  const toast = useToast()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { openBugReport, registerCollector } = useBugReporter()
  const [config, setConfig] = useState<Config | null>(null)
  const [images, setImages] = useState<GeneratedImage[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [loadingImages, setLoadingImages] = useState<boolean>(false)
  const [loadingBatches, setLoadingBatches] = useState<boolean>(false)
  const [currentJob, setCurrentJob] = useState<Job | null>(null)
  const [queuePosition, setQueuePosition] = useState<number | null>(null)
  const [batches, setBatches] = useState<BatchSummary[]>([])
  const [nsfwEnabled, setNsfwEnabled] = useState<boolean>(false)
  const [configAuthAlerted, setConfigAuthAlerted] = useState<boolean>(false)
  const toastRef = useRef(toast)

  useEffect(() => {
    toastRef.current = toast
  }, [toast])

  // Tab configuration
  const tabs: Tab[] = [
    { id: 'generate', label: 'Generate', icon: '✨' },
    { id: 'gallery', label: 'Gallery', icon: '🖼️' },
    { id: 'albums', label: 'Albums', icon: '📁' },
    { id: 'scraping', label: 'Scraping', icon: '🕷️' },
    { id: 'training', label: 'Training', icon: '🚀' },
    { id: 'queue', label: 'Queue', icon: '📋' },
    { id: 'loras', label: 'LoRAs', icon: '🎨' }
  ]

  // Get active tab from URL
  const activeTab = location.pathname.slice(1) || 'generate'

  // Register Ctrl+Shift+B keyboard shortcut for bug reporting (admin only)
  useKeyboardShortcut({
    key: 'b',
    ctrlKey: true,
    shiftKey: true,
    enabled: user?.role === 'admin',
    callback: openBugReport,
  })

  const fetchConfig = useCallback(async (signal?: AbortSignal): Promise<void> => {
    try {
      const config = await api.getConfig(signal)
      setConfig(config)
      if (config !== null) {
        setConfigAuthAlerted(false)
      }

      // Config is null when 401/403 (admin auth required) - already handled by api.getConfig
      if (config === null && user?.role !== 'admin') {
        // Only show message if user is not admin - helps them understand why config isn't loading
        logger.info('Config requires admin authentication')
        if (!configAuthAlerted) {
          toastRef.current.info('Admin login required to load configuration settings.')
          setConfigAuthAlerted(true)
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      logger.error('Failed to fetch config', error as Error)
      setConfig(null)
      if (!configAuthAlerted) {
        toastRef.current.error('Unable to load configuration. Please verify admin access.')
        setConfigAuthAlerted(true)
      }
    }
  }, [configAuthAlerted, user?.role])

  const fetchImages = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setLoadingImages(true)
    try {
      const images = await api.images.getAll(signal)
      setImages(images)
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      logger.error('Failed to fetch images', error as Error)
    } finally {
      setLoadingImages(false)
    }
  }, [])

  const fetchBatches = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setLoadingBatches(true)
    try {
      const batches = await api.batches.getAll(signal)
      setBatches(batches)
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      logger.error('Failed to fetch batches', error as Error)
    } finally {
      setLoadingBatches(false)
    }
  }, [])

  // Load config on mount
  useEffect(() => {
    const abortController = new AbortController()
    const { signal } = abortController

    void fetchConfig(signal)
    void fetchImages(signal)
    void fetchBatches(signal)

    return () => abortController.abort()
  }, [fetchConfig, fetchImages, fetchBatches])

  useEffect(() => {
    const unregister = registerCollector('application_state', () => {
      const imagePreview = images.slice(0, 5).map(({ filename, created, metadata }) => ({
        filename,
        created,
        model: metadata?.model,
        seed: metadata?.seed,
      }))

      const batchPreview = batches.slice(0, 5).map(({ batch_id, image_count, created }) => ({
        batch_id,
        image_count,
        created,
      }))

      const jobSnapshot = currentJob
        ? {
            id: currentJob.id,
            status: currentJob.status,
            queue_position: currentJob.queue_position,
            submitted_at: currentJob.submitted_at ?? currentJob.created ?? null,
            error: currentJob.error ?? null,
          }
        : null

      return {
        route: {
          pathname: location.pathname,
          search: location.search,
          hash: location.hash,
        },
        activeTab,
        loading: {
          generate: loading,
          images: loadingImages,
          batches: loadingBatches,
        },
        queuePosition,
        counts: {
          batches: batches.length,
          images: images.length,
        },
        currentJob: jobSnapshot,
        config,
        user,
        imagePreview,
        batchPreview,
      }
    })

    return unregister
  }, [
    activeTab,
    batches,
    config,
    currentJob,
    images,
    loading,
    loadingBatches,
    loadingImages,
    location.hash,
    location.pathname,
    location.search,
    queuePosition,
    registerCollector,
    user,
  ])

  const handleGenerate = async (params: GenerateParams): Promise<void> => {
    setLoading(true)
    setQueuePosition(null)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(params)
      })

      if (response.status === 201) {
        const payload = await response.json()

        // Validate response with Zod schema
        const validationResult = JobSchema.safeParse(payload)
        if (!validationResult.success) {
          logger.error('Invalid job response', validationResult.error)
          throw new Error('Invalid job response from API')
        }

        const job = validationResult.data
        setCurrentJob(job)
        setQueuePosition(job.queue_position ?? null)

        pollJobStatus(job.id)
      } else {
        const payload = (await response.json()) as unknown
        const errorMessage =
          isRecord(payload) && typeof payload.error === 'string'
            ? payload.error
            : 'Unknown error'
        toast.error(`Failed to submit job: ${errorMessage}`)
        setLoading(false)
      }
    } catch (error) {
      logger.error('Failed to generate', error as Error)
      toast.error('Error submitting job')
      setLoading(false)
    }
  }

  const pollJobStatus = (jobId: number | string): void => {
    const checkStatus = async (): Promise<void> => {
      try {
        const job = await api.jobs.getById(jobId)

        // Update queue position
        const queuePosition = typeof job.queue_position === 'number' ? job.queue_position : null
        setQueuePosition(queuePosition)

        if (job.status === 'completed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          toast.success('Image generated successfully!')
          fetchImages().catch((err) => logger.error('Failed to refresh images', err as Error))
          fetchBatches().catch((err) => logger.error('Failed to refresh batches', err as Error))
        } else if (job.status === 'failed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          toast.error(`Generation failed: ${job.error ?? 'Unknown error'}`)
        } else if (job.status === 'cancelled') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          toast.warning('Job was cancelled')
        } else {
          setTimeout(checkStatus, 2000)
        }
      } catch (error: unknown) {
        logger.error('Error checking job status', error as Error)
        setLoading(false)
        setCurrentJob(null)
        setQueuePosition(null)
      }
    }

    void checkStatus()
  }

  return (
    <div className="App">
      <SkipNav />
      <ToastContainer />
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <h1>✨ Imagineer</h1>
            <p>AI Image Generation Toolkit</p>
          </div>
          <div className="header-actions">
            {user ? (
              <>
                <BugReportButton />
                <SettingsMenu
                  user={user}
                  onLogout={logout}
                  onNsfwToggle={setNsfwEnabled}
                  nsfwEnabled={nsfwEnabled}
                />
              </>
            ) : (
              <button
                type="button"
                className="auth-button auth-button--primary"
                onClick={() => {
                  const sanitizedState = window.location.pathname + window.location.search + window.location.hash || '/'
                  const loginUrl = new URL('/api/auth/login', window.location.origin)
                  loginUrl.searchParams.set('state', sanitizedState)
                  window.location.href = loginUrl.toString()
                }}
              >
                Login
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="container">
        <nav id="tabs-navigation" aria-label="Main navigation">
          <Tabs tabs={tabs} activeTab={activeTab} />
        </nav>

        <main id="main-content" className="main-content">
          <Suspense fallback={<Spinner size="large" message="Loading..." />}>
            <Routes>
              <Route path="/" element={<Navigate to="/generate" replace />} />
              <Route
                path="/generate"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Generate Tab">
                    <GenerateTab
                      config={config}
                      loading={loading}
                      queuePosition={queuePosition}
                      currentJob={currentJob}
                      onGenerate={handleGenerate}
                      isAdmin={user?.role === 'admin'}
                    />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/gallery"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Gallery Tab">
                    <GalleryTab
                      batches={batches}
                      images={images}
                      onRefreshImages={fetchImages}
                      onRefreshBatches={fetchBatches}
                      loadingImages={loadingImages}
                      loadingBatches={loadingBatches}
                    />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/albums"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Albums Tab">
                    <AlbumsTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/scraping"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Scraping Tab">
                    <ScrapingTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/training"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Training Tab">
                    <TrainingTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/queue"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Queue Tab">
                    <QueueTab />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/loras"
                element={
                  <ErrorBoundaryWithReporting boundaryName="LoRAs Tab">
                    <LorasTab />
                  </ErrorBoundaryWithReporting>
                }
              />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <BugReportProvider>
            <AppContent />
          </BugReportProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}

export default App
