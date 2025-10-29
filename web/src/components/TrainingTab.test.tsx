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
      id: 1,
      name: 'deck-model',
      description: 'Test deck training',
      status: 'running',
      dataset_path: '/tmp/imagineer/data/training/training_run_1',
      output_path: '/tmp/imagineer/models/lora/trained_1',
      final_checkpoint: '/tmp/imagineer/models/lora/trained_1/model.safetensors',
      training_config: JSON.stringify({
        steps: 1000,
        rank: 4,
        learning_rate: 0.0001,
        batch_size: 1,
        album_ids: [123, 456],
      }),
      created_at: new Date('2025-10-20T12:00:00Z').toISOString(),
      started_at: new Date('2025-10-20T12:05:00Z').toISOString(),
      progress: 25,
      error_message: null,
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
    expect(screen.getByText(/dataset directory/i)).toBeInTheDocument()
    expect(screen.getByText(/\/tmp\/imagineer\/data\/training\/training_run_1/i)).toBeInTheDocument()
    expect(screen.getByText(/output directory/i)).toBeInTheDocument()
    expect(screen.getByText(/final checkpoint/i)).toBeInTheDocument()
    expect(screen.getByText(/albums: 123, 456/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view logs/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create training run/i })).toBeInTheDocument()
  })

  it('opens the log viewer and displays streamed logs', async () => {
    const trainingRun = {
      id: 2,
      name: 'log-model',
      description: '',
      status: 'running',
      dataset_path: '/tmp/imagineer/data/training/run_logs',
      output_path: '/tmp/imagineer/models/lora/run_logs',
      final_checkpoint: null,
      training_config: {
        steps: 750,
        rank: 8,
        learning_rate: 0.00005,
        batch_size: 2,
        album_ids: ['album-1'],
      },
      created_at: new Date().toISOString(),
      progress: 10,
      error_message: null,
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
        '/api/training/2/logs?tail=500',
        expect.objectContaining({
          credentials: 'include',
        }),
      )
    })

    expect(await screen.findByText(/epoch 1 - loss: 0\.123/i)).toBeInTheDocument()
    expect(screen.getByText(/\/tmp\/imagineer\/data\/training\/run_logs/i)).toBeInTheDocument()
  })
})
