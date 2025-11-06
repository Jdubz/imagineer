import { z } from 'zod'
import type { LogEntry } from '../lib/logger'
import * as schemas from '../lib/schemas'
import type {
  BugReportSubmissionRequest,
  BugReportSubmissionResponse as SharedBugReportSubmissionResponse,
} from './shared'

export type BugReportOptions = BugReportSubmissionRequest
export type BugReportSubmissionResponse = SharedBugReportSubmissionResponse

export type BugReportSummary = z.infer<typeof schemas.BugReportSummarySchema>
export type BugReportDetail = z.infer<typeof schemas.BugReportDetailSchema>
export type BugReportListResponse = z.infer<typeof schemas.BugReportListResponseSchema>
export type BugReportDetailResponse = z.infer<typeof schemas.BugReportDetailResponseSchema>

export type BugReportEnvironmentSnapshot = BugReportOptions['environment']
export type ClientMetadataSnapshot = BugReportOptions['clientMeta']
export type NetworkEventSnapshot = BugReportOptions['networkEvents'][number]
export type HeaderSnapshot = NetworkEventSnapshot['requestHeaders'][number]
export type LogSnapshot = BugReportOptions['recentLogs'][number] & LogEntry
