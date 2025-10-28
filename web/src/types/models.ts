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

export interface TrainingDataset {
  name: string
  path: string
  image_count: number
}

export interface TrainingJob {
  id: string
  status: JobStatus
  dataset: string
  output_name: string
  steps: number
  rank: number
  learning_rate: number
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
  progress?: number
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
