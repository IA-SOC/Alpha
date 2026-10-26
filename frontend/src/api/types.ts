import type { CorrelationResult } from './generated/correlation'
import type { components } from './generated/intake'
import type { SOCInvestigationReport } from './generated/report'

type Schemas = components['schemas']

export type IncidentCase = Schemas['IncidentCase']
export type AcceptedCase = Schemas['AcceptedCaseResponse']
export type ValidationIssue = Schemas['ValidationIssue']
export type ReviewDecision = Schemas['ReviewDecision']

export type Report = SOCInvestigationReport
export type Hypothesis = Report['hypotheses'][number]
export type AttackTechnique = Report['attack_mapping'][number]
export type TimelineEntry = Report['timeline'][number]
export type ReportEvidence = Hypothesis['evidence_for'][number]
export type Correlation = CorrelationResult

// GET /cases/{id}. The backend returns a plain dict here, so OpenAPI has no model for it.
export interface StoredCase {
  case_id: string
  submitted_case: IncidentCase
}

// POST /investigate, GET /investigation and POST /review all return this envelope.
// It is built in app/services/investigation_service.py and has no OpenAPI model either.
export interface Investigation {
  case_id: string
  run_id: string
  status: 'pending_review' | 'validated' | 'corrected' | 'rejected'
  correlation: Correlation
  investigation_context: Record<string, unknown>
  report: Report
  report_markdown: string
  validation: { ok: boolean; returncode: number; output: string; traceability_ok: boolean }
  audit_log: { phase: number; node: string; finished_at: string; duration_ms: number; detail: string }[]
}
