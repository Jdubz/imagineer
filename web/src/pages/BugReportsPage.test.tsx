import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BugReportsPage from './BugReportsPage'
import type { BugReportDetail, BugReportSummary } from '@/types/bugReport'

const mockToast = vi.fn()

const MockApiError = vi.hoisted(
  () =>
    class MockApiError extends Error {
      status?: number
      constructor(message: string, status?: number) {
        super(message)
        if (status) {
          this.status = status
        }
      }
    },
)

const { mockList, mockGet } = vi.hoisted(() => ({
  mockList: vi.fn<
    [],
    Promise<{
      reports: BugReportSummary[]
      pagination: { page: number; per_page: number; total: number; pages: number }
    }>
  >(),
  mockGet: vi.fn<[string], Promise<BugReportDetail>>(),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    bugReports: {
      list: mockList,
      get: mockGet,
      submit: vi.fn(),
    },
  },
  ApiError: MockApiError,
}))

const baseSummary: BugReportSummary = {
  report_id: '1',
  description: 'Example',
  status: 'open',
  submitted_at: '2025-11-05T00:00:00Z',
  submitted_by: 'admin@example.com',
  trace_id: 'trace-1',
  automation_attempts: 0,
  screenshot_path: null,
  screenshot_error: null,
  resolution_notes: null,
  resolution_commit_sha: null,
  resolution_actor_id: null,
  created_at: '2025-11-05T00:00:00Z',
  completed_at: null,
  expected_behavior: null,
  actual_behavior: null,
  steps_to_reproduce: [],
}

const detailFromSummary = (summary: BugReportSummary): BugReportDetail => ({
  ...summary,
  environment: {},
  client_meta: {},
  app_state: {},
  recent_logs: [],
  network_events: [],
  events: [],
})

describe('BugReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders latest bug report details by default', async () => {
    const newerReport: BugReportSummary = {
      ...baseSummary,
      report_id: 'newer',
      description: 'Latest failure on login',
      status: 'open',
      submitted_at: '2025-11-06T10:30:00Z',
    }
    const olderReport: BugReportSummary = {
      ...baseSummary,
      report_id: 'older',
      description: 'Background job timeout',
      status: 'completed',
      submitted_at: '2025-11-04T08:00:00Z',
    }

    mockList.mockResolvedValue({
      reports: [newerReport, olderReport],
      pagination: { page: 1, per_page: 50, total: 2, pages: 1 },
    })
    mockGet.mockImplementation((reportId: string) =>
      Promise.resolve(
        reportId === 'newer' ? detailFromSummary(newerReport) : detailFromSummary(olderReport),
      ),
    )

    render(<BugReportsPage isAdmin />)

    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(mockGet).toHaveBeenCalledWith('newer')

    const titles = await screen.findAllByText('Latest failure on login')
    expect(titles.length).toBeGreaterThan(0)
  })

  it('loads report details when another report is selected', async () => {
    const reports: BugReportSummary[] = [
      {
        ...baseSummary,
        report_id: 'first',
        description: 'First report',
        submitted_at: '2025-11-06T09:00:00Z',
      },
      {
        ...baseSummary,
        report_id: 'second',
        description: 'Second report',
        submitted_at: '2025-11-05T09:00:00Z',
      },
    ]

    mockList.mockResolvedValue({
      reports,
      pagination: { page: 1, per_page: 50, total: 2, pages: 1 },
    })
    mockGet.mockImplementation((reportId: string) => {
      const match = reports.find((r) => r.report_id === reportId)
      if (!match) {
        throw new Error(`Unknown report id ${reportId}`)
      }
      return Promise.resolve(detailFromSummary(match))
    })

    const user = userEvent.setup()
    render(<BugReportsPage isAdmin />)

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('first'))

    const secondButton = await screen.findByRole('button', { name: /Second report/i })
    await user.click(secondButton)

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('second'))
    const headings = await screen.findAllByRole('heading', { level: 3, name: 'Second report' })
    expect(headings.length).toBeGreaterThan(0)
  })
})
