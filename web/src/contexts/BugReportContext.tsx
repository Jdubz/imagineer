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
import html2canvas from 'html2canvas'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'

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
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [screenshotError, setScreenshotError] = useState<string | null>(null)
  const [isCapturingScreenshot, setIsCapturingScreenshot] = useState(false)

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

  const captureScreenshot = useCallback(async (): Promise<string | null> => {
    setIsCapturingScreenshot(true)
    setScreenshotError(null)

    try {
      // Wait a brief moment to ensure modal is hidden
      await new Promise((resolve) => setTimeout(resolve, 100))

      const canvas = await html2canvas(document.body, {
        allowTaint: true,
        useCORS: true,
        logging: false,
        scale: 0.5, // Reduce size for faster capture and smaller file size
      })

      const dataUrl = canvas.toDataURL('image/png', 0.8)
      return dataUrl
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      logger.error('Failed to capture screenshot', error as Error)
      setScreenshotError(`Screenshot capture failed: ${errorMessage}`)
      return null
    } finally {
      setIsCapturingScreenshot(false)
    }
  }, [])

  const openBugReport = useCallback(
    async (options?: { description?: string }) => {
      if (options?.description) {
        setPrefilledDescription(options.description)
      } else {
        setPrefilledDescription(undefined)
      }

      // Reset screenshot state
      setScreenshot(null)
      setScreenshotError(null)

      // Capture screenshot BEFORE opening modal so modal isn't visible
      const capturedScreenshot = await captureScreenshot()
      if (capturedScreenshot) {
        setScreenshot(capturedScreenshot)
      }

      // Now open the modal with the screenshot ready
      setIsOpen(true)
    },
    [captureScreenshot],
  )

  const closeBugReport = useCallback(() => {
    setIsOpen(false)
    setPrefilledDescription(undefined)
    setScreenshot(null)
    setScreenshotError(null)
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
    async (description: string, includeScreenshot: boolean, annotatedScreenshot?: string) => {
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

        // Include screenshot data if enabled
        let screenshotToSubmit: string | null = null
        if (includeScreenshot) {
          screenshotToSubmit = annotatedScreenshot || screenshot
          if (screenshotError) {
            // Record screenshot failure in the payload
            payload.screenshotError = screenshotError
          }
        }

        const response: BugReportSubmissionResponse = await api.bugReports.submit(payload, screenshotToSubmit)

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
    [collectAppState, closeBugReport, logs, networkEvents, screenshot, screenshotError, snapshotClient, snapshotEnvironment, toast],
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
            screenshot={screenshot}
            screenshotError={screenshotError}
            isCapturingScreenshot={isCapturingScreenshot}
          />,
          document.body,
        )}
    </BugReportContext.Provider>
  )
}

interface BugReportModalProps {
  isSubmitting: boolean
  onClose: () => void
  onSubmit: (description: string, includeScreenshot: boolean, annotatedScreenshot?: string) => Promise<void>
  recentLogCount: number
  networkEventCount: number
  defaultDescription?: string
  screenshot: string | null
  screenshotError: string | null
  isCapturingScreenshot: boolean
}

