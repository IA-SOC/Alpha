import { findNodeAtLocation, type Node, parse, type ParseError, parseTree, printParseErrorCode } from 'jsonc-parser'

export interface TextRange {
  start: number
  end: number
  line: number
  // false when the field is missing and the range points at the object that should hold it
  exact: boolean
}

export type ParsedCase = { ok: true; value: unknown } | { ok: false; line: number; column: number; reason: string }

function lineAt(text: string, offset: number) {
  let line = 1
  let lineStart = 0
  for (let i = 0; i < offset && i < text.length; i++) {
    if (text[i] === '\n') {
      line++
      lineStart = i + 1
    }
  }
  return { line, column: offset - lineStart + 1 }
}

// Strict JSON only. jsonc-parser is used for the error position, JSON.parse decides validity,
// so comments or trailing commas that jsonc would accept are still rejected.
export function parseCase(text: string): ParsedCase {
  try {
    return { ok: true, value: JSON.parse(text) }
  } catch {
    const errors: ParseError[] = []
    parse(text, errors, { allowTrailingComma: false, disallowComments: true })
    const offset = errors[0]?.offset ?? text.length
    return { ok: false, ...lineAt(text, offset), reason: errors[0] ? printParseErrorCode(errors[0].error) : 'Unknown' }
  }
}

// The backend reports `loc` as ["body", "alerts", 0, "source_system"]. Drop the "body" prefix.
export function fieldPath(loc: (string | number)[]): (string | number)[] {
  return loc[0] === 'body' ? loc.slice(1) : loc
}

export function formatPath(path: (string | number)[]): string {
  return path.reduce<string>(
    (out, part) => (typeof part === 'number' ? `${out}[${part}]` : out ? `${out}.${part}` : part),
    '',
  )
}

function rangeOf(text: string, node: Node, exact: boolean): TextRange {
  // Highlight the whole "key": value pair when the node is a property value.
  const target = exact && node.parent?.type === 'property' ? node.parent : node
  const end = exact ? target.offset + target.length : target.offset + 1
  return { start: target.offset, end, line: lineAt(text, target.offset).line, exact }
}

// Finds a backend issue's field in the pasted text. A missing field resolves to the closest
// ancestor that exists, so the analyst still lands next to where it belongs.
export function locate(text: string, path: (string | number)[]): TextRange | undefined {
  const root = parseTree(text)
  if (!root) return undefined
  for (let depth = path.length; depth >= 0; depth--) {
    const node = depth === 0 ? root : findNodeAtLocation(root, path.slice(0, depth))
    if (node) return rangeOf(text, node, depth === path.length)
  }
  return undefined
}
