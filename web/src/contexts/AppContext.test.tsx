import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { AppProvider, useApp } from './AppContext'

const mockRegisterCollector = vi.hoisted(() => vi.fn(() => vi.fn()))
const mockGetConfig = vi.hoisted(() => vi.fn())
const mockImagesGetAll = vi.hoisted(() => vi.fn())
const mockBatchesGetAll = vi.hoisted(() => vi.fn())

mockGetConfig.mockResolvedValue(null)
mockImagesGetAll.mockResolvedValue([])
mockBatchesGetAll.mockResolvedValue([])

vi.mock('./AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'admin@example.com', role: 'admin', authenticated: true },
    loading: false,
    checkAuth: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
  }),
}))

vi.mock('./BugReportContext', () => ({
  useBugReporter: () => ({
    openBugReport: vi.fn(),
    registerCollector: mockRegisterCollector,
  }),
}))

vi.mock('../lib/api', () => ({
  api: {
    getConfig: mockGetConfig,
    submitJob: vi.fn(),
    getJob: vi.fn(),
    images: {
      getAll: mockImagesGetAll,
    },
    batches: {
      getAll: mockBatchesGetAll,
    },
  },
}))

const NSFW_STORAGE_KEY = 'imagineer.nsfwPreference'

const PreferenceProbe: React.FC = () => {
  const { nsfwPreference, setNsfwPreference } = useApp()

  return (
    <div>
      <span data-testid="nsfw-pref">{nsfwPreference}</span>
      <button type="button" onClick={() => setNsfwPreference('blur')}>
        Make Blur
      </button>
    </div>
  )
}

const renderPreferenceProbe = async () => {
  const utils = render(
    <AppProvider>
      <PreferenceProbe />
    </AppProvider>
  )

  await waitFor(() => {
    expect(mockGetConfig).toHaveBeenCalled()
    expect(mockImagesGetAll).toHaveBeenCalled()
    expect(mockBatchesGetAll).toHaveBeenCalled()
  })

  return utils
}

describe('AppContext NSFW preference', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockGetConfig.mockResolvedValue(null)
    mockImagesGetAll.mockResolvedValue([])
    mockBatchesGetAll.mockResolvedValue([])
  })

  it('defaults to "show" when no stored preference exists', async () => {
    await renderPreferenceProbe()

    expect(screen.getByTestId('nsfw-pref').textContent).toBe('show')
    return waitFor(() => {
      expect(localStorage.getItem(NSFW_STORAGE_KEY)).toBe('show')
    })
  })

  it('persists updates to localStorage and re-renders with new preference', async () => {
    const user = userEvent.setup()

    await renderPreferenceProbe()

    const button = screen.getByRole('button', { name: /make blur/i })
    await user.click(button)

    // Wait for both the UI update and localStorage write
    await waitFor(() => {
      expect(screen.getByTestId('nsfw-pref').textContent).toBe('blur')
      expect(localStorage.getItem(NSFW_STORAGE_KEY)).toBe('blur')
    })
  })

  it('initialises from a stored preference value', async () => {
    localStorage.setItem(NSFW_STORAGE_KEY, 'hide')

    await renderPreferenceProbe()

    expect(screen.getByTestId('nsfw-pref').textContent).toBe('hide')
  })

  it('falls back to "show" when storage contains an unknown value', async () => {
    localStorage.setItem(NSFW_STORAGE_KEY, 'invalid')

    await renderPreferenceProbe()

    expect(screen.getByTestId('nsfw-pref').textContent).toBe('show')
    return waitFor(() => {
      expect(localStorage.getItem(NSFW_STORAGE_KEY)).toBe('show')
    })
  })
})
