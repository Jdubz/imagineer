import type { GeneratedImage } from '../types/models'
import { getApiUrl } from './apiConfig'

export interface ImageSourceSet {
  thumbnail: string
  full: string
  alt: string
  srcSet: string
}

const preloadCache = new Set<string>()

function toAbsolute(path?: string | null): string | undefined {
  if (!path) {
    return undefined
  }

  if (/^https?:\/\//i.test(path)) {
    return path
  }

  // Use getApiUrl to handle production vs development URLs
  if (path.startsWith('/api/')) {
    return getApiUrl(path)
  }

  if (path.startsWith('/')) {
    return getApiUrl(path)
  }

  return getApiUrl(`/${path.replace(/^\/+/, '')}`)
}

function resolveFallbackFull(image: GeneratedImage): string {
  const downloadUrl = toAbsolute(image.download_url)
  if (downloadUrl) {
    return downloadUrl
  }

  if (image.id) {
    return getApiUrl(`/images/${image.id}/file`)
  }

  const pathUrl = toAbsolute(image.path)
  if (pathUrl) {
    return pathUrl
  }

  if (image.filename) {
    const filenameUrl = toAbsolute(image.filename)
    if (filenameUrl) {
      return filenameUrl
    }
  }

  return getApiUrl('/images')
}

function resolveThumbnail(image: GeneratedImage, full: string): string {
  if (image.thumbnail_url) {
    const thumbnail = toAbsolute(image.thumbnail_url)
    if (thumbnail) {
      return thumbnail
    }
  }

  if (image.id) {
    return getApiUrl(`/images/${image.id}/thumbnail`)
  }

  return full
}

export function resolveImageSources(
  image: GeneratedImage,
  { fallbackAlt }: { fallbackAlt?: string } = {}
): ImageSourceSet {
  const full = resolveFallbackFull(image)
  const thumbnail = resolveThumbnail(image, full)

  const altCandidate =
    image.metadata?.prompt ??
    (typeof image.prompt === 'string' ? image.prompt : undefined) ??
    fallbackAlt ??
    image.filename

  const srcSet = thumbnail !== full ? `${thumbnail} 1x, ${full} 2x` : `${full} 1x`

  return {
    thumbnail,
    full,
    alt: altCandidate,
    srcSet,
  }
}

export function preloadImage(url: string | undefined): void {
  if (!url || preloadCache.has(url) || typeof window === 'undefined') {
    return
  }

  const img = new Image()
  img.src = url
  preloadCache.add(url)
}
