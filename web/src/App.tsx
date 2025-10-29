import React, { useState, useEffect } from 'react'
import './styles/App.css'
import SkipNav from './components/SkipNav'
import AuthButton from './components/AuthButton'
import Tabs from './components/Tabs'
import GenerateTab from './components/GenerateTab'
import GalleryTab from './components/GalleryTab'
import AlbumsTab from './components/AlbumsTab'
import ScrapingTab from './components/ScrapingTab'
import TrainingTab from './components/TrainingTab'
import LorasTab from './components/LorasTab'
import QueueTab from './components/QueueTab'
import ErrorBoundary from './components/ErrorBoundary'
import ToastContainer from './components/Toast'
import { ToastProvider } from './contexts/ToastContext'
import { useToast } from './hooks/useToast'
import { logger } from './lib/logger'
import { api } from './lib/api'
import type { AuthStatus } from './types/shared'
import type {
  Config,
  GeneratedImage,
  BatchSummary,
  Job,
  GenerateParams,
  BatchGenerateParams,
  Tab,
} from './types/models'

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

const AppContent: React.FC = () => {
  const toast = useToast()
  const [config, setConfig] = useState<Config | null>(null)
  const [images, setImages] = useState<GeneratedImage[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [loadingImages, setLoadingImages] = useState<boolean>(false)
  const [loadingBatches, setLoadingBatches] = useState<boolean>(false)
  const [currentJob, setCurrentJob] = useState<Job | null>(null)
  const [queuePosition, setQueuePosition] = useState<number | null>(null)
  const [batches, setBatches] = useState<BatchSummary[]>([])
  const [activeTab, setActiveTab] = useState<string>('generate')
  const [user, setUser] = useState<AuthStatus | null>(null)

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

  // Load config on mount
  useEffect(() => {
    const abortController = new AbortController()
    const { signal } = abortController

    void fetchConfig(signal)
    void fetchImages(signal)
    void fetchBatches(signal)
    void checkAuth(signal)

    return () => abortController.abort()
  }, [])

  const checkAuth = async (signal?: AbortSignal): Promise<void> => {
    try {
      const data = await api.auth.checkAuth(signal)

      if (data.authenticated) {
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was cancelled - this is expected behavior
        return
      }
      logger.error('Failed to check auth', error as Error)
      setUser(null)
    }
  }

  const fetchConfig = async (signal?: AbortSignal): Promise<void> => {
    try {
      const config = await api.getConfig(signal)
      setConfig(config)

      // Config is null when 401/403 (admin auth required) - already handled by api.getConfig
      if (config === null && user?.role !== 'admin') {
        // Only show message if user is not admin - helps them understand why config isn't loading
        logger.info('Config requires admin authentication')
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      logger.error('Failed to fetch config', error as Error)
      setConfig(null)
    }
  }

  const fetchImages = async (signal?: AbortSignal): Promise<void> => {
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
  }

  const fetchBatches = async (signal?: AbortSignal): Promise<void> => {
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
  }

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
        const payload = await response.json() as unknown
        if (!isRecord(payload)) {
          throw new Error('Invalid job response')
        }
        const result = payload as unknown as Job
        setCurrentJob(result)
        setQueuePosition(result.queue_position ?? null)

        pollJobStatus(result.id)
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

  const handleGenerateBatch = async (params: BatchGenerateParams): Promise<void> => {
    setLoading(true)
    try {
      const response = await fetch('/api/generate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(params)
      })

      if (response.status === 201) {
        const payload = (await response.json()) as unknown
        if (isRecord(payload) && typeof payload.total_jobs === 'number') {
          toast.success(`Batch generation started! ${payload.total_jobs} jobs queued for ${String(payload.set_name ?? 'unknown set')}`)
        } else {
          toast.success('Batch generation started!')
        }
        fetchBatches().catch((error) => logger.error('Failed to refresh batches', error as Error))
        setActiveTab('gallery')
      } else {
        const payload = (await response.json()) as unknown
        const errorMessage =
          isRecord(payload) && typeof payload.error === 'string'
            ? payload.error
            : 'Unknown error'
        toast.error(`Failed to submit batch: ${errorMessage}`)
      }
    } catch (error: unknown) {
      logger.error('Failed to generate batch', error as Error)
      toast.error('Error submitting batch')
    } finally {
      setLoading(false)
    }
  }

  const pollJobStatus = (jobId: string): void => {
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
          <AuthButton onAuthChange={setUser} />
        </div>
      </header>

      <div className="container">
        <nav id="tabs-navigation" aria-label="Main navigation">
          <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
        </nav>

        <main id="main-content" className="main-content">
          {activeTab === 'generate' && (
            <ErrorBoundary boundaryName="Generate Tab">
              <GenerateTab
                config={config}
                loading={loading}
                queuePosition={queuePosition}
                currentJob={currentJob}
                onGenerate={handleGenerate}
                onGenerateBatch={handleGenerateBatch}
                isAdmin={user?.role === 'admin'}
              />
            </ErrorBoundary>
          )}

          {activeTab === 'gallery' && (
            <ErrorBoundary boundaryName="Gallery Tab">
              <GalleryTab
                batches={batches}
                images={images}
                onRefreshImages={fetchImages}
                onRefreshBatches={fetchBatches}
                loadingImages={loadingImages}
                loadingBatches={loadingBatches}
              />
            </ErrorBoundary>
          )}

          {activeTab === 'albums' && (
            <ErrorBoundary boundaryName="Albums Tab">
              <AlbumsTab isAdmin={user?.role === 'admin'} />
            </ErrorBoundary>
          )}

          {activeTab === 'scraping' && (
            <ErrorBoundary boundaryName="Scraping Tab">
              <ScrapingTab isAdmin={user?.role === 'admin'} />
            </ErrorBoundary>
          )}

          {activeTab === 'training' && (
            <ErrorBoundary boundaryName="Training Tab">
              <TrainingTab isAdmin={user?.role === 'admin'} />
            </ErrorBoundary>
          )}

          {activeTab === 'queue' && (
            <ErrorBoundary boundaryName="Queue Tab">
              <QueueTab />
            </ErrorBoundary>
          )}

          {activeTab === 'loras' && (
            <ErrorBoundary boundaryName="LoRAs Tab">
              <LorasTab />
            </ErrorBoundary>
          )}
        </main>
      </div>
    </div>
  )
}

const App: React.FC = () => {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  )
}

export default App
