import type { JobStatus } from '@/types/models'

const STATUS_COLORS: Record<string, string> = {
  pending: '#f39c12',
  queued: '#f39c12',
  running: '#3498db',
  active: '#3498db',
  completed: '#27ae60',
  success: '#27ae60',
  failed: '#e74c3c',
  error: '#e74c3c',
  cancelled: '#95a5a6',
  canceled: '#95a5a6',
  cleaned_up: '#7f8c8d',
}

/**
 * Clamp a numeric value to the 0-100 range commonly used for progress bars.
 * Returns undefined when the input is not a finite number.
 */
export function clampPercent(value: number | null | undefined): number | undefined {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return undefined
  }
  return Math.min(100, Math.max(0, value))
}

/**
 * Clamp a numeric value to the 0-100 range returning a fallback when the value
 * is not provided.
 */
export function clampPercentOrDefault(
  value: number | null | undefined,
  defaultValue = 0,
): number {
  return clampPercent(value) ?? defaultValue
}

/**
 * Format gigabyte values with helpful precision.
 */
export function formatGigabytes(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'N/A'
  }
  const fractionDigits = value < 10 ? 1 : 0
  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: 1,
  })} GB`
}

/**
 * Map job status strings to consistent semantic colours for admin dashboards.
 */
export function getJobStatusColor(status: JobStatus | null | undefined): string {
  if (!status) {
    return '#95a5a6'
  }
  return STATUS_COLORS[status] ?? '#95a5a6'
}
