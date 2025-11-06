import { describe, it, beforeEach, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ImageDetailPage from './ImageDetailPage'
import type { GeneratedImage, Label as ImageLabel } from '../types/models'

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
    <button type="button" data-testid="labeling-panel" onClick={() => onComplete && onComplete()}>
      Label image
    </button>
  ),
}))

const mockGetById = vi.fn<[number, { includeLabels?: boolean }?], Promise<GeneratedImage>>()
const mockGetLabels = vi.fn<[number], Promise<ImageLabel[]>>()
const mockCreateLabel = vi.fn<[], Promise<ImageLabel>>()
const mockUpdateLabel = vi.fn<[], Promise<ImageLabel>>()
const mockDeleteLabel = vi.fn<[], Promise<void>>()
const mockUpdateImage = vi.fn<[], Promise<GeneratedImage>>()

vi.mock('../lib/api', () => ({
  api: {
    images: {
      getById: (...args: unknown[]) =>
        mockGetById(...(args as [number, { includeLabels?: boolean }?])),
      getLabels: (...args: unknown[]) => mockGetLabels(...(args as [number])),
      createLabel: (...args: unknown[]) => mockCreateLabel(...(args as [])),
      updateLabel: (...args: unknown[]) => mockUpdateLabel(...(args as [])),
      deleteLabel: (...args: unknown[]) => mockDeleteLabel(...(args as [])),
      update: (...args: unknown[]) => mockUpdateImage(...(args as [])),
    },
  },
}))

const baseLabel: ImageLabel = {
  id: 1,
  image_id: 123,
  label_text: 'portrait',
  confidence: null,
  label_type: 'auto',
  source_model: null,
  source_prompt: null,
  created_by: null,
  created_at: null,
}

const sampleImage: GeneratedImage = {
  id: 123,
  filename: 'sample.png',
  download_url: 'https://example.com/sample.png',
  thumbnail_url: 'https://example.com/sample-thumb.png',
  prompt: 'A scenic view',
  negative_prompt: null,
  path: '/images/123',
  relative_path: 'images/sample.png',
  storage_name: 'sample.png',
  seed: 42,
  steps: 30,
  guidance_scale: 7.5,
  width: 512,
  height: 512,
  is_nsfw: false,
  is_public: true,
  metadata: {},
  labels: [baseLabel],
  album_id: 12,
}

const renderPage = (isAdmin = true) =>
  render(
    <MemoryRouter initialEntries={['/image/123']}>
      <Routes>
        <Route path="/image/:imageId" element={<ImageDetailPage isAdmin={isAdmin} />} />
      </Routes>
    </MemoryRouter>,
  )

describe('ImageDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetById.mockResolvedValue(sampleImage)
    mockGetLabels.mockResolvedValue([baseLabel])
    mockCreateLabel.mockResolvedValue({
      ...baseLabel,
      id: 2,
      label_text: 'sunset',
    })
    mockUpdateLabel.mockResolvedValue({
      ...baseLabel,
      label_text: 'sunrise',
    })
    mockDeleteLabel.mockResolvedValue()
    mockUpdateImage.mockResolvedValue({ ...sampleImage, is_nsfw: true })
  })

  it('renders labels and allows adding a new label', async () => {
    const user = userEvent.setup()
    renderPage(true)

    await waitFor(() =>
      expect(mockGetById).toHaveBeenCalledWith(123, { includeLabels: true })
    )
    await waitFor(() => expect(mockGetLabels).toHaveBeenCalledWith(123))
    await waitFor(() => expect(screen.getByText('portrait')).toBeInTheDocument())

    const input = screen.getByPlaceholderText('e.g. portrait, sunset')
    await user.clear(input)
    await user.type(input, 'sunset')
    await user.click(screen.getByRole('button', { name: /add label/i }))

    await waitFor(() => {
      expect(mockCreateLabel).toHaveBeenCalledWith(123, { text: 'sunset', type: 'manual' })
    })
    await waitFor(() => expect(screen.getByText('sunset')).toBeInTheDocument())
  })

  it('toggles NSFW flag for admin users', async () => {
    const user = userEvent.setup()
    renderPage(true)

    await waitFor(() => expect(mockGetLabels).toHaveBeenCalledWith(123))
    await waitFor(() => expect(screen.getByText('portrait')).toBeInTheDocument())

    const checkbox = screen.getByLabelText('Mark as NSFW')
    await user.click(checkbox)

    await waitFor(() => expect(mockUpdateImage).toHaveBeenCalledWith(123, { is_nsfw: true }))
  })
})
