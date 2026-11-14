import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router'

import type { CaseListItem } from '../../api/types'
import { PrimaryButton, TextButton, textActionClass } from '../../ui/buttons'
import { formatCreated } from './format'
import { FilterButtons } from './StatusFilter'
import { filterCases, stageOf, type StatusFilter, useCases, useSetCaseStatus } from './useCases'

const parseFilter = (value: string | null): StatusFilter => (value === 'open' || value === 'closed' ? value : 'all')

// The stored cases as a work list. The question it answers: which case needs me next?
export function CasesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const filter = parseFilter(params.get('status'))
  const cases = useCases()
  const change = useSetCaseStatus()

  const all = cases.data ?? []
  const rows = filterCases(all, filter)

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl">{t('cases.title')}</h1>
          {cases.data && <p className="mt-1 text-[15px] text-muted">{t('cases.total', { count: all.length })}</p>}
        </div>
        <PrimaryButton onClick={() => navigate('/cases/new')}>{t('cases.newCase')}</PrimaryButton>
      </div>

      {cases.data && <Summary cases={all} />}

      <div className="mt-8 max-w-sm">
        <FilterButtons
          cases={all}
          value={filter}
          onChange={(next) => setParams(next === 'all' ? {} : { status: next }, { replace: true })}
        />
      </div>

      {change.isError && (
        <p role="alert" className="mt-4 border-l-4 border-state-error pl-3 text-sm">
          {t('cases.actions.failed')}
        </p>
      )}

      <div className="mt-4">
        {cases.isPending && <p className="text-sm text-muted">{t('cases.loading')}</p>}
        {cases.isError && (
          <section role="alert" className="rounded-2xl bg-surface p-5">
            <h2 className="text-base">{t('cases.error.title')}</h2>
            <p className="mt-1 text-sm text-muted">{t('cases.error.body')}</p>
            <TextButton onClick={() => void cases.refetch()} className="mt-3">
              {t('cases.error.retry')}
            </TextButton>
          </section>
        )}
        {cases.data && all.length === 0 && (
          <section className="rounded-2xl bg-surface p-5">
            <h2 className="text-base">{t('cases.empty.title')}</h2>
            <p className="mt-1 text-sm text-muted">{t('cases.empty.body')}</p>
            <Link to="/cases/new" className={`mt-3 inline-block ${textActionClass}`}>
              {t('cases.newCase')}
            </Link>
          </section>
        )}
        {cases.data && all.length > 0 && rows.length === 0 && (
          <p className="rounded-xl border border-dashed border-control px-4 py-3 text-sm text-muted">
            {t('cases.empty.filtered', { status: t(`cases.filter.${filter}`).toLowerCase() })}
          </p>
        )}
        {rows.length > 0 && (
          <CaseTable
            rows={rows}
            busyId={change.isPending ? change.variables.caseId : undefined}
            onToggle={(item) => change.mutate({ caseId: item.case_id, status: item.status === 'open' ? 'closed' : 'open' })}
          />
        )}
      </div>
    </div>
  )
}

// Three counts in one divided strip, label over figure. Zero prints as zero.
function Summary({ cases }: { cases: CaseListItem[] }) {
  const { t } = useTranslation()
  const open = cases.filter((item) => item.status === 'open')
  const stages = open.map(stageOf)
  const cells = [
    { key: 'open', value: open.length },
    { key: 'waiting', value: stages.filter((stage) => stage === 'pending').length },
    { key: 'notRun', value: stages.filter((stage) => stage === 'notInvestigated').length },
  ]

  return (
    <dl
      aria-label={t('cases.summary.label')}
      className="mt-6 grid max-w-2xl grid-cols-3 divide-x divide-rule rounded-2xl bg-surface"
    >
      {cells.map((cell) => (
        <div key={cell.key} className="px-5 py-4">
          <dt className="text-sm text-muted">{t(`cases.summary.${cell.key}`)}</dt>
          <dd className="mt-1 text-2xl font-medium tabular-nums">{cell.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function CaseTable({
  rows,
  busyId,
  onToggle,
}: {
  rows: CaseListItem[]
  busyId?: string
  onToggle: (item: CaseListItem) => void
}) {
  const { t } = useTranslation()

  return (
    // The identity column takes the most width, so case IDs are not cut. 36 + 12 + 24 + 16 + 12 = 100.
    <table className="w-full table-fixed text-left text-sm">
      <caption className="sr-only">{t('cases.table.label')}</caption>
      <colgroup>
        <col className="w-[36%]" />
        <col className="w-[12%]" />
        <col className="w-[24%]" />
        <col className="w-[16%]" />
        <col className="w-[12%]" />
      </colgroup>
      <thead>
        <tr className="border-b border-control text-muted">
          <th scope="col" className="py-2 pr-4 font-normal">{t('cases.table.case')}</th>
          <th scope="col" className="py-2 pr-4 font-normal">{t('cases.table.status')}</th>
          <th scope="col" className="py-2 pr-4 font-normal">{t('cases.table.investigation')}</th>
          <th scope="col" className="py-2 pr-4 text-right font-normal">{t('cases.table.created')}</th>
          <th scope="col" className="py-2 text-right font-normal">{t('cases.table.actions')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((item) => {
          const stage = stageOf(item)
          const closed = item.status === 'closed'
          return (
            <tr key={item.case_id} className="border-b border-rule">
              <td className="max-w-0 py-3 pr-4">
                <Link to={`/cases/${item.case_id}`} className="block truncate font-medium hover:underline">
                  {item.submitted_case_id}
                </Link>
                <code className="mt-0.5 block truncate font-mono text-xs text-muted">{item.case_id}</code>
              </td>
              <td className={`py-3 pr-4 ${closed ? 'text-muted' : ''}`}>{t(`cases.status.${item.status}`)}</td>
              <td className="py-3 pr-4">
                <span className="inline-flex items-center gap-2">
                  {stage === 'pending' && !closed && <span aria-hidden className="size-1.5 rounded-full bg-state-warn" />}
                  {t(`cases.stage.${stage}`)}
                </span>
              </td>
              <td className="py-3 pr-4 text-right tabular-nums text-muted">{formatCreated(item.created_at)}</td>
              <td className="py-3 text-right">
                <TextButton
                  onClick={() => onToggle(item)}
                  disabled={busyId === item.case_id}
                  aria-label={`${t(closed ? 'cases.actions.reopenCase' : 'cases.actions.closeCase')}: ${item.submitted_case_id}`}
                >
                  {t(closed ? 'cases.actions.reopen' : 'cases.actions.close')}
                </TextButton>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
