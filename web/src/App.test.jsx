import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

// Mock fetch globally
globalThis.fetch = vi.fn()

// Mock PasswordGate component to bypass authentication in tests
vi.mock('./components/PasswordGate', () => ({
  default: ({ children }) => children
}))

describe('App', () => {
  const mockConfig = {
    generation: {
      steps: 30,
      guidance_scale: 7.5
    }
  }

  const mockImages = [
    {
      filename: 'test1.png',
      path: '/outputs/test1.png',
      size: 100000,
      created: '2024-10-13T10:00:00',
      metadata: {
        prompt: 'test prompt',
        seed: 42
      }
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset fetch mock
    globalThis.fetch = vi.fn()
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockConfig)
    })
  })

  it('renders the app title', () => {
    render(<App />)
    expect(screen.getByText(/imagineer/i)).toBeInTheDocument()
  })

  it('loads configuration on mount', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockConfig)
    })
    render(<App />)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/config')
    })
  })

  it('loads images on mount', async () => {
    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: mockImages })
      })

    render(<App />)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/outputs')
    })
  })

  it('submits generation request', async () => {
    const user = userEvent.setup()
    const mockResponse = {
      success: true,
      job: { id: 1, status: 'queued', prompt: 'test prompt' }
    }

    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

    render(<App />)

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    // Fill in prompt and submit
    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/generate',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('test prompt')
        })
      )
    })
  })

  it('handles generation error', async () => {
    const user = userEvent.setup()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] })
      })
      .mockRejectedValueOnce(new Error('Generation failed'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  it('polls for job status after generation', async () => {
    const user = userEvent.setup()
    const mockJob = {
      success: true,
      job: { id: 1, status: 'queued', prompt: 'test' }
    }

    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockJob)
      })
      .mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ images: [] })
      })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    // Should reload images after job is created
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/outputs')
    }, { timeout: 10000 })
  })

  it('displays loading state during generation', async () => {
    const user = userEvent.setup()

    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] })
      })
      .mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/describe the image/i)
    await user.type(input, 'test')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    // Should show generating state
    expect(screen.getByRole('button', { name: /generating.../i })).toBeDisabled()
  })

  it('handles config loading error', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    globalThis.fetch.mockRejectedValueOnce(new Error('Config failed'))

    render(<App />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  it('handles images loading error', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig)
      })
      .mockRejectedValueOnce(new Error('Images failed'))

    render(<App />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })
})
