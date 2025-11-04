import { z, type ZodType } from 'zod'
import type { Job as JobContract, JobsResponse } from '../types/shared'

/**
 * Zod schemas for runtime validation of API responses
 *
 * These schemas validate the shape of data coming from the API,
 * providing type safety at runtime and catching API contract violations early.
 *
 * NOTE: This is a frontend-only validation layer. For better type coordination
 * between frontend and backend, these schemas should eventually be moved to the
 * shared schema system (shared/schema/*.json) which uses scripts/generate_shared_types.py
 * to generate both TypeScript and Python types from JSON Schema definitions.
 *
 * TODO: Consider generating Zod schemas from JSON Schemas in the generation script
 * to maintain a single source of truth for API contracts.
 */

// ============================================
// Job Status
// ============================================

export const JobStatusSchema = z.enum(['queued', 'running', 'completed', 'failed', 'cancelled'])

// ============================================
// Job
// ============================================

export const GenerateParamsSchema = z.object({
  prompt: z.string(),
  negative_prompt: z.string().optional(),
  steps: z.number().optional(),
  guidance_scale: z.number().optional(),
  seed: z.number().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  lora_path: z.string().optional(),
  lora_weight: z.number().optional(),
})

export const JobSchema: ZodType<JobContract> = z.object({
  id: z.number(),
  status: JobStatusSchema,
  prompt: z.string(),
  queue_position: z.number().nullable().optional(),
  submitted_at: z.string(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  cancelled_at: z.string().nullable().optional(),
  created_at: z.string().optional(),
  created: z.string().optional(),
  output_path: z.string().nullable().optional(),
  output_filename: z.string().optional(),
  output_directory: z.string().optional(),
  output_dir: z.string().optional(),
  output: z.string().optional(),
  lora_paths: z.array(z.string()).optional(),
  lora_weights: z.array(z.number()).optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  steps: z.number().optional(),
  seed: z.number().optional(),
  guidance_scale: z.number().optional(),
  negative_prompt: z.string().optional(),
  error: z.string().nullable().optional(),
  duration_seconds: z.number().optional(),
  estimated_time_remaining: z.number().nullable().optional(),
  album_id: z.number().optional(),
  batch_id: z.string().optional(),
  batch_item_name: z.string().optional(),
  batch_item_data: z.record(z.string(), z.unknown()).optional(),
})

// ============================================
// Images
// ============================================

/**
 * ImageMetadataSchema - Runtime validation for image metadata
 *
 * TODO: This schema duplicates the shared/schema/image_metadata.json schema.
 * Ideally, we should auto-generate this Zod schema from the JSON Schema
 * definition to maintain a single source of truth. The challenge is that
 * JSON Schema doesn't have a 1:1 mapping to Zod (e.g., Zod's .optional() vs
 * JSON Schema's required array). For now, we maintain both manually and
 * rely on contract tests to catch drift.
 *
 * @see shared/schema/image_metadata.json - Source of truth for this schema
 * @see web/src/__tests__/sharedContract.test.ts - Tests that validate consistency
 */
export const ImageMetadataSchema = z.object({
  prompt: z.string().optional(),
  negative_prompt: z.string().optional(),
  seed: z.number().optional(),
  steps: z.number().optional(),
  guidance_scale: z.number().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  model: z.string().optional(),
  lora_path: z.string().optional(),
  lora_weight: z.number().optional(),
  loras: z.array(z.object({
    path: z.string(),
    weight: z.number(),
  })).optional(),
})

export const GeneratedImageSchema = z.object({
  id: z.number().optional(),
  filename: z.string(),
  path: z.string().optional(),
  relative_path: z.string().optional(),
  storage_name: z.string().nullish(),
  download_url: z.string().optional(),
  thumbnail_url: z.string().optional(),
  size: z.number().optional(),
  created: z.string().optional(),
  created_at: z.string().optional(),
  prompt: z.string().nullish(),
  negative_prompt: z.string().nullish(),
  seed: z.number().nullish(),
  steps: z.number().nullish(),
  guidance_scale: z.number().nullish(),
  width: z.number().nullish(),
  height: z.number().nullish(),
  lora_config: z.string().nullish(),
  is_nsfw: z.boolean().optional(),
  is_public: z.boolean().optional(),
  metadata: ImageMetadataSchema.optional(),
}).catchall(z.unknown())

// ============================================
// Batches
// ============================================


export const BatchSummarySchema = z.object({
  batch_id: z.string(),
  album_id: z.number(),
  name: z.string(),
  album_type: z.string().optional(),
  image_count: z.number(),
  created: z.string().optional().nullable(),
  updated: z.string().optional().nullable(),
  preview_url: z.string().optional().nullable(),
})


export const BatchDetailSchema = z.object({
  batch_id: z.string(),
  album_id: z.number(),
  name: z.string(),
  album_type: z.string().optional(),
  image_count: z.number(),
  created: z.string().optional().nullable(),
  updated: z.string().optional().nullable(),
  images: z.array(GeneratedImageSchema).optional(),
})

// ============================================
// Scraping
// ============================================

export const ScrapingJobRuntimeSchema = z.object({
  stage: z.string().optional(),
  discovered: z.number().optional(),
  downloaded: z.number().optional(),
  progress: z.number().optional(),
  last_message: z.string().optional(),
  updated_at: z.string().optional(),
})

export const ScrapingJobStatusSchema = z.enum([
  'pending',
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled',
  'cleaned_up',
])

export const ScrapingJobSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(value => value.toString()),
  status: ScrapingJobStatusSchema,
  url: z.string().optional(),
  name: z.string().optional(),
  source_url: z.string().optional(),
  output_dir: z.string().optional(),
  output_directory: z.string().optional(),
  progress: z.number().optional().nullable(),
  progress_message: z.string().optional(),
  description: z.string().optional(),
  runtime: ScrapingJobRuntimeSchema.optional(),
  created_at: z.string(),
  completed_at: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  images_scraped: z.number().optional().nullable(),
  config: z.record(z.string(), z.unknown()).optional(),
})

