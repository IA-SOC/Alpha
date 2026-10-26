import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fakeBackend, json, pending } from '../../test/backend'
import { sampleCase, sampleInvestigation } from '../../test/fixtures'
import { renderApp } from '../../test/render'

const caseId = sampleInvestigation.case_id
const base = `/api/v1/cases/${caseId}`
const stored = json(200, { case_id: caseId, submitted_case: sampleCase })
const notRun = json(404, { detail: 'No completed investigation found' })
// The backend's own 502 and 504 bodies, from app/api/routes/investigations.py.
const agentFailed = json(502, { detail: 'Investigation failed; accepted evidence is retained' })
const timedOut = json(504, { detail: 'Investigation exceeded the 300-second timeout' })

function openAskingToRun() {
  return renderApp({ pathname: `/cases/${caseId}`, state: { investigate: true } })
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Investigating a case', () => {
  it('starts the run from New Case and shows the report when it ends', async () => {
    const backend = fakeBackend({
      'POST /api/v1/cases': json(201, { case_id: caseId, submitted_case_id: sampleCase.case_id, status: 'accepted' }),
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: json(200, sampleInvestigation),
    })
    const user = userEvent.setup()
    const { router } = renderApp('/cases/new')
    await user.click(screen.getByLabelText('Case JSON'))
    await user.paste(JSON.stringify(sampleCase))
    await user.click(screen.getByRole('button', { name: 'Submit case' }))

    await user.click(await screen.findByRole('button', { name: 'Investigate' }))

    expect(await screen.findByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/cases/${caseId}`)
    expect(screen.getByRole('heading', { level: 1, name: sampleCase.case_id })).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(1)
  })

  it('counts the time while the agent works, against the 5 minute limit', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: pending().promise,
    })
    openAskingToRun()
    expect(await screen.findByRole('status')).toHaveTextContent('Investigating the case')

    await act(() => vi.advanceTimersByTimeAsync(42_000))

    expect(screen.getByText('0:42')).toBeInTheDocument()
    expect(screen.getByText('of up to 5:00')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Time used of the limit' })).toHaveAttribute('aria-valuenow', '42')
  })

  it('keeps the case on a 504 and runs it again with the same ID', async () => {
    let answer = timedOut
    const backend = fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: () => answer.clone(),
    })
    const user = userEvent.setup()
    openAskingToRun()

    expect(await screen.findByRole('heading', { name: 'The investigation ran out of time' })).toHaveFocus()
    expect(screen.getByText('Investigation exceeded the 300-second timeout')).toBeInTheDocument()
    expect(screen.getByText(/Your case is still stored/)).toBeInTheDocument()

    answer = json(200, sampleInvestigation)
    await user.click(screen.getByRole('button', { name: 'Run the investigation again' }))

    expect(await screen.findByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(2)
  })

  it('shows the backend detail when the agent fails with a 502', async () => {
    fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: agentFailed,
    })
    openAskingToRun()

    expect(await screen.findByRole('heading', { name: 'The investigation failed' })).toBeInTheDocument()
    expect(screen.getByText('Investigation failed; accepted evidence is retained')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run the investigation again' })).toBeInTheDocument()
  })

  it('gives up on its own when the backend never answers', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: pending().promise,
    })
    openAskingToRun()
    await screen.findByRole('status')

    await act(() => vi.advanceTimersByTimeAsync(320_000))

    expect(await screen.findByRole('heading', { name: 'No answer after 5:00' })).toBeInTheDocument()
  })

  it('does not run the agent again on a reload', async () => {
    fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: json(200, sampleInvestigation),
    })
    const { router } = openAskingToRun()

    await screen.findByText(sampleInvestigation.report.executive_summary)

    expect(router.state.location.state).toBeNull()
  })

  it('shows a stored report without running the agent', async () => {
    const backend = fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: json(200, sampleInvestigation),
    })
    renderApp(`/cases/${caseId}`)

    expect(await screen.findByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(0)
  })

  it('offers to investigate a stored case that never ran', async () => {
    const backend = fakeBackend({
      [`GET ${base}`]: stored,
      [`GET ${base}/investigation`]: notRun,
      [`POST ${base}/investigate`]: json(200, sampleInvestigation),
    })
    const user = userEvent.setup()
    renderApp(`/cases/${caseId}`)

    await user.click(await screen.findByRole('button', { name: 'Investigate' }))

    expect(await screen.findByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(1)
  })

  it('says so when the case does not exist', async () => {
    fakeBackend({ [`GET ${base}`]: json(404, { detail: 'Case not found' }), [`GET ${base}/investigation`]: notRun })
    renderApp(`/cases/${caseId}`)

    expect(await screen.findByRole('heading', { name: 'No case with this ID' })).toBeInTheDocument()
  })
})
