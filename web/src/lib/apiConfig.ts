/**
 * API Configuration and URL utilities
 *
 * In development: Uses Vite proxy (/api -> http://localhost:10050)
 * In production: Uses VITE_API_BASE_URL environment variable
 */

import { logger } from './logger'

// Get the API base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// Check if we're in development mode (has Vite proxy)
const isDevelopment = import.meta.env.DEV

/**
 * Builds the full API URL for a given endpoint
 *
 * @param endpoint - The API endpoint (e.g., '/auth/login', 'images')
 * @returns The full URL to use for the API request
 *
 * @example
 * // Development (uses proxy)
 * getApiUrl('/auth/login') // => '/api/auth/login'
 *
 * // Production (uses full URL)
 * getApiUrl('/auth/login') // => 'https://imagineer-api.joshwentworth.com/api/auth/login'
 */
export function getApiUrl(endpoint: string): string {
  // Normalize endpoint to start with /
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  // In development, use relative URLs (Vite proxy handles routing)
  if (isDevelopment) {
    // If endpoint already starts with /api, use as-is
    if (normalizedEndpoint.startsWith('/api/')) {
      return normalizedEndpoint
    }
    // Otherwise prepend /api
    return `/api${normalizedEndpoint}`
  }

  // In production, use full URL from environment variable
  if (!API_BASE_URL) {
    logger.error('VITE_API_BASE_URL is not configured for production build')
    throw new Error('API base URL is not configured')
  }

  // Remove trailing slash from base URL
  const baseUrl = API_BASE_URL.replace(/\/$/, '')

  // Endpoint does not include /api/ prefix (added by base URL)
  return `${baseUrl}${normalizedEndpoint}`
}

/**
 * Get the API base URL (for external redirects that need the full origin)
 *
 * @returns The full API base URL
 *
 * @example
 * // Development
 * getApiBaseUrl() // => 'http://localhost:10050/api'
 *
 * // Production
 * getApiBaseUrl() // => 'https://imagineer-api.joshwentworth.com/api'
 */
export function getApiBaseUrl(): string {
  if (isDevelopment) {
    // In development, construct from window.location
    return `${window.location.origin}/api`
  }

  if (!API_BASE_URL) {
    logger.error('VITE_API_BASE_URL is not configured for production build')
    throw new Error('API base URL is not configured')
  }

  return API_BASE_URL.replace(/\/$/, '')
}
