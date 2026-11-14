import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useMatch } from 'react-router'

import { textActionClass } from '../../ui/buttons'
import { FilterButtons } from './StatusFilter'
import { filterCases, stageOf, type StatusFilter, useCases } from './useCases'

// The stored cases, always one click away. It reads the same list as the dashboard.
export function CaseSidebar() {
  const { t } = useTranslation()
  const cases = useCases()
  const current = useMatch('/cases/:caseId')?.params.caseId
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [query, setQuery] = useState('')
  const rows = filterCases(cases.data ?? [], filter, query)

  return (
    <nav
      aria-label={t('cases.sidebar.label')}
      className="flex flex-col gap-4 border-b border-rule px-4 py-5 md:sticky md:top-0 md:h-dvh md:border-r md:border-b-0"
    >
      <div className="flex items-baseline justify-between gap-3">
        <Link to="/cases" className="text-base font-bold">
          {t('cases.sidebar.label')}
        </Link>
        <Link to="/cases/new" className={textActionClass}>
          {t('cases.newCase')}
        </Link>
      </div>
      {cases.data && (
        <>
          <FilterButtons cases={cases.data} value={filter} onChange={setFilter} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label={t('cases.sidebar.search')}
            placeholder={t('cases.sidebar.search')}
            className="h-9 w-full rounded-xl bg-surface px-4 text-sm text-aligo-blanco placeholder:text-muted focus:outline-2 focus:outline-aligo-rojo"
          />
        </>
      )}
      {cases.isPending && <p className="text-sm text-muted">{t('cases.loading')}</p>}
      {cases.isError && (
        <p role="status" className="border-l-4 border-state-error pl-3 text-sm">
          {t('cases.error.title')}{' '}
          <button type="button" onClick={() => void cases.refetch()} className={textActionClass}>
            {t('cases.error.retry')}
          </button>
        </p>
      )}
      {cases.data && rows.length === 0 && <p className="text-sm text-muted">{t('cases.sidebar.none')}</p>}
      <ul className="-mx-2 min-h-0 flex-1 overflow-y-auto">
        {rows.map((item) => {
          const selected = item.case_id === current
          return (
            <li key={item.case_id}>
              <Link
                to={`/cases/${item.case_id}`}
                aria-current={selected ? 'page' : undefined}
                className={`block rounded-lg px-2 py-2 ${selected ? 'bg-surface' : 'hover:bg-surface'}`}
              >
                <span className={`block truncate text-sm font-medium ${item.status === 'closed' ? 'text-muted' : ''}`}>
                  {item.submitted_case_id}
                </span>
                <span className="mt-0.5 block truncate text-xs text-muted">
                  {item.status === 'closed' ? `${t('cases.sidebar.closedMark')}, ` : ''}
                  {t(`cases.stage.${stageOf(item)}`)}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
