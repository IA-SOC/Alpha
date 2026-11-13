import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { api } from '../../api/client'
import type { AnalysisState } from '../../api/types'
import { casesKey } from '../cases/useCases'
import { formatUtc } from './report/format'

export const analysisKey = (caseId: string) => ['analysis', caseId] as const

// How often the page asks while the backend works on the case. The run itself takes seconds to
// a few minutes, so every 3 seconds is quick enough to feel live without flooding the backend.
export const analysisPollMs = 3000

export const isWorking = (state?: AnalysisState) => state === 'queued' || state === 'running'

// Accepting a case queues its analysis on the backend, so the page follows that job instead of
// waiting for the analyst to start it. When the job ends, the report and the case list reload.
export function useAnalysisStatus(caseId: string) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: analysisKey(caseId),
    queryFn: () => api.getAnalysisStatus(caseId),
    // An older backend without the endpoint answers 404. That is an answer, not a hiccup.
    retry: false,
    refetchInterval: (current) => (isWorking(current.state.data?.status) ? analysisPollMs : false),
  })

  const state = query.data?.status
  const previous = useRef(state)
  useEffect(() => {
    if (isWorking(previous.current) && !isWorking(state)) {
      void queryClient.invalidateQueries({ queryKey: ['investigation', caseId] })
      void queryClient.invalidateQueries({ queryKey: casesKey })
    }
    previous.current = state
  }, [state, caseId, queryClient])

  return query
}

// SQLite writes "2026-11-13 08:00:00" in UTC without saying so. A browser would read that as local
// time, so the space becomes a T and formatUtc takes the bare time as UTC.
export function formatJobTime(value?: string | null) {
  if (!value) return undefined
  return formatUtc(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? value.replace(' ', 'T') : value)
}
