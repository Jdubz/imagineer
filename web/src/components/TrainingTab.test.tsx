import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TrainingTab from './TrainingTab'

const flush = async (): Promise<void> => {
  await act(async () => {
    await Promise.resolve()
  })
}

describe('TrainingTab', () => {
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

  it('hides admin controls for non-admin users', () => {
    render(<TrainingTab isAdmin={false} />)
    expect(screen.getByText(/sign in with an admin account/i)).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('loads training runs and albums for admins', async () => {
    const trainingRun = {
      id: 'run-1',
      status: 'running',
      output_name: 'deck-model',
      dataset: 'training_run_1',
      steps: 1000,
      rank: 4,
      learning_rate: 0.0001,
      created_at: new Date('2025-10-20T12:00:00Z').toISOString(),
      started_at: new Date('2025-10-20T12:05:00Z').toISOString(),
      progress: 25,
    }

    const albumsResponse = {
      albums: [
        {
          id: 'album-1',
          name: 'Tarot Deck',
          image_count: 150,
        },
      ],
    }

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            training_runs: [trainingRun],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(albumsResponse),
      })

    render(<TrainingTab isAdmin />)
    await flush()

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })

    expect(await screen.findByText(/deck-model/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view logs/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create training run/i })).toBeInTheDocument()
  })

  it('opens the log viewer and displays streamed logs', async () => {
    const trainingRun = {
      id: 'run-logs',
      status: 'running',
      output_name: 'log-model',
      dataset: 'training_run_logs',
      steps: 1000,
      rank: 4,
      learning_rate: 0.0001,
      created_at: new Date().toISOString(),
      progress: 10,
    }

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            training_runs: [trainingRun],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            albums: [],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            training_run_id: 1,
            status: 'running',
            progress: 10,
            log_available: true,
            log_path: '/tmp/logs/run-logs.log',
            logs: 'Epoch 1 - loss: 0.123',
          }),
      })

    const user = userEvent.setup()
    render(<TrainingTab isAdmin />)
    await flush()

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })

    expect(await screen.findByText(/log-model/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /view logs/i }))
    await flush()

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/training/run-logs/logs?tail=500',
        expect.objectContaining({
          credentials: 'include',
        }),
      )
    })

    expect(await screen.findByText(/epoch 1 - loss: 0\.123/i)).toBeInTheDocument()
  })
})
