import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import type { Evidence, Hypothesis, SourceField } from '../../../api/types'
import { textActionClass } from '../../../ui/buttons'
import { formatValue } from './format'
import { resolvePointer, sameValue } from './pointer'
import { useSubmittedCase } from './submittedCase'

export function Panel({ title, children, className = '' }: { title: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl bg-surface p-5 ${className}`}>
      <h2 className="text-base">{title}</h2>
      {children}
    </section>
  )
}

// A grey dash or a sentence for what is missing, so an empty block keeps its frame.
export function Empty({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-sm text-muted">{children}</p>
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className="inline-flex flex-none items-center whitespace-nowrap rounded bg-ground px-1.5 text-xs font-medium">{children}</span>
}

// Every alert ID opens that alert on the Evidence tab, with the fields the report read from it.
export function AlertId({ id }: { id: string }) {
  const { t } = useTranslation()

  return (
    <Link
      to={{ search: `?tab=evidence&alert=${encodeURIComponent(id)}` }}
      aria-label={t('report.evidence.openAlert', { id })}
      className="font-mono text-[13px] break-all underline decoration-control decoration-1 underline-offset-4 hover:decoration-aligo-blanco"
    >
      {id}
    </Link>
  )
}

export function AlertIds({ ids }: { ids: readonly string[] }) {
  return (
    <span className="inline-flex flex-wrap gap-x-3 gap-y-1">
      {ids.map((id) => (
        <AlertId key={id} id={id} />
      ))}
    </span>
  )
}

const levels: Hypothesis['confidence'][] = ['insuficiente', 'baja', 'media', 'alta']

// Four ordinal levels, never a percentage: the agent's rubric gives no calibrated probability.
export function Confidence({ value }: { value: Hypothesis['confidence'] }) {
  const { t } = useTranslation()
  const level = levels.indexOf(value)

  return (
    <p className="flex items-center gap-3 text-sm">
      <span className="flex gap-1" aria-hidden="true">
        {[1, 2, 3].map((step) => (
          <span key={step} className={`h-2 w-6 rounded-full ${step <= level ? 'bg-aligo-rojo' : 'bg-control'}`} />
        ))}
      </span>
      <span>
        <span className="text-muted">{t('report.confidence.label')} </span>
        <span className="font-medium">{t(`report.confidence.${value}`)}</span>
      </span>
    </p>
  )
}

export function EvidenceList({ items, empty }: { items: Evidence[]; empty: string }) {
  if (items.length === 0) return <Empty>{empty}</Empty>
  return (
    <ul className="divide-y divide-control">
      {items.map((evidence, index) => (
        <EvidenceItem key={`${evidence.alert_id}-${index}`} evidence={evidence} />
      ))}
    </ul>
  )
}

function EvidenceItem({ evidence }: { evidence: Evidence }) {
  const { t } = useTranslation()

  return (
    <li className="py-3">
      <AlertId id={evidence.alert_id} />
      <p className="mt-1 text-sm">{evidence.observation}</p>
      <p className="mt-0.5 text-sm text-muted">{evidence.relevance}</p>
      {evidence.fields && evidence.fields.length > 0 && (
        <p className="mt-1 text-xs text-muted">{t('report.evidence.fields', { fields: evidence.fields.join(', ') })}</p>
      )}
      {evidence.source_fields && evidence.source_fields.length > 0 && (
        <details className="mt-2">
          <summary className={`cursor-pointer ${textActionClass}`}>
            {t('report.evidence.sourceFields', { count: evidence.source_fields.length })}
          </summary>
          <SourceFields fields={evidence.source_fields} />
        </details>
      )}
    </li>
  )
}

export function TextList({ items, empty }: { items: readonly string[]; empty: string }) {
  if (items.length === 0) return <Empty>{empty}</Empty>
  return (
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm marker:text-muted">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  )
}

// Each cited field next to what the submitted case really holds at that path. A path that does not
// resolve, or a value that differs, is said in words rather than hidden.
export function SourceFields({ fields }: { fields: SourceField[] }) {
  const { t } = useTranslation()
  const { submitted, failed } = useSubmittedCase()

  return (
    <div className="mt-2 overflow-x-auto">
      {/* Fixed columns so every alert's table lines up with the next one. */}
      <table className="w-full min-w-[560px] table-fixed text-left text-sm">
        <colgroup>
          <col className="w-[44%]" />
          <col className="w-[34%]" />
          <col className="w-[22%]" />
        </colgroup>
        <thead className="text-xs text-muted">
          <tr>
            <th scope="col" className="py-1.5 pr-4 font-normal">
              {t('report.evidence.path')}
            </th>
            <th scope="col" className="py-1.5 pr-4 font-normal">
              {t('report.evidence.value')}
            </th>
            <th scope="col" className="py-1.5 font-normal">
              {t('report.evidence.check')}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-control">
          {fields.map((field) => {
            const resolved = submitted ? resolvePointer(submitted, field.path) : undefined
            let value = field.value
            let check: ReactNode
            if (!resolved) check = <span className="text-muted">{failed ? t('report.evidence.caseFailed') : t('report.evidence.caseLoading')}</span>
            else if (!resolved.found) check = <span className="border-l-4 border-state-error pl-2">{t('report.evidence.notFound')}</span>
            else if (!sameValue(resolved.value, field.value)) {
              value = resolved.value
              check = (
                <span className="border-l-4 border-state-warn pl-2">
                  {t('report.evidence.differs', { value: formatValue(field.value) })}
                </span>
              )
            } else check = <span className="text-muted">{t('report.evidence.matches')}</span>
            return (
              <tr key={`${field.alert_id}${field.path}`} className="align-top">
                <td className="py-2 pr-4">
                  <code className="font-mono text-[13px] break-all">{field.path}</code>
                </td>
                <td className="py-2 pr-4">
                  <code className="font-mono text-[13px] break-all">{formatValue(value)}</code>
                </td>
                <td className="py-2">{check}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
