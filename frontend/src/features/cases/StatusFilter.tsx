import { useTranslation } from 'react-i18next'

import { countByStatus, type StatusFilter } from './useCases'
import type { CaseListItem } from '../../api/types'

const filters: StatusFilter[] = ['all', 'open', 'closed']

// Counts come from the whole list, not from the rows on screen, so a filter never changes them.
export function FilterButtons({
  cases,
  value,
  onChange,
}: {
  cases: CaseListItem[]
  value: StatusFilter
  onChange: (next: StatusFilter) => void
}) {
  const { t } = useTranslation()
  const counts = countByStatus(cases)

  return (
    <div role="group" aria-label={t('cases.filter.label')} className="flex rounded border border-aligo-gris">
      {filters.map((filter) => (
        <button
          key={filter}
          type="button"
          aria-pressed={value === filter}
          onClick={() => onChange(filter)}
          className={`flex flex-1 items-baseline justify-center gap-1.5 px-3 py-1 text-sm ${
            value === filter
              ? 'bg-aligo-blanco font-medium text-aligo-negro'
              : 'text-aligo-gris-claro hover:text-aligo-blanco'
          }`}
        >
          {t(`cases.filter.${filter}`)}
          <span className="tabular-nums">{counts[filter]}</span>
        </button>
      ))}
    </div>
  )
}
