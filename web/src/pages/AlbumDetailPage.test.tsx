import { describe, it, beforeEach, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AlbumDetailPage from './AlbumDetailPage'
import type { Album, GeneratedImage, Label as ImageLabel } from '../types/models'

const mockToast = vi.fn()
const mockShowErrorToast = vi.fn()

vi.mock('../hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

vi.mock('../hooks/use-error-toast', () => ({
  useErrorToast: () => ({ showErrorToast: mockShowErrorToast }),
}))

vi.mock('@/components/LabelingPanel', () => ({
  default: ({ onComplete }: { onComplete?: () => Promise<void> | void }) => (
    <button type="button" data-testid="album-labeling" onClick={() => onComplete && onComplete()}>
      Run labeling
    </button>
  ),
}))

const mockGetAlbum = vi.fn<[], Promise<Album>>()
const mockCreateLabel = vi.fn<[], Promise<ImageLabel>>()
const mockDeleteLabel = vi.fn<[], Promise<void>>()

vi.mock('../lib/api', () => ({
  api: {
    albums: {
      getById: (...args: unknown[]) => mockGetAlbum(...(args as [])),
      update: vi.fn(),
      delete: vi.fn(),
    },
    images: {
      createLabel: (...args: unknown[]) => mockCreateLabel(...(args as [])),
      deleteLabel: (...args: unknown[]) => mockDeleteLabel(...(args as [])),
    },
  },
}))

const baseLabel: ImageLabel = {
  id: 11,
  image_id: 501,
  label_text: 'portrait',
  confidence: null,
  label_type: 'manual',
  source_model: null,
  source_prompt: null,
  created_by: null,
  created_at: null,
}

const baseImage: GeneratedImage = {
  id: 501,
  filename: 'album-image.png',
  download_url: 'https://example.com/image.png',
  thumbnail_url: 'https://example.com/image-thumb.png',
  prompt: 'Prompt',
  negative_prompt: null,
  path: '/images/501',
  relative_path: 'images/album-image.png',
  storage_name: 'album-image.png',
  is_nsfw: false,
  is_public: true,
  width: 512,
  height: 512,
  labels: [baseLabel],
  metadata: {},
  album_id: 42,
}

const baseAlbum: Album = {
  id: '42',
  name: 'Training Album',
  description: 'Sample album',
  album_type: 'manual',
  image_count: 1,
  created_at: '2025-11-01T10:00:00Z',
  updated_at: '2025-11-05T10:00:00Z',
  images: [baseImage],
  is_set_template: false,
}

const renderPage = (isAdmin = true) =>
  render(
    <MemoryRouter initialEntries={['/albums/42']}>
      <Routes>
        <Route path="/albums/:albumId" element={<AlbumDetailPage isAdmin={isAdmin} />} />
      </Routes>
    </MemoryRouter>,
  )

describe('AlbumDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetAlbum.mockResolvedValue(baseAlbum)
    mockCreateLabel.mockResolvedValue({ ...baseLabel, id: 12, label_text: 'sunset' })
    mockDeleteLabel.mockResolvedValue()
  })

  it('fetches album with labels and allows adding a label to an image', async () => {
    const user = userEvent.setup()
    renderPage(true)

    await waitFor(() => expect(mockGetAlbum).toHaveBeenCalledWith(42, true))
    await waitFor(() => expect(screen.getByText('portrait')).toBeInTheDocument())

    const input = screen.getByPlaceholderText('Add label')
    await user.type(input, 'sunset')
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      expect(mockCreateLabel).toHaveBeenCalledWith(501, { text: 'sunset', type: 'manual' })
    })
  })

  it('allows deleting a label from an image', async () => {
    const user = userEvent.setup()
    renderPage(true)

    await waitFor(() => expect(screen.getByText('portrait')).toBeInTheDocument())

    const deleteButton = screen.getByRole('button', { name: /delete label portrait/i })
    await user.click(deleteButton)

    await waitFor(() => expect(mockDeleteLabel).toHaveBeenCalledWith(501, 11))
  })
})
