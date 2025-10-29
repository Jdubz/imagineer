import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import AlbumsTab from './AlbumsTab'
import { ToastProvider } from '../contexts/ToastContext'

describe('AlbumsTab admin labeling integration', () => {
  const originalFetch = globalThis.fetch
  const mockFetch = vi.fn()

  beforeEach(() => {
    mockFetch.mockReset()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  const mockAlbumListResponse = {
    albums: [
      {
        id: '1',
        name: 'Sample Album',
        description: 'Test description',
        image_count: 1,
        created_at: '2025-10-20T12:00:00Z',
        updated_at: '2025-10-20T12:00:00Z',
        images: [
          {
            id: '100',
            filename: 'cover.png',
            is_nsfw: false,
          },
        ],
      },
    ],
  }

  const mockAlbumDetailResponse = {
    id: '1',
    name: 'Sample Album',
    description: 'Test description',
    image_count: 1,
    created_at: '2025-10-20T12:00:00Z',
    updated_at: '2025-10-20T12:00:00Z',
    images: [
      {
        id: 100,
        filename: 'cover.png',
        is_nsfw: false,
        labels: [
          {
            id: 501,
            image_id: 100,
            label_text: 'existing',
            label_type: 'tag',
            confidence: null,
            source_model: 'unit-test',
            source_prompt: null,
            created_by: 'tester@example.com',
            created_at: '2025-10-20T12:00:00Z',
          },
        ],
        label_count: 1,
        manual_label_count: 0,
      },
    ],
  }

  const mockAnalyticsResponse = {
    album_id: 1,
    image_count: 1,
    labels_total: 1,
    labels_by_type: { tag: 1 },
    images_with_labels: 1,
    images_with_manual_labels: 0,
    images_with_captions: 0,
    unlabeled_images: 0,
    average_labels_per_image: 1,
    coverage: {
      labels_percent: 100,
      manual_percent: 0,
      caption_percent: 0,
    },
    top_tags: [{ label_text: 'existing', count: 1 }],
    last_labeled_at: '2025-10-20T12:00:00Z',
  }

  it('shows labeling controls for admins', async () => {
    mockFetch.mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : input.url

      if (url === '/api/albums') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAlbumListResponse),
        } as Response)
      }

      if (url.includes('/api/albums/1/labeling/analytics')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAnalyticsResponse),
        } as Response)
      }

      if (url.includes('/api/albums/1')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAlbumDetailResponse),
        } as Response)
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        } as Response)
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <ToastProvider>
          <AlbumsTab isAdmin />
        </ToastProvider>
      </MemoryRouter>
    )

    const albumCard = await screen.findByText(/sample album/i)
    await user.click(albumCard)

    // Verify album-level labeling controls are present
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start labeling/i })).toBeInTheDocument()
    })

    // Verify analytics section is present
    expect(screen.getByText(/top tags/i)).toBeInTheDocument()
    expect(screen.getAllByText(/existing/i)[0]).toBeInTheDocument()
  })

  it('hides labeling controls for non-admin users', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockAlbumListResponse),
    })

    render(
      <MemoryRouter>
        <ToastProvider>
          <AlbumsTab isAdmin={false} />
        </ToastProvider>
      </MemoryRouter>
    )

    expect(await screen.findByText(/sample album/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start labeling/i })).not.toBeInTheDocument()
  })
})
