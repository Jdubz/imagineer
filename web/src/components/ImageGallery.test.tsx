import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ImageGallery from './ImageGallery'
import { AppProvider } from '../contexts/AppContext'
import { AuthProvider } from '../contexts/AuthContext'
import { BugReportProvider } from '../contexts/BugReportContext'
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

// Wrapper to provide necessary contexts for ImageGallery
const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>
    <BugReportProvider>
      <AppProvider>{children}</AppProvider>
    </BugReportProvider>
  </AuthProvider>
)

describe('ImageGallery', () => {
  const mockImages: GeneratedImage[] = [
    makeImage({ filename: 'test1.png', path: '/outputs/test1.png' }),
    makeImage({ filename: 'test2.png', path: '/outputs/test2.png', metadata: { prompt: 'mountain view' } }),
  ]

  it('renders empty state when no images', () => {
    render(<ImageGallery images={[]} />, { wrapper: Wrapper })

    expect(screen.getByText(/no images yet/i)).toBeInTheDocument()
  })

  it('renders all images', () => {
    render(<ImageGallery images={mockImages} />, { wrapper: Wrapper })

    const images = screen.getAllByRole('img')
    expect(images).toHaveLength(mockImages.length)
  })

  it('opens and closes the modal', async () => {
    const user = userEvent.setup()
    render(<ImageGallery images={mockImages} />, { wrapper: Wrapper })

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

  // Note: Backdrop click behavior is handled by shadcn Dialog (Radix UI)
  // The dialog automatically closes when clicking outside, so we don't need
  // to test this explicitly. Radix UI has its own comprehensive tests for this.
})

