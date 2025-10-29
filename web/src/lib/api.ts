import { logger } from './logger'
import type {
  Config,
  GeneratedImage,
  BatchSummary,
  Job,
  SetInfo,
  Album,
  LabelAnalytics,
} from '../types/models'
import type { AuthStatus } from '../types/shared'

/**
 * Typed API Client with improved type safety
 *
 * Features:
 * - Type-safe API calls using existing type definitions
 * - AbortSignal support for cancellation
 * - Consistent error handling
 * - Eliminates unsafe type assertions
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

/**
 * Type guard to check if value is a record
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Makes a typed API request
 */
async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
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
    return data as T
  } catch (error) {
    if (error instanceof ApiError) {
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
      return apiRequest<AuthStatus>('/api/auth/me', {
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
      return await apiRequest<Config>('/api/config', {
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
      const response = await apiRequest<{ images: GeneratedImage[] }>('/api/outputs', { signal })
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
      const response = await apiRequest<{ batches: BatchSummary[] }>('/api/batches', { signal })
      return response.batches || []
    },

    /**
     * Fetch batch details by ID
     */
    async getById(batchId: string, signal?: AbortSignal): Promise<{ batch_id: string; image_count: number; images?: Array<{ filename: string; relative_path: string; created: string; metadata?: unknown }> }> {
      return apiRequest(`/api/batches/${batchId}`, { signal })
    },
  },

  // ============================================
  // Jobs
  // ============================================

  jobs: {
    /**
     * Fetch job status by ID
     */
    async getById(jobId: string, signal?: AbortSignal): Promise<Job> {
      return apiRequest<Job>(`/api/jobs/${jobId}`, { signal })
    },
  },

  // ============================================
  // Sets
  // ============================================

  sets: {
    /**
     * Fetch all available sets
     */
    async getAll(signal?: AbortSignal): Promise<Array<{ id: string; name: string }>> {
      const response = await apiRequest<{ sets: Array<{ id: string; name: string }> }>('/api/sets', { signal })
      return response.sets || []
    },

    /**
     * Fetch set information
     */
    async getInfo(setName: string, signal?: AbortSignal): Promise<SetInfo> {
      return apiRequest<SetInfo>(`/api/sets/${setName}/info`, { signal })
    },

    /**
     * Fetch set LoRA configuration
     */
    async getLoras(setName: string, signal?: AbortSignal): Promise<Array<{ folder: string; weight: number }>> {
      const response = await apiRequest<{ loras: Array<{ folder: string; weight: number }> }>(
        `/api/sets/${setName}/loras`,
        { signal }
      )
      return response.loras || []
    },

    /**
     * Update set LoRA configuration
     */
    async updateLoras(
      setName: string,
      loras: Array<{ folder: string; weight: number }>,
      signal?: AbortSignal
    ): Promise<{ success: boolean; error?: string }> {
      try {
        const response = await fetch(`/api/sets/${setName}/loras`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ loras }),
          signal,
        })

        if (response.status === 401 || response.status === 403) {
          return {
            success: false,
            error: 'Admin authentication required',
          }
        }

        if (!response.ok) {
          const data = await response.json()
          return {
            success: false,
            error: isRecord(data) && typeof data.error === 'string' ? data.error : 'Failed to update LoRAs',
          }
        }

        const data = await response.json()
        return {
          success: isRecord(data) && typeof data.success === 'boolean' ? data.success : true,
          error: isRecord(data) && typeof data.error === 'string' ? data.error : undefined,
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          throw error
        }
        logger.error('Failed to update set LoRAs:', error)
        return {
          success: false,
          error: 'Failed to update LoRA configuration',
        }
      }
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
      const response = await apiRequest<{ loras: Array<{ folder: string; filename: string }> }>('/api/loras', { signal })
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
      const response = await apiRequest<{ theme: string }>('/api/themes/random', { signal })
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
      const response = await apiRequest<{ albums: Album[] } | Album[]>('/api/albums', { signal })

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
      return apiRequest<Album>(`/api/albums/${albumId}${includeParam}`, {
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
      return apiRequest<LabelAnalytics>(`/api/albums/${albumId}/labeling/analytics`, {
        credentials: 'include',
        signal,
      })
    },
  },
}
