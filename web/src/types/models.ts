import type {
  ImageMetadata as SharedImageMetadata,
  Job as JobContract,
  JobsResponse as JobsResponseContract,
} from './shared'

export type NsfwPreference = 'show' | 'blur' | 'hide'

export interface Config {
  model?: {
    name?: string
    device?: string
    default?: string
    cache_dir?: string
  }
  generation?: {
    steps?: number
    guidance_scale?: number
    width?: number
    height?: number
    negative_prompt?: string
  }
  output?: {
    directory?: string
    format?: string
  }
  outputs?: {
    base_dir?: string
  }
  [key: string]: unknown
}

export type ImageMetadata = SharedImageMetadata

export interface GeneratedImage {
  id?: number
  filename: string
  path?: string
  relative_path?: string
  storage_name?: string | null
  download_url?: string
  thumbnail_url?: string
  size?: number
  created?: string
  created_at?: string | null
  prompt?: string | null
  negative_prompt?: string | null
  seed?: number | null
  steps?: number | null
  guidance_scale?: number | null
  width?: number | null
  height?: number | null
  lora_config?: string | null
  is_nsfw?: boolean
  is_public?: boolean
  metadata?: ImageMetadata
  labels?: Label[]
  album_id?: number | null
}

export interface BatchSummary {
  batch_id: string
  album_id: number
  name: string
  album_type?: string
  image_count: number
  created?: string | null
  updated?: string | null
  preview_url?: string | null
  path?: string | null
}

export type JobStatus = JobContract['status']

export type Job = JobContract

export type JobsResponse = JobsResponseContract

export interface GenerateParams {
  prompt: string
  negative_prompt?: string
  steps?: number
  guidance_scale?: number
  seed?: number
  width?: number
  height?: number
  lora_path?: string
  lora_weight?: number
}

export interface AlbumBatchGenerateParams {
  user_theme: string
  seed?: number
  steps?: number
  width?: number
  height?: number
  guidance_scale?: number
  negative_prompt?: string
}

export interface AlbumBatchGenerateResponse {
  message: string
  album_id: number
  album_name: string
  batch_id: string
  job_ids: number[]
  output_dir: string
}

export interface LoRAConfig {
  path: string
  weight: number
  name?: string
}

export interface LoRA {
  name: string
  path: string
  size?: number
}

export interface Tab {
  id: string
  label: string
  icon: string
}

export interface Album {
  id: string
  name: string
  description?: string | null
  image_count: number
  cover_image?: string | null
  created_at?: string | null
  updated_at?: string | null
  album_type?: string | null
  is_public?: boolean
  is_training_source?: boolean
  created_by?: string | null
  // Set template fields
  is_set_template?: boolean
  csv_data?: string | null
  base_prompt?: string | null
  prompt_template?: string | null
  style_suffix?: string | null
  example_theme?: string | null
  lora_config?: string | null
  template_item_count?: number
  template_items_preview?: unknown[]
  lora_count?: number
  slug?: string
  generation_prompt?: string | null
  generation_config?: string | null
}

export interface Label {
  id: number
  image_id: number
  label_text: string
  confidence?: number | null
  label_type?: string | null
  source_model?: string | null
  source_prompt?: string | null
  created_by?: string | null
  created_at?: string | null
}

export interface LabelAnalytics {
  album_id: number
  image_count: number
  labels_total: number
  labels_by_type: Record<string, number>
  images_with_labels: number
  images_with_manual_labels: number
  images_with_captions: number
  unlabeled_images: number
  average_labels_per_image: number
  coverage: {
    labels_percent: number
    manual_percent: number
    caption_percent: number
  }
  top_tags: Array<{ label_text: string; count: number }>
  last_labeled_at?: string | null
}

export interface TrainingDataset {
  name: string
  path: string
  image_count: number
}

export interface TrainingJob {
  id: number
  name: string
  description?: string | null
  status: JobStatus
  dataset_path?: string | null
  output_path?: string | null
  training_config?: string | Record<string, unknown> | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  error_message?: string | null
  error?: string | null
  progress?: number | null
  final_checkpoint?: string | null
  training_loss?: number | null
  validation_loss?: number | null
  last_error_at?: string | null
}

export interface TrainingAlbum {
  id: string
  name: string
  image_count: number
}

export interface TrainingLogResponse {
  training_run_id: number
  status: JobStatus
  progress: number
  error_message?: string | null
  log_path: string
  log_available: boolean
  logs: string
}

export interface ScrapingJobRuntime {
  stage?: string
  discovered?: number
  downloaded?: number
  progress?: number
  last_message?: string
  updated_at?: string
}

export interface ScrapingStorageStats {
  path: string
  total_gb?: number
  used_gb?: number
  free_gb?: number
  free_percent?: number | null
  error?: string
}

export interface ScrapingStats {
  total_jobs: number
  total_images_scraped: number
  recent_jobs: number
  storage?: ScrapingStorageStats
}

export interface ScrapingJob {
  id: string
  status: JobStatus | 'pending' | 'cleaned_up'
  url?: string
  name?: string
  source_url?: string
  output_dir?: string
  output_directory?: string
  progress?: number | null
  progress_message?: string
  description?: string
  runtime?: ScrapingJobRuntime
  created_at: string
  completed_at?: string
  error?: string
  images_scraped?: number
  config?: Record<string, unknown>
}

export type { AuthStatus } from './shared'
