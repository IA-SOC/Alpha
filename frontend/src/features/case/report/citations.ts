import type { Report, SourceField } from '../../../api/types'
import { asEvidence } from './extras'

export type Citation =
  | { kind: 'hypothesis'; rank: number; side: 'for' | 'against' }
  | { kind: 'technique'; name: string }
  | { kind: 'timeline' }
  | { kind: 'action'; number: number }

export interface AlertCitations {
  citations: Citation[]
  fields: SourceField[]
}

// Where the report uses each alert, and every field it reads from it, without duplicates.
export function citationsByAlert(report: Report): Map<string, AlertCitations> {
  const byAlert = new Map<string, AlertCitations>()
  const entry = (alertId: string) => {
    let found = byAlert.get(alertId)
    if (!found) byAlert.set(alertId, (found = { citations: [], fields: [] }))
    return found
  }
  const cite = (alertId: string, citation: Citation) => {
    const { citations } = entry(alertId)
    if (!citations.some((known) => JSON.stringify(known) === JSON.stringify(citation))) citations.push(citation)
  }
  const read = (fields: SourceField[] | undefined) => {
    for (const field of fields ?? []) {
      const { fields: known } = entry(field.alert_id)
      if (!known.some((seen) => seen.path === field.path)) known.push(field)
    }
  }

  for (const hypothesis of report.hypotheses) {
    for (const [side, items] of [['for', hypothesis.evidence_for], ['against', hypothesis.evidence_against]] as const) {
      for (const evidence of asEvidence(items)) {
        cite(evidence.alert_id, { kind: 'hypothesis', rank: hypothesis.rank, side })
        read(evidence.source_fields)
      }
    }
  }
  for (const technique of report.attack_mapping) {
    for (const evidence of asEvidence(technique.evidence)) {
      cite(evidence.alert_id, { kind: 'technique', name: technique.technique_id ?? technique.technique_name })
      read(evidence.source_fields)
    }
  }
  for (const event of report.timeline) {
    for (const alertId of event.alert_ids) cite(alertId, { kind: 'timeline' })
    read(event.source_fields as SourceField[] | undefined)
  }
  report.recommended_actions.forEach((action, index) => {
    for (const alertId of action.evidence_ids) cite(alertId, { kind: 'action', number: index + 1 })
  })
  return byAlert
}
