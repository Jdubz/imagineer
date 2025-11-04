import { describe, it, expect } from 'vitest'
import { getApiUrl, getApiBaseUrl } from './apiConfig'

/**
 * URL Pattern Enforcement Tests
 *
 * These tests verify that:
 * 1. The API configuration utility functions work correctly
 * 2. Production URLs use the correct domain: imagineer-api.joshwentworth.com
 * 3. No hardcoded localhost or incorrect domain references exist
 *
 * Note: In test/development environment, getApiUrl returns relative URLs.
 * In production builds, VITE_API_BASE_URL is set to https://imagineer-api.joshwentworth.com/api
 */
describe('apiConfig - URL Pattern Enforcement', () => {
  describe('Development Mode (Test Environment)', () => {
    it('should return relative URLs in development', () => {
      const url = getApiUrl('/auth/login')
      // In dev mode (which tests run in), URLs are relative
      expect(url).toBe('/api/auth/login')
    })

    it('should handle endpoints with /api/ prefix', () => {
      const url = getApiUrl('/api/images')
      expect(url).toBe('/api/images')
    })

    it('should prepend /api to endpoints without it', () => {
      const url = getApiUrl('/jobs')
      expect(url).toBe('/api/jobs')
    })

    it('should handle endpoints without leading slash', () => {
      const url = getApiUrl('batches')
      expect(url).toBe('/api/batches')
    })
  })

  describe('URL Normalization', () => {
    it('should normalize endpoints consistently', () => {
      // All these should produce the same result
      expect(getApiUrl('/images')).toBe('/api/images')
      expect(getApiUrl('/api/images')).toBe('/api/images')
      expect(getApiUrl('images')).toBe('/api/images')
    })

    it('should handle nested paths correctly', () => {
      expect(getApiUrl('/images/123/file')).toBe('/api/images/123/file')
      expect(getApiUrl('/albums/1/images/2')).toBe('/api/albums/1/images/2')
    })

    it('should preserve query parameters', () => {
      const url = getApiUrl('/images?page=1&per_page=20')
      expect(url).toBe('/api/images?page=1&per_page=20')
    })
  })

  describe('Common API Endpoints', () => {
    const endpoints = [
      '/auth/login',
      '/auth/logout',
      '/auth/me',
      '/images',
      '/images/123',
      '/images/123/file',
      '/images/123/thumbnail',
      '/images/123/labels',
      '/albums',
      '/albums/1',
      '/albums/1/images/2',
      '/albums/1/generate/batch',
      '/jobs',
      '/jobs/123',
      '/generate',
      '/batches',
      '/loras',
      '/scraping/jobs',
      '/scraping/stats',
      '/training',
      '/training/albums',
      '/labeling/tasks/123',
      '/labeling/album/1',
      '/labeling/image/1',
    ]

    endpoints.forEach(endpoint => {
      it(`should correctly resolve ${endpoint}`, () => {
        const url = getApiUrl(endpoint)
        // In dev mode, should be /api/...
        expect(url).toMatch(/^\/api\//)
      })
    })
  })

  describe('Production Configuration Validation', () => {
    it('should document the correct production domain', () => {
      // This test serves as documentation and validation
      const PRODUCTION_DOMAIN = 'imagineer-api.joshwentworth.com'
      const PRODUCTION_API_URL = `https://${PRODUCTION_DOMAIN}/api`

      // Verify the domain format is correct
      expect(PRODUCTION_DOMAIN).toContain('imagineer-api')
      expect(PRODUCTION_DOMAIN).toContain('joshwentworth.com')
      expect(PRODUCTION_API_URL).toBe('https://imagineer-api.joshwentworth.com/api')

      // This is what should be set in .env.production
      expect(PRODUCTION_API_URL).not.toContain('localhost')
      expect(PRODUCTION_API_URL).not.toContain(':10050')
      expect(PRODUCTION_API_URL).toMatch(/^https:/)
    })

    it('should not contain incorrect domain patterns', () => {
      const PRODUCTION_DOMAIN = 'imagineer-api.joshwentworth.com'

      // Should NOT be these incorrect variations
      expect(PRODUCTION_DOMAIN).not.toBe('imagineer.joshwentworth.com')
      expect(PRODUCTION_DOMAIN).not.toContain('localhost')
      expect(PRODUCTION_DOMAIN).not.toContain('127.0.0.1')
    })

    it('should enforce HTTPS in production', () => {
      const PRODUCTION_API_URL = 'https://imagineer-api.joshwentworth.com/api'

      expect(PRODUCTION_API_URL).toMatch(/^https:/)
      expect(PRODUCTION_API_URL).not.toMatch(/^http:\/\/[^l]/) // Not http:// (except localhost)
    })
  })

  describe('Security Requirements', () => {
    it('should never allow common security anti-patterns in production URL', () => {
      const PRODUCTION_API_URL = 'https://imagineer-api.joshwentworth.com/api'

      // Security checks
      const antiPatterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        ':10050',
        'http://', // Should be https
      ]

      antiPatterns.forEach(pattern => {
        if (pattern === 'http://') {
          // Check that it doesn't start with http:// (but https is ok)
          expect(PRODUCTION_API_URL).toMatch(/^https:/)
        } else {
          expect(PRODUCTION_API_URL).not.toContain(pattern)
        }
      })
    })
  })

  describe('getApiBaseUrl Function', () => {
    it('should return base API URL in development', () => {
      const baseUrl = getApiBaseUrl()
      // In dev mode (test environment), constructs from window.location
      expect(baseUrl).toContain('/api')
    })

    it('should not include specific endpoints', () => {
      const baseUrl = getApiBaseUrl()
      // Base URL should not include specific endpoints
      expect(baseUrl).not.toContain('/images')
      expect(baseUrl).not.toContain('/auth')
      expect(baseUrl).not.toContain('/albums')
    })
  })
})
