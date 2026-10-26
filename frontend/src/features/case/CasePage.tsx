import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { api, ApiError } from '../../api/client'
import type { Investigation, StoredCase } from '../../api/types'
import { PrimaryButton, TextButton } from '../../ui/buttons'
import { ReportView } from './report/ReportView'
import { backendLimitSeconds, formatElapsed, RunTimeout, withTimeLimit } from './runLimit'

const isMissing = (error: Error | null) => error instanceof ApiError && (error.status === 404 || error.status === 422)

// A 4xx is an answer, not a hiccup: retrying a missing report only delays the Investigate button.
const retryUnlessAnswered = (count: number, error: Error) =>
  count < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500)

export function CasePage() {
  const { caseId = '' } = useParams()
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const stored = useQuery({ queryKey: ['case', caseId], queryFn: () => api.getCase(caseId), retry: retryUnlessAnswered })
  const investigation = useQuery({
    queryKey: ['investigation', caseId],
    queryFn: () => api.getInvestigation(caseId),
    retry: retryUnlessAnswered,
  })
  const run = useMutation<Investigation, Error>({
    mutationFn: () => withTimeLimit(api.investigate(caseId)),
    onSuccess: (data) => queryClient.setQueryData(['investigation', caseId], data),
  })
  const { mutate } = run
  const started = useRef(false)

  // New Case sends the analyst here asking for a run. The request is dropped from history right
  // away, so a reload shows the stored report instead of starting the agent again.
  const askedToRun = (location.state as { investigate?: boolean } | null)?.investigate === true
  useEffect(() => {
    if (!askedToRun || started.current) return
    started.current = true
    mutate()
    navigate(location.pathname, { replace: true, state: null })
  }, [askedToRun, mutate, navigate, location.pathname])

  if (isMissing(stored.error)) {
    return (
      <section>
        <h1 className="text-2xl">{t('case.missing.title')}</h1>
        <p className="mt-1 text-[15px] text-muted">{t('case.missing.body')}</p>
        <Link to="/cases/new" className="mt-4 inline-block text-sm font-medium underline decoration-aligo-rojo decoration-2 underline-offset-4">
          {t('case.missing.newCase')}
        </Link>
      </section>
    )
  }

  let body
  if (run.isPending) body = <RunProgress />
  else if (run.error) body = <RunFailed error={run.error} onRetry={() => run.mutate()} />
  else if (investigation.data) body = <ReportView investigation={investigation.data} />
  else if (investigation.isPending) body = <p className="text-sm text-muted">{t('case.loading')}</p>
  else if (isMissing(investigation.error)) body = <NotInvestigated onStart={() => run.mutate()} />
  else body = <LoadFailed error={investigation.error} onRetry={() => void investigation.refetch()} />

  return (
    <div>
      <CaseHeader caseId={caseId} stored={stored.data} />
      {body}
    </div>
  )
}

function CaseHeader({ caseId, stored }: { caseId: string; stored?: StoredCase }) {
  const { t } = useTranslation()
  const submitted = stored?.submitted_case

  return (
    <div className="mb-6">
      <h1 className="text-2xl break-all">{submitted?.case_id ?? t('case.title')}</h1>
      {submitted?.title && <p className="mt-1 text-[15px] text-muted">{submitted.title}</p>}
      <p className="mt-1 text-xs text-muted">
        {t('case.applicationId')} <code className="font-mono text-[13px] break-all text-aligo-blanco">{caseId}</code>
      </p>
    </div>
  )
}

function RunProgress() {
  const { t } = useTranslation()
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [])

  const shown = Math.min(seconds, backendLimitSeconds)
  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      <h2 className="text-base" role="status">
        {t('case.run.title')}
      </h2>
      <p className="mt-1 text-sm text-muted">{t('case.run.body')}</p>
      <p className="mt-5 flex items-baseline gap-2">
        <span className="text-2xl font-medium tabular-nums">{formatElapsed(shown)}</span>
        <span className="text-sm text-muted">{t('case.run.limit', { limit: formatElapsed(backendLimitSeconds) })}</span>
      </p>
      {/* The bar is the share of the time limit used, not a guess at how much work is left. */}
      <div
        className="mt-3 h-1.5 overflow-hidden rounded-full bg-ground"
        role="progressbar"
        aria-label={t('case.run.timeUsed')}
        aria-valuemin={0}
        aria-valuemax={backendLimitSeconds}
        aria-valuenow={shown}
        aria-valuetext={t('case.run.timeUsedValue', { elapsed: formatElapsed(shown), limit: formatElapsed(backendLimitSeconds) })}
      >
        <div className="h-full bg-aligo-rojo" style={{ width: `${(shown / backendLimitSeconds) * 100}%` }} />
      </div>
    </section>
  )
}

function RunFailed({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const { t } = useTranslation()
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => headingRef.current?.focus(), [])

  let title: string
  let detail: string
  if (error instanceof RunTimeout) {
    title = t('case.failed.pageTimeout.title', { limit: formatElapsed(backendLimitSeconds) })
    detail = t('case.failed.pageTimeout.body')
  } else if (!(error instanceof ApiError)) {
    title = t('case.failed.unexpected.title')
    detail = error.message
  } else if (error.status === 0) {
    title = t('newCase.offline.title')
    detail = t('newCase.offline.body')
  } else if (error.status === 504) {
    title = t('case.failed.timeout')
    detail = typeof error.detail === 'string' ? error.detail : ''
  } else if (error.status === 502) {
    title = t('case.failed.agent')
    detail = typeof error.detail === 'string' ? error.detail : ''
  } else {
    title = t('newCase.failed.title', { status: error.status })
    detail = typeof error.detail === 'string' && error.detail ? error.detail : t('newCase.failed.noDetail')
  }

  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      <div className="border-l-4 border-state-error pl-4">
        <h2 ref={headingRef} tabIndex={-1} className="text-base">
          {title}
        </h2>
        {detail && <p className="mt-1 text-sm text-muted">{detail}</p>}
        <p className="mt-3 text-sm">{t('case.failed.kept')}</p>
        <TextButton onClick={onRetry} className="mt-3">
          {t('case.failed.retry')}
        </TextButton>
      </div>
    </section>
  )
}

function NotInvestigated({ onStart }: { onStart: () => void }) {
  const { t } = useTranslation()

  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      <h2 className="text-base">{t('case.notRun.title')}</h2>
      <p className="mt-1 text-sm text-muted">{t('case.notRun.body')}</p>
      <PrimaryButton onClick={onStart} className="mt-5">
        {t('newCase.accepted.investigate')}
      </PrimaryButton>
    </section>
  )
}

function LoadFailed({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const { t } = useTranslation()
  const offline = error instanceof ApiError && error.status === 0

  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      <div className="border-l-4 border-state-error pl-4">
        <h2 className="text-base">{offline ? t('newCase.offline.title') : t('case.loadFailed.title')}</h2>
        <p className="mt-1 text-sm text-muted">{offline ? t('newCase.offline.body') : error?.message}</p>
        <TextButton onClick={onRetry} className="mt-3">
          {t('newCase.retry')}
        </TextButton>
      </div>
    </section>
  )
}
