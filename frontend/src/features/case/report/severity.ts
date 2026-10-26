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
  for (const field of severityFields) {
    // Elastic exports carry these both nested and as flat dotted keys.
    const nested = resolvePointer(rawAlert, `/${field.replaceAll('.', '/')}`)
    const flat = resolvePointer(rawAlert, `/${field}`)
    const hit = [nested, flat].find((resolved) => resolved.found && ['string', 'number'].includes(typeof resolved.value))
    if (hit?.found) return { field, value: hit.value as string | number }
  }
  return undefined
}