export const ScrapingJobsResponseSchema = z
  .object({
    jobs: z.array(ScrapingJobSchema),
    total: z.number().optional(),
    page: z.number().optional(),
    per_page: z.number().optional(),
    pages: z.number().optional(),
  })
  .passthrough()

export const ScrapingStorageStatsSchema = z.object({
  path: z.string(),
  total_gb: z.number().optional(),
  used_gb: z.number().optional(),
  free_gb: z.number().optional(),
  free_percent: z.number().optional().nullable(),
  error: z.string().optional(),
})

export const ScrapingStatsSchema = z.object({
  total_jobs: z.number(),
  total_images_scraped: z.number(),
  recent_jobs: z.number(),
  storage: ScrapingStorageStatsSchema.optional(),
})

export const ScrapingActionResponseSchema = z.object({
  success: z.boolean().optional(),
  message: z.string().optional(),
}).passthrough()

// ============================================
// Training
// ============================================

export const TrainingJobSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().optional().nullable(),
  status: JobStatusSchema,
  dataset_path: z.string().optional().nullable(),
  output_path: z.string().optional().nullable(),
  training_config: z.union([z.string(), z.record(z.string(), z.unknown())]).optional().nullable(),
  created_at: z.string(),
  started_at: z.string().optional().nullable(),
  completed_at: z.string().optional().nullable(),
  error_message: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  progress: z.number().optional().nullable(),
  final_checkpoint: z.string().optional().nullable(),
  training_loss: z.number().optional().nullable(),
  validation_loss: z.number().optional().nullable(),
  last_error_at: z.string().optional().nullable(),
})

export const TrainingRunsResponseSchema = z.object({
  training_runs: z.array(TrainingJobSchema),
})

export const TrainingAlbumSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(value => value.toString()),
  name: z.string(),
  image_count: z.number(),
})

export const TrainingAlbumsResponseSchema = z.object({
  albums: z.array(TrainingAlbumSchema),
})

export const TrainingLogResponseSchema = z.object({
  training_run_id: z.number(),
  status: JobStatusSchema,
  progress: z.number(),
  error_message: z.string().optional().nullable(),
  log_path: z.string(),
  log_available: z.boolean(),
  logs: z.string(),
})

export const TrainingActionResponseSchema = z.object({
  success: z.boolean().optional(),
  message: z.string().optional(),
}).passthrough()

// ============================================
// Configuration
// ============================================

export const ConfigSchema = z.object({
  model: z.object({
    name: z.string().optional(),
    device: z.string().optional(),
    default: z.string().optional(),
    cache_dir: z.string().optional(),
  }).optional(),
  generation: z.object({
    steps: z.number().optional(),
    guidance_scale: z.number().optional(),
    width: z.number().optional(),
    height: z.number().optional(),
    negative_prompt: z.string().optional(),
  }).optional(),
  output: z.object({
    directory: z.string().optional(),
    format: z.string().optional(),
  }).optional(),
  outputs: z.object({
    base_dir: z.string().optional(),
  }).optional(),
}).catchall(z.unknown()) // Allow additional properties

