import { z } from 'zod'
import { logger } from './logger'
import { getApiUrl } from './apiConfig'
import type {
  Album,
  BatchSummary,
  Config,
  GeneratedImage,
  ImageMetadata,
  Job,
  JobsResponse,
  LabelAnalytics,
  ScrapingJob,
  ScrapingStats,
  TrainingAlbum,
  TrainingJob,
  TrainingLogResponse,
} from '../types/models'
import type { AuthStatus } from '../types/shared'
import type { BugReportOptions, BugReportSubmissionResponse } from '../types/bugReport'
import * as schemas from './schemas'

/**
 * Typed API Client with runtime validation
 *
 * Features:
 * - Type-safe API calls with Zod runtime validation
 * - AbortSignal support for cancellation
 * - Consistent error handling
 * - Validates API responses against schemas
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: unknown,
    public traceId?: string,
    public retryAfter?: number
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class ValidationError extends Error {
  constructor(
    message: string,
    public zodError: z.ZodError
  ) {
    super(message)
    this.name = 'ValidationError'
  }
}

/**
 * Type guard to check if value is a record
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function toFiniteNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10)
    return Number.isNaN(parsed) ? undefined : parsed
  }

  return undefined
}

function getErrorMessageFromBody(body: unknown, fallback: string): string {
  if (typeof body === 'string') {
    const trimmed = body.trim()
    if (trimmed.length > 0) {
      return trimmed
    }
  }

  if (isRecord(body)) {
    const candidateKeys = ['error', 'message', 'detail'] as const
    for (const key of candidateKeys) {
      const value = body[key]
      if (typeof value === 'string') {
        const trimmed = value.trim()
        if (trimmed.length > 0) {
          return trimmed
        }
      }
    }
  }

  return fallback
}

type GeneratedImageContract = z.infer<typeof schemas.GeneratedImageSchema>

function toAbsoluteApiPath(path?: string | null): string | undefined {
  if (!path) {
    return undefined
  }

  if (/^https?:\/\//i.test(path)) {
    return path
  }

  if (path.startsWith('/')) {
    return path
  }

  return `/api/${path.replace(/^\/+/, '')}`
}

function buildMetadataFromImage(image: GeneratedImageContract): ImageMetadata | undefined {
  if (image.metadata) {
    return image.metadata
  }

  const metadata: ImageMetadata = {}

  if (typeof image.prompt === 'string' && image.prompt.trim().length > 0) {
    metadata.prompt = image.prompt
  }
  if (typeof image.negative_prompt === 'string' && image.negative_prompt.trim().length > 0) {
    metadata.negative_prompt = image.negative_prompt
  }
  type NumericMetadataKey = 'seed' | 'steps' | 'guidance_scale' | 'width' | 'height'
  const numericFields: Array<[NumericMetadataKey, number | null | undefined]> = [
    ['seed', image.seed],
    ['steps', image.steps],
    ['guidance_scale', image.guidance_scale],
    ['width', image.width],
    ['height', image.height],
  ]
  for (const [key, value] of numericFields) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      metadata[key] = value
    }
  }

  return Object.keys(metadata).length > 0 ? metadata : undefined
}

function normalizeGeneratedImage(image: GeneratedImageContract): GeneratedImage {
  const downloadUrl =
    toAbsoluteApiPath(image.download_url) ??
    toAbsoluteApiPath(image.path) ??
    (image.id ? `/api/images/${image.id}/file` : undefined)

  const thumbnailUrl =
    toAbsoluteApiPath(image.thumbnail_url) ??
    (image.id ? `/api/images/${image.id}/thumbnail` : undefined) ??
    downloadUrl

  const created = image.created ?? image.created_at ?? undefined

  return {
    id: image.id,
    filename: image.filename,
    path: image.path,
    relative_path: image.relative_path,
    storage_name: image.storage_name ?? undefined,
    download_url: downloadUrl,
    thumbnail_url: thumbnailUrl,
    size: typeof image.size === 'number' ? image.size : undefined,
    created,
    created_at: image.created_at ?? (created ?? undefined),
    prompt: typeof image.prompt === 'string' ? image.prompt : null,
    negative_prompt: typeof image.negative_prompt === 'string' ? image.negative_prompt : null,
    seed: typeof image.seed === 'number' ? image.seed : null,
    steps: typeof image.steps === 'number' ? image.steps : null,
    guidance_scale: typeof image.guidance_scale === 'number' ? image.guidance_scale : null,
    width: typeof image.width === 'number' ? image.width : null,
    height: typeof image.height === 'number' ? image.height : null,
    is_nsfw: image.is_nsfw,
    is_public: image.is_public,
    metadata: buildMetadataFromImage(image),
  }
}

export interface GenerateBatchParams {
  user_theme: string
  steps?: number
  seed?: number
  width?: number
  height?: number
  guidance_scale?: number
  negative_prompt?: string
}

export type GenerateBatchSuccess = {
  success: true
  message: string
  jobIds: number[]
  queuedCount: number
  batchId?: string
  albumId?: number
  albumName?: string
  outputDir?: string
}

export type GenerateBatchError = {
  success: false
  error: string
  status?: number
}

export type GenerateBatchResult = GenerateBatchSuccess | GenerateBatchError

export interface StartScrapingJobParams {
  url: string
  name?: string
  description?: string
  depth?: number
  max_images?: number
}

export interface CreateTrainingRunParams {
  name: string
  description: string
  album_ids: Array<string | number>
  config: {
    steps: number
    rank: number
    learning_rate: number
    batch_size: number
  }
}

export interface TrainingLogRequestOptions {
  tail?: number
  signal?: AbortSignal
}

/**
 * Makes a typed API request with Zod validation
 *
 * Features:
 * - Automatically includes credentials: 'include' for all requests
 * - Captures X-Trace-Id header for error tracking
 * - Handles Retry-After header for rate limiting (429 responses)
 * - Runtime validation with Zod schemas
 */
