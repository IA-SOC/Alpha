import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'

import type { Investigation, Report } from '../../../api/types'
import { type Tab, Tabs } from '../../../ui/Tabs'
import { timeWindow } from './extras'
import { formatUtc, formatUtcRange } from './format'
import { MitreTab } from './MitreTab'
import { ReviewTab } from './ReviewTab'
import { SummaryTab } from './SummaryTab'

export function ReportView({ investigation }: { investigation: Investigation }) {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const { report } = investigation

  const tabs: Tab[] = [
    { id: 'summary', label: t('report.tabs.summary'), content: <SummaryTab report={report} /> },
    { id: 'mitre', label: t('report.tabs.mitre'), content: <MitreTab report={report} /> },
    { id: 'review', label: t('report.tabs.review'), content: <ReviewTab report={report} /> },
  ]

  return (
    <div className="space-y-6">
      <Facts report={report} />
      <Tabs
        label={t('report.tabs.label')}
        tabs={tabs}
        selected={params.get('tab') ?? 'summary'}
        onSelect={(tab) => setParams(tab === 'summary' ? {} : { tab }, { replace: true })}
      />
    </div>
  )
}

// One divided strip rather than a tile per fact: these are the report's header fields.
function Facts({ report }: { report: Report }) {
  const { t } = useTranslation()
  const window = timeWindow(report)
  const facts: { label: string; value?: ReactNode }[] = [
    { label: t('report.facts.sources'), value: t(`report.sourceFormat.${report.input.source_format}`) },
    {
      label: t('report.facts.alerts'),
      value: t('report.facts.alertsValue', { processed: report.input.processed_alert_count, total: report.input.alert_count }),
    },
    { label: t('report.facts.window'), value: window.start && window.end && <TimeRange start={window.start} end={window.end} /> },
    {
      label: t('report.facts.generated'),
      value: report.generated_at && <span className="whitespace-nowrap">{formatUtc(report.generated_at)}</span>,
    },
    { label: t('report.facts.review'), value: t(`report.reviewStatus.${report.review.status}`) },
  ]

  return (
    <dl className="grid gap-px overflow-hidden rounded-2xl bg-ground sm:grid-cols-2 lg:grid-cols-[repeat(2,minmax(0,1fr))_minmax(0,1.6fr)_repeat(2,minmax(0,1fr))]">
      {facts.map(({ label, value }) => (
        <div key={label} className="bg-surface px-5 py-4 sm:last:col-span-2 lg:last:col-span-1">
          <dt className="text-xs text-muted">{label}</dt>
          <dd className={`mt-1 text-sm tabular-nums ${value ? 'font-medium' : 'text-muted'}`}>{value || '-'}</dd>
        </div>
      ))}
    </dl>
  )
}

function TimeRange({ start, end }: { start: string; end: string }) {
  const { t } = useTranslation()
  const { from, to } = formatUtcRange(start, end)

  return (
    <>
      <span className="whitespace-nowrap">{from}</span> {t('report.facts.to')} <span className="whitespace-nowrap">{to}</span>
    </>
  )
}
