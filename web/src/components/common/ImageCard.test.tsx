import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import ImageCard from './ImageCard'
import type { GeneratedImage } from '../../types/models'

// Mock the imageSources module
vi.mock('../../lib/imageSources', () => ({
  resolveImageSources: vi.fn((image: GeneratedImage) => ({
    thumbnail: `/api/images/${image.id}/thumbnail`,
    full: `/api/images/${image.id}/file`,
    alt: image.metadata?.prompt || image.filename,
    srcSet: `/api/images/${image.id}/thumbnail 1x, /api/images/${image.id}/file 2x`,
  })),
  preloadImage: vi.fn(),
}))

describe('ImageCard', () => {
  const mockImage: GeneratedImage = {
    id: 1,
    filename: 'test-image.png',
    metadata: {
      prompt: 'A beautiful landscape',
      seed: 12345,
      steps: 30,
      guidance_scale: 7.5,
    },
    is_nsfw: false,
  }

  describe('Basic Rendering', () => {
    it('renders an image card', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', '/api/images/1/thumbnail')
    })

    it('displays the prompt when provided', () => {
      render(<ImageCard image={mockImage} showPrompt={true} />)

      expect(screen.getByText('A beautiful landscape')).toBeInTheDocument()
    })

    it('truncates long prompts', () => {
      const longPrompt = 'A'.repeat(100)
      const imageWithLongPrompt = {
        ...mockImage,
        metadata: { ...mockImage.metadata, prompt: longPrompt },
      }

      render(<ImageCard image={imageWithLongPrompt} showPrompt={true} />)

      const truncatedText = screen.getByText(/A+\.\.\./)
      expect(truncatedText).toBeInTheDocument()
      expect(truncatedText.textContent?.length).toBeLessThan(60)
    })

    it('hides prompt when showPrompt is false', () => {
      render(<ImageCard image={mockImage} showPrompt={false} />)

      expect(screen.queryByText('A beautiful landscape')).not.toBeInTheDocument()
    })
  })

  describe('NSFW handling', () => {
    const nsfwImage: GeneratedImage = {
      ...mockImage,
      is_nsfw: true,
    }

    it('hides NSFW images when preference is hide (default)', () => {
      const { container } = render(
        <ImageCard image={nsfwImage} />
      )

      expect(container.firstChild).toBeNull()
    })

    it('shows NSFW images when preference is show', () => {
      render(<ImageCard image={nsfwImage} nsfwPreference="show" />)

      const img = screen.getByRole('img')
      expect(img).toBeInTheDocument()
    })

    it('blurs NSFW images when preference is blur', () => {
      render(<ImageCard image={nsfwImage} nsfwPreference="blur" />)

      const img = screen.getByRole('img')
      expect(img).toHaveClass('blurred')
      expect(screen.getByLabelText(/nsfw content blurred/i)).toBeInTheDocument()
      expect(screen.getByText(/blurred/i)).toBeInTheDocument()
    })

    it('shows NSFW badge on NSFW images when visible', () => {
      render(<ImageCard image={nsfwImage} nsfwPreference="show" />)

      expect(screen.getByText('18+')).toBeInTheDocument()
      expect(screen.getByLabelText('NSFW content')).toBeInTheDocument()
    })

    it('does not show NSFW badge when showNsfwBadge is false', () => {
      render(
        <ImageCard
          image={nsfwImage}
          nsfwPreference="show"
          showNsfwBadge={false}
        />
      )

      expect(screen.queryByText('18+')).not.toBeInTheDocument()
    })

    it('does not show NSFW badge on non-NSFW images', () => {
      render(<ImageCard image={mockImage} />)

      expect(screen.queryByText('18+')).not.toBeInTheDocument()
    })
  })

  describe('Label Badge', () => {
    it('shows label badge when labelCount > 0', () => {
      render(<ImageCard image={mockImage} labelCount={3} />)

      expect(screen.getByText('🏷️')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByLabelText('3 labels')).toBeInTheDocument()
    })

    it('does not show label count when labelCount is 1', () => {
      render(<ImageCard image={mockImage} labelCount={1} />)

      expect(screen.getByText('🏷️')).toBeInTheDocument()
      expect(screen.queryByText('1')).not.toBeInTheDocument()
    })

    it('does not show label badge when labelCount is 0', () => {
      render(<ImageCard image={mockImage} labelCount={0} />)

      expect(screen.queryByText('🏷️')).not.toBeInTheDocument()
    })

    it('does not show label badge when showLabelBadge is false', () => {
      render(
        <ImageCard
          image={mockImage}
          labelCount={3}
          showLabelBadge={false}
        />
      )

      expect(screen.queryByText('🏷️')).not.toBeInTheDocument()
    })
  })

  describe('Click Handling', () => {
    it('calls onImageClick when image is clicked', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <ImageCard
          image={mockImage}
          onImageClick={handleClick}
        />
      )

      const img = screen.getByRole('img')
      await user.click(img)

      expect(handleClick).toHaveBeenCalledOnce()
      expect(handleClick).toHaveBeenCalledWith(mockImage)
    })

    it('does not apply clickable class when onImageClick is not provided', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).not.toHaveClass('clickable')
    })

    it('applies clickable class when onImageClick is provided', () => {
      render(
        <ImageCard
          image={mockImage}
          onImageClick={vi.fn()}
        />
      )

      const img = screen.getByRole('img')
      expect(img).toHaveClass('clickable')
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      const { container } = render(
        <ImageCard
          image={mockImage}
          className="custom-class"
        />
      )

      const card = container.firstChild as HTMLElement
      expect(card).toHaveClass('image-card')
      expect(card).toHaveClass('custom-class')
    })

    it('applies nsfw class to NSFW images', () => {
      const { container } = render(
        <ImageCard
          image={{ ...mockImage, is_nsfw: true }}
          nsfwPreference="show"
        />
      )

      const card = container.firstChild as HTMLElement
      expect(card).toHaveClass('nsfw')
    })
  })

  describe('Responsive Images', () => {
    it('uses default sizes attribute', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute(
        'sizes',
        '(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 100vw'
      )
    })

    it('accepts custom sizes attribute', () => {
      render(
        <ImageCard
          image={mockImage}
          sizes="(min-width: 1280px) 20vw, 50vw"
        />
      )

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('sizes', '(min-width: 1280px) 20vw, 50vw')
    })

    it('includes srcSet for responsive images', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('srcSet')
    })

    it('uses lazy loading', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('loading', 'lazy')
    })

    it('uses async decoding', () => {
      render(<ImageCard image={mockImage} />)

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('decoding', 'async')
    })
  })
})
