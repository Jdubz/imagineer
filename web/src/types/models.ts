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

export interface ImageMetadata {
  prompt?: string
  negative_prompt?: string
  seed?: number
  steps?: number
  guidance_scale?: number
  width?: number
  height?: number
  model?: string
  lora_path?: string
  lora_weight?: number
  loras?: {
    path: string
    weight: number
  }[]
  set_name?: string
  card_data?: Record<string, unknown>
}

export interface GeneratedImage {
  filename: string
  path: string
  size: number
  created: string
  metadata?: ImageMetadata
}

export interface BatchSummary {
  batch_id: string
  path: string
  image_count: number
  created: string
}

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface Job {
  id: string
  status: JobStatus
  prompt: string
  params?: GenerateParams
  queue_position?: number | null
  created?: string
  created_at?: string
  started_at?: string | null
  completed_at?: string | null
  output_path?: string | null
  error?: string | null
}

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

export interface BatchGenerateParams {
  set_name: string
  user_theme?: string
  steps?: number
  guidance_scale?: number
  width?: number
  height?: number
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

export interface SetConfig {
  name: string
  prompt_template: string
  negative_prompt?: string
  width: number
  height: number
  loras?: LoRAConfig[]
  style_suffix?: string
}

export interface SetInfo extends SetConfig {
  item_count: number
}

export interface Tab {
  id: string
  label: string
  icon: string
}

export interface Album {
  id: string
  name: string
  description?: string
  image_count: number
  cover_image?: string
  created_at: string
  updated_at: string
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

export interface ScrapingJobRuntime {
  stage?: string
  discovered?: number
  downloaded?: number
  progress?: number
  last_message?: string
  updated_at?: string
}

export interface ScrapingJob {
  id: string
  status: JobStatus
  url?: string
  name?: string
  source_url?: string
  output_dir?: string
  output_directory?: string
  progress?: number
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
