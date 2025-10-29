import { z } from 'zod'

/**
 * Validation schemas for form inputs using Zod
 *
 * These schemas provide:
 * - Type-safe validation
 * - Clear error messages
 * - Consistent validation logic
 * - Protection against invalid/malicious input
 */

// ============================================
// Image Generation Validation
// ============================================

/**
 * Prompt validation
 * - Max 2000 characters (prevents excessive API payload)
 * - Trimmed whitespace
 */
export const promptSchema = z
  .string()
  .trim()
  .min(1, 'Prompt is required')
  .max(2000, 'Prompt must be 2000 characters or less')

/**
 * Steps validation
 * - Min: 1 (at least one diffusion step)
 * - Max: 150 (prevents excessive generation time)
 * - Default: 30
 */
export const stepsSchema = z
  .number()
  .int('Steps must be a whole number')
  .min(1, 'Steps must be at least 1')
  .max(150, 'Steps must be 150 or less')

/**
 * Guidance scale validation
 * - Min: 1.0 (minimum useful guidance)
 * - Max: 30.0 (prevents numerical instability)
 * - Default: 7.5
 */
export const guidanceScaleSchema = z
  .number()
  .min(1.0, 'Guidance scale must be at least 1.0')
  .max(30.0, 'Guidance scale must be 30.0 or less')

/**
 * Seed validation
 * - Optional field
 * - Min: 0
 * - Max: 2^31 - 1 (32-bit signed integer max)
 */
export const seedSchema = z
  .number()
  .int('Seed must be a whole number')
  .min(0, 'Seed must be non-negative')
  .max(2147483647, 'Seed must be less than 2147483648')
  .optional()

/**
 * Theme validation for batch generation
 * - Max 500 characters
 * - Trimmed whitespace
 */
export const themeSchema = z
  .string()
  .trim()
  .min(1, 'Theme is required')
  .max(500, 'Theme must be 500 characters or less')

/**
 * Complete generation form validation schema
 */
export const generateFormSchema = z.object({
  prompt: promptSchema,
  steps: stepsSchema,
  guidance_scale: guidanceScaleSchema,
  seed: seedSchema,
})

/**
 * Complete batch generation form validation schema
 */
export const batchGenerateFormSchema = z.object({
  set_name: z.string().min(1, 'Set name is required'),
  user_theme: themeSchema,
  steps: stepsSchema,
  guidance_scale: guidanceScaleSchema,
})

export type GenerateFormData = z.infer<typeof generateFormSchema>
export type BatchGenerateFormData = z.infer<typeof batchGenerateFormSchema>

// ============================================
// Web Scraping Validation
// ============================================

/**
 * URL validation
 * - Must be valid URL format
 * - Must use http or https protocol
 * - No localhost URLs (security)
 */
export const urlSchema = z
  .string()
  .trim()
  .url('Please enter a valid URL')
  .refine(
    (url) => {
      try {
        const parsed = new URL(url)
        return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      } catch {
        return false
      }
    },
    { message: 'URL must use http or https protocol' }
  )
  .refine(
    (url) => {
      try {
        const parsed = new URL(url)
        const hostname = parsed.hostname.toLowerCase()
        return (
          hostname !== 'localhost' &&
          hostname !== '127.0.0.1' &&
          !hostname.startsWith('192.168.') &&
          !hostname.startsWith('10.') &&
          !hostname.startsWith('172.')
        )
      } catch {
        return false
      }
    },
    { message: 'Cannot scrape localhost or private network URLs' }
  )

/**
 * Scrape job name validation
 * - Max 200 characters
 * - Optional (defaults to generated name)
 */
export const scrapeNameSchema = z
  .string()
  .trim()
  .max(200, 'Name must be 200 characters or less')
  .optional()

/**
 * Scrape job description validation
 * - Max 1000 characters
 * - Optional
 */
export const scrapeDescriptionSchema = z
  .string()
  .trim()
  .max(1000, 'Description must be 1000 characters or less')
  .optional()

/**
 * Crawl depth validation
 * - Min: 1 (scrape at least the starting page)
 * - Max: 5 (prevents excessive crawling)
 * - Default: 3
 */
export const depthSchema = z
  .number()
  .int('Depth must be a whole number')
  .min(1, 'Depth must be at least 1')
  .max(5, 'Depth must be 5 or less to prevent excessive crawling')

/**
 * Max images validation
 * - Min: 1 (scrape at least one image)
 * - Max: 10000 (prevents storage issues)
 * - Default: 1000
 */
export const maxImagesSchema = z
  .number()
  .int('Max images must be a whole number')
  .min(1, 'Must scrape at least 1 image')
  .max(10000, 'Max images must be 10000 or less to prevent storage issues')

/**
 * Complete scrape form validation schema
 */
export const scrapeFormSchema = z.object({
  url: urlSchema,
  name: scrapeNameSchema,
  description: scrapeDescriptionSchema,
  depth: depthSchema,
  maxImages: maxImagesSchema,
})

export type ScrapeFormData = z.infer<typeof scrapeFormSchema>

// ============================================
// Label Validation (for Albums)
// ============================================

/**
 * Label text validation
 * - Max 100 characters
 * - Trimmed whitespace
 */
export const labelSchema = z
  .string()
  .trim()
  .min(1, 'Label cannot be empty')
  .max(100, 'Label must be 100 characters or less')

// ============================================
// Helper Functions
// ============================================

/**
 * Validates form data and returns typed result with errors
 *
 * @param schema - Zod schema to validate against
 * @param data - Data to validate
 * @returns Object with success boolean, data (if valid), and errors (if invalid)
 *
 * @example
 * const result = validateForm(generateFormSchema, formData)
 * if (result.success) {
 *   // formData is valid, use result.data
 * } else {
 *   // Show validation errors: result.errors
 * }
 */
export function validateForm<T extends z.ZodType>(
  schema: T,
  data: unknown
): { success: true; data: z.infer<T> } | { success: false; errors: Record<string, string> } {
  const result = schema.safeParse(data)

  if (result.success) {
    return { success: true, data: result.data }
  }

  // Convert Zod errors to field-level error messages
  const errors: Record<string, string> = {}
  for (const issue of result.error.issues) {
    const path = issue.path.join('.')
    errors[path] = issue.message
  }

  return { success: false, errors }
}

/**
 * Sanitizes user input by removing potentially dangerous characters
 * Note: This is defense-in-depth; Zod validation is the primary protection
 *
 * @param input - String to sanitize
 * @returns Sanitized string
 */
export function sanitizeInput(input: string): string {
  return input
    .trim()
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // Remove control characters
    .replace(/<script[^>]*>.*?<\/script>/gi, '') // Remove script tags
    .replace(/<[^>]+>/g, '') // Remove HTML tags
}
