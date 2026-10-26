import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import type { Evidence, Hypothesis } from '../../../api/types'

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

export function AlertId({ id }: { id: string }) {
  return <code className="font-mono text-[13px] break-all">{id}</code>
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
