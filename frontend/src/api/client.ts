import createClient from 'openapi-fetch'

import type { paths } from './generated/intake'
import type { AcceptedCase, IncidentCase, Investigation, ReviewDecision, StoredCase, ValidationIssue } from './types'

// status 0 means the request never got an answer, usually because the backend is down.
export class ApiError extends Error {
  readonly status: number
  readonly detail: string | ValidationIssue[]

  constructor(status: number, detail: string | ValidationIssue[]) {
    super(typeof detail === 'string' ? detail : `Request failed with ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }

  get issues(): ValidationIssue[] {
    return Array.isArray(this.detail) ? this.detail : []
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response }

async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await request
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError(0, 'network')
  }
  const { data, error, response } = result
  if (response.ok) return data as T
  const detail = (error as { detail?: unknown } | undefined)?.detail
  throw new ApiError(
    response.status,
    typeof detail === 'string' || Array.isArray(detail) ? (detail as string | ValidationIssue[]) : response.statusText,
  )
}

export function createApi(fetchImpl: typeof fetch = (...args) => globalThis.fetch(...args)) {
  const client = createClient<paths>({ baseUrl: globalThis.location?.origin ?? '', fetch: fetchImpl })
  const byId = (caseId: string) => ({ params: { path: { case_id: caseId } } })

  return {
    // The body is whatever the analyst pasted. The backend is the validator, so it goes as is.
    submitCase: (body: unknown) =>
      unwrap<AcceptedCase>(client.POST('/api/v1/cases', { body: body as IncidentCase })),

    getCase: (caseId: string) =>
      unwrap(client.GET('/api/v1/cases/{case_id}', byId(caseId))) as Promise<StoredCase>,

    investigate: (caseId: string, signal?: AbortSignal) =>
      unwrap(client.POST('/api/v1/cases/{case_id}/investigate', { ...byId(caseId), signal })) as Promise<Investigation>,

    getInvestigation: (caseId: string) =>
      unwrap(client.GET('/api/v1/cases/{case_id}/investigation', byId(caseId))) as Promise<Investigation>,

    review: (caseId: string, decision: ReviewDecision) =>
      unwrap(client.POST('/api/v1/cases/{case_id}/review', { ...byId(caseId), body: decision })) as Promise<Investigation>,
  }
}

export type Api = ReturnType<typeof createApi>

export const api = createApi()
