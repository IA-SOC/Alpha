import type { AttackTechnique, Hypothesis, Report, ReviewDecision } from '../../../api/types'

// Per finding review for the Alpha. The backend keeps one review per run, so until per finding
// storage lands in issue #88 the decisions travel together, written out in the review notes.
export type Decision = ReviewDecision['status']
export const decisions: Decision[] = ['validated', 'corrected', 'rejected']

export type Finding =
  | { key: string; kind: 'hypothesis'; hypothesis: Hypothesis }
  | { key: string; kind: 'technique'; technique: AttackTechnique }

// The key is the finding's own text, not its position, so a decision only comes back after a new
// run when the agent reached the same conclusion again.
export function findingsOf(report: Report): Finding[] {
  const seen = new Map<string, number>()
  const unique = (key: string) => {
    const count = (seen.get(key) ?? 0) + 1
    seen.set(key, count)
    return count === 1 ? key : `${key}#${count}`
  }
  const hypotheses = [...report.hypotheses].sort((a, b) => a.rank - b.rank)
  return [
    ...hypotheses.map((hypothesis) => ({
      key: unique(`hypothesis:${hypothesis.statement}`),
      kind: 'hypothesis' as const,
      hypothesis,
    })),
    ...report.attack_mapping.map((technique) => ({
      key: unique(`technique:${techniqueLabel(technique)}`),
      kind: 'technique' as const,
      technique,
    })),
  ]
}

export function techniqueLabel(technique: AttackTechnique): string {
  const name = [technique.technique_id, technique.technique_name].filter(Boolean).join(' ')
  return technique.tactic ? `${name}, ${technique.tactic}` : name
}

export interface FindingDraft {
  decision?: Decision
  note: string
}

export interface ReviewDraft {
  findings: Record<string, FindingDraft>
  // Set only when the analyst picks a status other than the suggested one. It counts only for the
  // findings it was picked for, so a new run with other conclusions goes back to the suggestion.
  status?: Decision
  statusFor?: string
  // A name typed over the session's, kept only while that same session is signed in.
  analyst?: string
  analystFor?: string
  generalNote: string
}

export const emptyDraft = (): ReviewDraft => ({ findings: {}, generalNote: '' })

export const findingDraft = (draft: ReviewDraft, key: string): FindingDraft => draft.findings[key] ?? { note: '' }

export const findingsSignature = (findings: Finding[]) => findings.map((finding) => finding.key).join('\n')

export const draftAnalyst = (draft: ReviewDraft, sessionAnalyst: string) =>
  draft.analyst !== undefined && draft.analystFor === sessionAnalyst ? draft.analyst : sessionAnalyst

// All validated or all rejected keeps that word. Any mix means the analyst changed the outcome.
export function suggestedStatus(findings: Finding[], draft: ReviewDraft): Decision | undefined {
  const picked = findings.map((finding) => findingDraft(draft, finding.key).decision)
  if (picked.length === 0 || picked.some((decision) => !decision)) return undefined
  if (picked.every((decision) => decision === 'validated')) return 'validated'
  if (picked.every((decision) => decision === 'rejected')) return 'rejected'
  return 'corrected'
}

export function chosenStatus(findings: Finding[], draft: ReviewDraft): Decision | undefined {
  if (draft.status && draft.statusFor === findingsSignature(findings)) return draft.status
  return suggestedStatus(findings, draft)
}

export interface ReviewProblems {
  analyst: boolean
  generalNote: boolean
  status: boolean
  decision: Set<string>
  note: Set<string>
}

export function problemsOf(findings: Finding[], draft: ReviewDraft, analyst: string): ReviewProblems {
  const blank = (text: string) => !text.trim()
  return {
    analyst: blank(analyst),
    // With nothing to decide, the general note is what the backend's required notes hold.
    generalNote: findings.length === 0 && blank(draft.generalNote),
    status: !chosenStatus(findings, draft),
    decision: new Set(findings.filter((finding) => !findingDraft(draft, finding.key).decision).map((finding) => finding.key)),
    note: new Set(findings.filter((finding) => blank(findingDraft(draft, finding.key).note)).map((finding) => finding.key)),
  }
}

export const problemCount = (problems: ReviewProblems) =>
  Number(problems.analyst) + Number(problems.generalNote) + Number(problems.status) + problems.decision.size + problems.note.size

// The notes stay in English whatever the screen language, so every stored review reads the same
// and can be split back into per finding decisions once #88 stores them on their own.
export function composeNotes(findings: Finding[], draft: ReviewDraft): string {
  const blocks = findings.map((finding) => {
    const { decision, note } = findingDraft(draft, finding.key)
    const title =
      finding.kind === 'hypothesis'
        ? `Hypothesis ${finding.hypothesis.rank}: ${finding.hypothesis.statement}`
        : `MITRE technique: ${techniqueLabel(finding.technique)}`
    return `${title}\nDecision: ${decision}\nNote: ${note.trim()}`
  })
  if (draft.generalNote.trim()) blocks.push(`General note: ${draft.generalNote.trim()}`)
  if (findings.length === 0) return blocks.join('\n\n')
  return ['Per finding decisions, sent as one review for the whole report.', ...blocks].join('\n\n')
}

export function toDecision(findings: Finding[], draft: ReviewDraft, analyst: string): ReviewDecision {
  return {
    status: chosenStatus(findings, draft)!,
    analyst: analyst.trim(),
    notes: composeNotes(findings, draft),
  }
}

// The draft lives in this browser per case, so a restarted backend or a closed tab does not cost
// the analyst their work. Blocked storage falls back to memory for this tab.
const storageKey = (caseId: string) => `soc.review.${caseId}`
const memory = new Map<string, ReviewDraft>()

export function loadDraft(caseId: string): ReviewDraft {
  try {
    const raw = localStorage.getItem(storageKey(caseId))
    if (raw) return parseDraft(JSON.parse(raw))
  } catch {
    // Blocked or broken storage, use what this tab remembers.
  }
  return memory.get(caseId) ?? emptyDraft()
}

const isDecision = (value: unknown): value is Decision => decisions.includes(value as Decision)
const text = (value: unknown) => (typeof value === 'string' ? value : undefined)
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)

// Storage may hold an older or hand edited draft, so each field is checked before the form trusts it.
function parseDraft(value: unknown): ReviewDraft {
  const draft = emptyDraft()
  if (!isRecord(value)) return draft
  if (isRecord(value.findings)) {
    for (const [key, entry] of Object.entries(value.findings)) {
      if (!isRecord(entry)) continue
      draft.findings[key] = { note: text(entry.note) ?? '', ...(isDecision(entry.decision) && { decision: entry.decision }) }
    }
  }
  draft.generalNote = text(value.generalNote) ?? ''
  if (isDecision(value.status) && text(value.statusFor) !== undefined) {
    draft.status = value.status
    draft.statusFor = text(value.statusFor)
  }
  if (text(value.analyst) !== undefined && text(value.analystFor) !== undefined) {
    draft.analyst = text(value.analyst)
    draft.analystFor = text(value.analystFor)
  }
  return draft
}

export function saveDraft(caseId: string, draft: ReviewDraft) {
  try {
    localStorage.setItem(storageKey(caseId), JSON.stringify(draft))
    memory.delete(caseId)
  } catch {
    memory.set(caseId, draft)
  }
}

export function clearDraft(caseId: string) {
  memory.delete(caseId)
  try {
    localStorage.removeItem(storageKey(caseId))
  } catch {
    // Nothing stored, nothing to remove.
  }
}
