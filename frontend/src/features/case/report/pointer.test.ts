import { describe, expect, it } from 'vitest'

import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { resolvePointer, sameValue } from './pointer'

describe('resolvePointer', () => {
  it('resolves the paths the agent cites in the demo case', () => {
    expect(resolvePointer(sampleCase, '/alerts/0/raw_alert/event/action')).toEqual({ found: true, value: 'failed_login' })
    expect(resolvePointer(sampleCase, '/alerts/1/raw_alert/rule/level')).toEqual({ found: true, value: 8 })
  })

  it('agrees with every value the demo report cites', () => {
    const cited = sampleInvestigation.report.timeline.flatMap((entry) => (entry.source_fields as { path: string; value: unknown }[]) ?? [])
    expect(cited.length).toBeGreaterThan(0)
    for (const field of cited) {
      const resolved = resolvePointer(sampleCase, field.path)
      expect(resolved.found && sameValue(resolved.value, field.value)).toBe(true)
    }
  })

  it('unescapes ~1 and ~0 and keeps keys with dots whole', () => {
    const doc = { 'a/b': { 'm~n': 1 }, 'kibana.alert.severity': 'high' }
    expect(resolvePointer(doc, '/a~1b/m~0n')).toEqual({ found: true, value: 1 })
    expect(resolvePointer(doc, '/kibana.alert.severity')).toEqual({ found: true, value: 'high' })
  })

  it('reports a path that does not resolve instead of guessing', () => {
    expect(resolvePointer(sampleCase, '/alerts/9/raw_alert')).toEqual({ found: false })
    expect(resolvePointer(sampleCase, '/alerts/01')).toEqual({ found: false })
    expect(resolvePointer(sampleCase, '/alerts/0/raw_alert/nope')).toEqual({ found: false })
    expect(resolvePointer(sampleCase, 'alerts/0')).toEqual({ found: false })
    expect(resolvePointer({ a: { toString: 1 } }, '/a/constructor')).toEqual({ found: false })
  })

  it('treats a stored null as found', () => {
    expect(resolvePointer({ a: null }, '/a')).toEqual({ found: true, value: null })
  })
})

describe('sameValue', () => {
  it('compares lists and objects by content', () => {
    expect(sameValue(['brute_force'], ['brute_force'])).toBe(true)
    expect(sameValue({ a: [1, { b: 2 }] }, { a: [1, { b: 2 }] })).toBe(true)
    expect(sameValue(['a'], ['b'])).toBe(false)
    expect(sameValue({ a: 1 }, { a: 1, b: 2 })).toBe(false)
    expect(sameValue([], {})).toBe(false)
  })
})
