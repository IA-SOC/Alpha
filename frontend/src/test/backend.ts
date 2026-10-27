import { vi } from 'vitest'

export type Answer = Response | Promise<Response>

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

// A fetch that answers by method and path, such as 'GET /api/v1/cases/abc'. Each value is the
// answer, or a function called on every request, so a test can change it between calls.
export function fakeBackend(routes: Record<string, Answer | (() => Answer)>) {
  const fetch = vi.fn<typeof globalThis.fetch>(async (input) => {
    const request = input as Request
    const key = `${request.method} ${new URL(request.url).pathname}`
    const answer = routes[key]
    if (!answer) return json(404, { detail: `No fake answer for ${key}` })
    if (typeof answer === 'function') return answer()
    return answer instanceof Response ? answer.clone() : answer
  })
  vi.stubGlobal('fetch', fetch)
  return {
    fetch,
    calls: (key: string) =>
      fetch.mock.calls.filter(([input]) => {
        const request = input as Request
        return `${request.method} ${new URL(request.url).pathname}` === key
      }).length,
  }
}

// A request that stays open until the test settles it.
export function pending() {
  let settle!: (response: Response) => void
  const promise = new Promise<Response>((resolve) => {
    settle = resolve
  })
  return { promise, settle }
}
