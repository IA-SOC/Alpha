import { useTranslation } from 'react-i18next'

import type { Correlation, Investigation, TimelineEntry } from '../../../api/types'
import { textActionClass } from '../../../ui/buttons'
import { stage } from './extras'
import { splitTimeline } from './timeline'
import { formatUtc } from './format'
import { AlertIds, Chip, Empty, Panel } from './parts'

// 1104 = 720 chronology + 24 gap + 360 correlation rail.
export function TimelineTab({ investigation }: { investigation: Investigation }) {
  const { t } = useTranslation()
  const { report, correlation } = investigation
  const { story, noise, undated } = splitTimeline(report.timeline, correlation)

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <Panel title={t('report.timeline.title', { count: story.length })}>
          <p className="mt-1 text-sm text-muted">{t('report.timeline.intro')}</p>
          <Events entries={story} correlation={correlation} empty={t('report.timeline.none')} />
        </Panel>
        <Panel title={t('report.timeline.noiseTitle', { count: noise.length })}>
          <p className="mt-1 text-sm text-muted">{t('report.timeline.noiseIntro')}</p>
          <Events entries={noise} correlation={correlation} empty={t('report.timeline.noNoise')} />
        </Panel>
        <Panel title={t('report.timeline.undatedTitle', { count: undated.length })}>
          <p className="mt-1 text-sm text-muted">{t('report.timeline.undatedIntro')}</p>
          <Events entries={undated} correlation={correlation} empty={t('report.timeline.noUndated')} />
        </Panel>
      </div>
      <CorrelationPanel correlation={correlation} />
    </div>
  )
}

function Events({ entries, correlation, empty }: { entries: TimelineEntry[]; correlation: Correlation; empty: string }) {
  if (entries.length === 0) return <Empty>{empty}</Empty>
  return (
    <ol className="mt-3 divide-y divide-control">
      {entries.map((entry, index) => (
        <Event key={`${entry.timestamp_original}-${entry.alert_ids.join()}-${index}`} entry={entry} correlation={correlation} />
      ))}
    </ol>
  )
}

function Event({ entry, correlation }: { entry: TimelineEntry; correlation: Correlation }) {
  const { t } = useTranslation()
  const utc = formatUtc(entry.timestamp_utc)
  const uncertain = entry.alert_ids.filter((id) => correlation.alerts.some((alert) => alert.alert_id === id && alert.classification === 'uncertain'))
  const phase = stage(entry)

  return (
    <li className="grid gap-x-6 gap-y-1 py-3 sm:grid-cols-[200px_minmax(0,1fr)]">
      <div className="text-sm">
        {utc ? <p className="font-medium tabular-nums">{utc}</p> : <p className="text-muted">{t('report.timeline.noTime')}</p>}
        {entry.timestamp_original && entry.timestamp_original !== entry.timestamp_utc && (
          <p className="text-xs text-muted">{t('report.timeline.asSent', { value: entry.timestamp_original })}</p>
        )}
        {entry.timezone_unknown && <p className="text-xs text-muted">{t('report.timeline.timezoneUnknown')}</p>}
      </div>
      <div className="text-sm">
        <p>{entry.description}</p>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          {phase && <Chip>{t(`report.stage.${phase}`, { defaultValue: phase })}</Chip>}
          {entry.certainty !== 'observed' && <Chip>{t(`report.certainty.${entry.certainty}`)}</Chip>}
          {uncertain.length > 0 && <Chip>{t('report.timeline.uncertainLink')}</Chip>}
          <AlertIds ids={entry.alert_ids} />
        </p>
      </div>
    </li>
  )
}

function CorrelationPanel({ correlation }: { correlation: Correlation }) {
  const { t } = useTranslation()
  const uncertain = correlation.alerts.filter((alert) => alert.classification === 'uncertain')
  const unrelated = correlation.alerts.filter((alert) => alert.classification === 'unrelated')

  return (
    <Panel title={t('report.correlationPanel.title')}>
      <p className="mt-1 text-sm text-muted">{t('report.correlationPanel.intro', { seconds: correlation.window_seconds })}</p>

      <h3 className="mt-5 text-sm font-medium">{t('report.correlationPanel.groups', { count: correlation.related_groups.length })}</h3>
      {correlation.related_groups.length === 0 ? (
        <Empty>{t('report.correlationPanel.noGroups')}</Empty>
      ) : (
        <ul className="mt-2 space-y-2 text-sm">
          {correlation.related_groups.map((group, index) => (
            <li key={group.join()}>
              <span className="text-muted">{t('report.correlationPanel.group', { number: index + 1 })} </span>
              <AlertIds ids={group} />
            </li>
          ))}
        </ul>
      )}

      <AlertsOfKind title={t('report.correlationPanel.uncertain', { count: uncertain.length })} alerts={uncertain} />
      <AlertsOfKind title={t('report.correlationPanel.unrelated', { count: unrelated.length })} alerts={unrelated} />

      <details className="mt-5">
        <summary className={`cursor-pointer ${textActionClass}`}>
          {t('report.correlationPanel.pairs', { count: correlation.relationships.length })}
        </summary>
        <ul className="mt-2 divide-y divide-control text-sm">
          {correlation.relationships.map((pair) => (
            <li key={pair.relationship_id} className="py-2.5">
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <AlertIds ids={pair.alert_ids} />
                <Chip>{t(`report.correlation.${pair.classification}`)}</Chip>
              </p>
              <p className="mt-1 text-muted">
                {pair.explanation}
                {pair.time_delta_seconds !== null && ` ${t('report.correlationPanel.apart', { seconds: pair.time_delta_seconds })}`}
              </p>
              <ul className="mt-1 space-y-0.5 text-xs text-muted">
                {pair.evidence.map((item, index) => (
                  <li key={index}>{item.observation}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </details>
    </Panel>
  )
}

function AlertsOfKind({ title, alerts }: { title: string; alerts: Correlation['alerts'] }) {
  const { t } = useTranslation()

  return (
    <>
      <h3 className="mt-5 text-sm font-medium">{title}</h3>
      {alerts.length === 0 ? (
        <Empty>{t('report.correlationPanel.noneOfKind')}</Empty>
      ) : (
        <ul className="mt-2 space-y-2 text-sm">
          {alerts.map((alert) => (
            <li key={alert.alert_id}>
              <AlertIds ids={[alert.alert_id]} />
              <p className="text-muted">{alert.explanation}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
