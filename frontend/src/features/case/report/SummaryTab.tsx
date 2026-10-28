import { useTranslation } from 'react-i18next'

import type { Hypothesis, Report } from '../../../api/types'
import { asEvidence, groupAlertIds, interpretation, iocReferences } from './extras'
import { AlertIds, Chip, Confidence, Empty, EvidenceList, Panel, TextList } from './parts'

// 1152 container minus 2 x 24 padding = 1104 = 720 main column + 24 gap + 360 rail, as in New Case.
export function SummaryTab({ report }: { report: Report }) {
  const { t } = useTranslation()
  const hypotheses = [...report.hypotheses].sort((a, b) => a.rank - b.rank)

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <Panel title={t('report.summary.title')}>
          <p className="mt-2 text-base">{report.executive_summary}</p>
        </Panel>
        <section aria-labelledby="hypotheses-title" className="space-y-4">
          <h2 id="hypotheses-title" className="text-base">
            {t('report.hypotheses.title', { count: hypotheses.length })}
          </h2>
          {hypotheses.length === 0 ? (
            <div className="rounded-2xl bg-surface p-5">
              <Empty>{t('report.hypotheses.none')}</Empty>
            </div>
          ) : (
            hypotheses.map((hypothesis) => <HypothesisCard key={hypothesis.rank} hypothesis={hypothesis} />)
          )}
        </section>
      </div>

      <div className="space-y-6">
        <Actions actions={report.recommended_actions} />
        <Panel title={t('report.limits.title')}>
          <TextList items={report.limitations} empty={t('report.limits.none')} />
          {report.input.missing_fields && report.input.missing_fields.length > 0 && (
            <>
              <h3 className="mt-5 text-sm font-medium">{t('report.limits.missingFields')}</h3>
              <ul className="mt-2 space-y-1">
                {report.input.missing_fields.map((field) => (
                  <li key={field}>
                    <code className="font-mono text-[13px] break-all">{field}</code>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Panel>
      </div>
    </div>
  )
}

function HypothesisCard({ hypothesis }: { hypothesis: Hypothesis }) {
  const { t } = useTranslation()
  const against = asEvidence(hypothesis.evidence_against)
  const support = asEvidence(hypothesis.evidence_for)
  const group = groupAlertIds(hypothesis)
  const iocs = iocReferences(hypothesis)
  const reading = interpretation(hypothesis)

  return (
    <article className="rounded-2xl bg-surface p-5">
      <h3 className="text-base">
        <span className="tabular-nums text-muted">{hypothesis.rank}.</span> {hypothesis.statement}
      </h3>
      <div className="mt-3">
        <Confidence value={hypothesis.confidence} />
        <p className="mt-1 text-sm text-muted">{hypothesis.confidence_basis}</p>
      </div>
      {reading && (
        <div className="mt-4">
          <h4 className="flex flex-wrap items-baseline gap-x-2 text-sm font-medium">
            {t('report.hypotheses.interpretation')}
            <Chip>{t(`report.hypotheses.source.${reading.source}`, { defaultValue: reading.source })}</Chip>
          </h4>
          <p className="mt-1 text-sm">
            {t(`report.hypotheses.assessment.${reading.assessment}`)} {reading.explanation}
          </p>
          {reading.cited_alert_ids.length > 0 && (
            <p className="mt-1 text-sm">
              <span className="text-muted">{t('report.hypotheses.cites')} </span>
              <AlertIds ids={reading.cited_alert_ids} />
            </p>
          )}
        </div>
      )}
      {group.length > 0 && (
        <p className="mt-3 text-sm">
          <span className="text-muted">{t('report.hypotheses.group')} </span>
          <AlertIds ids={group} />
        </p>
      )}

      {/* Evidence against sits beside the evidence for, at the same size, even when it is empty. */}
      <div className="mt-5 grid gap-x-6 gap-y-4 md:grid-cols-2">
        <div>
          <h4 className="text-sm font-medium">{t('report.hypotheses.for', { count: support.length })}</h4>
          <EvidenceList items={support} empty={t('report.hypotheses.noneFor')} />
        </div>
        <div>
          <h4 className="text-sm font-medium">{t('report.hypotheses.against', { count: against.length })}</h4>
          <EvidenceList items={against} empty={t('report.hypotheses.noneAgainst')} />
        </div>
      </div>

      <div className="mt-5 grid gap-x-6 gap-y-4 md:grid-cols-2">
        <div>
          <h4 className="text-sm font-medium">{t('report.hypotheses.alternatives')}</h4>
          <TextList items={hypothesis.alternatives ?? []} empty={t('report.hypotheses.noAlternatives')} />
        </div>
        <div>
          <h4 className="text-sm font-medium">{t('report.hypotheses.unknowns')}</h4>
          <TextList items={hypothesis.unknowns} empty={t('report.hypotheses.noUnknowns')} />
        </div>
      </div>

      {iocs.length > 0 && (
        <div className="mt-5">
          <h4 className="text-sm font-medium">{t('report.hypotheses.iocs', { count: iocs.length })}</h4>
          <ul className="divide-y divide-control">
            {iocs.map((ioc, index) => (
              <li key={`${ioc.evidence_id}-${ioc.alert_id}-${index}`} className="py-3 text-sm">
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <Chip>{ioc.observable.type}</Chip>
                  <code className="font-mono text-[13px] break-all">{ioc.observable.value}</code>
                </p>
                <p className="mt-1 text-muted">
                  {t('report.hypotheses.iocSource', { provider: ioc.provider, alert: ioc.alert_id })}
                </p>
                <p className="mt-0.5 text-muted">{ioc.relevance}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}

function Actions({ actions }: { actions: Report['recommended_actions'] }) {
  const { t } = useTranslation()

  return (
    <Panel title={t('report.actions.title', { count: actions.length })}>
      {actions.length === 0 ? (
        <Empty>{t('report.actions.none')}</Empty>
      ) : (
        <ul className="divide-y divide-control">
          {actions.map((action, index) => (
            <li key={index} className="py-3">
              <p className="text-sm">
                <span className="sr-only">{t('report.actions.priority')} </span>
                <Chip>{t(`report.priority.${action.priority}`)}</Chip>
              </p>
              <p className="mt-1.5 text-sm font-medium">{action.action}</p>
              <p className="mt-0.5 text-sm text-muted">{action.rationale}</p>
              {action.evidence_ids.length > 0 && (
                <p className="mt-1 text-xs text-muted">
                  {t('report.actions.basedOn')} <AlertIds ids={action.evidence_ids} />
                </p>
              )}
              {action.requires_human_approval && (
                <p className="mt-2 border-l-4 border-state-warn pl-2 text-sm">{t('report.actions.approval')}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
