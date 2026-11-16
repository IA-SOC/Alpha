import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalysisStatus, Investigation, ModelReview } from '../../../api/types'
import { type Answer, fakeBackend, json, pending } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'
import { analysisPollMs, formatJobTime } from '../analysis'

const caseId = sampleInvestigation.case_id
const base = `/api/v1/cases/${caseId}`
const stored = json(200, { case_id: caseId, submitted_case: sampleCase })
const notRun = json(404, { detail: 'No completed investigation found' })

const status = (state: AnalysisStatus['status'], error: string | null = null) =>
  json(200, { case_id: caseId, status: state, error, updated_at: '2026-11-13 08:30:05' })

// Gemini's answer as agent/llm.py saves it after core/llm_guard.py has checked it.
const okReview: ModelReview = {
  status: 'ok',
  provider: 'gemini',
  model: 'gemini-3.5-flash',
  prompt_version: '1.0.0',
  latency_ms: 4210,
  context_stats: { alerts_sent: 2, iocs_sent: 0, redacted_fields: 0 },
  items: [
    {
      rank: 1,
      assessment: 'weak',
      explanation: 'Two failed logins in a minute are thin for a brute force.',
      cited_alert_ids: ['wazuh-auth-002'],
    },
  ],
  rejected_count: 1,
}

function withReview(review: ModelReview | undefined, change?: (copy: Investigation) => void): Investigation {
  const copy = structuredClone(sampleInvestigation)
  copy.report.model_review = review as Investigation['report']['model_review']
  change?.(copy)
  return copy
}

