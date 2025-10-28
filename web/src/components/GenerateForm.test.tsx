import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GenerateForm from './GenerateForm'
import type { Config } from '../types/models'

describe('GenerateForm', () => {
  const mockOnGenerate = vi.fn()
  const mockOnGenerateBatch = vi.fn()
  const mockConfig: Partial<Config> = {
    generation: {
      steps: 30,
      guidance_scale: 7.5,
    },
  }

  const renderForm = (overrides: Partial<React.ComponentProps<typeof GenerateForm>> = {}) =>
    render(
      <GenerateForm
        onGenerate={mockOnGenerate}
        onGenerateBatch={mockOnGenerateBatch}
        loading={false}
        config={(mockConfig as Config) ?? null}
        {...overrides}
      />,
    )

  beforeEach(() => {
    mockOnGenerate.mockReset()
    mockOnGenerateBatch.mockReset()
  })

  it('renders the form with all inputs', () => {
    renderForm()

    expect(screen.getByPlaceholderText(/describe the image/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate image/i })).toBeInTheDocument()
  })

  it('shows loading state when generating', () => {
    renderForm({ loading: true })

    const generatingButtons = screen.getAllByRole('button', { name: /generating/i })
    expect(generatingButtons).toHaveLength(2)
    generatingButtons.forEach((button) => {
      expect(button).toBeDisabled()
    })
  })

  it('submits form with prompt', async () => {
    const user = userEvent.setup()
    renderForm()

    const input = screen.getByPlaceholderText(/describe the image/i)
    const button = screen.getByRole('button', { name: /generate image/i })

    await user.type(input, 'a beautiful sunset')
    await user.click(button)

    expect(mockOnGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: 'a beautiful sunset',
      }),
    )
  })

  it('does not submit with empty prompt', async () => {
    const user = userEvent.setup()
    renderForm()

    const button = screen.getByRole('button', { name: /generate image/i })
    await user.click(button)

    expect(mockOnGenerate).not.toHaveBeenCalled()
  })

  it('clears prompt after submission', async () => {
    const user = userEvent.setup()
    renderForm()

    const input = screen.getByPlaceholderText<HTMLInputElement>(/describe the image/i)

    await user.type(input, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    expect(input.value).toBe('')
  })

  it('displays steps slider with correct range', () => {
    renderForm()

    const stepsSlider = screen.getByLabelText<HTMLInputElement>(/steps/i)
    expect(stepsSlider).toBeInTheDocument()
    expect(stepsSlider.min).toBe('10')
    expect(stepsSlider.max).toBe('75')
  })

  it('displays guidance scale slider with correct range', () => {
    renderForm()

    const guidanceSlider = screen.getByLabelText<HTMLInputElement>(/guidance scale/i)
    expect(guidanceSlider).toBeInTheDocument()
    expect(guidanceSlider.min).toBe('1')
    expect(guidanceSlider.max).toBe('20')
  })

  it('allows toggling between random and fixed seed', async () => {
    const user = userEvent.setup()
    renderForm()

    const randomRadio = screen.getByRole('radio', { name: /random/i })
    expect(randomRadio).toBeChecked()

    const fixedRadio = screen.getByRole('radio', { name: /fixed/i })
    await user.click(fixedRadio)

    expect(fixedRadio).toBeChecked()
    expect(randomRadio).not.toBeChecked()
  })

  it('includes seed in submission when fixed seed is selected', async () => {
    const user = userEvent.setup()
    renderForm()

    await user.click(screen.getByLabelText(/fixed/i))

    const seedInput = screen.getByPlaceholderText(/enter seed or generate random/i)
    await user.type(seedInput, '12345')

    const promptInput = screen.getByPlaceholderText(/describe the image/i)
    await user.type(promptInput, 'test prompt')
    await user.click(screen.getByRole('button', { name: /generate image/i }))

    expect(mockOnGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        seed: 12345,
      }),
    )
  })

  it('generates random seed when button is clicked', async () => {
    const user = userEvent.setup()
    renderForm()

    await user.click(screen.getByLabelText(/fixed/i))

    const seedInput = screen.getByPlaceholderText<HTMLInputElement>(/enter seed or generate random/i)
    const randomButton = screen.getByTitle(/generate random seed/i)

    await user.click(randomButton)

    expect(seedInput.value).not.toBe('')
    expect(Number.parseInt(seedInput.value, 10)).toBeGreaterThan(0)
    expect(Number.parseInt(seedInput.value, 10)).toBeLessThanOrEqual(2147483647)
  })

  it('updates steps value when slider is moved', () => {
    renderForm()

    const stepsSlider = screen.getByLabelText(/steps/i)

    fireEvent.change(stepsSlider, { target: { value: '50' } })

    const stepsDisplay = screen.getByText(/steps: 50/i)
    expect(stepsDisplay).toBeInTheDocument()
  })

  it('updates guidance scale when slider is moved', () => {
    renderForm()

    const guidanceSlider = screen.getByLabelText(/guidance scale/i)

    fireEvent.change(guidanceSlider, { target: { value: '12' } })

    const guidanceDisplay = screen.getByText(/guidance scale: 12/i)
    expect(guidanceDisplay).toBeInTheDocument()
  })
})

