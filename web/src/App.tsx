import React, { useState, useEffect } from 'react'
import './styles/App.css'
import AuthButton from './components/AuthButton'
import Tabs from './components/Tabs'
import GenerateTab from './components/GenerateTab'
import GalleryTab from './components/GalleryTab'
import AlbumsTab from './components/AlbumsTab'
import ScrapingTab from './components/ScrapingTab'
import TrainingTab from './components/TrainingTab'
import LorasTab from './components/LorasTab'
import QueueTab from './components/QueueTab'
import { logger } from './lib/logger'
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

const App: React.FC = () => {
  const [config, setConfig] = useState<Config | null>(null)
  const [images, setImages] = useState<GeneratedImage[]>([])
  const [loading, setLoading] = useState<boolean>(false)
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
    void fetchConfig()
    void fetchImages()
    void fetchBatches()
    void checkAuth()
  }, [])

  const checkAuth = async (): Promise<void> => {
    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include'
      })
      const data: AuthStatus = await response.json()

      if (data.authenticated) {
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      logger.error('Failed to check auth', error as Error)
      setUser(null)
    }
  }

  const fetchConfig = async (): Promise<void> => {
    try {
      const response = await fetch('/api/config')
      const payload = (await response.json()) as unknown
      setConfig(isRecord(payload) ? (payload as Config) : null)
    } catch (error) {
      logger.error('Failed to fetch config', error as Error)
    }
  }

  const fetchImages = async (): Promise<void> => {
    try {
      const response = await fetch('/api/outputs')
      const payload = (await response.json()) as unknown
      let images: GeneratedImage[] = []
      if (isRecord(payload)) {
        const maybeImages = (payload as { images?: unknown }).images
        if (Array.isArray(maybeImages)) {
          images = maybeImages as GeneratedImage[]
        }
      }
      setImages(images)
    } catch (error) {
      logger.error('Failed to fetch images', error as Error)
    }
  }

  const fetchBatches = async (): Promise<void> => {
    try {
      const response = await fetch('/api/batches')
      const payload = (await response.json()) as unknown
      let batches: BatchSummary[] = []
      if (isRecord(payload)) {
        const maybeBatches = (payload as { batches?: unknown }).batches
        if (Array.isArray(maybeBatches)) {
          batches = maybeBatches as BatchSummary[]
        }
      }
      setBatches(batches)
    } catch (error) {
      logger.error('Failed to fetch batches', error as Error)
    }
  }

  const handleGenerate = async (params: GenerateParams): Promise<void> => {
    setLoading(true)
    setQueuePosition(null)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        alert(`Failed to submit job: ${errorMessage}`)
        setLoading(false)
      }
    } catch (error) {
      logger.error('Failed to generate', error as Error)
      alert('Error submitting job')
      setLoading(false)
    }
  }

  const handleGenerateBatch = async (params: BatchGenerateParams): Promise<void> => {
    setLoading(true)
    try {
      const response = await fetch('/api/generate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      })

      if (response.status === 201) {
        const payload = (await response.json()) as unknown
        if (isRecord(payload) && typeof payload.total_jobs === 'number') {
          alert(`Batch generation started!\n${payload.total_jobs} jobs queued for ${String(payload.set_name ?? 'unknown set')}`)
        } else {
          alert('Batch generation started!')
        }
        fetchBatches().catch((error) => logger.error('Failed to refresh batches', error as Error))
        setActiveTab('gallery')
      } else {
        const payload = (await response.json()) as unknown
        const errorMessage =
          isRecord(payload) && typeof payload.error === 'string'
            ? payload.error
            : 'Unknown error'
        alert(`Failed to submit batch: ${errorMessage}`)
      }
    } catch (error: unknown) {
      logger.error('Failed to generate batch', error as Error)
      alert('Error submitting batch')
    } finally {
      setLoading(false)
    }
  }

  const pollJobStatus = (jobId: string): void => {
    const checkStatus = async (): Promise<void> => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`)
        const job: Job = await response.json()

        // Update queue position
        const queuePosition = typeof job.queue_position === 'number' ? job.queue_position : null
        setQueuePosition(queuePosition)

        if (job.status === 'completed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          fetchImages().catch((err) => logger.error('Failed to refresh images', err as Error))
          fetchBatches().catch((err) => logger.error('Failed to refresh batches', err as Error))
        } else if (job.status === 'failed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          alert(`Generation failed: ${job.error ?? 'Unknown error'}`)
        } else if (job.status === 'cancelled') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          alert('Job was cancelled')
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
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="main-content">
          {activeTab === 'generate' && (
            <GenerateTab
              config={config}
              loading={loading}
              queuePosition={queuePosition}
              currentJob={currentJob}
              onGenerate={handleGenerate}
              onGenerateBatch={handleGenerateBatch}
            />
          )}

          {activeTab === 'gallery' && (
            <GalleryTab
              batches={batches}
              images={images}
              onRefreshImages={fetchImages}
              onRefreshBatches={fetchBatches}
            />
          )}

          {activeTab === 'albums' && (
            <AlbumsTab isAdmin={user?.role === 'admin'} />
          )}

          {activeTab === 'scraping' && (
            <ScrapingTab isAdmin={user?.role === 'admin'} />
          )}

          {activeTab === 'training' && (
            <TrainingTab isAdmin={user?.role === 'admin'} />
          )}

          {activeTab === 'queue' && <QueueTab />}

          {activeTab === 'loras' && <LorasTab />}
        </div>
      </div>
    </div>
  )
}

export default App
