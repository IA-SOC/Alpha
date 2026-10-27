import { createContext, useContext } from 'react'

import type { IncidentCase } from '../../../api/types'

// The case as submitted, from GET /cases/{id}. Every source_fields path resolves against it.
// Undefined while it loads or when the request failed.
export interface SubmittedCaseState {
  submitted?: IncidentCase
  failed: boolean
}

export const SubmittedCaseContext = createContext<SubmittedCaseState>({ failed: false })

export const useSubmittedCase = () => useContext(SubmittedCaseContext)
