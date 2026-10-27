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

// Fields the agent adds on top of report-schema.json, which allows extra properties. They come
// from agent/investigation.py and app/services/agent_adapter.py in the backend.
export interface SourceField {
  alert_id: string
  path: string // JSON Pointer into the submitted case
  value: unknown
}

export type Evidence = ReportEvidence & { source_fields?: SourceField[] }

export interface Observable {
  type: string
  value: string
}

export interface IocReference {
  evidence_id: string
  source_path: string
  alert_id: string
  provider: string
  observable: Observable
  association_methods: string[]
  relevance: string
}

export interface EnrichmentItem {
  evidence_id?: string
  provider?: string
  observable?: Observable
  raw_result?: unknown
  source_path?: string
  associated_alert_ids?: string[]
}
