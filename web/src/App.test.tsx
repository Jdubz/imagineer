import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

interface ResponseInit {
  ok?: boolean
  status?: number
}

interface MockResponse {
  ok: boolean
  status: number
  json: () => Promise<unknown>
}

const createResponse = (data: unknown, init: ResponseInit = {}): MockResponse => ({
  ok: init.ok ?? true,
  status: init.status ?? 200,
  json: () => Promise.resolve(data)
})

type Handler = (options?: RequestInit) => Promise<MockResponse>
type Handlers = Record<string, Handler>

let handlers: Handlers

const defaultHandlers = (): Handlers => ({
  '/api/config': () => Promise.resolve(createResponse({
    generation: {
      steps: 30,
      guidance_scale: 7.5
    }
  })),
  '/api/outputs': () => Promise.resolve(createResponse({ images: [] })),
  '/api/batches': () => Promise.resolve(createResponse({ batches: [] })),
  '/api/loras': () => Promise.resolve(createResponse({ loras: [] })),
  '/api/sets': () => Promise.resolve(createResponse({ sets: [] })),
  '/api/themes/random': () => Promise.resolve(createResponse({ theme: '' })),
  '/api/auth/me': () => Promise.resolve(createResponse({ authenticated: false }))
})

const setupFetchMock = (overrides: Partial<Handlers> = {}): void => {
  handlers = defaultHandlers()
  Object.assign(handlers, overrides)

  globalThis.fetch = vi.fn(async (url: RequestInfo | URL, options?: RequestInit): Promise<MockResponse> => {
    let requestUrl = ''
    if (typeof url === 'string') {
      requestUrl = url
    } else if (url instanceof URL) {
      requestUrl = url.toString()
    } else if (isRecord(url) && typeof (url as { url?: unknown }).url === 'string') {
      requestUrl = (url as { url: string }).url
    }

    const handler = handlers[requestUrl]
    if (handler) {
      return handler(options)
    }

    if (requestUrl.startsWith('/api/sets/') && requestUrl.endsWith('/loras')) {
      return Promise.resolve(createResponse({ loras: [] }))
    }

    if (requestUrl.startsWith('/api/sets/') && requestUrl.endsWith('/info')) {
      return Promise.resolve(createResponse({}))
    }

    return Promise.resolve(createResponse({}))
  }) as unknown as typeof fetch
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupFetchMock()
  })

  it('renders the app title', () => {
    render(<App />)
    expect(screen.getByText(/imagineer/i)).toBeInTheDocument()
  })

  it('submits generation request', async () => {
    const user = userEvent.setup()
    const mockJobResponse = {
      id: '1',
      status: 'queued' as const,
      queue_position: 1,
      prompt: 'test prompt',
      params: {},
      created_at: new Date().toISOString()
    }

    handlers['/api/outputs'] = () => Promise.resolve(createResponse({ images: [] }))
    handlers['/api/generate'] = () =>
      Promise.resolve(createResponse(mockJobResponse, { status: 201 }))
    handlers['/api/jobs/1'] = (() => {
      let completed = false
      return () => {
        const payload = completed
          ? { ...mockJobResponse, status: 'completed' as const, queue_position: 0 }
          : { ...mockJobResponse, status: 'queued' as const, queue_position: 1 }
        completed = true
        return Promise.resolve(createResponse(payload))
      }
    })()

    render(<App />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/generate',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
          body: expect.stringContaining('test prompt')
        })
      )
    })
  })

  it('handles generation error', async () => {
    const user = userEvent.setup()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    handlers['/api/outputs'] = () => Promise.resolve(createResponse({ images: [] }))
    handlers['/api/generate'] = () => Promise.reject(new Error('Generation failed'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  it('handles images loading error', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    handlers['/api/outputs'] = () => Promise.reject(new Error('Images failed'))

    render(<App />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })
})
