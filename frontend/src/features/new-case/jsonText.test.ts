import { describe, expect, it } from 'vitest'

import { fieldPath, formatPath, locate, parseCase } from './jsonText'

const text = `{
  "schema_version": "1.0",
  "alerts": [
    { "alert_id": "a-1", "source_system": "splunk" }
  ]
}`

describe('parseCase', () => {
  it('accepts strict JSON', () => {
    expect(parseCase('{"a": 1}')).toEqual({ ok: true, value: { a: 1 } })
  })

  it('points at the line and column of a syntax error', () => {
    const result = parseCase('{\n  "a": 1,\n  "b" 2\n}')
    expect(result).toMatchObject({ ok: false, line: 3, column: 7 })
  })

  it('rejects trailing commas even though jsonc would allow them', () => {
    expect(parseCase('{"a": 1,}').ok).toBe(false)
  })

  it('treats empty input as invalid', () => {
    expect(parseCase('   ').ok).toBe(false)
  })
})

describe('paths', () => {
  it('drops the body prefix and prints a readable path', () => {
    expect(formatPath(fieldPath(['body', 'alerts', 0, 'source_system']))).toBe('alerts[0].source_system')
    expect(formatPath(fieldPath(['body']))).toBe('')
  })
})

describe('locate', () => {
  it('selects the whole key and value of a field that exists', () => {
    const range = locate(text, ['alerts', 0, 'source_system'])!
    expect(text.slice(range.start, range.end)).toBe('"source_system": "splunk"')
    expect(range).toMatchObject({ line: 4, exact: true })
  })

  it('falls back to the object that should hold a missing field', () => {
    const range = locate(text, ['alerts', 0, 'raw_alert'])!
    expect(text.slice(range.start, range.end)).toBe('{')
    expect(range).toMatchObject({ line: 4, exact: false })
  })

  it('falls back to the root for a missing top-level field', () => {
    expect(locate(text, ['case_id'])).toMatchObject({ start: 0, line: 1, exact: false })
  })

  it('returns nothing when the text is not JSON', () => {
    expect(locate('not json', ['a'])).toBeUndefined()
  })
})
