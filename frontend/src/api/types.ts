import type { CorrelationResult } from './generated/correlation'
import type { components } from './generated/intake'
import type { SOCInvestigationReport } from './generated/report'

type Schemas = components['schemas']

export type IncidentCase = Schemas['IncidentCase']
export type AcceptedCase = Schemas['AcceptedCaseResponse']
export type ValidationIssue = Schemas['ValidationIssue']
export type ReviewDecision = Schemas['ReviewDecision']
export type CaseListItem = Schemas['CaseListItem']
export type CaseStatus = Schemas['CaseStatusUpdate']['status']

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

// GET /cases/{id}/analysis-status, from app/api/routes/investigations.py. Another plain dict.
// not_started is a case stored before automatic analysis existed. updated_at is SQLite's
// CURRENT_TIMESTAMP, UTC written as "YYYY-MM-DD HH:MM:SS".
export type AnalysisState = 'queued' | 'running' | 'completed' | 'error' | 'not_started'

export interface AnalysisStatus {
  case_id: string
  status: AnalysisState
  error: string | null
  updated_at: string | null
}

// Gemini's second opinion, added by agent/llm.py build_model_review. The schema only fixes status.
export interface ModelReviewItem {
  rank: number
  assessment: 'supports' | 'weak' | 'contradicts'
  explanation: string
  cited_alert_ids: string[]
}

export interface ModelAttempt {
  model: string
  outcome: string
  latency_ms?: number
}

export interface ModelReview {
  status: 'ok' | 'error' | 'unavailable'
  provider?: string
  model?: string
  prompt_version?: string
  error?: string
  latency_ms?: number
  context_stats?: { alerts_sent?: number; iocs_sent?: number; redacted_fields?: number }
  items?: ModelReviewItem[]
  rejected_count?: number
  // Only once the model fallback lands, see PR #179.
  attempts?: ModelAttempt[]
}

// The case chat from app/api/routes/chat.py and app/services/chat_service.py. No response models
// in OpenAPI either. Evidence keys are "alert:<alert_id>" for a submitted alert and
// "mcp:<run_id>:<section>:<index>" for a part of the saved investigation, which a rerun retires.
export interface ChatMessage {
  role: 'user' | 'assistant'
  analyst_id?: string
  content: string
  evidence_refs: string[]
  created_at: string
}

export interface ChatHistory {
  case_id: string
  messages: ChatMessage[]
}

export interface ChatReply {
  case_id: string
  message: ChatMessage
}

export type ChatEvidenceItem =
  | { source: 'submitted_case'; alert_id: string; data: Record<string, unknown> }
  | { source: 'investigation'; section: 'hypotheses' | 'timeline' | 'attack_mapping' | 'ioc'; data: Record<string, unknown> }

export interface ChatEvidence {
  case_id: string
  evidence: Record<string, ChatEvidenceItem>
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
