/* API Response Types */
// Type definitions for all API endpoint responses

import type { GeneratedImage, Job, Album } from './models'
import type { BatchSummary } from './models'

export interface ConfigResponse {
  generation: {
    steps: number
    guidance_scale: number
    width: number
    height: number
    negative_prompt?: string
  }
  model?: {
    default: string
    cache_dir: string
  }
  output?: {
    directory: string
    format: string
  }
}

export interface OutputsResponse {
  images: GeneratedImage[]
}

export interface BatchesResponse {
  batches: BatchSummary[]
}

export type JobResponse = Job

export interface AlbumsResponse {
  albums: Album[]
}

export type AlbumResponse = Album

export interface LorasResponse {
  loras: {
    name: string
    path: string
    size?: number
  }[]
}

export interface SetsResponse {
  sets: {
    name: string
    item_count: number
  }[]
}

export interface SetInfoResponse {
  name: string
  prompt_template: string
  negative_prompt?: string
  width: number
  height: number
  loras?: {
    path: string
    weight: number
  }[]
  style_suffix?: string
  item_count: number
}

export interface SetLorasResponse {
  loras: {
    folder: string
    weight: number
  }[]
}

export interface ThemeResponse {
  theme: string
}

export interface BatchGenerateResponse {
  total_jobs: number
  set_name: string
  batch_id: string
}

export interface ErrorResponse {
  error: string
  message?: string
}
