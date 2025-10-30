import { describe, expect, it } from 'vitest'

import { JobSchema } from './schemas'

describe('JobSchema', () => {
  it('accepts numeric ids from the backend contract', () => {
    const job = JobSchema.parse({
      id: 42,
      status: 'queued',
      prompt: 'test prompt',
      submitted_at: new Date().toISOString(),
    })

    expect(job.id).toBe(42)
  })

  it('rejects string ids to prevent schema drift', () => {
    expect(() =>
      JobSchema.parse({
        id: 'job-99',
        status: 'running',
        prompt: 'another prompt',
        submitted_at: new Date().toISOString(),
      })
    ).toThrowError(/expected number/i)
  })
})
