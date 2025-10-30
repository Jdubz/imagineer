import type { LogEntry } from '../lib/logger'
import type {
  BugReportSubmissionRequest,
  BugReportSubmissionResponse as SharedBugReportSubmissionResponse,
} from './shared'

export type BugReportOptions = BugReportSubmissionRequest
export type BugReportSubmissionResponse = SharedBugReportSubmissionResponse

export type BugReportEnvironmentSnapshot = BugReportOptions['environment']
export type ClientMetadataSnapshot = BugReportOptions['clientMeta']
export type NetworkEventSnapshot = BugReportOptions['networkEvents'][number]
export type HeaderSnapshot = NetworkEventSnapshot['requestHeaders'][number]
export type LogSnapshot = BugReportOptions['recentLogs'][number] & LogEntry
