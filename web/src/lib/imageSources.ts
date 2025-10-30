import type { GeneratedImage } from '../types/models'

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

  if (path.startsWith('/')) {
    return path
  }

  return `/api/${path.replace(/^\/+/, '')}`
}

function resolveFallbackFull(image: GeneratedImage): string {
  const legacyOutput =
    image.relative_path && image.relative_path.length > 0
      ? `/api/outputs/${image.relative_path}`
      : undefined

  const filenameFallback =
    image.filename && !/^https?:\/\//i.test(image.filename)
      ? `/api/outputs/${image.filename}`
      : image.filename

  return (
    toAbsolute(image.download_url) ??
    toAbsolute(image.path) ??
    legacyOutput ??
    filenameFallback ??
    '/api/outputs'
  )
}

function resolveThumbnail(image: GeneratedImage, full: string): string {
  if (image.thumbnail_url) {
    const thumbnail = toAbsolute(image.thumbnail_url)
    if (thumbnail) {
      return thumbnail
    }
  }

  if (image.id) {
    return `/api/images/${image.id}/thumbnail`
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
