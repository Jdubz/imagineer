import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

const originalFetch = globalThis.fetch

vi.stubGlobal('fetch', fetchMock)

const getApiUrlMock = vi.fn((endpoint: string) => {
  const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `https://api.example.com${normalized}`
})

vi.mock('./apiConfig', () => ({
  getApiUrl: getApiUrlMock,
  getApiBaseUrl: vi.fn(() => 'https://api.example.com'),
}))

const { api } = await import('./api')

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client uses getApiUrl for absolute requests', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    getApiUrlMock.mockClear()
  })

  it('jobs.getAll requests the configured API origin', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ current: null, queue: [], history: [] }))

    await api.jobs.getAll()

    expect(getApiUrlMock).toHaveBeenCalledWith('/jobs')
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/jobs',
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('jobs.getById requests the configured API origin', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: 42,
        status: 'queued',
        prompt: 'test prompt',
        queue_position: 1,
        submitted_at: '2025-11-03T00:00:00.000Z',
      })
    )

    await api.jobs.getById(42)

    expect(getApiUrlMock).toHaveBeenCalledWith('/jobs/42')
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/jobs/42',
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('batches.getById requests the configured API origin', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        batch_id: 'demo-batch',
        album_id: 1,
        name: 'Demo Batch',
        image_count: 0,
        images: [],
      })
    )

    await api.batches.getById('demo-batch')

    expect(getApiUrlMock).toHaveBeenCalledWith('/batches/demo-batch')
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/batches/demo-batch',
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('images.getAll requests the configured API origin with query params', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        images: [],
        total: 0,
        page: 1,
        per_page: 60,
        pages: 1,
      })
    )

    await api.images.getAll()

    expect(getApiUrlMock).toHaveBeenCalledWith('/images?visibility=public&page=1&per_page=60')
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/images?visibility=public&page=1&per_page=60',
      expect.objectContaining({ credentials: 'include' })
    )
  })
})

afterAll(() => {
  vi.unstubAllGlobals()
  if (originalFetch) {
    globalThis.fetch = originalFetch
  }
})
