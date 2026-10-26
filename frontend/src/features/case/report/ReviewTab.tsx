import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type ReactNode, useId, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, ApiError } from '../../../api/client'
import type { Investigation, Report, ReviewDecision } from '../../../api/types'
import { maxNameLength, useSession } from '../../../session/session'
import { PrimaryButton } from '../../../ui/buttons'
import { formatUtc } from './format'
import { Chip, Confidence, Panel } from './parts'
import {
  clearDraft,
  type Decision,
  decisions,
  type Finding,
  findingDraft,
  findingsOf,
  loadDraft,
  problemCount,
  problemsOf,
  type ReviewDraft,
  saveDraft,
  suggestedStatus,
  techniqueLabel,
  toDecision,
} from './review'

// The two 409 details from app/services/investigation_service.py. Both mean this run can no
// longer take a review, so the way out is a new run.
const conflictReasons: Record<string, string> = {
  'No resumable investigation in this process': 'restarted',
  'The investigation is not awaiting review': 'reviewed',
}

export function ReviewTab({ investigation, onRerun }: { investigation: Investigation; onRerun: () => void }) {
  if (investigation.report.review.status !== 'pending') return <RecordedReview report={investigation.report} />
  // A new run starts a clean form, with the decisions reloaded from the saved draft.
  return <ReviewForm key={investigation.run_id} investigation={investigation} onRerun={onRerun} />
}

