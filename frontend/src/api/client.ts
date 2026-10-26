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

// The Vite dev proxy answers these with an empty body when the backend is not running.
// The backend's own 502 and 504 always carry a JSON detail, so they stay as they are.
const gatewayStatuses = [502, 503, 504]

async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await request
  } catch (cause) {
    // fetch rejects with a TypeError only when no answer arrived. Anything else, such as a
    // body that is not JSON, is a real fault and keeps its own error.
    if (cause instanceof TypeError) throw new ApiError(0, 'network')
    throw cause
  }
  const { data, error, response } = result
  if (response.ok) return data as T
  const detail = (error as { detail?: unknown } | undefined)?.detail
  const known = typeof detail === 'string' || Array.isArray(detail)
  if (!known && gatewayStatuses.includes(response.status)) throw new ApiError(0, 'network')
  throw new ApiError(response.status, known ? (detail as string | ValidationIssue[]) : response.statusText)
}

export function createApi(fetchImpl: typeof fetch = (...args) => globalThis.fetch(...args)) {
  const client = createClient<paths>({ baseUrl: globalThis.location?.origin ?? '', fetch: fetchImpl })
  const byId = (caseId: string) => ({ params: { path: { case_id: caseId } } })

  return {
    // Sends the analyst's text exactly as written. Re-serializing it would round integers above
    // 2^53 and drop duplicate keys inside raw_alert. The backend is the validator.
    submitCase: (json: string) =>
      unwrap<AcceptedCase>(
        client.POST('/api/v1/cases', {
          body: json as unknown as IncidentCase,
          bodySerializer: (body) => body as unknown as string,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),

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
