import { describe, expect, it, vi } from 'vitest'

import { sampleCase, sampleInvestigation } from '../test/fixtures'
import { ApiError, createApi } from './client'

function respond(status: number, body: unknown) {
  return vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

async function rejection(promise: Promise<unknown>) {
  return promise.then(
    () => expect.fail('expected the request to fail'),
    (error: unknown) => error as ApiError,
  )
}

describe('api client', () => {
  it('submits the case as JSON and returns the accepted UUID', async () => {
    const accepted = { case_id: 'b0b5f3a8-0000-4000-8000-000000000001', submitted_case_id: 'X-1', status: 'accepted' }
    const fetch = respond(201, accepted)

    await expect(createApi(fetch).submitCase(JSON.stringify(sampleCase))).resolves.toEqual(accepted)

    const request = fetch.mock.calls[0][0] as Request
    expect(request.method).toBe('POST')
    expect(new URL(request.url).pathname).toBe('/api/v1/cases')
    expect(request.headers.get('Content-Type')).toBe('application/json')
    expect(await request.json()).toEqual(sampleCase)
  })

  it('sends the text exactly as written, so big integers keep every digit', async () => {
    const fetch = respond(201, {})
    const text = '{"alerts": [{"raw_alert": {"id": 1234567890123456789}}]}'

    await createApi(fetch).submitCase(text)

    expect(await (fetch.mock.calls[0][0] as Request).text()).toBe(text)
  })

  it('turns a 422 into an ApiError with every validation issue', async () => {
    const issues = [{ rule: 'VR-01', loc: ['body', 'schema_version'], msg: 'Field required', type: 'missing' }]

    const error = await rejection(createApi(respond(422, { detail: issues })).submitCase('{}'))

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
    expect(error.issues).toEqual(issues)
  })

  it('keeps the message of plain HTTP errors like a 504', async () => {
    const detail = 'Investigation exceeded the 300-second timeout'

    const error = await rejection(createApi(respond(504, { detail })).investigate('abc'))

    expect(error.status).toBe(504)
    expect(error.detail).toBe(detail)
    expect(error.issues).toEqual([])
  })

  it('reports status 0 when the backend cannot be reached', async () => {
    const offline = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await rejection(createApi(offline).getInvestigation('abc'))

    expect(error.status).toBe(0)
  })

  it('reports status 0 when the dev proxy answers 502 with no body', async () => {
    const proxy = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 502 }))

    const error = await rejection(createApi(proxy).submitCase('{}'))

    expect(error.status).toBe(0)
  })

  it('keeps the backend 502 when it explains itself', async () => {
    const detail = 'Investigation failed; accepted evidence is retained'

    const error = await rejection(createApi(respond(502, { detail })).investigate('abc'))

    expect(error.status).toBe(502)
    expect(error.detail).toBe(detail)
  })

  it('does not call a 200 that is not JSON a network failure', async () => {
    const html = vi.fn<typeof fetch>().mockResolvedValue(
      new Response('<!doctype html>', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )

    const error = await createApi(html).getInvestigation('abc').catch((caught: unknown) => caught)

    expect(error).not.toBeInstanceOf(ApiError)
    expect(error).toBeInstanceOf(SyntaxError)
  })

  it('reads an investigation by the application UUID', async () => {
    const fetch = respond(200, sampleInvestigation)
    const caseId = sampleInvestigation.case_id

    const result = await createApi(fetch).getInvestigation(caseId)

    expect(result.report.hypotheses.length).toBeGreaterThan(0)
    expect(new URL((fetch.mock.calls[0][0] as Request).url).pathname).toBe(`/api/v1/cases/${caseId}/investigation`)
  })

  it('posts the review decision', async () => {
    const fetch = respond(200, sampleInvestigation)
    const decision = { status: 'validated' as const, analyst: 'Roberto', notes: 'Checked' }

    await createApi(fetch).review('abc', decision)

    const request = fetch.mock.calls[0][0] as Request
    expect(new URL(request.url).pathname).toBe('/api/v1/cases/abc/review')
    expect(await request.json()).toEqual(decision)
  })
})
