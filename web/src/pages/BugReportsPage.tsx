import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import type { BugReportDetail, BugReportSummary } from '@/types/bugReport'
import Spinner from '@/components/Spinner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { formatErrorMessage } from '@/lib/errorUtils'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface BugReportsPageProps {
  isAdmin?: boolean
}

const statusVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  open: 'secondary',
  triaging: 'secondary',
  investigating: 'default',
  running: 'default',
  completed: 'outline',
  resolved: 'outline',
  closed: 'outline',
  failed: 'destructive',
  rejected: 'destructive',
}

const formatTimestamp = (value?: string | null): string => {
  if (!value) {
    return 'Unknown'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

const getStatusVariant = (status?: string | null) => {
  if (!status) {
    return 'outline' as const
  }
  return statusVariant[status.toLowerCase()] ?? 'outline'
}

const BugReportsPage: React.FC<BugReportsPageProps> = ({ isAdmin = false }) => {
  const { toast } = useToast()
  const [reports, setReports] = useState<BugReportSummary[]>([])
  const [pagination, setPagination] = useState<{ page: number; per_page: number; total: number; pages: number } | null>(
    null,
  )
  const [listError, setListError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState<boolean>(false)
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [detail, setDetail] = useState<BugReportDetail | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false)

  const sortReports = useCallback((items: BugReportSummary[]) => {
    return [...items].sort((a, b) => {
      const aTime = a.submitted_at ? Date.parse(a.submitted_at) : 0
      const bTime = b.submitted_at ? Date.parse(b.submitted_at) : 0
      return bTime - aTime
    })
  }, [])

  const sortedReports = useMemo(() => sortReports(reports), [reports, sortReports])

  const refreshReports = useCallback(async () => {
    if (!isAdmin) {
      setReports([])
      setPagination(null)
      return
    }

    setLoadingList(true)
    try {
      const response = await api.bugReports.list({ perPage: 50 })
      const orderedReports = sortReports(response.reports)
      setReports(orderedReports)
      setPagination(response.pagination)
      setListError(null)

      if (orderedReports.length > 0) {
        setSelectedReportId((current) => {
          if (current) {
            const stillExists = orderedReports.some((report) => report.report_id === current)
            if (stillExists) {
              return current
            }
          }
          return orderedReports[0].report_id
        })
      } else {
        setSelectedReportId(null)
      }
    } catch (error) {
      const message = formatErrorMessage(error, 'Failed to load bug reports')
      setListError(message)
      toast({
        title: 'Unable to load bug reports',
        description: message,
        variant: 'destructive',
      })
    } finally {
      setLoadingList(false)
    }
  }, [isAdmin, sortReports, toast])

  useEffect(() => {
    void refreshReports()
  }, [refreshReports])

  useEffect(() => {
    if (!isAdmin || !selectedReportId) {
      setDetail(null)
      return
    }

    let isActive = true
    setLoadingDetail(true)
    setDetailError(null)

    api.bugReports
      .get(selectedReportId)
      .then((response) => {
        if (!isActive) {
          return
        }
        setDetail(response)
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return
        }
        const message =
          error instanceof ApiError && error.status === 404
            ? 'Bug report not found. It may have been removed.'
            : formatErrorMessage(error, 'Failed to load bug report details')
        setDetailError(message)
        toast({
          title: 'Unable to load bug report',
          description: message,
          variant: 'destructive',
        })
      })
      .finally(() => {
        if (isActive) {
          setLoadingDetail(false)
        }
      })

    return () => {
      isActive = false
    }
  }, [isAdmin, selectedReportId, toast])

  const handleSelect = useCallback((reportId: string) => {
    setSelectedReportId(reportId)
  }, [])

  if (!isAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Bug Reports</CardTitle>
          <CardDescription>Administrator access is required to review submitted bug reports.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sign in with an administrator account to see the stream of submitted bug reports and their current status.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Bug Reports</h2>
          <p className="text-sm text-muted-foreground">
            Review the latest bug submissions, track their status, and inspect diagnostic details.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {pagination ? (
            <span className="text-xs text-muted-foreground">
              Showing {sortedReports.length.toLocaleString()} of {pagination.total.toLocaleString()} total
            </span>
          ) : null}
          <Button variant="outline" onClick={() => void refreshReports()} disabled={loadingList}>
            {loadingList ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>
      </div>

      {listError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load bug reports</AlertTitle>
          <AlertDescription>{listError}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <Card className="min-h-[320px]">
          <CardHeader>
            <CardTitle>Recent Reports</CardTitle>
            <CardDescription>The newest submissions appear first.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loadingList ? (
              <div className="flex h-60 items-center justify-center p-6">
                <Spinner message="Loading bug reports..." />
              </div>
            ) : sortedReports.length === 0 ? (
              <div className="p-6 text-sm text-muted-foreground">No bug reports have been submitted yet.</div>
            ) : (
              <div className="max-h-[480px] overflow-y-auto">
                <ul className="divide-y divide-border">
                  {sortedReports.map((report) => {
                    const isSelected = report.report_id === selectedReportId
                    return (
                      <li key={report.report_id}>
                        <button
                          type="button"
                          onClick={() => handleSelect(report.report_id)}
                          className={cn(
                            'flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors hover:bg-muted/60',
                            isSelected ? 'bg-muted' : 'bg-transparent',
                          )}
                          aria-current={isSelected}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-medium text-foreground">{report.description}</span>
                            <Badge variant={getStatusVariant(report.status)}>{report.status ?? 'UNKNOWN'}</Badge>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span>{formatTimestamp(report.submitted_at)}</span>
                            {report.submitted_by ? <span>• {report.submitted_by}</span> : null}
                            {report.trace_id ? <span>• #{report.trace_id.slice(0, 8)}</span> : null}
                          </div>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-h-[320px]">
          <CardHeader>
            <CardTitle>Report Details</CardTitle>
            <CardDescription>Inspect reproduction steps, attachments, and resolution notes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingDetail ? (
              <div className="flex h-48 items-center justify-center">
                <Spinner message="Loading details..." />
              </div>
            ) : detailError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load report</AlertTitle>
                <AlertDescription>{detailError}</AlertDescription>
              </Alert>
            ) : detail ? (
              <div className="space-y-4">
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-lg font-semibold text-foreground">{detail.description}</h3>
                    <Badge variant={getStatusVariant(detail.status)}>{detail.status ?? 'UNKNOWN'}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Submitted {formatTimestamp(detail.submitted_at)}
                    {detail.submitted_by ? ` by ${detail.submitted_by}` : ''}
                  </p>
                </div>

                {detail.expected_behavior ? (
                  <section>
                    <h4 className="text-sm font-medium text-foreground">Expected</h4>
                    <p className="text-sm text-muted-foreground">{detail.expected_behavior}</p>
                  </section>
                ) : null}

                {detail.actual_behavior ? (
                  <section>
                    <h4 className="text-sm font-medium text-foreground">Actual</h4>
                    <p className="text-sm text-muted-foreground">{detail.actual_behavior}</p>
                  </section>
                ) : null}

                {Array.isArray(detail.steps_to_reproduce) && detail.steps_to_reproduce.length > 0 ? (
                  <section>
                    <h4 className="text-sm font-medium text-foreground">Steps to reproduce</h4>
                    <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
                      {detail.steps_to_reproduce.map((step, index) => (
                        <li key={index}>{typeof step === 'string' ? step : JSON.stringify(step)}</li>
                      ))}
                    </ol>
                  </section>
                ) : null}

                {detail.resolution_notes ? (
                  <section>
                    <h4 className="text-sm font-medium text-foreground">Resolution notes</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{detail.resolution_notes}</p>
                  </section>
                ) : null}

                <section className="rounded-md border border-border/60 bg-muted/40 p-3 text-xs text-muted-foreground">
                  <h4 className="font-medium text-foreground">Metadata</h4>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div>
                      <span className="block font-medium text-foreground">Report ID</span>
                      <span>{detail.report_id}</span>
                    </div>
                    {detail.trace_id ? (
                      <div>
                        <span className="block font-medium text-foreground">Trace ID</span>
                        <span>{detail.trace_id}</span>
                      </div>
                    ) : null}
                    {detail.resolution_commit_sha ? (
                      <div>
                        <span className="block font-medium text-foreground">Resolution commit</span>
                        <span className="font-mono text-xs">{detail.resolution_commit_sha}</span>
                      </div>
                    ) : null}
                    {detail.completed_at ? (
                      <div>
                        <span className="block font-medium text-foreground">Completed</span>
                        <span>{formatTimestamp(detail.completed_at)}</span>
                      </div>
                    ) : null}
                  </div>
                </section>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Select a bug report from the list to view diagnostic information.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default BugReportsPage
