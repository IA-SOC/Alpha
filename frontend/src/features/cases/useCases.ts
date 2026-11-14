import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../../api/client'
import type { CaseListItem, CaseStatus } from '../../api/types'

export const casesKey = ['cases'] as const

// One list feeds the sidebar, the dashboard and the case header, so they never disagree.
export function useCases() {
  return useQuery({ queryKey: casesKey, queryFn: api.listCases })
}

// The backend answers with the updated row, so the cache takes it as it is.
export function useSetCaseStatus() {
  const queryClient = useQueryClient()
  return useMutation<CaseListItem, Error, { caseId: string; status: CaseStatus }>({
    mutationFn: ({ caseId, status }) => api.setCaseStatus(caseId, status),
    onSuccess: (updated) =>
      queryClient.setQueryData<CaseListItem[]>(casesKey, (list) =>
        list?.map((item) => (item.case_id === updated.case_id ? updated : item)),
      ),
  })
}

export type StatusFilter = 'all' | CaseStatus

export function countByStatus(cases: CaseListItem[]) {
  const open = cases.filter((item) => item.status === 'open').length
  return { all: cases.length, open, closed: cases.length - open }
}

export function filterCases(cases: CaseListItem[], filter: StatusFilter, query = '') {
  const needle = query.trim().toLowerCase()
  return cases
    .filter((item) => filter === 'all' || item.status === filter)
    .filter((item) => !needle || item.submitted_case_id.toLowerCase().includes(needle) || item.case_id.includes(needle))
    .toSorted((a, b) => b.created_at.localeCompare(a.created_at))
}

// Where the case stands in the work, read from the stored investigation. No investigation
// means the agent has not run on it yet.
export type Stage = 'notInvestigated' | 'pending' | 'validated' | 'corrected' | 'rejected'

export function stageOf(item: CaseListItem): Stage {
  if (!item.investigation) return 'notInvestigated'
  const review = item.investigation.review_status
  return review === 'validated' || review === 'corrected' || review === 'rejected' ? review : 'pending'
}
