import { useMutation, useMutationState, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { api, ApiError } from '../../api/client'
import type { AnalysisStatus, Investigation, StoredCase } from '../../api/types'
import { PrimaryButton, TextButton, textActionClass } from '../../ui/buttons'
import { casesKey, useCases, useSetCaseStatus } from '../cases/useCases'
import { analysisKey, formatJobTime, isWorking, useAnalysisStatus } from './analysis'
import { ReportView } from './report/ReportView'
import { backendLimitSeconds, formatElapsed, RunTimeout, withTimeLimit } from './runLimit'

const isMissing = (error: Error | null) => error instanceof ApiError && (error.status === 404 || error.status === 422)

// A 4xx is an answer, not a hiccup: retrying a missing report only delays the Investigate button.
const retryUnlessAnswered = (count: number, error: Error) =>
  count < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500)

// Keyed by the ID so a different case always starts with fresh run state.
export function CaseRoute() {
  const { caseId = '' } = useParams()
  return <CasePage key={caseId} caseId={caseId} />
}

function CasePage({ caseId }: { caseId: string }) {
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
  const analysis = useAnalysisStatus(caseId)
  const runKey = ['investigate', caseId]
  const run = useMutation<Investigation, Error, boolean | void>({
    mutationKey: runKey,
    mutationFn: (force) => withTimeLimit((signal) => api.investigate(caseId, signal, force === true)),
    onSuccess: (data) => {
      queryClient.setQueryData(['investigation', caseId], data)
      void queryClient.invalidateQueries({ queryKey: casesKey })
    },
    onError: () => void queryClient.invalidateQueries({ queryKey: ['investigation', caseId] }),
    // Either way the backend job moved, so its status is read again.
    onSettled: () => void queryClient.invalidateQueries({ queryKey: analysisKey(caseId) }),
  })
  // Runs live in the shared mutation cache, so leaving the page mid-run and coming back shows the
  // same run still going instead of offering a second one.
  const latest = useMutationState({ filters: { mutationKey: runKey }, select: (mutation) => mutation.state }).at(-1)
  const { mutate } = run
  const started = useRef(false)

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
        <Link to="/cases/new" className={`mt-4 inline-block ${textActionClass}`}>
          {t('case.missing.newCase')}
        </Link>
      </section>
    )
  }

  const failure = latest?.status === 'error' && latest.error
    ? <RunFailed error={latest.error as Error} onRetry={() => run.mutate(true)} />
    : null

  let body
  if (latest?.status === 'pending') body = <RunProgress startedAt={latest.submittedAt} />
  else if (investigation.data)
    body = (
      <ReportView
        investigation={investigation.data}
        caseState={{ submitted: stored.data?.submitted_case, failed: stored.isError }}
        analysis={analysis.data}
        onRerun={() => run.mutate(true)}
      />
    )
  else if (failure) body = null
  else if (investigation.isPending) body = <p className="text-sm text-muted">{t('case.loading')}</p>
  else if (isMissing(investigation.error) && analysis.data && isWorking(analysis.data.status))
    body = <AnalysisRunning status={analysis.data} />
  else if (isMissing(investigation.error))
    body = (
      <NotInvestigated
        failed={analysis.data?.status === 'error' ? analysis.data : undefined}
        onStart={() => run.mutate(true)}
      />
    )
  else body = <LoadFailed error={investigation.error} onRetry={() => void investigation.refetch()} />

  return (
    <div>
      <CaseHeader caseId={caseId} stored={stored.data} />
      {failure && <div className="mb-6">{failure}</div>}
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
      <CaseStatusRow caseId={caseId} />
    </div>
  )
}

// Whether the case is open or closed, with the one action that flips it. It reads the shared case
// list, which also tells the sidebar. Closing never touches the stored findings.
function CaseStatusRow({ caseId }: { caseId: string }) {
  const { t } = useTranslation()
  const cases = useCases()
  const change = useSetCaseStatus()
  const item = cases.data?.find((entry) => entry.case_id === caseId)
  if (!item) return null
  const closed = item.status === 'closed'

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      <span className={closed ? 'text-muted' : ''}>{t(`cases.status.${item.status}`)}</span>
      <TextButton
        onClick={() => change.mutate({ caseId, status: closed ? 'open' : 'closed' })}
        disabled={change.isPending}
      >
        {t(closed ? 'cases.actions.reopenCase' : 'cases.actions.closeCase')}
      </TextButton>
      {change.isError && (
        <span role="alert" className="border-l-4 border-state-error pl-2">
          {t('cases.actions.failed')}
        </span>
      )}
    </div>
  )
}

const secondsSince = (startedAt: number) => Math.max(0, Math.floor((Date.now() - startedAt) / 1000))

function RunProgress({ startedAt }: { startedAt: number }) {
  const { t } = useTranslation()
  const [seconds, setSeconds] = useState(() => secondsSince(startedAt))

  useEffect(() => {
    const timer = setInterval(() => setSeconds(secondsSince(startedAt)), 1000)
    return () => clearInterval(timer)
  }, [startedAt])

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

// The backend started on the case by itself when it was accepted. Nothing to press: the page
// follows the job and shows the report as soon as it is saved.
function AnalysisRunning({ status }: { status: AnalysisStatus }) {
  const { t } = useTranslation()

  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      <h2 className="text-base" role="status">
        {t(`case.auto.${status.status === 'queued' ? 'queued' : 'running'}`)}
      </h2>
      <p className="mt-1 text-sm text-muted">{t('case.auto.body')}</p>
      {status.updated_at && (
        <p className="mt-3 text-xs text-muted">{t('case.auto.since', { time: formatJobTime(status.updated_at) })}</p>
      )}
    </section>
  )
}

function NotInvestigated({ failed, onStart }: { failed?: AnalysisStatus; onStart: () => void }) {
  const { t } = useTranslation()

  return (
    <section className="max-w-2xl rounded-2xl bg-surface p-5">
      {failed ? (
        <div className="border-l-4 border-state-error pl-4">
          <h2 className="text-base">{t('case.auto.failed')}</h2>
          <p className="mt-1 text-sm text-muted">
            {failed.error ? t('case.auto.failedReason', { reason: failed.error }) : t('case.auto.failedNoReason')}
          </p>
          <p className="mt-3 text-sm">{t('case.failed.kept')}</p>
        </div>
      ) : (
        <>
          <h2 className="text-base">{t('case.notRun.title')}</h2>
          <p className="mt-1 text-sm text-muted">{t('case.notRun.body')}</p>
        </>
      )}
      <PrimaryButton onClick={onStart} className="mt-5">
        {t(failed ? 'case.failed.retry' : 'newCase.accepted.investigate')}
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
