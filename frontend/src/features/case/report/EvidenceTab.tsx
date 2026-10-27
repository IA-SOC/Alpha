import { useEffect, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'

import type { Correlation, EnrichmentItem, IncidentCase, Investigation } from '../../../api/types'
import { textActionClass } from '../../../ui/buttons'
import { type AlertCitations, type Citation, citationsByAlert } from './citations'
import { enrichmentItems } from './extras'
import { formatValue } from './format'
import { AlertIds, Chip, Empty, Panel, SourceFields } from './parts'
import { resolvePointer } from './pointer'
import { originalSeverity } from './severity'
import { useSubmittedCase } from './submittedCase'

type SubmittedAlert = IncidentCase['alerts'][number]

// 1104 = 720 alerts + 24 gap + 360 IoC rail, the same split as Summary.
export function EvidenceTab({ investigation }: { investigation: Investigation }) {
  const { t } = useTranslation()
  const { submitted, failed } = useSubmittedCase()
  const [params] = useSearchParams()
  const target = params.get('alert')
  const citations = useMemo(() => citationsByAlert(investigation.report), [investigation.report])

  if (!submitted) {
    return (
      <div className="rounded-2xl bg-surface p-5">
        <Empty>{failed ? t('report.evidence.caseFailed') : t('report.evidence.caseLoading')}</Empty>
      </div>
    )
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section aria-labelledby="alerts-title" className="space-y-4">
        <div>
          <h2 id="alerts-title" className="text-base">
            {t('report.evidence.alertsTitle', { count: submitted.alerts.length })}
          </h2>
          <p className="mt-1 text-sm text-muted">{t('report.evidence.alertsIntro')}</p>
        </div>
        {submitted.alerts.map((alert) => (
          <AlertCard
            key={alert.alert_id}
            alert={alert}
            correlation={investigation.correlation}
            cited={citations.get(alert.alert_id)}
            targeted={alert.alert_id === target}
          />
        ))}
      </section>
      <Iocs investigation={investigation} submitted={submitted} />
    </div>
  )
}

interface AlertCardProps {
  alert: SubmittedAlert
  correlation: Correlation
  cited?: AlertCitations
  targeted: boolean
}

function AlertCard({ alert, correlation, cited, targeted }: AlertCardProps) {
  const { t } = useTranslation()
  const heading = useRef<HTMLHeadingElement>(null)
  const severity = originalSeverity(alert.raw_alert)
  const disposition = correlation.alerts.find((item) => item.alert_id === alert.alert_id)

  // Arriving from a link elsewhere in the report puts this alert in view and focus.
  useEffect(() => {
    if (!targeted) return
    heading.current?.scrollIntoView?.({ block: 'start' })
    heading.current?.focus()
  }, [targeted])

  return (
    <article id={`alert-${alert.alert_id}`} className={`scroll-mt-6 rounded-2xl bg-surface p-5 ${targeted ? 'outline-2 outline-aligo-blanco' : ''}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 ref={heading} tabIndex={-1} className="font-mono text-[15px] break-all">
          {alert.alert_id}
        </h3>
        <p className="text-sm text-muted">
          {t(`report.evidence.system.${alert.source_system}`)}
          {alert.source_version && ` ${alert.source_version}`}
        </p>
      </div>

      <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[160px_minmax(0,1fr)]">
        <dt className="text-muted">{t('report.evidence.severity')}</dt>
        <dd>
          {severity ? (
            <>
              <span className="font-medium tabular-nums">{severity.value}</span>{' '}
              <span className="text-muted">{t('report.evidence.severityField', { field: severity.field })}</span>
            </>
          ) : (
            <span className="text-muted">{t('report.evidence.noSeverity')}</span>
          )}
        </dd>
        <dt className="text-muted">{t('report.evidence.correlation')}</dt>
        <dd>
          {disposition ? (
            <>
              <span className="font-medium">{t(`report.correlation.${disposition.classification}`)}</span>
              <span className="text-muted"> {disposition.explanation}</span>
            </>
          ) : (
            <span className="text-muted">-</span>
          )}
        </dd>
        <dt className="text-muted">{t('report.evidence.citedBy')}</dt>
        <dd>
          {cited && cited.citations.length > 0 ? (
            <span className="flex flex-wrap gap-1.5">
              {cited.citations.map((citation, index) => (
                <Chip key={index}>{citationLabel(citation, t)}</Chip>
              ))}
            </span>
          ) : (
            <span className="text-muted">{t('report.evidence.notCited')}</span>
          )}
        </dd>
      </dl>

      <h4 className="mt-5 text-sm font-medium">{t('report.evidence.fieldsRead', { count: cited?.fields.length ?? 0 })}</h4>
      {cited && cited.fields.length > 0 ? <SourceFields fields={cited.fields} /> : <Empty>{t('report.evidence.noFields')}</Empty>}

      <details className="mt-4">
        <summary className={`cursor-pointer ${textActionClass}`}>{t('report.evidence.original')}</summary>
        <pre className="mt-2 max-h-96 overflow-auto rounded-xl bg-ground p-4 font-mono text-[13px] leading-5">{JSON.stringify(alert, null, 2)}</pre>
      </details>
    </article>
  )
}

function citationLabel(citation: Citation, t: ReturnType<typeof useTranslation>['t']) {
  switch (citation.kind) {
    case 'hypothesis':
      return t(`report.evidence.cite.hypothesis_${citation.side}`, { rank: citation.rank })
    case 'technique':
      return citation.name
    case 'timeline':
      return t('report.evidence.cite.timeline')
    case 'action':
      return t('report.evidence.cite.action', { number: citation.number })
  }
}

// The provider's own result, never a verdict of ours. Older reports drop raw_result from the item,
// so it is read from the submitted case at the item's source_path.
function providerResult(item: EnrichmentItem, submitted: IncidentCase) {
  if (item.raw_result !== undefined) return item.raw_result
  if (!item.source_path) return undefined
  const resolved = resolvePointer(submitted, `${item.source_path}/raw_result`)
  return resolved.found ? resolved.value : undefined
}

function Iocs({ investigation, submitted }: { investigation: Investigation; submitted: IncidentCase }) {
  const { t } = useTranslation()
  const { enrichment } = investigation.report
  const items = enrichmentItems(investigation.report)

  return (
    <Panel title={t('report.iocs.title', { count: items.length })}>
      <p className="mt-1 text-sm">
        <span className="text-muted">{t('report.iocs.status')} </span>
        <span className="font-medium">{t(`report.iocs.statuses.${enrichment.status}`)}</span>
      </p>
      {enrichment.note && <p className="mt-1 text-sm text-muted">{enrichment.note}</p>}
      {items.length === 0 ? (
        <Empty>{t('report.iocs.none')}</Empty>
      ) : (
        <ul className="mt-2 divide-y divide-control">
          {items.map((item, index) => {
            const result = providerResult(item, submitted)
            const facts = summarize(result)
            return (
              <li key={item.evidence_id ?? index} className="py-3 text-sm">
                {item.observable && (
                  <p className="flex flex-wrap items-baseline gap-x-2">
                    <Chip>{item.observable.type}</Chip>
                    <code className="font-mono text-[13px] break-all">{item.observable.value}</code>
                  </p>
                )}
                <p className="mt-1 text-muted">{t('report.iocs.provider', { provider: item.provider ?? '-' })}</p>
                <p className="mt-1">
                  <span className="text-muted">{t('report.iocs.alerts')} </span>
                  {item.associated_alert_ids && item.associated_alert_ids.length > 0 ? (
                    <AlertIds ids={item.associated_alert_ids} />
                  ) : (
                    <span className="text-muted">{t('report.iocs.noAlerts')}</span>
                  )}
                </p>
                {result === undefined ? (
                  <p className="mt-1 text-muted">{t('report.iocs.noResult')}</p>
                ) : (
                  <>
                    <p className="mt-2 text-xs text-muted">{t('report.iocs.result')}</p>
                    {facts.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {facts.map(([key, value]) => (
                          <li key={key}>
                            <code className="font-mono text-[13px] break-all">
                              {key}: {value}
                            </code>
                          </li>
                        ))}
                      </ul>
                    )}
                    <details className="mt-2">
                      <summary className={`cursor-pointer ${textActionClass}`}>{t('report.iocs.full')}</summary>
                      <pre className="mt-2 max-h-72 overflow-auto rounded-xl bg-ground p-3 font-mono text-[13px] leading-5">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    </details>
                  </>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

// The top level plain values of the provider's result, at most four, as it sent them.
function summarize(result: unknown): [string, string][] {
  if (typeof result !== 'object' || result === null || Array.isArray(result)) {
    return result === undefined ? [] : [['result', formatValue(result)]]
  }
  return Object.entries(result)
    .filter(([, value]) => value === null || typeof value !== 'object')
    .slice(0, 4)
    .map(([key, value]) => [key, formatValue(value)])
}
