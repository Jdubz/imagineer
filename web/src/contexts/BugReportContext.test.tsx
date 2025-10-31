import React, { useEffect } from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { SpyInstance } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { BugReportProvider, useBugReporter } from './BugReportContext'
import type { BugReportOptions, BugReportSubmissionResponse } from '../types/bugReport'
import { logger } from '../lib/logger'

const mocks = vi.hoisted(() => ({
  toast: vi.fn(),
  submit: vi.fn<[BugReportOptions], Promise<BugReportSubmissionResponse>>(),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mocks.toast,
    dismiss: vi.fn(),
    toasts: [],
  }),
}))

vi.mock('../lib/api', () => ({
  api: {
    bugReports: {
      submit: mocks.submit,
    },
  },
}))

let fetchSpy: SpyInstance

const setupFetch = (): void => {
  const response = new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'X-Trace-Id': 'abc-123',
    },
  })

  fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response.clone())
}

const CollectorComponent: React.FC = () => {
  const { openBugReport, registerCollector } = useBugReporter()

  useEffect(() => {
    return registerCollector('custom_state', () => ({ foo: 'bar' }))
  }, [registerCollector])

  return (
    <button type="button" onClick={() => openBugReport({ description: 'Preset description' })}>
      Open Bug Report
    </button>
  )
}

const renderWithProvider = (ui: React.ReactElement): void => {
  render(<BugReportProvider>{ui}</BugReportProvider>)
}

describe('BugReportProvider', () => {
  beforeEach(() => {
    mocks.submit.mockReset()
    mocks.toast.mockReset()
    setupFetch()
  })

  afterEach(() => {
    fetchSpy?.mockRestore()
  })

  it('opens the modal with a prefilled description when openBugReport is invoked', async () => {
    const user = userEvent.setup()

    renderWithProvider(<CollectorComponent />)

    await user.click(screen.getByRole('button', { name: /open bug report/i }))

    const modal = await screen.findByRole('dialog', { name: /report a bug/i })
    expect(modal).toBeInTheDocument()

    const textarea = screen.getByLabelText<HTMLTextAreaElement>(/what went wrong/i)
    expect(textarea.value).toBe('Preset description')
  })

  it('submits a bug report with collected application state, logs, and network activity', async () => {
    const user = userEvent.setup()
    mocks.submit.mockResolvedValue({
      success: true,
      report_id: 'bug_123',
      trace_id: 'trace-123',
      stored_at: '/tmp/bug.json',
    })

    renderWithProvider(<CollectorComponent />)

    logger.info('first log entry')

    await user.click(screen.getByRole('button', { name: /open bug report/i }))

    await fetch('/api/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer token' },
      body: JSON.stringify({ foo: 'bar' }),
    })

    const textarea = await screen.findByLabelText<HTMLTextAreaElement>(/what went wrong/i)
    await user.clear(textarea)
    await user.type(textarea, 'New description')

    await user.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => expect(mocks.submit).toHaveBeenCalledTimes(1))

    const [payload] = mocks.submit.mock.calls[0]
    expect(payload.description).toBe('New description')
    expect(payload.appState).toHaveProperty('custom_state', { foo: 'bar' })
    expect(payload.recentLogs.length).toBeGreaterThan(0)
    expect(payload.networkEvents.length).toBeGreaterThan(0)

    expect(mocks.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        description: expect.stringMatching(/saved/i),
      })
    )
  })
})
