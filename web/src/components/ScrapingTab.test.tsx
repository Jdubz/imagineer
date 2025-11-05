import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ScrapingTab from './ScrapingTab'
import { BugReportProvider } from '../contexts/BugReportContext'

vi.mock('../hooks/usePolling', () => ({
  usePolling: (
    callback: () => void | Promise<void>,
    options: { enabled?: boolean; runImmediately?: boolean } = {},
  ) => {
    if (options.enabled === false) {
      return
    }
    if (options.runImmediately) {
      void Promise.resolve(callback()).catch(() => {})
    }
  },
}))

vi.mock('@/components/ui/dialog', () => {
  const React = require('react') as typeof import('react')
  const Dialog = ({
    open = false,
    children,
  }: {
    open?: boolean
    children?: React.ReactNode
  }) => (open ? <div data-testid="dialog-root">{children}</div> : null)

  const passthrough =
    (role?: string) =>
    ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) =>
      React.createElement(
        'div',
        { ...(role ? { role } : {}), ...props },
        children,
      )

  return {
    Dialog,
    DialogContent: passthrough('dialog'),
    DialogHeader: passthrough(),
    DialogFooter: passthrough(),
    DialogTitle: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) =>
      React.createElement('h2', props, children),
    DialogDescription: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) =>
      React.createElement('p', props, children),
    DialogTrigger: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
    DialogClose: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
    DialogPortal: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
    DialogOverlay: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  }
})

const flushPromises = async (): Promise<void> => {
  await act(async () => {
    await Promise.resolve()
  })
}

describe('ScrapingTab', () => {
  const originalFetch = globalThis.fetch
  const mockFetch = vi.fn()

  beforeEach(() => {
    mockFetch.mockReset()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = originalFetch
  })

  const renderScrapingTab = async (isAdmin: boolean): Promise<void> => {
    await act(async () => {
      render(
        <BugReportProvider>
          <ScrapingTab isAdmin={isAdmin} />
        </BugReportProvider>
      )
    })
  }

  it('requires admin access when viewer is not an admin', async () => {
    await renderScrapingTab(false)
    expect(screen.getByText(/admin access is required/i)).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('renders admin metrics and telemetry details from runtime data', async () => {
    const jobPayload = {
      id: 1,
      status: 'running' as const,
      url: 'https://example.com/gallery',
      output_dir: '/tmp/job-1',
      created_at: new Date('2025-10-20T12:00:00Z').toISOString(),
      images_scraped: 12,
      progress: 45,
      progress_message: 'Downloading latest images…',
      config: {},
      runtime: {
        stage: 'downloading',
        discovered: 123,
        downloaded: 12,
        progress: 45,
        last_message: 'Downloading latest images…',
        updated_at: new Date('2025-10-20T12:05:00Z').toISOString(),
      },
    }

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jobs: [jobPayload],
            total: 1,
            page: 1,
            per_page: 10,
            pages: 1,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 1,
            total_images_scraped: 12,
            recent_jobs: 1,
            status_breakdown: { running: 1 },
            storage: {
              path: '/mnt/storage/imagineer/scraped',
              total_gb: 900,
              used_gb: 300,
              free_gb: 600,
              free_percent: 66.7,
            },
          }),
      })

    await renderScrapingTab(true)

    await flushPromises()
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })

    await flushPromises()

    expect(await screen.findByText(/web scraping/i)).toBeInTheDocument()
    expect(await screen.findByText(/links discovered: 123/i)).toBeInTheDocument()
    expect(await screen.findByText(/images downloaded: 12/i)).toBeInTheDocument()
    expect(await screen.findByText(/downloading latest images/i)).toBeInTheDocument()
    expect(await screen.findByText(/images scraped:\s*12/i)).toBeInTheDocument()
    expect(await screen.findByText(/storage free/i)).toBeInTheDocument()
    expect(await screen.findByText(/\/mnt\/storage\/imagineer\/scraped/i)).toBeInTheDocument()
  })

  it('starts a new scrape and refreshes the job list', async () => {
    const user = userEvent.setup()

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jobs: [],
            total: 0,
            page: 1,
            per_page: 10,
            pages: 0,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 0,
            total_images_scraped: 0,
            recent_jobs: 0,
            status_breakdown: {},
            storage: {
              path: '/mnt/storage/imagineer/scraped',
              total_gb: 900,
              used_gb: 300,
              free_gb: 600,
              free_percent: 66.7,
            },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            job_id: 'job-2',
            task_id: 'task-99',
            status: 'pending',
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jobs: [
              {
                id: 2,
                status: 'pending',
                url: 'https://cards.test',
                created_at: new Date().toISOString(),
                images_scraped: null,
                progress: null,
                config: {},
                runtime: {},
              },
            ],
            total: 1,
            page: 1,
            per_page: 10,
            pages: 1,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 1,
            total_images_scraped: 0,
            recent_jobs: 1,
            status_breakdown: { pending: 1 },
            storage: {
              path: '/mnt/storage/imagineer/scraped',
              total_gb: 900,
              used_gb: 300,
              free_gb: 600,
              free_percent: 66.7,
            },
          }),
      })

    await renderScrapingTab(true)
    await flushPromises()

    await user.click(screen.getByRole('button', { name: /start new scrape/i }))
    await user.type(screen.getByLabelText(/url to scrape/i), 'https://cards.test')
    await user.click(screen.getByRole('button', { name: /start scrape/i }))

    await flushPromises()
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/scraping/start'),
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })

    const payload = mockFetch.mock.calls[2]?.[1]
    expect(payload).toBeDefined()
    if (payload && typeof payload.body === 'string') {
      const parsed = JSON.parse(payload.body)
      expect(parsed.url).toEqual('https://cards.test')
    }

    await flushPromises()

    expect(await screen.findByRole('link', { name: /cards\.test/i })).toBeInTheDocument()
  })
})
