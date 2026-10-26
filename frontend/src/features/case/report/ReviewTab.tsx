import { useTranslation } from 'react-i18next'

import type { Report } from '../../../api/types'
import { formatUtc } from './format'
import { Panel } from './parts'

// Read only for now. Recording a decision is issue #56.
export function ReviewTab({ report }: { report: Report }) {
  const { t } = useTranslation()
  const { review } = report
  const rows = [
    [t('report.review.status'), t(`report.reviewStatus.${review.status}`)],
    [t('report.review.analyst'), review.analyst],
    [t('report.review.notes'), review.notes],
    [t('report.review.reviewedAt'), formatUtc(review.reviewed_at)],
  ] as const

  return (
    <Panel title={t('report.review.title')} className="max-w-2xl">
      <dl className="mt-3 divide-y divide-control">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[140px_minmax(0,1fr)] gap-4 py-2.5 text-sm">
            <dt className="text-muted">{label}</dt>
            <dd className={value ? '' : 'text-muted'}>{value || '-'}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-sm text-muted">{t('report.review.soon')}</p>
    </Panel>
  )
}
