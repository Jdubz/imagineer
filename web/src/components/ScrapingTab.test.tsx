import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ScrapingTab from './ScrapingTab'

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

  it('requires admin access when viewer is not an admin', () => {
    render(<ScrapingTab isAdmin={false} />)
    expect(screen.getByText(/admin access is required/i)).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('renders admin metrics and telemetry details from runtime data', async () => {
    const jobPayload = {
      id: 'job-1',
      status: 'running' as const,
      url: 'https://example.com/gallery',
      output_dir: '/tmp/job-1',
      created_at: new Date('2025-10-20T12:00:00Z').toISOString(),
      images_scraped: 12,
      progress: 45,
      progress_message: 'Downloading latest images…',
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
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 1,
            total_images_scraped: 12,
            recent_jobs: 1,
            storage: {
              path: '/mnt/storage/imagineer/scraped',
              total_gb: 900,
              used_gb: 300,
              free_gb: 600,
              free_percent: 66.7,
            },
          }),
      })

    render(<ScrapingTab isAdmin />)

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
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 0,
            total_images_scraped: 0,
            recent_jobs: 0,
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
                id: 'job-2',
                status: 'pending',
                url: 'https://cards.test',
                created_at: new Date().toISOString(),
              },
            ],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            total_jobs: 1,
            total_images_scraped: 0,
            recent_jobs: 1,
            storage: {
              path: '/mnt/storage/imagineer/scraped',
              total_gb: 900,
              used_gb: 300,
              free_gb: 600,
              free_percent: 66.7,
            },
          }),
      })

    render(<ScrapingTab isAdmin />)
    await flushPromises()

    await user.click(screen.getByRole('button', { name: /start new scrape/i }))
    await user.type(screen.getByLabelText(/url to scrape/i), 'https://cards.test')
    await user.click(screen.getByRole('button', { name: /start scrape/i }))

    await flushPromises()
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/scraping/start',
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
