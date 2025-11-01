import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'
import { logger, type LogEntry } from '../lib/logger'
import { useToast } from '../hooks/use-toast'
import type {
  BugReportEnvironmentSnapshot,
  BugReportOptions,
  BugReportSubmissionResponse,
  ClientMetadataSnapshot,
  LogSnapshot,
  NetworkEventSnapshot,
} from '../types/bugReport'
import { api } from '../lib/api'
import '../styles/BugReport.css'

type CollectorResult =
  | Record<string, unknown>
  | Array<unknown>
  | string
  | number
  | boolean
  | null
  | void

type BugReportCollectorFn = () => CollectorResult | Promise<CollectorResult>

interface BugReportCollector {
  name: string
  collect: () => Promise<CollectorResult>
}

interface BugReportContextValue {
  openBugReport: (options?: { description?: string }) => void
  registerCollector: (name: string, collector: BugReportCollectorFn) => () => void
}

const BugReportContext = createContext<BugReportContextValue | undefined>(undefined)

const MAX_NETWORK_EVENTS = 50
const MAX_LOG_ENTRIES = 200
const MAX_BODY_LENGTH = 4096
const MAX_SERIALIZATION_DEPTH = 4
const MAX_SERIALIZATION_PROPS = 25
const MAX_SERIALIZATION_ARRAY = 25

interface BugReportProviderProps {
  children: React.ReactNode
}

const generateId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `id_${Math.random().toString(36).slice(2)}`
}

const toHeaderSnapshots = (headers: HeadersInit | undefined): Array<{ name: string; value: string }> => {
  const snapshots: Array<{ name: string; value: string }> = []
  if (!headers) {
    return snapshots
  }

  if (headers instanceof Headers) {
    headers.forEach((value, name) => snapshots.push({ name, value }))
    return snapshots
  }

  if (Array.isArray(headers)) {
    for (const [name, value] of headers) {
      snapshots.push({ name, value })
    }
    return snapshots
  }

  for (const [name, value] of Object.entries(headers)) {
    snapshots.push({ name, value: String(value) })
  }

  return snapshots
}

const shouldCaptureBody = (contentType: string | null): boolean => {
  if (!contentType) {
    return false
  }
  const lowered = contentType.toLowerCase()
  return (
    lowered.includes('application/json') ||
    lowered.includes('text/') ||
    lowered.includes('application/problem+json') ||
    lowered.includes('application/vnd.api+json')
  )
}

const truncateBody = (body?: string | null): string | null => {
  if (!body) {
    return null
  }
  if (body.length <= MAX_BODY_LENGTH) {
    return body
  }
  return `${body.slice(0, MAX_BODY_LENGTH)}…`
}

