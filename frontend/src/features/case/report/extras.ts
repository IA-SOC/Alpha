import type { EnrichmentItem, Evidence, Hypothesis, IocReference, Report, TimelineEntry } from '../../../api/types'

// Typed reads of the agent's extra fields. Each one falls back to empty when a report from an
// older agent does not carry the field.
export const iocReferences = (hypothesis: Hypothesis) => (hypothesis.ioc_evidence as IocReference[] | undefined) ?? []

export type Interpretation = {
  source: string
  assessment: 'supports' | 'weak' | 'contradicts'
  explanation: string
  cited_alert_ids: string[]
}

export const interpretation = (hypothesis: Hypothesis) => hypothesis.interpretation as Interpretation | undefined

export const groupAlertIds = (item: Hypothesis | Report['attack_mapping'][number]) =>
  (item.correlation_group_alert_ids as string[] | undefined) ?? []

export const enrichmentItems = (report: Report) => report.enrichment.items as EnrichmentItem[]

export const stage = (entry: TimelineEntry) => (typeof entry.stage === 'string' ? entry.stage : undefined)

export const asEvidence = (items: Report['hypotheses'][number]['evidence_for']) => items as Evidence[]

export function timeWindow(report: Report) {
  const window = report.input.time_window_utc as { start?: string | null; end?: string | null } | null | undefined
  return { start: window?.start ?? undefined, end: window?.end ?? undefined }
}