function RecordedReview({ report }: { report: Report }) {
  const { t } = useTranslation()
  const { review } = report
  const rows = [
    { label: t('report.review.status'), value: t(`report.reviewStatus.${review.status}`) },
    { label: t('report.review.analyst'), value: review.analyst },
    { label: t('report.review.notes'), value: review.notes },
    { label: t('report.review.reviewedAt'), value: formatUtc(review.reviewed_at) },
  ]

  return (
    <Panel title={t('report.review.title')} className="max-w-3xl">
      <dl className="mt-3 divide-y divide-control">
        {rows.map(({ label, value }) => (
          <div key={label} className="grid grid-cols-[140px_minmax(0,1fr)] gap-4 py-2.5 text-sm">
            <dt className="text-muted">{label}</dt>
            <dd className={`whitespace-pre-wrap break-words ${value ? '' : 'text-muted'}`}>{value || '-'}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}

function ReviewForm({ investigation, onRerun }: { investigation: Investigation; onRerun: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const session = useSession()
  const caseId = investigation.case_id
  const findings = useMemo(() => findingsOf(investigation.report), [investigation.report])
  const [draft, setDraft] = useState(() => loadDraft(caseId))
  const [tried, setTried] = useState(false)
  const summaryRef = useRef<HTMLDivElement>(null)

  const send = useMutation<Investigation, Error, ReviewDecision>({
    mutationFn: (decision) => api.review(caseId, decision),
    onSuccess: (data) => {
      clearDraft(caseId)
      queryClient.setQueryData(['investigation', caseId], data)
    },
  })

  function update(next: ReviewDraft) {
    setDraft(next)
    saveDraft(caseId, next)
  }

  const analyst = draft.analyst ?? session?.analyst ?? ''
  const suggested = suggestedStatus(findings, draft)
  const problems = problemsOf(findings, draft, analyst)
  const shown = tried ? problems : undefined
  const decided = findings.filter((finding) => findingDraft(draft, finding.key).decision).length

  function submit(event: FormEvent) {
    event.preventDefault()
    setTried(true)
    if (problemCount(problems) > 0) {
      // The summary is rendered in this same update, so focus it once it is on screen.
      requestAnimationFrame(() => summaryRef.current?.focus())
      return
    }
    send.mutate(toDecision(findings, draft, analyst))
  }

  return (
    <form noValidate onSubmit={submit} className="max-w-4xl space-y-4">
      <div>
        <p className="text-sm text-muted">{t('report.review.intro')}</p>
        <p className="mt-1 text-sm text-muted">{t('report.review.oneReview')}</p>
      </div>

      {shown && problemCount(shown) > 0 && (
        <div ref={summaryRef} tabIndex={-1} role="alert" className="rounded-2xl bg-surface p-5">
          <p className="border-l-4 border-state-error pl-4 text-sm">{t('report.review.problems', { count: problemCount(shown) })}</p>
        </div>
      )}

      {findings.length > 0 && (
        <section aria-labelledby="findings-title" className="space-y-4">
          <h2 id="findings-title" className="flex flex-wrap items-baseline justify-between gap-2 text-base">
            {t('report.review.findings', { count: findings.length })}
            <span className="text-sm font-normal text-muted tabular-nums">
              {t('report.review.decided', { decided, total: findings.length })}
            </span>
          </h2>
          {findings.map((finding, index) => {
            const current = findingDraft(draft, finding.key)
            return (
              <FindingCard
                key={finding.key}
                finding={finding}
                index={index}
                decision={current.decision}
                note={current.note}
                missingDecision={shown?.decision.has(finding.key) ?? false}
                missingNote={shown?.note.has(finding.key) ?? false}
                onDecision={(decision) => update({ ...draft, findings: { ...draft.findings, [finding.key]: { ...current, decision } } })}
                onNote={(note) => update({ ...draft, findings: { ...draft.findings, [finding.key]: { ...current, note } } })}
              />
            )
          })}
        </section>
      )}

      <Panel title={t('report.review.outcome')}>
        <Outcome
          selected={draft.status ?? suggested}
          suggested={suggested}
          noFindings={findings.length === 0}
          missing={shown?.status ?? false}
          onSelect={(status) => update({ ...draft, status: status === suggested ? undefined : status })}
        />
        <TextField
          label={t('report.review.analyst')}
          value={analyst}
          maxLength={maxNameLength}
          error={shown?.analyst ? t('report.review.analystMissing') : undefined}
          onChange={(value) => update({ ...draft, analyst: value })}
        />
        <TextArea
          label={findings.length === 0 ? t('report.review.generalNoteRequired') : t('report.review.generalNote')}
          hint={findings.length === 0 ? t('report.review.generalNoteHintRequired') : t('report.review.generalNoteHint')}
          value={draft.generalNote}
          error={shown?.generalNote ? t('report.review.noteMissing') : undefined}
          onChange={(value) => update({ ...draft, generalNote: value })}
        />
        <div className="mt-5 flex flex-wrap items-center gap-4">
          <PrimaryButton type="submit" disabled={send.isPending}>
            {send.isPending ? t('report.review.saving') : t('report.review.save')}
          </PrimaryButton>
        </div>
      </Panel>

      {send.error && <SendFailed error={send.error} onRerun={onRerun} />}
    </form>
  )
}

interface FindingCardProps {
  finding: Finding
  index: number
  decision?: Decision
  note: string
  missingDecision: boolean
  missingNote: boolean
  onDecision: (decision: Decision) => void
  onNote: (note: string) => void
}

function FindingCard({ finding, index, decision, note, missingDecision, missingNote, onDecision, onNote }: FindingCardProps) {
  const { t } = useTranslation()
  const errorId = useId()

  let kind: string
  let title: string
  let detail: ReactNode
  if (finding.kind === 'hypothesis') {
    kind = t('report.review.hypothesis', { rank: finding.hypothesis.rank })
    title = finding.hypothesis.statement
    detail = <Confidence value={finding.hypothesis.confidence} />
  } else {
    kind = t('report.review.technique')
    title = techniqueLabel(finding.technique)
    detail = (
      <p className="text-sm">
        <span className="text-muted">{t('report.mitre.status')} </span>
        <Chip>{t(`report.mitre.statuses.${finding.technique.status}`)}</Chip>
      </p>
    )
  }

  return (
    <article className="rounded-2xl bg-surface p-5">
      <fieldset aria-describedby={missingDecision ? errorId : undefined}>
        <legend className="text-base">
          <span className="block text-xs font-medium text-muted">{kind}</span>{' '}
          <span className="mt-1 block font-bold">{title}</span>
        </legend>
        <div className="mt-3">{detail}</div>
        <div className="mt-4">
          <Choices
            name={`finding-${index}`}
            options={decisions.map((value) => ({ value, label: t(`report.review.decisions.${value}`) }))}
            selected={decision}
            onSelect={onDecision}
          />
          {missingDecision && <FieldError id={errorId}>{t('report.review.decisionMissing')}</FieldError>}
        </div>
      </fieldset>
      <TextArea
        label={t('report.review.findingNote')}
        hint={t('report.review.findingNoteHint')}
        value={note}
        error={missingNote ? t('report.review.noteMissing') : undefined}
        onChange={onNote}
      />
    </article>
  )
}

function Outcome({
  selected,
  suggested,
  noFindings,
  missing,
  onSelect,
}: {
  selected?: Decision
  suggested?: Decision
  noFindings: boolean
  missing: boolean
  onSelect: (status: Decision) => void
}) {
  const { t } = useTranslation()
  const errorId = useId()
  const hintId = useId()

  let hint: string
  if (noFindings) hint = t('report.review.outcomeNoFindings')
  else if (suggested) hint = t('report.review.outcomeSuggested', { status: t(`report.reviewStatus.${suggested}`) })
  else hint = t('report.review.outcomeWaiting')

  return (
    <fieldset className="mt-3" aria-describedby={missing ? `${hintId} ${errorId}` : hintId}>
      <legend className="text-sm font-medium">{t('report.review.status')}</legend>
      <p id={hintId} className="mt-1 text-sm text-muted">
        {hint}
      </p>
      <div className="mt-3">
        <Choices
          name="outcome"
          options={decisions.map((value) => ({
            value,
            label: t(`report.reviewStatus.${value}`),
            note: value === suggested ? t('report.review.suggested') : undefined,
          }))}
          selected={selected}
          onSelect={onSelect}
        />
      </div>
      {missing && <FieldError id={errorId}>{t('report.review.outcomeMissing')}</FieldError>}
    </fieldset>
  )
}

// Native radios, so arrows, Tab and screen readers behave as usual. Only the look is custom.
function Choices({
  name,
  options,
  selected,
  onSelect,
}: {
  name: string
  options: { value: Decision; label: string; note?: string }[]
  selected?: Decision
  onSelect: (value: Decision) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <label
          key={option.value}
          className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-full border border-control px-4 text-sm font-medium hover:border-aligo-blanco has-checked:border-aligo-blanco has-checked:bg-aligo-blanco has-checked:text-aligo-negro has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-aligo-rojo"
        >
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={selected === option.value}
            onChange={() => onSelect(option.value)}
            className="sr-only"
          />
          {option.label}
          {option.note && ' '}
          {option.note && <span className="text-xs font-normal opacity-80">{option.note}</span>}
        </label>
      ))}
    </div>
  )
}

function TextField({
  label,
  value,
  maxLength,
  error,
  onChange,
}: {
  label: string
  value: string
  maxLength: number
  error?: string
  onChange: (value: string) => void
}) {
  const id = useId()

  return (
    <div className="mt-5 max-w-sm">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        value={value}
        maxLength={maxLength}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 block h-10 w-full rounded-xl bg-ground px-4 text-[15px] text-aligo-blanco focus:outline-2 focus:outline-aligo-rojo"
      />
      {error && <FieldError id={`${id}-error`}>{error}</FieldError>}
    </div>
  )
}

function TextArea({
  label,
  hint,
  value,
  error,
  onChange,
}: {
  label: string
  hint: string
  value: string
  error?: string
  onChange: (value: string) => void
}) {
  const id = useId()

  return (
    <div className="mt-5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <p id={`${id}-hint`} className="mt-0.5 text-sm text-muted">
        {hint}
      </p>
      <textarea
        id={id}
        value={value}
        rows={3}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-hint ${id}-error` : `${id}-hint`}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 block w-full resize-y rounded-xl bg-ground p-4 text-sm text-aligo-blanco focus:outline-2 focus:outline-aligo-rojo"
      />
      {error && <FieldError id={`${id}-error`}>{error}</FieldError>}
    </div>
  )
}

function FieldError({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p id={id} className="mt-2 border-l-4 border-state-error pl-2 text-sm">
      {children}
    </p>
  )
}

function SendFailed({ error, onRerun }: { error: Error; onRerun: () => void }) {
  const { t } = useTranslation()
  const apiError = error instanceof ApiError ? error : undefined

  if (apiError?.status === 409) {
    const reason = typeof apiError.detail === 'string' ? conflictReasons[apiError.detail] : undefined
    return (
      <section role="alert" className="rounded-2xl bg-surface p-5">
        <div className="border-l-4 border-state-warn pl-4">
          <h2 className="text-base">{t('report.review.conflict.title')}</h2>
          <p className="mt-1 text-sm text-muted">{t(`report.review.conflict.${reason ?? 'other'}`)}</p>
          <p className="mt-3 text-sm">{t('report.review.conflict.kept')}</p>
          <PrimaryButton onClick={onRerun} className="mt-4">
            {t('report.review.conflict.rerun')}
          </PrimaryButton>
        </div>
      </section>
    )
  }

  let title: string
  let detail: string
  if (apiError?.status === 0) {
    title = t('newCase.offline.title')
    detail = t('newCase.offline.body')
  } else if (apiError) {
    title = t('newCase.failed.title', { status: apiError.status })
    detail = apiError.issues.length > 0 ? apiError.issues.map((issue) => issue.msg).join(' ') : apiError.message || t('newCase.failed.noDetail')
  } else {
    title = t('case.failed.unexpected.title')
    detail = error.message
  }

  return (
    <section role="alert" className="rounded-2xl bg-surface p-5">
      <div className="border-l-4 border-state-error pl-4">
        <h2 className="text-base">{title}</h2>
        {detail && <p className="mt-1 text-sm text-muted">{detail}</p>}
        <p className="mt-3 text-sm">{t('report.review.kept')}</p>
      </div>
    </section>
  )
}