function open(investigation: Answer | (() => Answer), analysis: Answer | (() => Answer) = status('completed'), extra = {}) {
  const backend = fakeBackend({
    [`GET ${base}`]: stored,
    [`GET ${base}/investigation`]: investigation,
    [`GET ${base}/analysis-status`]: analysis,
    ...extra,
  })
  return { backend, ...renderApp(`/cases/${caseId}`) }
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Agent analysis tab', () => {
  it('opens first, with the summary, Gemini’s remark and the evidence it cited', async () => {
    open(json(200, withReview(okReview)))

    const tab = await screen.findByRole('tab', { name: 'Agent analysis' })
    expect(tab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getAllByRole('tab')[0]).toBe(tab)
    const panel = screen.getByRole('tabpanel')
    expect(within(panel).getByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    expect(within(panel).getByText('1 hypothesis, 1 ATT&CK technique and 2 recommended actions.', { exact: false })).toBeInTheDocument()

    const card = within(panel).getByRole('heading', { name: /^1\. Actividad compatible con Brute Force/ }).closest('article')!
    expect(within(card).getByText('Weak')).toBeInTheDocument()
    expect(within(card).getByText(okReview.items![0].explanation)).toBeInTheDocument()
    expect(within(card).getByText('1 alert cited')).toBeInTheDocument()
    // Only the cited piece of evidence, with what the report observed in it.
    expect(within(card).getByRole('link', { name: 'Open alert wazuh-auth-002 in Evidence' })).toBeInTheDocument()
    expect(within(card).queryByRole('link', { name: 'Open alert ecs-auth-001 in Evidence' })).not.toBeInTheDocument()
    expect(within(card).getByText('Repeated authentication failures en web-01 (usuario demo-user)')).toBeInTheDocument()
    expect(within(panel).getByText(/1 answer from Gemini was dropped/)).toBeInTheDocument()
  })

  it('shows where the processing stands and which model answered', async () => {
    open(json(200, withReview(okReview)))

    const processing = (await screen.findByRole('heading', { name: 'Processing' })).closest('section')!
    const row = (label: string) => within(processing).getByText(label).closest('div')!
    expect(row('Analysis')).toHaveTextContent('Completed')
    expect(row('Last update')).toHaveTextContent('2026-11-13 08:30:05 UTC')
    expect(row('Model')).toHaveTextContent('gemini-3.5-flash')
    expect(row('Prompt version')).toHaveTextContent('1.0.0')
    expect(row('Gemini response time')).toHaveTextContent('4.2 s')
    expect(row('Alerts sent to Gemini')).toHaveTextContent('2')
  })

  it('lists each model attempt once the fallback reports them', async () => {
    const review = {
      ...okReview,
      attempts: [
        { model: 'gemini-3.8-flash', outcome: 'unavailable', latency_ms: 900 },
        { model: 'gemini-3.5-flash', outcome: 'ok', latency_ms: 4210 },
      ],
    }
    open(json(200, withReview(review)))

    const list = (await screen.findByRole('heading', { name: '2 attempts' })).nextElementSibling as HTMLElement
    expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'gemini-3.8-flashunavailable',
      'gemini-3.5-flashok',
    ])
  })

  it('explains a missing second opinion and keeps the rules report', async () => {
    open(json(200, withReview({ status: 'unavailable', provider: 'gemini', error: 'GEMINI_API_KEY es obligatoria para Gemini' })))

    expect(await screen.findByText(/Gemini’s second opinion could not be completed/)).toBeInTheDocument()
    expect(screen.getByText('GEMINI_API_KEY es obligatoria para Gemini')).toBeInTheDocument()
    expect(screen.getByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    // The banner is for the other tabs; here the tab already says it.
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('says when the rules raised nothing for Gemini to assess', async () => {
    open(
      json(
        200,
        withReview({ ...okReview, items: [], rejected_count: 0 }, (copy) => {
          copy.report.hypotheses = []
        }),
      ),
    )

    expect(await screen.findByText('The rules raised no hypotheses, so Gemini had nothing to assess.')).toBeInTheDocument()
  })

  it('says when the run never asked Gemini', async () => {
    open(json(200, sampleInvestigation))

    expect(await screen.findByText('This run did not ask Gemini for a second opinion.')).toBeInTheDocument()
  })

  it('takes a cited alert to the Evidence tab', async () => {
    const user = userEvent.setup()
    const { router } = open(json(200, withReview(okReview)))

    await user.click(await screen.findByRole('link', { name: 'Open alert wazuh-auth-002 in Evidence' }))

    expect(router.state.location.search).toBe('?tab=evidence&alert=wazuh-auth-002')
  })

  it('warns that a newer run is going while it shows the previous report', async () => {
    open(json(200, withReview(okReview)), status('running'))

    expect(await screen.findByText(/A new run is in progress/)).toBeInTheDocument()
  })
})

describe('Automatic analysis on the case page', () => {
  it('follows the queued job and shows the report when it is saved, without pressing anything', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let job = status('queued')
    let report = notRun
    const { backend } = open(
      () => report.clone(),
      () => job.clone(),
      { [`POST ${base}/investigate`]: json(500, { detail: 'should not be called' }) },
    )

    expect(await screen.findByRole('status')).toHaveTextContent('Waiting for the agent')
    expect(screen.getByText('Last update 2026-11-13 08:30:05 UTC')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Investigate' })).not.toBeInTheDocument()

    job = status('running')
    await act(() => vi.advanceTimersByTimeAsync(analysisPollMs))
    expect(await screen.findByRole('status')).toHaveTextContent('The agent is analysing this case')

    job = status('completed')
    report = json(200, withReview(okReview))
    await act(() => vi.advanceTimersByTimeAsync(analysisPollMs))

    expect(await screen.findByText(okReview.items![0].explanation)).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(0)
  })

  it('loads the report when the job finished between the first report and status answers', async () => {
    // The report answers 404 first. The job ends right after, so the first status already says
    // completed and the page never sees it queued or running.
    const firstStatus = pending()
    let statusCalls = 0
    let report = notRun
    const { backend } = open(
      () => report.clone(),
      () => (++statusCalls === 1 ? firstStatus.promise : status('completed')),
    )
    expect(await screen.findByRole('heading', { name: 'Not investigated yet' })).toBeInTheDocument()

    report = json(200, withReview(okReview))
    await act(async () => firstStatus.settle(status('completed')))

    expect(await screen.findByText(okReview.items![0].explanation)).toBeInTheDocument()
    expect(backend.calls(`GET ${base}/investigation`)).toBe(2)
  })

  it('loads the report when the status says completed before the first report answer arrives', async () => {
    const firstReport = pending()
    let reportCalls = 0
    const { backend } = open(
      () => (++reportCalls === 1 ? firstReport.promise : json(200, withReview(okReview))),
      status('completed'),
    )
    await waitFor(() => expect(backend.calls(`GET ${base}/analysis-status`)).toBe(1))

    await act(async () => firstReport.settle(notRun.clone()))

    expect(await screen.findByText(okReview.items![0].explanation)).toBeInTheDocument()
    expect(backend.calls(`GET ${base}/investigation`)).toBe(2)
  })

  it('says the automatic analysis failed and retries it on request', async () => {
    const { backend } = open(notRun, status('error', 'ProviderUnavailable'), {
      [`POST ${base}/investigate`]: json(200, withReview(okReview)),
    })
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'The automatic analysis failed' })).toBeInTheDocument()
    expect(screen.getByText('The backend stopped with ProviderUnavailable.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Run the investigation again' }))

    expect(await screen.findByText(okReview.items![0].explanation)).toBeInTheDocument()
    const post = backend.fetch.mock.calls.map(([input]) => input as Request).find((request) => request.method === 'POST')!
    expect(new URL(post.url).searchParams.get('force')).toBe('true')
  })

  it('still offers a manual run when the backend has no automatic job for the case', async () => {
    open(notRun, status('not_started'))

    expect(await screen.findByRole('heading', { name: 'Not investigated yet' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Investigate' })).toBeInTheDocument()
  })
})

describe('formatJobTime', () => {
  it('reads the SQLite timestamp as UTC, not local time', () => {
    expect(formatJobTime('2026-11-13 08:30:05')).toBe('2026-11-13 08:30:05 UTC')
    expect(formatJobTime(null)).toBeUndefined()
  })
})
