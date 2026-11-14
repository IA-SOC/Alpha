import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import type { AnalysisStatus, Hypothesis, Investigation, ModelReview, ModelReviewItem } from '../../../api/types'
import { textActionClass } from '../../../ui/buttons'
import { formatJobTime, isWorking } from '../analysis'
import { asEvidence } from './extras'
import { AlertIds, Chip, Empty, EvidenceList, Panel } from './parts'

interface AgentTabProps {
  investigation: Investigation
  analysis?: AnalysisStatus
}

// The first thing an analyst reads: what the automatic run concluded, what Gemini said about it,
// the evidence behind each remark, and where the processing stands. Same 720 + 360 split as Summary.
export function AgentTab({ investigation, analysis }: AgentTabProps) {
  const { t } = useTranslation()
  const { report } = investigation
  const review = report.model_review as ModelReview | undefined

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <Panel title={t('report.summary.title')}>
          <p className="mt-2 text-base">{report.executive_summary}</p>
          <p className="mt-3 text-sm text-muted">
            {t('report.agent.counts', {
              hypotheses: t('report.agent.hypotheses', { count: report.hypotheses.length }),
              techniques: t('report.agent.techniques', { count: report.attack_mapping.length }),
              actions: t('report.agent.actions', { count: report.recommended_actions.length }),
            })}{' '}
            <Link to={{ search: '?tab=summary' }} className={textActionClass}>
              {t('report.agent.openSummary')}
            </Link>
          </p>
        </Panel>
        <SecondOpinion review={review} hypotheses={report.hypotheses} />
      </div>
      <Processing analysis={analysis} review={review} />
    </div>
  )
}

function SecondOpinion({ review, hypotheses }: { review?: ModelReview; hypotheses: Hypothesis[] }) {
  const { t } = useTranslation()
  let body: ReactNode

  if (!review) body = <Empty>{t('report.agent.noReview')}</Empty>
  else if (review.status !== 'ok') {
    body = (
      <div className="mt-3 border-l-4 border-state-warn pl-4">
        <p className="text-sm">{t('report.modelReviewUnavailable')}</p>
        {review.error && (
          <p className="mt-1 text-sm text-muted">
            {t('report.agent.reason')} <code className="font-mono text-[13px] break-all">{review.error}</code>
          </p>
        )}
      </div>
    )
  } else {
    const items = [...(review.items ?? [])].sort((a, b) => a.rank - b.rank)
    body = (
      <>
        {items.length === 0 && (
          <Empty>{hypotheses.length === 0 ? t('report.agent.nothingToAssess') : t('report.agent.noItems')}</Empty>
        )}
        {items.length > 0 && (
          <div className="mt-4 space-y-4">
            {items.map((item) => (
              <OpinionCard key={item.rank} item={item} hypothesis={hypotheses.find((entry) => entry.rank === item.rank)} />
            ))}
          </div>
        )}
        {(review.rejected_count ?? 0) > 0 && (
          <p className="mt-4 border-l-4 border-state-warn pl-3 text-sm">
            {t('report.agent.rejected', { count: review.rejected_count })}
          </p>
        )}
      </>
    )
  }

  return (
    <section aria-labelledby="opinion-title" className="rounded-2xl bg-surface p-5">
      <h2 id="opinion-title" className="text-base">
        {t('report.agent.opinionTitle')}
      </h2>
      <p className="mt-1 text-sm text-muted">{t('report.agent.opinionIntro')}</p>
      {body}
    </section>
  )
}

// One remark from Gemini on one hypothesis, with the evidence it cited shown in full. The
// explanation is the model's own text, printed as it came.
function OpinionCard({ item, hypothesis }: { item: ModelReviewItem; hypothesis?: Hypothesis }) {
  const { t } = useTranslation()
  const cited = new Set(item.cited_alert_ids)
  const evidence = hypothesis
    ? [...asEvidence(hypothesis.evidence_for), ...asEvidence(hypothesis.evidence_against)].filter((entry) =>
        cited.has(entry.alert_id),
      )
    : []
  const shown = new Set(evidence.map((entry) => entry.alert_id))
  const loose = item.cited_alert_ids.filter((id) => !shown.has(id))

  return (
    <article className="rounded-xl border border-control p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <h3 className="text-sm font-medium">
          <span className="tabular-nums text-muted">{item.rank}.</span>{' '}
          {hypothesis?.statement ?? t('report.agent.unknownHypothesis')}
        </h3>
        <Chip>{t(`report.agent.assessment.${item.assessment}`)}</Chip>
      </div>
      <p className="mt-2 text-sm">{item.explanation}</p>
      <h4 className="mt-4 text-xs text-muted">{t('report.agent.cited', { count: item.cited_alert_ids.length })}</h4>
      {evidence.length > 0 && <EvidenceList items={evidence} empty="" />}
      {loose.length > 0 && (
        <p className="mt-2 text-sm">
          <AlertIds ids={loose} />
        </p>
      )}
    </article>
  )
}

function Processing({ analysis, review }: { analysis?: AnalysisStatus; review?: ModelReview }) {
  const { t } = useTranslation()
  const rows: { label: string; value?: ReactNode }[] = [
    { label: t('report.agent.state'), value: analysis && t(`report.agent.states.${analysis.status}`) },
    { label: t('report.agent.updated'), value: formatJobTime(analysis?.updated_at) },
    { label: t('report.agent.model'), value: review?.model },
    { label: t('report.agent.prompt'), value: review?.prompt_version },
    {
      label: t('report.agent.latency'),
      value: review?.latency_ms !== undefined ? t('report.agent.seconds', { value: (review.latency_ms / 1000).toFixed(1) }) : undefined,
    },
    { label: t('report.agent.alertsSent'), value: review?.context_stats?.alerts_sent },
  ]

  return (
    <Panel title={t('report.agent.processingTitle')}>
      {analysis && isWorking(analysis.status) && (
        <p className="mt-3 border-l-4 border-state-warn pl-3 text-sm">{t('report.agent.rerunning')}</p>
      )}
      {analysis?.status === 'error' && (
        <p className="mt-3 border-l-4 border-state-error pl-3 text-sm">
          {analysis.error ? t('case.auto.failedReason', { reason: analysis.error }) : t('case.auto.failedNoReason')}
        </p>
      )}
      <dl className="mt-3 divide-y divide-control text-sm">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex justify-between gap-4 py-2">
            <dt className="text-muted">{label}</dt>
            <dd className={`text-right tabular-nums break-all ${value === undefined || value === null ? 'text-muted' : ''}`}>
              {value ?? '-'}
            </dd>
          </div>
        ))}
      </dl>
      {review?.attempts && review.attempts.length > 0 && (
        <>
          <h3 className="mt-4 text-sm font-medium">{t('report.agent.attempts', { count: review.attempts.length })}</h3>
          <ol className="mt-2 space-y-1 text-sm">
            {review.attempts.map((attempt, index) => (
              <li key={index} className="flex justify-between gap-4">
                <code className="font-mono text-[13px] break-all">{attempt.model}</code>
                <span className="text-muted">{attempt.outcome}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </Panel>
  )
}
