import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AlbumsTab from './AlbumsTab'
import { BugReportProvider } from '../contexts/BugReportContext'

describe('AlbumsTab admin listing', () => {
  const originalFetch = globalThis.fetch
  const mockFetch = vi.fn()

  beforeEach(() => {
    mockFetch.mockReset()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  const mockAlbumListResponse = [
    {
      id: '1',
      name: 'Sample Album',
      description: 'Test description',
      album_type: 'manual',
      image_count: 1,
      created_at: '2025-10-20T12:00:00Z',
      updated_at: '2025-10-20T12:00:00Z',
      images: [
        {
          id: 100,
          filename: 'cover.png',
          is_nsfw: false,
        },
      ],
    },
  ]

  it('shows admin actions for albums', async () => {
    mockFetch.mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : input.url

      if (url === '/api/albums') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAlbumListResponse),
        } as Response)
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        } as Response)
    })

    render(
      <BugReportProvider>
        <MemoryRouter>
          <AlbumsTab isAdmin />
        </MemoryRouter>
      </BugReportProvider>
    )

    const albumLink = await screen.findByRole('link', { name: /sample album/i })
    expect(albumLink).toHaveAttribute('href', '/albums/1')

    // Admin-specific actions on the card
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
    })
  })

  it('hides labeling controls for non-admin users', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockAlbumListResponse),
    })

    render(
      <BugReportProvider>
        <MemoryRouter>
          <AlbumsTab isAdmin={false} />
        </MemoryRouter>
      </BugReportProvider>
    )

    expect(await screen.findByText(/sample album/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })
})
