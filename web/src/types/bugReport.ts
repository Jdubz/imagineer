import type { LogEntry } from '../lib/logger'

export interface BugReportOptions {
  description: string
  environment: BugReportEnvironmentSnapshot
  appState: Record<string, unknown>
  recentLogs: Array<LogSnapshot>
  networkEvents: Array<NetworkEventSnapshot>
  clientMeta: ClientMetadataSnapshot
}

export interface BugReportSubmissionResponse {
  success: boolean
  report_id: string
  trace_id: string
  stored_at?: string
}

export interface LogSnapshot extends LogEntry {
  serializedArgs: unknown[]
}

export interface HeaderSnapshot {
  name: string
  value: string
}

export interface NetworkEventSnapshot {
  id: string
  method: string
  url: string
  started_at: string
  completed_at?: string
  duration_ms?: number
  status?: number
  ok?: boolean
  trace_id?: string | null
  requestHeaders: HeaderSnapshot[]
  responseHeaders: HeaderSnapshot[]
  requestBody?: string | null
  responseBody?: string | null
  error?: string
}

export interface BugReportEnvironmentSnapshot {
  appVersion?: string | null
  mode: string
  gitSha?: string | null
  buildTime?: string | null
}

export interface ClientMetadataSnapshot {
  locale?: string
  userAgent?: string
  platform?: string
  language?: string
  timezone?: string
  viewport?: { width: number; height: number }
  locationHref: string
}
