/**
 * AppContext - Centralized Application State Management
 *
 * This context eliminates props drilling by providing app-wide state
 * for generation, gallery, and configuration management.
 *
 * Benefits:
 * - Eliminates passing 6+ props through component tree
 * - Single source of truth for app state
 * - Type-safe with full TypeScript support
 * - Logical separation of concerns (generation, gallery, config)
 */

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'
import { logger } from '../lib/logger'
import { api } from '../lib/api'
import { JobSchema } from '../lib/schemas'
import { useToast } from '../hooks/use-toast'
import { useAuth } from './AuthContext'
import type {
  Config,
  GeneratedImage,
  BatchSummary,
  Job,
  GenerateParams,
  NsfwPreference,
} from '../types/models'

const NSFW_STORAGE_KEY = 'imagineer.nsfwPreference'

const getStoredNsfwPreference = (): NsfwPreference => {
  if (typeof window === 'undefined') {
    return 'show'
  }
  const stored = window.localStorage.getItem(NSFW_STORAGE_KEY)
  if (stored === 'show' || stored === 'blur' || stored === 'hide') {
    return stored
  }
  return 'show'
}

// ===== Type Definitions =====

interface GenerationState {
  config: Config | null
  loading: boolean
  currentJob: Job | null
  queuePosition: number | null
}

interface GalleryState {
  images: GeneratedImage[]
  batches: BatchSummary[]
  loadingImages: boolean
  loadingBatches: boolean
}

interface AppContextValue {
  // Generation State
  generation: GenerationState

  // Gallery State
  gallery: GalleryState

  // NSFW Filter
  nsfwPreference: NsfwPreference
  setNsfwPreference: (preference: NsfwPreference) => void

  // Generation Actions
  handleGenerate: (params: GenerateParams) => Promise<void>
  fetchConfig: (signal?: AbortSignal) => Promise<void>

  // Gallery Actions
  fetchImages: (signal?: AbortSignal) => Promise<void>
  fetchBatches: (signal?: AbortSignal) => Promise<void>
}

// ===== Context Creation =====

const AppContext = createContext<AppContextValue | undefined>(undefined)

// ===== Provider Component =====

interface AppProviderProps {
  children: ReactNode
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const { toast } = useToast()
  const { user } = useAuth()

  // ===== Generation State =====
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [currentJob, setCurrentJob] = useState<Job | null>(null)
  const [queuePosition, setQueuePosition] = useState<number | null>(null)
  const [configAuthAlerted, setConfigAuthAlerted] = useState<boolean>(false)

  // ===== Gallery State =====
  const [images, setImages] = useState<GeneratedImage[]>([])
  const [batches, setBatches] = useState<BatchSummary[]>([])
  const [loadingImages, setLoadingImages] = useState<boolean>(false)
  const [loadingBatches, setLoadingBatches] = useState<boolean>(false)

