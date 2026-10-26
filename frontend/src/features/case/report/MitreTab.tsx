import { useTranslation } from 'react-i18next'

import type { AttackTechnique, Report } from '../../../api/types'
import { asEvidence } from './extras'
import { Chip, Empty, EvidenceList } from './parts'

export function MitreTab({ report }: { report: Report }) {
  const { t } = useTranslation()

  return (
    <div className="max-w-4xl space-y-4">
      <p className="text-sm text-muted">{t('report.mitre.intro')}</p>
      {report.attack_mapping.length === 0 ? (
        <div className="rounded-2xl bg-surface p-5">
          <Empty>{t('report.mitre.none')}</Empty>
        </div>
      ) : (
        report.attack_mapping.map((technique, index) => <TechniqueCard key={`${technique.technique_id}-${index}`} technique={technique} />)
      )}
    </div>
  )
}

function TechniqueCard({ technique }: { technique: AttackTechnique }) {
  const { t } = useTranslation()
  const evidence = asEvidence(technique.evidence)

  return (
    <article className="rounded-2xl bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base">
            {technique.technique_id && <code className="mr-2 font-mono text-[15px]">{technique.technique_id}</code>} {technique.technique_name}
          </h2>
          <p className="mt-0.5 text-sm text-muted">{technique.tactic ?? t('report.mitre.noTactic')}</p>
        </div>
        <p className="text-sm">
          <span className="sr-only">{t('report.mitre.status')} </span>
          <Chip>{t(`report.mitre.statuses.${technique.status}`)}</Chip>
        </p>
      </div>
      <h3 className="mt-4 text-sm font-medium">{t('report.mitre.evidence', { count: evidence.length })}</h3>
      <EvidenceList items={evidence} empty={t('report.mitre.noEvidence')} />
      <p className="mt-2 text-xs text-muted">
        {technique.source_version ? t('report.mitre.version', { version: technique.source_version }) : t('report.mitre.noVersion')}
      </p>
    </article>
  )
}
