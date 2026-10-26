import { useTranslation } from 'react-i18next'

import type { Report } from '../../../api/types'
import { AlertIds, Empty, Panel, TextList } from './parts'

type Named = { name: string; basis_alert_ids: string[] }

// Each list keeps the report's own label: observed, suspected or confirmed. Nothing is promoted
// from one to another here.
export function AssetsTab({ report }: { report: Report }) {
  const { t } = useTranslation()
  const radius = report.blast_radius
  const assets = (items: { asset: string; basis_alert_ids: string[] }[]) => items.map((item) => ({ name: item.asset, basis_alert_ids: item.basis_alert_ids }))
  const identities = (items: { identity: string; basis_alert_ids: string[] }[] = []) =>
    items.map((item) => ({ name: item.identity, basis_alert_ids: item.basis_alert_ids }))

  // Pairs stretch to one height so each row of two panels ends on the same line.
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Panel title={t('report.assets.observed', { count: radius.observed_assets.length })} className="lg:col-span-2">
        <p className="mt-1 text-sm text-muted">{t('report.assets.observedIntro')}</p>
        {radius.observed_assets.length === 0 ? (
          <Empty>{t('report.assets.none')}</Empty>
        ) : (
          <table className="mt-3 w-full table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[22%]" />
              <col className="w-[48%]" />
              <col className="w-[30%]" />
            </colgroup>
            <thead className="text-xs text-muted">
              <tr>
                <th scope="col" className="py-1.5 pr-4 font-normal">
                  {t('report.assets.asset')}
                </th>
                <th scope="col" className="py-1.5 pr-4 font-normal">
                  {t('report.assets.activity')}
                </th>
                <th scope="col" className="py-1.5 font-normal">
                  {t('report.assets.basis')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-control">
              {radius.observed_assets.map((item) => (
                <tr key={item.asset} className="align-top">
                  <td className="py-2.5 pr-4 font-medium break-words">{item.asset}</td>
                  <td className="py-2.5 pr-4">{item.observed_activity}</td>
                  <td className="py-2.5">
                    <AlertIds ids={item.basis_alert_ids} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
      <NamedList title={t('report.assets.suspectedAssets', { count: radius.suspected_assets.length })} items={assets(radius.suspected_assets)} />
      <NamedList title={t('report.assets.confirmedAssets', { count: radius.confirmed_assets.length })} items={assets(radius.confirmed_assets)} />
      <NamedList
        title={t('report.assets.suspectedIdentities', { count: radius.suspected_identities?.length ?? 0 })}
        items={identities(radius.suspected_identities)}
      />
      <NamedList
        title={t('report.assets.confirmedIdentities', { count: radius.confirmed_identities?.length ?? 0 })}
        items={identities(radius.confirmed_identities)}
      />
      <Panel title={t('report.assets.unknowns')} className="lg:col-span-2">
        <TextList items={radius.unknowns} empty={t('report.assets.noUnknowns')} />
      </Panel>
    </div>
  )
}

function NamedList({ title, items }: { title: string; items: Named[] }) {
  const { t } = useTranslation()

  return (
    <Panel title={title}>
      {items.length === 0 ? (
        <Empty>{t('report.assets.none')}</Empty>
      ) : (
        <ul className="mt-2 divide-y divide-control text-sm">
          {items.map((item) => (
            <li key={item.name} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
              <span className="font-medium break-words">{item.name}</span>
              <span>
                <span className="sr-only">{t('report.assets.basis')} </span>
                <AlertIds ids={item.basis_alert_ids} />
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
