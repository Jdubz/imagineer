import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LabelingPanel from './LabelingPanel'

const flushPromises = async (): Promise<void> => {
  await act(async () => {
    await Promise.resolve()
  })
}

describe('LabelingPanel', () => {
  const originalFetch = globalThis.fetch
  const mockFetch = vi.fn()

  beforeEach(() => {
    mockFetch.mockReset()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    globalThis.fetch = originalFetch
  })

  it('renders album labeling controls for admins', () => {
    render(<LabelingPanel albumId={42} />)

    expect(screen.getByRole('button', { name: /start labeling/i })).toBeInTheDocument()
    expect(screen.getByText(/caption, tag, and classify/i)).toBeInTheDocument()
  })

  it('queues labeling task and polls progress until completion', async () => {
    vi.useFakeTimers()
    const onComplete = vi.fn()
    mockFetch
      .mockResolvedValueOnce({
        status: 202,
        ok: true,
        json: () => Promise.resolve({ task_id: 'task-123' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ state: 'PROGRESS', progress: { current: 2, total: 5 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ state: 'SUCCESS', result: { status: 'success' } }),
      })

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<LabelingPanel albumId={1} onComplete={onComplete} />)

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /start labeling/i }))
    })
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/labeling/album/1',
      expect.objectContaining({
        method: 'POST',
      }),
    )

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await flushPromises()
    })

    expect(mockFetch).toHaveBeenCalledWith('/api/labeling/tasks/task-123', expect.any(Object))
    expect(screen.getByText(/labeled 2 of 5 images/i)).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await flushPromises()
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/labeling complete/i)).toBeInTheDocument()
  })

  it('shows error when initial request fails', async () => {
    mockFetch.mockResolvedValueOnce({
      status: 400,
      ok: false,
      json: () => Promise.resolve({ error: 'Album is empty' }),
    })

    const user = userEvent.setup()
    render(<LabelingPanel albumId={99} />)

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /start labeling/i }))
    })
    await flushPromises()

    await waitFor(() => {
      expect(screen.getByText(/album is empty/i)).toBeInTheDocument()
    })
  })

  it('renders compact variant for single images', async () => {
    vi.useFakeTimers()
    mockFetch.mockResolvedValueOnce({
      status: 202,
      ok: true,
      json: () => Promise.resolve({ task_id: 'img-task' }),
    })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ state: 'SUCCESS', result: { status: 'success' } }),
    })

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<LabelingPanel imageId={7} variant="compact" />)

    const trigger = screen.getByRole('button', { name: /label image/i })
    await act(async () => {
      await user.click(trigger)
    })

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await flushPromises()
    })

    expect(screen.getByText(/labeling complete/i)).toBeInTheDocument()
  })
})
