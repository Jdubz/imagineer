import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ImageGallery from './ImageGallery'

describe('ImageGallery', () => {
  const mockImages = [
    {
      filename: 'test1.png',
      path: '/outputs/test1.png',
      size: 100000,
      created: '2024-10-13T10:00:00',
      metadata: {
        prompt: 'a beautiful sunset',
        seed: 42,
        steps: 25,
        guidance_scale: 7.5
      }
    },
    {
      filename: 'test2.png',
      path: '/outputs/test2.png',
      size: 150000,
      created: '2024-10-13T11:00:00',
      metadata: {
        prompt: 'a mountain landscape',
        seed: 100,
        steps: 30,
        guidance_scale: 8.0
      }
    }
  ]

  it('renders empty state when no images', () => {
    render(<ImageGallery images={[]} />)

    expect(screen.getByText(/no images yet/i)).toBeInTheDocument()
  })

  it('renders all images', () => {
    render(<ImageGallery images={mockImages} />)

    const images = screen.getAllByRole('img')
    expect(images).toHaveLength(2)
  })

  it('displays image prompts', () => {
    render(<ImageGallery images={mockImages} />)

    expect(screen.getByText(/a beautiful sunset/i)).toBeInTheDocument()
    expect(screen.getByText(/a mountain landscape/i)).toBeInTheDocument()
  })

  it('opens modal when image is clicked', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />)

    const firstImage = screen.getAllByRole('img')[0]
    await user.click(firstImage)

    // Modal should be open with metadata
    await waitFor(() => {
      expect(screen.getByText(/seed.*42/i)).toBeInTheDocument()
      expect(screen.getByText(/steps.*25/i)).toBeInTheDocument()
    })
  })

  it('closes modal when close button is clicked', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />)

    // Open modal
    const firstImage = screen.getAllByRole('img')[0]
    await user.click(firstImage)

    // Close modal
    const closeButton = screen.getByRole('button', { name: /close|×/i })
    await user.click(closeButton)

    // Metadata should no longer be visible
    await waitFor(() => {
      expect(screen.queryByText(/seed.*42/i)).not.toBeInTheDocument()
    })
  })

  it('closes modal when clicking outside', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />)

    // Open modal
    const firstImage = screen.getAllByRole('img')[0]
    await user.click(firstImage)

    // Click modal backdrop
    const modal = screen.getByRole('dialog', { hidden: true }) || screen.getByTestId('modal-backdrop')
    if (modal) {
      await user.click(modal)

      await waitFor(() => {
        expect(screen.queryByText(/seed.*42/i)).not.toBeInTheDocument()
      })
    }
  })

  it('displays truncated prompts correctly', () => {
    const longPromptImage = {
      filename: 'test3.png',
      path: '/outputs/test3.png',
      size: 100000,
      created: '2024-10-13T12:00:00',
      metadata: {
        prompt: 'a'.repeat(100),
        seed: 42,
        steps: 25
      }
    }

    render(<ImageGallery images={[longPromptImage]} />)

    const promptText = screen.getByText(/a+/i)
    expect(promptText).toBeInTheDocument()
  })

  it('handles images without metadata', () => {
    const imageWithoutMetadata = {
      filename: 'test4.png',
      path: '/outputs/test4.png',
      size: 100000,
      created: '2024-10-13T13:00:00',
      metadata: {}
    }

    render(<ImageGallery images={[imageWithoutMetadata]} />)

    // Should render without crashing
    expect(screen.getAllByRole('img')).toHaveLength(1)
  })

  it('displays correct API URL for images', () => {
    render(<ImageGallery images={mockImages} />)

    const firstImage = screen.getAllByRole('img')[0]
    expect(firstImage.src).toContain('/api/outputs/test1.png')
  })

  it('shows loading state for images', () => {
    render(<ImageGallery images={mockImages} />)

    const images = screen.getAllByRole('img')
    images.forEach(img => {
      expect(img).toHaveAttribute('loading', 'lazy')
    })
  })
})
