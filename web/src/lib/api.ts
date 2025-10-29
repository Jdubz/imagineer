import { z } from 'zod'
import { logger } from './logger'
import type {
  Config,
  GeneratedImage,
  BatchSummary,
  Job,
  Album,
  LabelAnalytics,
} from '../types/models'
import type { AuthStatus } from '../types/shared'
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
    public response?: unknown
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

/**
 * Makes a typed API request with Zod validation
 */
async function apiRequest<T>(
  url: string,
  schema: z.ZodType<T>,
  options?: RequestInit
): Promise<T> {
  try {
    const response = await fetch(url, options)

    if (!response.ok) {
      // Try to get error message from response
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        if (isRecord(errorData) && typeof errorData.error === 'string') {
          errorMessage = errorData.error
        }
      } catch {
        // Couldn't parse error response, use status text
      }

      throw new ApiError(errorMessage, response.status)
    }

    const data = await response.json()

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
      return apiRequest('/api/auth/me', schemas.AuthStatusSchema, {
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
      return await apiRequest('/api/config', schemas.ConfigSchema, {
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
    async getAll(signal?: AbortSignal): Promise<GeneratedImage[]> {
      const response = await apiRequest('/api/outputs', schemas.ImagesResponseSchema, { signal })
      return response.images || []
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
      const response = await apiRequest('/api/batches', schemas.BatchesResponseSchema, { signal })
      return response.batches || []
    },

    /**
     * Fetch batch details by ID
     */
    async getById(batchId: string, signal?: AbortSignal): Promise<{ batch_id: string; image_count: number; images?: Array<{ filename: string; relative_path: string; created: string; metadata?: unknown }> }> {
      return apiRequest(`/api/batches/${batchId}`, schemas.BatchDetailSchema, { signal })
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
    async getById(jobId: string, signal?: AbortSignal): Promise<Job> {
      return apiRequest(`/api/jobs/${jobId}`, schemas.JobSchema, {
        credentials: 'include',
        signal,
      })
    },

    /**
     * Fetch all jobs (current, queue, history)
     * Requires admin authentication
     */
    async getAll(signal?: AbortSignal): Promise<{ current: Job | null; queue: Job[]; history: Job[] }> {
      return apiRequest(`/api/jobs`, schemas.JobsResponseSchema, {
        credentials: 'include',
        signal,
      })
    },
  },

  // ============================================
  // LoRAs
  // ============================================

  loras: {
    /**
     * Fetch all available LoRAs
     */
    async getAll(signal?: AbortSignal): Promise<Array<{ folder: string; filename: string }>> {
      const response = await apiRequest('/api/loras', schemas.LorasResponseSchema, { signal })
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
      const response = await apiRequest('/api/themes/random', schemas.ThemeResponseSchema, { signal })
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
      const response = await apiRequest('/api/albums', schemas.AlbumsResponseSchema, { signal })

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
      albumId: string,
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
     * Create a new album
     */
    async create(
      name: string,
      description: string,
      albumType: string = 'manual',
      signal?: AbortSignal
    ): Promise<{ success: boolean; error?: string }> {
      try {
        const response = await fetch('/api/albums', {
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
        const response = await fetch(`/api/albums/${albumId}`, {
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
      params: {
        user_theme: string
        steps?: number
        seed?: number
        width?: number
        height?: number
        guidance_scale?: number
        negative_prompt?: string
      },
      signal?: AbortSignal
    ): Promise<{ success: boolean; error?: string }> {
      try {
        const response = await fetch(`/api/albums/${albumId}/generate/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(params),
          signal,
        })

        if (!response.ok) {
          const data = await response.json()
          return {
            success: false,
            error: isRecord(data) && typeof data.error === 'string' ? data.error : 'Failed to generate batch',
          }
        }

        return { success: true }
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
}