  // ===== Other State =====
  const [nsfwPreference, setNsfwPreferenceState] = useState<NsfwPreference>(() => getStoredNsfwPreference())

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(NSFW_STORAGE_KEY, nsfwPreference)
    }
  }, [nsfwPreference])

  const setNsfwPreference = useCallback((preference: NsfwPreference) => {
    setNsfwPreferenceState(preference)
  }, [])

  // ===== Config Fetching =====
  const fetchConfig = useCallback(async (signal?: AbortSignal): Promise<void> => {
    try {
      const config = await api.getConfig(signal)
      setConfig(config)
      if (config !== null) {
        setConfigAuthAlerted(false)
      }

      // Config is null when 401/403 (admin auth required)
      if (config === null && user?.role !== 'admin') {
        logger.info('Config requires admin authentication')
        if (!configAuthAlerted) {
          toast({ title: 'Info', description: 'Admin login required to load configuration settings.' })
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
        toast({ title: 'Error', description: 'Unable to load configuration. Please verify admin access.', variant: 'destructive' })
        setConfigAuthAlerted(true)
      }
    }
  }, [configAuthAlerted, user?.role, toast])

  // ===== Image Fetching =====
  const fetchImages = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setLoadingImages(true)
    try {
      const images = await api.images.getAll({ signal })
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

  // ===== Batch Fetching =====
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

  // ===== Generation Handler =====
  const handleGenerate = useCallback(async (params: GenerateParams): Promise<void> => {
    setLoading(true)
    setCurrentJob(null)
    setQueuePosition(null)

    try {
      const job = await api.submitJob(params)
      setCurrentJob(job)

      // Poll for job completion
      const pollInterval = 2000
      const maxAttempts = 60
      let attempts = 0

      const pollJobStatus = async (): Promise<void> => {
        try {
          const jobData = await api.getJob(job.id)
          const validatedJob = JobSchema.parse(jobData)

          setCurrentJob(validatedJob)

          if (validatedJob.queue_position !== null && validatedJob.queue_position !== undefined) {
            setQueuePosition(validatedJob.queue_position)
          }

          if (validatedJob.status === 'completed' || validatedJob.status === 'failed' || validatedJob.status === 'cancelled') {
            setLoading(false)
            setQueuePosition(null)

            if (validatedJob.status === 'completed') {
              toast({ title: 'Success', description: 'Image generated successfully!' })
              await fetchImages()
            } else if (validatedJob.status === 'failed') {
              toast({ title: 'Generation failed', description: validatedJob.error ?? 'Unknown error', variant: 'destructive' })
            } else if (validatedJob.status === 'cancelled') {
              toast({ title: 'Warning', description: 'Job was cancelled' })
            }
          } else if (attempts < maxAttempts) {
            attempts++
            setTimeout(() => void pollJobStatus(), pollInterval)
          } else {
            setLoading(false)
            toast({ title: 'Error', description: 'Job polling timeout', variant: 'destructive' })
          }
        } catch (error) {
          logger.error('Error polling job status', error as Error)
          setLoading(false)
          toast({ title: 'Error', description: 'Failed to check job status', variant: 'destructive' })
        }
      }

      await pollJobStatus()
    } catch (error) {
      setLoading(false)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'

      if (errorMessage.includes('401') || errorMessage.includes('403')) {
        logger.warn('Job submission requires authentication')
        return
      }

      toast({ title: 'Failed to submit job', description: errorMessage, variant: 'destructive' })
    }
  }, [toast, fetchImages])

  // ===== Initial Data Fetch =====
  useEffect(() => {
    const controller = new AbortController()
    void fetchConfig(controller.signal)
    void fetchImages(controller.signal)
    void fetchBatches(controller.signal)

    return () => {
      controller.abort()
    }
  }, [fetchConfig, fetchImages, fetchBatches])

  // ===== Context Value =====
  const value: AppContextValue = {
    generation: {
      config,
      loading,
      currentJob,
      queuePosition,
    },
    gallery: {
      images,
      batches,
      loadingImages,
      loadingBatches,
    },
    nsfwPreference,
    setNsfwPreference,
    handleGenerate,
    fetchConfig,
    fetchImages,
    fetchBatches,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

// ===== Custom Hook =====

/**
 * Hook to access app-wide state and actions
 * @throws Error if used outside AppProvider
 */
export const useApp = (): AppContextValue => {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}

// ===== Convenience Hooks =====

/**
 * Hook to access only generation-related state and actions
 */
export const useGeneration = () => {
  const { generation, handleGenerate, fetchConfig } = useApp()
  return { ...generation, handleGenerate, fetchConfig }
}

/**
 * Hook to access only gallery-related state and actions
 */
export const useGallery = () => {
  const { gallery, fetchImages, fetchBatches, nsfwPreference, setNsfwPreference } = useApp()
  return { ...gallery, fetchImages, fetchBatches, nsfwPreference, setNsfwPreference }
}
