import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '@testing-library/jest-dom'
import GalleryTab from './GalleryTab'

const mockUseGallery = vi.fn()
const mockUseApp = vi.fn()

vi.mock('../contexts/AppContext', () => ({
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  useGallery: () => mockUseGallery(),
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  useApp: () => mockUseApp(),
}))

vi.mock('./BatchList', () => ({
  __esModule: true,
  default: () => <div data-testid="batch-list" />,
}))

vi.mock('./BatchGallery', () => ({
  __esModule: true,
  default: () => <div data-testid="batch-gallery" />,
}))

describe('GalleryTab NSFW handling', () => {
  const baseState = {
    batches: [],
    loadingImages: false,
    loadingBatches: false,
    fetchImages: vi.fn(),
    fetchBatches: vi.fn(),
    setNsfwPreference: vi.fn(),
  }

  beforeEach(() => {
    mockUseGallery.mockReset()
    mockUseApp.mockReset()
  })

  it('omits NSFW images when preference is hide', () => {
    mockUseGallery.mockReturnValue({
      ...baseState,
      images: [
        {
          id: 1,
          filename: 'sfw.png',
          is_nsfw: false,
          download_url: '/api/images/1/file',
          thumbnail_url: '/api/images/1/thumbnail',
          metadata: { prompt: 'SFW forest scene' },
        },
        {
          id: 2,
          filename: 'nsfw.png',
          is_nsfw: true,
          download_url: '/api/images/2/file',
          thumbnail_url: '/api/images/2/thumbnail',
          metadata: { prompt: 'NSFW sunset' },
        },
      ],
      nsfwPreference: 'hide',
    })
    mockUseApp.mockReturnValue({ nsfwPreference: 'hide', setNsfwPreference: vi.fn() })

    render(
      <MemoryRouter>
        <GalleryTab />
      </MemoryRouter>,
    )

    expect(screen.getByAltText('SFW forest scene')).toBeInTheDocument()
    expect(screen.queryByAltText('NSFW sunset')).not.toBeInTheDocument()
  })

  it('blurs NSFW images when preference is blur', () => {
    mockUseGallery.mockReturnValue({
      ...baseState,
      images: [
        {
          id: 3,
          filename: 'nsfw.png',
          is_nsfw: true,
          download_url: '/api/images/3/file',
          thumbnail_url: '/api/images/3/thumbnail',
          metadata: { prompt: 'Blurred content' },
        },
      ],
      nsfwPreference: 'blur',
    })
    mockUseApp.mockReturnValue({ nsfwPreference: 'blur', setNsfwPreference: vi.fn() })

    render(
      <MemoryRouter>
        <GalleryTab />
      </MemoryRouter>,
    )

    expect(screen.getByAltText('Blurred content')).toBeInTheDocument()
    expect(screen.getByLabelText('NSFW content blurred')).toBeInTheDocument()
  })
})