const BugReportModal: React.FC<BugReportModalProps> = ({
  isSubmitting,
  onClose,
  onSubmit,
  recentLogCount,
  networkEventCount,
  defaultDescription,
  screenshot,
  screenshotError,
  isCapturingScreenshot,
}) => {
  const [description, setDescription] = useState(defaultDescription ?? '')
  const [error, setError] = useState<string | null>(null)
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const [isAnnotating, setIsAnnotating] = useState(false)
  const [annotatedScreenshot, setAnnotatedScreenshot] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)

  useEffect(() => {
    setDescription(defaultDescription ?? '')
  }, [defaultDescription])

  // Load screenshot into canvas when annotation mode is enabled
  useEffect(() => {
    if (isAnnotating && screenshot && canvasRef.current) {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const img = new Image()
      img.onload = () => {
        canvas.width = img.width
        canvas.height = img.height
        ctx.drawImage(img, 0, 0)
      }
      img.src = screenshot
    }
  }, [isAnnotating, screenshot])

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isAnnotating || !canvasRef.current) return
    setIsDrawing(true)
    const rect = canvasRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvasRef.current.width / rect.width)
    const y = (e.clientY - rect.top) * (canvasRef.current.height / rect.height)

    const ctx = canvasRef.current.getContext('2d')
    if (ctx) {
      ctx.beginPath()
      ctx.moveTo(x, y)
      ctx.strokeStyle = '#ff0000'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvasRef.current.width / rect.width)
    const y = (e.clientY - rect.top) * (canvasRef.current.height / rect.height)

    const ctx = canvasRef.current.getContext('2d')
    if (ctx) {
      ctx.lineTo(x, y)
      ctx.stroke()
    }
  }

  const handleMouseUp = () => {
    if (isDrawing && canvasRef.current) {
      setIsDrawing(false)
      // Save the annotated screenshot
      setAnnotatedScreenshot(canvasRef.current.toDataURL('image/png'))
    }
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = description.trim()
    if (trimmed.length === 0) {
      setError('Please describe what happened so we can troubleshoot.')
      return
    }
    setError(null)
    await onSubmit(trimmed, includeScreenshot, annotatedScreenshot || undefined)
  }

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-2xl">Report a Bug</DialogTitle>
            <DialogDescription className="text-base leading-relaxed">
              We'll automatically attach the latest {networkEventCount} network requests and{' '}
              {recentLogCount} log entries to help with troubleshooting.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="bug-report-description" className="font-semibold">
                What went wrong?
              </Label>
              <Textarea
                id="bug-report-description"
                placeholder="Tell us what you were trying to do and what happened."
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                minLength={10}
                maxLength={4000}
                disabled={isSubmitting}
                required
                className="min-h-[160px] resize-y"
              />
              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            {/* Screenshot Section */}
            <div className="space-y-2 border-t pt-4">
              <div className="flex items-center justify-between">
                <Label className="font-semibold">Screenshot</Label>
                {isCapturingScreenshot && (
                  <span className="text-sm text-muted-foreground">Capturing...</span>
                )}
              </div>

              {screenshotError && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                  <p className="text-sm text-destructive">{screenshotError}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    The report will still be submitted without a screenshot.
                  </p>
                </div>
              )}

              {screenshot && !screenshotError && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="include-screenshot"
                      checked={includeScreenshot}
                      onCheckedChange={(checked: boolean) => setIncludeScreenshot(checked === true)}
                    />
                    <Label
                      htmlFor="include-screenshot"
                      className="text-sm font-normal cursor-pointer"
                    >
                      Include screenshot with bug report
                    </Label>
                  </div>

                  {includeScreenshot && (
                    <>
                      {!isAnnotating ? (
                        <div className="space-y-2">
                          <img
                            src={screenshot}
                            alt="Screenshot preview"
                            className="w-full border rounded-md"
                            style={{ maxHeight: '300px', objectFit: 'contain' }}
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => setIsAnnotating(true)}
                          >
                            ✏️ Add Annotations
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="border rounded-md overflow-auto max-h-[600px]">
                            <canvas
                              ref={canvasRef}
                              onMouseDown={handleMouseDown}
                              onMouseMove={handleMouseMove}
                              onMouseUp={handleMouseUp}
                              onMouseLeave={handleMouseUp}
                              className="cursor-crosshair"
                              style={{ display: 'block', width: '100%', height: 'auto' }}
                            />
                          </div>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setIsAnnotating(false)
                                setAnnotatedScreenshot(null)
                              }}
                            >
                              Cancel Annotations
                            </Button>
                            <Button
                              type="button"
                              variant="default"
                              size="sm"
                              onClick={() => setIsAnnotating(false)}
                            >
                              Done Annotating
                            </Button>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Click and drag to draw red annotations highlighting the issue
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {!screenshot && !screenshotError && !isCapturingScreenshot && (
                <p className="text-sm text-muted-foreground">No screenshot available</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving…' : 'Submit Report'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
