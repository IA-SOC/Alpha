import { describe, expect, it } from 'vitest'

import { formatUtc, formatUtcRange } from './format'

describe('formatUtc', () => {
  it('shows any offset in UTC', () => {
    expect(formatUtc('2026-10-09T07:02:00-05:00')).toBe('2026-10-09 12:02:00 UTC')
  })

  it('reads a time with no offset as UTC, not local time', () => {
    expect(formatUtc('2026-10-09T12:00:00')).toBe('2026-10-09 12:00:00 UTC')
    expect(formatUtc('2026-10-09T12:00:00.250')).toBe('2026-10-09 12:00:00 UTC')
  })

  it('leaves what it cannot read as it came', () => {
    expect(formatUtc('yesterday')).toBe('yesterday')
    expect(formatUtc(null)).toBeUndefined()
  })
})

describe('formatUtcRange', () => {
  it('drops the repeated date inside one day', () => {
    expect(formatUtcRange('2026-10-09T12:00:00Z', '2026-10-09T12:03:00Z')).toEqual({ from: '2026-10-09 12:00:00', to: '12:03:00 UTC' })
    expect(formatUtcRange('2026-10-09T23:59:00Z', '2026-10-10T00:01:00Z')).toEqual({ from: '2026-10-09 23:59:00', to: '2026-10-10 00:01:00 UTC' })
  })
})
