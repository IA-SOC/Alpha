import { resolvePointer } from './pointer'

// The severity the source system put on the alert, with the field it came from. The UI never
// computes a case severity of its own, and shows nothing when the alert carries none.
const severityFields = [
  'rule.level', // Wazuh, 0 to 15
  'kibana.alert.severity', // Elastic Security
  'kibana.alert.rule.severity',
  'signal.rule.severity',
  'event.severity', // ECS, numeric
] as const

export function originalSeverity(rawAlert: unknown): { field: string; value: string | number } | undefined {
  // An Elastic search hit wraps the alert in _source, which the backend's read_field also unwraps.
  for (const prefix of ['', '_source.']) {
    const root = prefix ? resolvePointer(rawAlert, '/_source') : { found: true as const, value: rawAlert }
    if (!root.found) continue
    for (const field of severityFields) {
      // Elastic exports carry these both nested and as flat dotted keys.
      const nested = resolvePointer(root.value, `/${field.replaceAll('.', '/')}`)
      const flat = resolvePointer(root.value, `/${field}`)
      const hit = [nested, flat].find((resolved) => resolved.found && ['string', 'number'].includes(typeof resolved.value))
      if (hit?.found) return { field: prefix + field, value: hit.value as string | number }
    }
  }
  return undefined
}
