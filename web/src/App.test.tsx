import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

interface ResponseInit {
  ok?: boolean
  status?: number
  headers?: Record<string, string>
}

interface MockHeaders {
  get: (name: string) => string | null
}

interface MockResponse {
  ok: boolean
  status: number
  json: () => Promise<unknown>
  headers: MockHeaders
}

const createResponse = (data: unknown, init: ResponseInit = {}): MockResponse => {
  const headerLookup = init.headers
    ? Object.fromEntries(Object.entries(init.headers).map(([key, value]) => [key.toLowerCase(), value]))
    : {}

  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: () => Promise.resolve(data),
    headers: {
      get: (name: string) => {
        const normalized = name.toLowerCase()
        if (normalized === 'content-type') {
          return headerLookup[normalized] ?? 'application/json'
        }
        return headerLookup[normalized] ?? null
      },
    },
  }
}

const createImagesResponse = (images: unknown[] = []): MockResponse =>
  createResponse({
    images,
    total: images.length,
    page: 1,
    per_page: 60,
    pages: images.length > 0 ? 1 : 0,
  })

type Handler = (options?: RequestInit) => Promise<MockResponse>
type Handlers = Record<string, Handler>

let handlers: Handlers
let fetchMock: Mock

const defaultHandlers = (): Handlers => ({
  '/api/config': () => Promise.resolve(createResponse({
    generation: {
      steps: 30,
      guidance_scale: 7.5
    }
  })),
  '/api/images': () => Promise.resolve(createImagesResponse()),
  '/api/batches': () => Promise.resolve(createResponse({ batches: [] })),
  '/api/loras': () => Promise.resolve(createResponse({ loras: [] })),
  '/api/sets': () => Promise.resolve(createResponse({ sets: [] })),
  '/api/themes/random': () => Promise.resolve(createResponse({ theme: '' })),
  '/api/auth/me': () => Promise.resolve(createResponse({ authenticated: false }))
})

const setupFetchMock = (overrides: Partial<Handlers> = {}): void => {
  handlers = defaultHandlers()
  Object.assign(handlers, overrides)

  fetchMock = vi.fn(async (url: RequestInfo | URL, options?: RequestInit): Promise<MockResponse> => {
    let requestUrl = ''
    if (typeof url === 'string') {
      requestUrl = url
    } else if (url instanceof URL) {
      requestUrl = url.toString()
    } else if (isRecord(url) && typeof (url as { url?: unknown }).url === 'string') {
      requestUrl = (url as { url: string }).url
    }

    if (requestUrl.startsWith('http://') || requestUrl.startsWith('https://')) {
      const parsed = new URL(requestUrl)
      requestUrl = `${parsed.pathname}${parsed.search}`
    }

    const lookupKey = requestUrl
    const handler =
      handlers[lookupKey] ??
      handlers[lookupKey.split('?')[0] ?? lookupKey]
    if (handler) {
      return handler(options)
    }

    if (requestUrl.startsWith('/api/sets/') && requestUrl.endsWith('/loras')) {
      return Promise.resolve(createResponse({ loras: [] }))
    }

    if (requestUrl.startsWith('/api/sets/') && requestUrl.endsWith('/info')) {
      return Promise.resolve(createResponse({}))
    }

    console.warn('Unhandled API request in App.test mock:', requestUrl)
    return Promise.resolve(createResponse({}))
  })

  globalThis.fetch = fetchMock as unknown as typeof fetch
}

describe('App', () => {
  const renderApp = (): ReturnType<typeof render> => {
    let utils: ReturnType<typeof render>
    act(() => {
      utils = render(<App />)
    })
    return utils!
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setupFetchMock()
  })

  it('renders the app title', () => {
    renderApp()
    expect(screen.getByRole('heading', { name: /imagineer/i })).toBeInTheDocument()
  })

  it('shows the viewer auth button when signed out', async () => {
    renderApp()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /viewer/i })).toBeInTheDocument()
    })
  })

  it('renders settings actions when the user is authenticated', async () => {
    handlers['/api/auth/me'] = () =>
      Promise.resolve(
        createResponse({
          authenticated: true,
          email: 'admin@example.com',
          role: 'admin',
        }),
      )

    renderApp()

    await waitFor(() => {
      expect(screen.getByLabelText(/open settings menu/i)).toBeInTheDocument()
    })
  })

  it('submits generation request', async () => {
    const user = userEvent.setup()
    const mockJobResponse = {
      id: 1,
      status: 'queued' as const,
      queue_position: 1,
      prompt: 'test prompt',
      submitted_at: new Date().toISOString(),
      created_at: new Date().toISOString()
    }

    handlers['/api/images'] = () => Promise.resolve(createImagesResponse())
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

    renderApp()

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/generate$/),
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

    handlers['/api/images'] = () => Promise.resolve(createImagesResponse())
    handlers['/api/generate'] = () => Promise.reject(new Error('Generation failed'))

    renderApp()

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

    handlers['/api/images'] = () => Promise.reject(new Error('Images failed'))

    renderApp()

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  it('handles 401 unauthorized response for config endpoint', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined)

    // Mock config endpoint to return 401 (requires admin auth)
    handlers['/api/config'] = () =>
      Promise.resolve(createResponse({ error: 'Unauthorized' }, { ok: false, status: 401 }))

    renderApp()

    // App should render without crashing
    expect(screen.getByRole('heading', { name: /imagineer/i })).toBeInTheDocument()

    // Verify warning was logged about auth requirement
    await waitFor(() => {
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Config endpoint requires admin authentication')
      )
    })

    consoleWarnSpy.mockRestore()
  })

  it('handles 403 forbidden response for config endpoint', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined)

    // Mock config endpoint to return 403 (forbidden)
    handlers['/api/config'] = () =>
      Promise.resolve(createResponse({ error: 'Forbidden' }, { ok: false, status: 403 }))

    renderApp()

    // App should render without crashing
    expect(screen.getByRole('heading', { name: /imagineer/i })).toBeInTheDocument()

    // Verify warning was logged about auth requirement
    await waitFor(() => {
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Config endpoint requires admin authentication')
      )
    })

    consoleWarnSpy.mockRestore()
  })

  it('allows admin users to open the bug report modal via the settings menu', async () => {
    const user = userEvent.setup()
    const bugReportHandler = vi.fn(() =>
      Promise.resolve(
        createResponse({
          success: true,
          report_id: 'bug_20251030_abcdef01',
          trace_id: 'abcdef01-2345-6789-abcd-ef0123456789',
          stored_at: '/tmp/bug.json'
        })
      )
    )

    handlers['/api/auth/me'] = () =>
      Promise.resolve(
        createResponse({
          authenticated: true,
          email: 'admin@example.com',
          role: 'admin',
          is_admin: true
        })
      )
    handlers['/api/bug-reports'] = bugReportHandler

    renderApp()

    await waitFor(() => expect(screen.queryByRole('button', { name: /login/i })).not.toBeInTheDocument())

    const settingsTrigger = screen.getByRole('button', { name: /open settings menu/i })
    await user.click(settingsTrigger)

    const menuBugButton = await screen.findByRole('menuitem', { name: /report bug/i })
    await user.click(menuBugButton)

    const modal = await screen.findByRole('dialog', { name: /report a bug/i })
    expect(modal).toBeInTheDocument()
    expect(bugReportHandler).not.toHaveBeenCalled()
  })
})
