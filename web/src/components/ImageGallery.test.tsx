import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ImageGallery from './ImageGallery'
import type { GeneratedImage } from '../types/models'

const makeImage = (overrides: Partial<GeneratedImage> = {}): GeneratedImage => ({
  filename: overrides.filename ?? 'test.png',
  path: overrides.path ?? '/outputs/test.png',
  size: overrides.size ?? 100_000,
  created: overrides.created ?? new Date().toISOString(),
  metadata: overrides.metadata ?? {
    prompt: 'a test prompt',
    seed: 42,
    steps: 25,
    guidance_scale: 7.5,
  },
})

describe('ImageGallery', () => {
  const mockImages: GeneratedImage[] = [
    makeImage({ filename: 'test1.png', path: '/outputs/test1.png' }),
    makeImage({ filename: 'test2.png', path: '/outputs/test2.png', metadata: { prompt: 'mountain view' } }),
  ]

  it('renders empty state when no images', () => {
    render(<ImageGallery images={[]} />)

    expect(screen.getByText(/no images yet/i)).toBeInTheDocument()
  })

  it('renders all images', () => {
    render(<ImageGallery images={mockImages} />)

    const images = screen.getAllByRole('img')
    expect(images).toHaveLength(mockImages.length)
  })

  it('opens and closes the modal', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />)

    const firstImage = screen.getAllByRole('img')[0]
    await user.click(firstImage)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const closeButton = screen.getByRole('button', { name: /close|×/i })
    await user.click(closeButton)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('closes modal when clicking the backdrop', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />)

    const firstImage = screen.getAllByRole('img')[0]
    await user.click(firstImage)

    const backdrop = screen.getByTestId('modal-backdrop')
    await user.click(backdrop)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})

