import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AlbumsTab from './AlbumsTab'

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
    images: [
      {
        id: '100',
        filename: 'cover.png',
        is_nsfw: false,
        labels: [],
      },
    ],
  }

  it('shows labeling controls for admins', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAlbumListResponse),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAlbumDetailResponse),
      })

    const user = userEvent.setup()
    render(<AlbumsTab isAdmin />)

    const albumCard = await screen.findByText(/sample album/i)
    await user.click(albumCard)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start labeling/i })).toBeInTheDocument()
    })

    expect(await screen.findByRole('button', { name: /label image/i })).toBeInTheDocument()
  })

  it('hides labeling controls for non-admin users', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockAlbumListResponse),
    })

    render(<AlbumsTab isAdmin={false} />)

    expect(await screen.findByText(/sample album/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start labeling/i })).not.toBeInTheDocument()
  })
})