// ============================================
// Authentication
// ============================================

export const AuthStatusSchema = z.object({
  authenticated: z.boolean(),
  email: z.string().nullish(),
  name: z.string().nullish(),
  picture: z.string().nullish(),
  role: z.string().nullish(),
  is_admin: z.boolean().nullish(),
  error: z.string().nullish(),
  message: z.string().nullish(),
})

// ============================================
// LoRAs and Albums
// ============================================

export const LoRAConfigSchema = z.object({
  path: z.string(),
  weight: z.number(),
  name: z.string().optional(),
})

export const AlbumSchema = z.object({
  id: z
    .union([z.string(), z.number()])
    .transform((value) => value.toString()),
  name: z.string(),
  description: z.string().optional(),
  image_count: z.number(),
  cover_image: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  images: z.array(z.lazy(() => GeneratedImageSchema)).optional(),
  album_type: z.string().optional(),
  is_set_template: z.boolean().optional(),
  template_item_count: z.number().optional(),
  example_theme: z.string().optional(),
  base_prompt: z.string().optional(),
  // Additional fields from backend Album.to_dict()
  generation_prompt: z.string().optional().nullable(),
  generation_config: z.string().nullish(),
  is_public: z.boolean().optional(),
  is_training_source: z.boolean().optional(),
  created_by: z.string().optional().nullable(),
  csv_data: z.string().optional().nullable(),
  prompt_template: z.string().optional().nullable(),
  style_suffix: z.string().optional().nullable(),
  lora_config: z.string().optional().nullable(),
  lora_count: z.number().optional(),
  template_items_preview: z.array(z.unknown()).optional(),
  slug: z.string().optional(),
})

export const LabelAnalyticsSchema = z.object({
  album_id: z.number(),
  image_count: z.number(),
  labels_total: z.number(),
  labels_by_type: z.record(z.string(), z.number()),
  images_with_labels: z.number(),
  images_with_manual_labels: z.number(),
  images_with_captions: z.number(),
  unlabeled_images: z.number(),
  average_labels_per_image: z.number(),
  coverage: z.object({
    labels_percent: z.number(),
    manual_percent: z.number(),
    caption_percent: z.number(),
  }),
  top_tags: z.array(z.object({
    label_text: z.string(),
    count: z.number(),
  })),
  last_labeled_at: z.string().nullable().optional(),
})

// ============================================
// API Response Wrappers
// ============================================

export const ImagesResponseSchema = z.object({
  images: z.array(GeneratedImageSchema),
})

export const PaginatedImagesResponseSchema = z.object({
  images: z.array(GeneratedImageSchema),
  total: z.number(),
  page: z.number(),
  per_page: z.number(),
  pages: z.number(),
})

export const BatchesResponseSchema = z.object({
  batches: z.array(BatchSummarySchema),
})

export const LorasResponseSchema = z.object({
  loras: z.array(z.object({
    folder: z.string(),
    filename: z.string(),
  })),
})

export const ThemeResponseSchema = z.object({
  theme: z.string(),
})

export const AlbumsResponseSchema = z.union([
  z.array(AlbumSchema),
  z.object({
    albums: z.array(AlbumSchema),
  }),
])

export const JobsResponseSchema: ZodType<JobsResponse> = z.object({
  current: JobSchema.nullable(),
  queue: z.array(JobSchema),
  history: z.array(JobSchema),
})

// ============================================
// Bug Reports
// ============================================

export const BugReportResponseSchema = z.object({
  success: z.boolean(),
  report_id: z.string(),
  trace_id: z.string(),
  stored_at: z.string().nullable().optional(),
})

// ============================================
// Type exports (inferred from schemas)
// ============================================

export type JobStatus = z.infer<typeof JobStatusSchema>
export type Job = z.infer<typeof JobSchema>
export type GenerateParams = z.infer<typeof GenerateParamsSchema>
export type ImageMetadata = z.infer<typeof ImageMetadataSchema>
export type GeneratedImage = z.infer<typeof GeneratedImageSchema>
export type BatchSummary = z.infer<typeof BatchSummarySchema>
export type BatchDetail = z.infer<typeof BatchDetailSchema>
export type Config = z.infer<typeof ConfigSchema>
export type AuthStatus = z.infer<typeof AuthStatusSchema>
export type LoRAConfig = z.infer<typeof LoRAConfigSchema>
export type Album = z.infer<typeof AlbumSchema>
export type LabelAnalytics = z.infer<typeof LabelAnalyticsSchema>
