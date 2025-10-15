import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GenerateForm from './GenerateForm'

describe('GenerateForm', () => {
  const mockOnGenerate = vi.fn()
  const mockConfig = {
    generation: {
      steps: 30,
      guidance_scale: 7.5
    }
  }

  beforeEach(() => {
    mockOnGenerate.mockClear()
  })

  it('renders the form with all inputs', () => {
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument()
  })

  it('shows loading state when generating', () => {
    render(<GenerateForm onGenerate={mockOnGenerate} loading={true} config={mockConfig} />)

    expect(screen.getByRole('button', { name: /generating/i })).toBeDisabled()
  })

  it('submits form with prompt', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const input = screen.getByPlaceholderText(/describe the image/i)
    const button = screen.getByRole('button', { name: /generate/i })

    await user.type(input, 'a beautiful sunset')
    await user.click(button)

    expect(mockOnGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: 'a beautiful sunset'
      })
    )
  })

  it('does not submit with empty prompt', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const button = screen.getByRole('button', { name: /generate/i })
    await user.click(button)

    expect(mockOnGenerate).not.toHaveBeenCalled()
  })

  it('clears prompt after submission', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const input = screen.getByPlaceholderText(/describe the image/i)

    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    expect(input.value).toBe('')
  })

  it('displays steps slider with correct range', () => {
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const stepsSlider = screen.getByLabelText(/steps/i)
    expect(stepsSlider).toBeInTheDocument()
    expect(stepsSlider).toHaveAttribute('min', '10')
    expect(stepsSlider).toHaveAttribute('max', '75')
  })

  it('displays guidance scale slider with correct range', () => {
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const guidanceSlider = screen.getByLabelText(/guidance scale/i)
    expect(guidanceSlider).toBeInTheDocument()
    expect(guidanceSlider).toHaveAttribute('min', '1')
    expect(guidanceSlider).toHaveAttribute('max', '20')
  })

  it('allows toggling between random and fixed seed', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    // Check random seed is selected by default
    const randomRadio = screen.getByLabelText(/random/i)
    expect(randomRadio).toBeChecked()

    // Switch to fixed seed
    const fixedRadio = screen.getByLabelText(/fixed/i)
    await user.click(fixedRadio)

    expect(fixedRadio).toBeChecked()
    expect(randomRadio).not.toBeChecked()
  })

  it('includes seed in submission when fixed seed is selected', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    // Switch to fixed seed
    await user.click(screen.getByLabelText(/fixed/i))

    // Enter seed value
    const seedInput = screen.getByPlaceholderText(/seed value/i)
    await user.type(seedInput, '12345')

    // Submit form
    const promptInput = screen.getByPlaceholderText(/describe the image/i)
    await user.type(promptInput, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    expect(mockOnGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        seed: 12345
      })
    )
  })

  it('generates random seed when button is clicked', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    await user.click(screen.getByLabelText(/fixed/i))

    const seedInput = screen.getByPlaceholderText(/seed value/i)
    const randomButton = screen.getByRole('button', { name: /🎲/i })

    await user.click(randomButton)

    // Seed input should have a value
    expect(seedInput.value).not.toBe('')
    expect(parseInt(seedInput.value)).toBeGreaterThan(0)
    expect(parseInt(seedInput.value)).toBeLessThanOrEqual(2147483647)
  })

  it('updates steps value when slider is moved', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const stepsSlider = screen.getByLabelText(/steps/i)

    fireEvent.change(stepsSlider, { target: { value: '50' } })

    const stepsDisplay = screen.getByText(/50/)
    expect(stepsDisplay).toBeInTheDocument()
  })

  it('updates guidance scale when slider is moved', async () => {
    const user = userEvent.setup()
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={mockConfig} />)

    const guidanceSlider = screen.getByLabelText(/guidance scale/i)

    fireEvent.change(guidanceSlider, { target: { value: '10' } })

    const guidanceDisplay = screen.getByText(/10/)
    expect(guidanceDisplay).toBeInTheDocument()
  })

  it('uses config defaults if not provided', () => {
    render(<GenerateForm onGenerate={mockOnGenerate} loading={false} config={null} />)

    // Should still render without crashing
    expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
  })
})