const serializeError = (error: unknown): string => {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`
  }
  return typeof error === 'string' ? error : JSON.stringify(error, null, 2)
}

const toSerializable = (
  value: unknown,
  depth = 0,
  seen: WeakSet<object> = new WeakSet(),
): unknown => {
  if (value == null) {
    return value
  }

  if (depth > MAX_SERIALIZATION_DEPTH) {
    return '[Truncated]'
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value
  }

  if (value instanceof Date) {
    return value.toISOString()
  }

  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: value.stack,
    }
  }

  if (Array.isArray(value)) {
    return value.slice(0, MAX_SERIALIZATION_ARRAY).map((item) =>
      toSerializable(item, depth + 1, seen),
    )
  }

  if (value && typeof value === 'object') {
    if (seen.has(value)) {
      return '[Circular]'
    }
    seen.add(value)
    const entries = Object.entries(value as Record<string, unknown>).slice(
      0,
      MAX_SERIALIZATION_PROPS,
    )
    const result: Record<string, unknown> = {}
    for (const [key, val] of entries) {
      result[key] = toSerializable(val, depth + 1, seen)
    }
    return result
  }

  return String(value)
}

const serializeLogEntry = (entry: LogEntry): LogSnapshot => ({
  ...entry,
  serializedArgs: entry.args.map((arg) => toSerializable(arg)),
})

export const BugReportProvider: React.FC<BugReportProviderProps> = ({ children }) => {
  const { toast } = useToast()
  const [isOpen, setIsOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [prefilledDescription, setPrefilledDescription] = useState<string | undefined>(undefined)

  const collectorsRef = useRef<Map<string, BugReportCollector>>(new Map())
  const [logs, setLogs] = useState<LogSnapshot[]>([])
  const [networkEvents, setNetworkEvents] = useState<NetworkEventSnapshot[]>([])

  const addLogEntry = useCallback((entry: LogEntry) => {
    setLogs((prev) => {
      const next = [serializeLogEntry(entry), ...prev]
      if (next.length > MAX_LOG_ENTRIES) {
        return next.slice(0, MAX_LOG_ENTRIES)
      }
      return next
    })
  }, [])

  useEffect(() => {
    const unsubscribe = logger.addListener(addLogEntry)
    return unsubscribe
  }, [addLogEntry])

  const pushNetworkEvent = useCallback((event: NetworkEventSnapshot) => {
    setNetworkEvents((prev) => {
      const next = [event, ...prev]
      if (next.length > MAX_NETWORK_EVENTS) {
        return next.slice(0, MAX_NETWORK_EVENTS)
      }
      return next
    })
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.fetch !== 'function') {
      return
    }

    const originalFetch = window.fetch.bind(window)

    const instrumentedFetch: typeof window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const requestId = generateId()
      const startedAt = new Date().toISOString()
      const meta = normalizeRequestInfo(input, init)
      const startTime = performance.now()

      try {
        const response = await originalFetch(input, init)
        const durationMs = performance.now() - startTime
        const traceId = response.headers?.get?.('X-Trace-Id') ?? null

        let responseBody: string | null = null
        try {
          if (shouldCaptureBody(response.headers?.get?.('content-type') ?? null)) {
            const clone = response.clone()
            responseBody = truncateBody(await clone.text())
          }
        } catch {
          responseBody = null
        }

        pushNetworkEvent({
          id: requestId,
          method: meta.method,
          url: meta.url,
          started_at: startedAt,
          completed_at: new Date().toISOString(),
          duration_ms: Math.round(durationMs),
          status: response.status,
          ok: response.ok,
          trace_id: traceId,
          requestHeaders: meta.headers,
          responseHeaders: toHeaderSnapshots(response.headers),
          requestBody: meta.body,
          responseBody,
        })

        return response
      } catch (error) {
        const durationMs = performance.now() - startTime
        pushNetworkEvent({
          id: requestId,
          method: meta.method,
          url: meta.url,
          started_at: startedAt,
          completed_at: new Date().toISOString(),
          duration_ms: Math.round(durationMs),
          trace_id: null,
          status: undefined,
          ok: false,
          requestHeaders: meta.headers,
          responseHeaders: [],
          requestBody: meta.body,
          responseBody: null,
          error: serializeError(error),
        })
        throw error
      }
    }

    window.fetch = instrumentedFetch

    return () => {
      window.fetch = originalFetch
    }
  }, [pushNetworkEvent])

  const registerCollector = useCallback(
    (name: string, collector: BugReportCollectorFn) => {
      const key = `${name}:${generateId()}`
      collectorsRef.current.set(key, {
        name,
        collect: () => Promise.resolve(collector()),
      })

      return () => {
        collectorsRef.current.delete(key)
      }
    },
    [],
  )

  const openBugReport = useCallback(
    (options?: { description?: string }) => {
      if (options?.description) {
        setPrefilledDescription(options.description)
      } else {
        setPrefilledDescription(undefined)
      }
      setIsOpen(true)
    },
    [],
  )

  const closeBugReport = useCallback(() => {
    setIsOpen(false)
    setPrefilledDescription(undefined)
  }, [])

  const snapshotEnvironment = useCallback((): BugReportEnvironmentSnapshot => {
    return {
      mode: import.meta.env.MODE,
      appVersion: import.meta.env.VITE_APP_VERSION ?? null,
      gitSha: import.meta.env.VITE_GIT_SHA ?? null,
      buildTime: import.meta.env.VITE_BUILD_TIME ?? null,
    }
  }, [])

  const snapshotClient = useCallback((): ClientMetadataSnapshot => {
    if (typeof window === 'undefined') {
      return {
        locationHref: '',
      }
    }

    return {
      locationHref: window.location.href,
      userAgent: window.navigator.userAgent,
      platform: window.navigator.platform,
      language: window.navigator.language,
      locale: window.navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    }
  }, [])

  const collectAppState = useCallback(async (): Promise<Record<string, unknown>> => {
    const state: Record<string, unknown> = {}
    const collectors = Array.from(collectorsRef.current.values())

    await Promise.all(
      collectors.map(async ({ name, collect }) => {
        try {
          const value = await collect()
          state[name] = toSerializable(value)
        } catch (error) {
          state[name] = {
            error: serializeError(error),
          }
        }
      }),
    )

    return state
  }, [])

  const handleSubmit = useCallback(
    async (description: string) => {
      setIsSubmitting(true)

      try {
        const payload: BugReportOptions = {
          description,
          environment: snapshotEnvironment(),
          clientMeta: snapshotClient(),
          appState: await collectAppState(),
          recentLogs: logs.map((entry) => ({
            ...entry,
            serializedArgs: entry.serializedArgs,
          })),
          networkEvents,
        }

        const response: BugReportSubmissionResponse = await api.bugReports.submit(payload)

        toast({ title: 'Success', description: 'Bug report saved for review. Thank you!' })
        logger.info('Bug report submitted', response)
        closeBugReport()
      } catch (error) {
        logger.error('Failed to submit bug report', error as Error)
        toast({ title: 'Error', description: 'Failed to submit bug report. Please try again.', variant: 'destructive' })
      } finally {
        setIsSubmitting(false)
      }
    },
    [collectAppState, closeBugReport, logs, networkEvents, snapshotClient, snapshotEnvironment, toast],
  )

  const contextValue = useMemo<BugReportContextValue>(
    () => ({
      openBugReport,
      registerCollector,
    }),
    [openBugReport, registerCollector],
  )

  return (
    <BugReportContext.Provider value={contextValue}>
      {children}
      {isOpen &&
        createPortal(
          <BugReportModal
            isSubmitting={isSubmitting}
            onClose={closeBugReport}
            onSubmit={handleSubmit}
            recentLogCount={logs.length}
            networkEventCount={networkEvents.length}
            defaultDescription={prefilledDescription}
          />,
          document.body,
        )}
    </BugReportContext.Provider>
  )
}

interface BugReportModalProps {
  isSubmitting: boolean
  onClose: () => void
  onSubmit: (description: string) => Promise<void>
  recentLogCount: number
  networkEventCount: number
  defaultDescription?: string
}

const BugReportModal: React.FC<BugReportModalProps> = ({
  isSubmitting,
  onClose,
  onSubmit,
  recentLogCount,
  networkEventCount,
  defaultDescription,
}) => {
  const [description, setDescription] = useState(defaultDescription ?? '')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDescription(defaultDescription ?? '')
  }, [defaultDescription])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = description.trim()
    if (trimmed.length === 0) {
      setError('Please describe what happened so we can troubleshoot.')
      return
    }
    setError(null)
    await onSubmit(trimmed)
  }

  return (
    <div className="bug-report-backdrop" role="presentation">
      <div
        className="bug-report-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bug-report-title"
      >
        <form onSubmit={handleSubmit} className="bug-report-form">
          <header className="bug-report-header">
            <h2 id="bug-report-title">Report a Bug</h2>
            <p>
              We’ll automatically attach the latest {networkEventCount} network requests and{' '}
              {recentLogCount} log entries to help with troubleshooting.
            </p>
          </header>

          <label className="bug-report-label" htmlFor="bug-report-description">
            What went wrong?
          </label>
          <textarea
            id="bug-report-description"
            className="bug-report-textarea"
            placeholder="Tell us what you were trying to do and what happened."
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            minLength={10}
            maxLength={4000}
            disabled={isSubmitting}
            required
          />
          {error ? <p className="bug-report-error">{error}</p> : null}

          <div className="bug-report-actions">
            <button
              type="button"
              className="bug-report-button bug-report-button--secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bug-report-button bug-report-button--primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving…' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const normalizeRequestInfo = (
  input: RequestInfo | URL,
  init?: RequestInit,
): { url: string; method: string; headers: Array<{ name: string; value: string }>; body: string | null } => {
  let url: string
  let method = init?.method ?? 'GET'
  let headers: HeadersInit | undefined = init?.headers
  let body: string | null = null

  if (typeof input === 'string' || input instanceof URL) {
    url = input.toString()
  } else if (input instanceof Request) {
    url = input.url
    method = input.method || method
    headers = init?.headers ?? input.headers
    if (init?.body && typeof init.body === 'string') {
      body = truncateBody(init.body)
    }
  } else {
    url = String(input)
  }

  if (init?.body && typeof init.body === 'string') {
    body = truncateBody(init.body)
  } else if (init?.body instanceof URLSearchParams) {
    body = truncateBody(init.body.toString())
  } else if (init?.body instanceof FormData) {
    const entries: string[] = []
    init.body.forEach((value, key) => {
      entries.push(`${key}=${typeof value === 'string' ? value : '[binary]'}`)
    })
    body = truncateBody(entries.join('&'))
  }

  const headerSnapshots = toHeaderSnapshots(headers)

  return {
    url,
    method,
    headers: headerSnapshots,
    body,
  }
}

export const useBugReporter = (): BugReportContextValue => {
  const context = useContext(BugReportContext)
  if (!context) {
    throw new Error('useBugReporter must be used within a BugReportProvider')
  }
  return context
}
