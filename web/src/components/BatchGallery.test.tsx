import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import BatchGallery from './BatchGallery'

const mockUseApp = vi.fn()
const mockGetById = vi.fn()

vi.mock('../contexts/AppContext', () => ({
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  useApp: () => mockUseApp(),
}))

vi.mock('@/lib/api', () => ({
  api: {
    batches: {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-return
      getById: (...args: unknown[]) => mockGetById(...args),
    },
  },
}))

describe('BatchGallery NSFW handling', () => {
  const batchId = 'batch-123'

  const makeBatchResponse = () => ({
    batch_id: batchId,
    image_count: 1,
    images: [
      {
        id: 101,
        filename: 'batch-image.png',
        download_url: '/api/images/101/file',
        thumbnail_url: '/api/images/101/thumbnail',
        is_nsfw: true,
        created: new Date().toISOString(),
        metadata: {
          prompt: 'Batch prompt',
          steps: 20,
          seed: 42,
        },
      },
    ],
  })

  beforeEach(() => {
    mockUseApp.mockReset()
    mockGetById.mockReset()
    mockGetById.mockResolvedValue(makeBatchResponse())
  })

  it('hides NSFW batch images when preference is hide', async () => {
    mockUseApp.mockReturnValue({ nsfwPreference: 'hide' })

    render(<BatchGallery batchId={batchId} onBack={vi.fn()} />)

    await waitFor(() => expect(mockGetById).toHaveBeenCalledWith(batchId))
    await waitFor(() => {
      expect(screen.queryByText('Loading batch...')).not.toBeInTheDocument()
    })

    expect(screen.queryByAltText('Batch prompt')).not.toBeInTheDocument()
  })

  it('blurs NSFW batch images when preference is blur', async () => {
    mockUseApp.mockReturnValue({ nsfwPreference: 'blur' })

    render(<BatchGallery batchId={batchId} onBack={vi.fn()} />)

    await waitFor(() => expect(mockGetById).toHaveBeenCalledWith(batchId))
    await waitFor(() => {
      expect(screen.queryByText('Loading batch...')).not.toBeInTheDocument()
    })

    expect(screen.getByAltText('Batch prompt')).toBeInTheDocument()
    expect(screen.getByLabelText('NSFW content blurred')).toBeInTheDocument()
  })
})
