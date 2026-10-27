// RFC 6901 JSON Pointer, the format of every source_fields[].path in the report.
// Resolves against the submitted case from GET /cases/{id}.
export type Resolved = { found: true; value: unknown } | { found: false }

export function resolvePointer(document: unknown, pointer: string): Resolved {
  if (pointer === '') return { found: true, value: document }
  if (!pointer.startsWith('/')) return { found: false }
  let current = document
  for (const raw of pointer.slice(1).split('/')) {
    const key = raw.replaceAll('~1', '/').replaceAll('~0', '~')
    if (Array.isArray(current)) {
      if (!/^(0|[1-9]\d*)$/.test(key) || Number(key) >= current.length) return { found: false }
      current = current[Number(key)]
    } else if (typeof current === 'object' && current !== null && Object.hasOwn(current, key)) {
      current = (current as Record<string, unknown>)[key]
    } else {
      return { found: false }
    }
  }
  return { found: true, value: current }
}

export function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false
  if (Array.isArray(a) !== Array.isArray(b)) return false
  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  return (
    keysA.length === keysB.length &&
    keysA.every((key) => Object.hasOwn(b, key) && sameValue((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key]))
  )
}