async function apiRequest<T>(
  url: string,
  schema: z.ZodType<T>,
  options?: RequestInit
): Promise<T> {
  try {
    // Ensure credentials are always included unless explicitly overridden
    const requestOptions: RequestInit = {
      credentials: 'include',
      ...options,
    }

    const response = await fetch(url, requestOptions)
    const traceId = response.headers?.get?.('X-Trace-Id') ?? undefined

    // Parse Retry-After header if present (for 429 responses)
    let retryAfter: number | undefined
    const retryAfterHeader = response.headers?.get?.('Retry-After')
    if (retryAfterHeader) {
      // Retry-After can be a number (seconds) or an HTTP date
      const retrySeconds = Number.parseInt(retryAfterHeader, 10)
      if (!Number.isNaN(retrySeconds)) {
        retryAfter = retrySeconds
      } else {
        // Try parsing as HTTP date
        const retryDate = Date.parse(retryAfterHeader)
        if (!Number.isNaN(retryDate)) {
          retryAfter = Math.max(0, Math.floor((retryDate - Date.now()) / 1000))
        }
      }
    }

    if (!response.ok) {
      // Try to get error message from response
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        if (isRecord(errorData) && typeof errorData.error === 'string') {
          errorMessage = errorData.error
        } else if (isRecord(errorData) && typeof errorData.message === 'string') {
          errorMessage = errorData.message
        }
      } catch {
        // Couldn't parse error response, use status text
      }

      // Special handling for rate limiting
      if (response.status === 429 && retryAfter) {
        errorMessage = `Rate limit exceeded. Please retry after ${retryAfter} seconds.`
      }

      throw new ApiError(errorMessage, response.status, undefined, traceId, retryAfter)
    }

    let data: unknown
    try {
      data = await response.json()
    } catch (error) {
      logger.error('Failed to parse JSON response:', error)
      throw new ApiError('Failed to parse JSON response', response.status, undefined, traceId, retryAfter)
    }

    // Validate response with Zod schema
    const validationResult = schema.safeParse(data)

    if (!validationResult.success) {
      logger.error('API response validation failed:', validationResult.error)
      throw new ValidationError(
        'API response does not match expected schema',
        validationResult.error
      )
    }

    return validationResult.data
  } catch (error) {
    if (error instanceof ApiError || error instanceof ValidationError) {
      throw error
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        // Re-throw AbortError as-is for proper handling
        throw error
      }

      // Wrap other errors
      logger.error('API request failed:', error)
      throw new ApiError(`API request failed: ${error.message}`)
    }

    throw new ApiError('Unknown API error occurred')
  }
}


/**
 * API Client
 */
export const api = {
  // ============================================
  // Authentication
  // ============================================

  auth: {
    /**
     * Check current authentication status
     */
    async checkAuth(signal?: AbortSignal): Promise<AuthStatus> {
      return apiRequest(getApiUrl('/auth/me'), schemas.AuthStatusSchema, {
        credentials: 'include',
        signal,
      })
    },
  },

  // ============================================
  // Configuration
  // ============================================

  /**
   * Fetch application configuration
   */
  async getConfig(signal?: AbortSignal): Promise<Config | null> {
    try {
      return await apiRequest(getApiUrl('/config'), schemas.ConfigSchema, {
        credentials: 'include',
        signal,
      })
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        // Config endpoint requires admin auth - return null
        logger.warn('Config endpoint requires admin authentication')
        return null
      }
      throw error
    }
  },

  // ============================================
  // Images
  // ============================================

  images: {
    /**
     * Fetch all generated images
     */

async getAll(options: { signal?: AbortSignal; page?: number; perPage?: number } = {}): Promise<GeneratedImage[]> {
  const { signal, page = 1, perPage = 60 } = options
  const params = new URLSearchParams({
    visibility: 'public',
    page: String(page),
    per_page: String(perPage),
  })

  const response = await apiRequest(
    `/api/images?${params.toString()}`,
    schemas.PaginatedImagesResponseSchema,
    { signal }
  )
  return response.images.map(normalizeGeneratedImage)
},

    /**
     * Fetch image by ID
     */
    async getById(imageId: number, signal?: AbortSignal): Promise<GeneratedImage> {
      const response = await apiRequest(
        getApiUrl(`/images/${imageId}`),
        schemas.GeneratedImageSchema,
        { signal }
      )
      return normalizeGeneratedImage(response)
    },

    /**
     * Update image metadata
     */
    async update(
      imageId: number,
      data: { prompt?: string; negative_prompt?: string },
      signal?: AbortSignal
    ): Promise<GeneratedImage> {
      const response = await apiRequest(
        getApiUrl(`/images/${imageId}`),
        schemas.GeneratedImageSchema,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(data),
          signal,
        }
      )
      return normalizeGeneratedImage(response)
    },

    /**
     * Delete an image
     */
    async delete(imageId: number, signal?: AbortSignal): Promise<void> {
      await fetch(getApiUrl(`/images/${imageId}`), {
        method: 'DELETE',
        credentials: 'include',
        signal,
      })
    },
  },

  // ============================================
  // Batches
  // ============================================

  batches: {
    /**
     * Fetch all batch summaries
     */

async getAll(signal?: AbortSignal): Promise<BatchSummary[]> {
  const response = await apiRequest(getApiUrl('/batches'), schemas.BatchesResponseSchema, { signal })
  return response.batches ?? []
},

    /**
     * Fetch batch details by ID
     */

async getById(batchId: string, signal?: AbortSignal): Promise<{ batch_id: string; album_id: number; name: string; album_type?: string; image_count: number; created?: string | null; updated?: string | null; images?: GeneratedImage[] }> {
  const response = await apiRequest(`/api/batches/${batchId}`, schemas.BatchDetailSchema, { signal })
  return {
    ...response,
    images: response.images?.map(normalizeGeneratedImage),
  }
},
  },

  // ============================================
  // Jobs
  // ============================================

  jobs: {
    /**
     * Fetch job status by ID
     * Requires admin authentication
     */
    async getById(jobId: number | string, signal?: AbortSignal): Promise<Job> {
      const id = encodeURIComponent(jobId.toString())
      return apiRequest(`/api/jobs/${id}`, schemas.JobSchema, {
        credentials: 'include',
        signal,
      })
    },

    /**
     * Fetch all jobs (current, queue, history)
     * Requires admin authentication
     */
    async getAll(signal?: AbortSignal): Promise<JobsResponse> {
      return apiRequest(`/api/jobs`, schemas.JobsResponseSchema, {
        credentials: 'include',
        signal,
      })
    },
  },

  /**
   * Submit a new generation job
   * @param params Generation parameters (prompt, steps, seed, etc.)
   * @returns The created job with ID and status
   */
  async submitJob(params: { prompt: string; negative_prompt?: string; steps?: number; guidance_scale?: number; seed?: number }, signal?: AbortSignal): Promise<Job> {
    return apiRequest(getApiUrl('/generate'), schemas.JobSchema, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(params),
      signal,
    })
  },

  // ============================================
  // Scraping
  // ============================================

  scraping: {
    async getJobs(signal?: AbortSignal): Promise<ScrapingJob[]> {
      const response = await apiRequest(getApiUrl('/scraping/jobs'), schemas.ScrapingJobsResponseSchema, { signal })
      const normalizeScrapingJob = (job: (typeof response.jobs)[number]): ScrapingJob => {
        const {
          id,
          status,
          url,
          name,
          source_url,
          output_dir,
          output_directory,
          progress,
          progress_message,
          description,
          runtime,
          created_at,
          completed_at,
          error,
          images_scraped,
          config,
        } = job

        return {
          id,
          status,
          url: url ?? undefined,
          name: name ?? undefined,
          source_url: source_url ?? undefined,
          output_dir: output_dir ?? undefined,
          output_directory: output_directory ?? undefined,
          progress: typeof progress === 'number' ? progress : progress ?? null,
          progress_message: progress_message ?? undefined,
          description: description ?? undefined,
          runtime: runtime ?? undefined,
          created_at,
          completed_at: completed_at ?? undefined,
          error: error ?? undefined,
          images_scraped: images_scraped ?? undefined,
          config: config ?? undefined,
        }
      }

      return (response.jobs ?? []).map(normalizeScrapingJob)
    },

    async getStats(signal?: AbortSignal): Promise<ScrapingStats> {
      return apiRequest(getApiUrl('/scraping/stats'), schemas.ScrapingStatsSchema, { signal })
    },

    async startJob(params: StartScrapingJobParams, signal?: AbortSignal): Promise<void> {
      await apiRequest(getApiUrl('/scraping/start'), schemas.ScrapingActionResponseSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal,
      })
    },

    async cancelJob(jobId: string | number, signal?: AbortSignal): Promise<void> {
      const id = encodeURIComponent(jobId.toString())
      await apiRequest(getApiUrl(`/scraping/jobs/${id}/cancel`), schemas.ScrapingActionResponseSchema, {
        method: 'POST',
        signal,
      })
    },

    async cleanupJob(jobId: string | number, signal?: AbortSignal): Promise<void> {
      const id = encodeURIComponent(jobId.toString())
      await apiRequest(getApiUrl(`/scraping/jobs/${id}/cleanup`), schemas.ScrapingActionResponseSchema, {
        method: 'POST',
        signal,
      })
    },
  },

  // ============================================
  // Training
  // ============================================

  training: {
    async getRuns(signal?: AbortSignal): Promise<TrainingJob[]> {
      const response = await apiRequest(getApiUrl('/training'), schemas.TrainingRunsResponseSchema, { signal })
      return response.training_runs || []
    },

    async getAlbums(signal?: AbortSignal): Promise<TrainingAlbum[]> {
      const response = await apiRequest(getApiUrl('/training/albums'), schemas.TrainingAlbumsResponseSchema, { signal })
      return response.albums || []
    },

    async getLogs(runId: string | number, options: TrainingLogRequestOptions = {}): Promise<TrainingLogResponse> {
      const tail = options.tail ?? 500
      const id = encodeURIComponent(runId.toString())
      const url = getApiUrl(`/training/${id}/logs?tail=${tail}`)
      return apiRequest(url, schemas.TrainingLogResponseSchema, { signal: options.signal })
    },

    async createRun(params: CreateTrainingRunParams, signal?: AbortSignal): Promise<void> {
      await apiRequest(getApiUrl('/training'), schemas.TrainingActionResponseSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal,
      })
    },

    async startRun(runId: string | number, signal?: AbortSignal): Promise<void> {
      const id = encodeURIComponent(runId.toString())
      await apiRequest(getApiUrl(`/training/${id}/start`), schemas.TrainingActionResponseSchema, {
        method: 'POST',
        signal,
      })
    },

    async cancelRun(runId: string | number, signal?: AbortSignal): Promise<void> {
      const id = encodeURIComponent(runId.toString())
      await apiRequest(getApiUrl(`/training/${id}/cancel`), schemas.TrainingActionResponseSchema, {
        method: 'POST',
        signal,
      })
    },

    async cleanupRun(runId: string | number, signal?: AbortSignal): Promise<void> {
      const id = encodeURIComponent(runId.toString())
      await apiRequest(getApiUrl(`/training/${id}/cleanup`), schemas.TrainingActionResponseSchema, {
        method: 'POST',
        signal,
      })
    },
  },

  /**
   * Get job status by ID (convenience alias for jobs.getById)
   * @param jobId Job ID to fetch
   * @returns Job status data
   */
  async getJob(jobId: number | string, signal?: AbortSignal): Promise<Job> {
    return api.jobs.getById(jobId, signal)
  },

  // ============================================
  // LoRAs
  // ============================================

  loras: {
    /**
     * Fetch all available LoRAs
     */
    async getAll(signal?: AbortSignal): Promise<Array<{ folder: string; filename: string }>> {
      const response = await apiRequest(getApiUrl('/loras'), schemas.LorasResponseSchema, {
        signal,
        credentials: 'include',
      })
      return response.loras || []
    },
  },

  // ============================================
  // Themes
  // ============================================

  themes: {
    /**
     * Fetch a random theme
     */
    async getRandom(signal?: AbortSignal): Promise<string> {
      const response = await apiRequest(getApiUrl('/themes/random'), schemas.ThemeResponseSchema, { signal })
      return response.theme || ''
    },
  },

  // ============================================
  // Albums
  // ============================================

  albums: {
    /**
     * Fetch all albums
     */
    async getAll(signal?: AbortSignal): Promise<Album[]> {
      const response = await apiRequest(getApiUrl('/albums'), schemas.AlbumsResponseSchema, { signal })

      if (Array.isArray(response)) {
        return response
      }

      if (isRecord(response) && Array.isArray(response.albums)) {
        return response.albums
      }

      return []
    },

    /**
     * Fetch album by ID
     */
    async getById(
      albumId: string | number,
      includeLabels: boolean = false,
      signal?: AbortSignal
    ): Promise<Album> {
      const includeParam = includeLabels ? '?include_labels=1' : ''
      return apiRequest(`/api/albums/${albumId}${includeParam}`, schemas.AlbumSchema, {
        credentials: 'include',
        signal,
      })
    },

    /**
     * Update album metadata
     */
    async update(
      albumId: string | number,
      data: { name?: string; description?: string },
      signal?: AbortSignal
    ): Promise<Album> {
      return apiRequest(
        getApiUrl(`/albums/${albumId}`),
        schemas.AlbumSchema,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(data),
          signal,
        }
      )
    },

    /**
     * Create a new album
     */
    async create(
      name: string,
      description: string,
      albumType: string = 'manual',
      signal?: AbortSignal
    ): Promise<{ success: boolean; error?: string }> {
      try {
        const response = await fetch(getApiUrl('/albums'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            name,
            description,
            album_type: albumType,
            is_public: true,
          }),
          signal,
        })

        if (!response.ok) {
          const data = await response.json()
          return {
            success: false,
            error: isRecord(data) && typeof data.error === 'string' ? data.error : 'Failed to create album',
          }
        }

        return { success: true }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          throw error
        }
        logger.error('Failed to create album:', error)
        return {
          success: false,
          error: 'Error creating album',
        }
      }
    },

    /**
     * Delete an album
     */
    async delete(albumId: string, signal?: AbortSignal): Promise<{ success: boolean; error?: string }> {
      try {
        const response = await fetch(getApiUrl(`/albums/${albumId}`), {
          method: 'DELETE',
          credentials: 'include',
          signal,
        })

        if (!response.ok) {
          const data = await response.json()
          return {
            success: false,
            error: isRecord(data) && typeof data.error === 'string' ? data.error : 'Failed to delete album',
          }
        }

        return { success: true }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          throw error
        }
        logger.error('Failed to delete album:', error)
        return {
          success: false,
          error: 'Error deleting album',
        }
      }
    },

    /**
     * Fetch album analytics
     */
    async getAnalytics(albumId: string, signal?: AbortSignal): Promise<LabelAnalytics> {
      return apiRequest(`/api/albums/${albumId}/labeling/analytics`, schemas.LabelAnalyticsSchema, {
        credentials: 'include',
        signal,
      })
    },

    /**
     * Generate batch of images from album template
     */
    async generateBatch(
      albumId: string,
      params: GenerateBatchParams,
      signal?: AbortSignal
    ): Promise<GenerateBatchResult> {
      try {
        const response = await fetch(getApiUrl(`/albums/${albumId}/generate/batch`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(params),
          signal,
        })

        const body = await response
          .json()
          .catch((error: unknown) => {
            logger.debug('Failed to parse batch generation response body', error)
            return undefined
          })

        if (!response.ok) {
          const fallbackError =
            response.status === 401 || response.status === 403
              ? 'Admin access required to generate batches'
              : 'Failed to generate batch'

          const errorMessage = getErrorMessageFromBody(body, fallbackError)

          return {
            success: false,
            error: errorMessage,
            status: response.status,
          }
        }

        const bodyRecord = isRecord(body) ? body : undefined
        const jobIds = Array.isArray(bodyRecord?.job_ids)
          ? bodyRecord.job_ids
              .map((value) => toFiniteNumber(value))
              .filter((id): id is number => typeof id === 'number')
          : []

        const message =
          typeof bodyRecord?.message === 'string' && bodyRecord.message.trim().length > 0
            ? bodyRecord.message.trim()
            : jobIds.length > 0
            ? `Queued ${jobIds.length} generation ${jobIds.length === 1 ? 'job' : 'jobs'}`
            : 'Batch generation started'

        const batchId =
          typeof bodyRecord?.batch_id === 'string' && bodyRecord.batch_id.trim().length > 0
            ? bodyRecord.batch_id
            : undefined
        const albumIdValue = toFiniteNumber(bodyRecord?.album_id)
        const albumName =
          typeof bodyRecord?.album_name === 'string' && bodyRecord.album_name.trim().length > 0
            ? bodyRecord.album_name
            : undefined
        const outputDir =
          typeof bodyRecord?.output_dir === 'string' && bodyRecord.output_dir.trim().length > 0
            ? bodyRecord.output_dir
            : undefined

        return {
          success: true,
          message,
          jobIds,
          queuedCount: jobIds.length,
          batchId,
          albumId: albumIdValue,
          albumName,
          outputDir,
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          throw error
        }
        logger.error('Failed to generate batch:', error)
        return {
          success: false,
          error: 'Error generating batch',
        }
      }
    },
  },

  bugReports: {
    async submit(payload: BugReportOptions): Promise<BugReportSubmissionResponse> {
      return apiRequest(getApiUrl('/bug-reports'), schemas.BugReportResponseSchema, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      })
    },
  },
}
