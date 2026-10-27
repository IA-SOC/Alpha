import { cleanup, screen, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Investigation, ReviewDecision } from '../../../api/types'
import { type Answer, fakeBackend, json } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'

const caseId = sampleInvestigation.case_id
const base = `/api/v1/cases/${caseId}`
const report = sampleInvestigation.report
const hypothesisLegend = `Hypothesis 1 ${report.hypotheses[0].statement}`
const techniqueLegend = 'MITRE ATT&CK technique T1110 Brute Force, Credential Access'

// What the backend sends back after POST /review: the same run with the review filled in.
function reviewed(decision: ReviewDecision): Investigation {
  const copy = structuredClone(sampleInvestigation)
  copy.status = decision.status
  copy.report.review = { ...decision, reviewed_at: '2026-10-26T18:00:00Z' }
  return copy
}

function openReview(answers: Record<string, Answer | (() => Answer)> = {}, investigation: Investigation = sampleInvestigation) {
  const backend = fakeBackend({
    [`GET ${base}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET ${base}/investigation`]: json(200, investigation),
    ...answers,
  })
  renderApp(`/cases/${caseId}?tab=review`)
  return backend
}

async function sentReviews(fetch: ReturnType<typeof fakeBackend>['fetch']): Promise<ReviewDecision[]> {
  const requests = fetch.mock.calls.map(([input]) => input as Request).filter((request) => request.url.endsWith('/review'))
  return Promise.all(requests.map((request) => request.clone().json() as Promise<ReviewDecision>))
}

const finding = (legend: string) => screen.getByRole('group', { name: legend }).closest('article')!

async function decide(user: UserEvent, legend: string, decision: 'Validate' | 'Correct' | 'Reject', note: string) {
  const card = finding(legend)
  await user.click(within(card).getByRole('radio', { name: decision }))
  const field = within(card).getByRole('textbox', { name: 'Note' })
  await user.clear(field)
  await user.type(field, note)
}

async function decideAll(user: UserEvent) {
  await screen.findByRole('group', { name: hypothesisLegend })
  await decide(user, hypothesisLegend, 'Validate', 'Both failed logins are real.')
  await decide(user, techniqueLegend, 'Reject', 'Two attempts are not brute force.')
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Analyst review', () => {
  it('asks for a decision and a note on every hypothesis and technique', async () => {
    openReview()

    expect(await screen.findByRole('heading', { name: /2 findings/ })).toBeInTheDocument()
    for (const legend of [hypothesisLegend, techniqueLegend]) {
      const card = finding(legend)
      expect(within(card).getAllByRole('radio').map((radio) => radio.getAttribute('value'))).toEqual(['validated', 'corrected', 'rejected'])
      expect(within(card).getByRole('textbox', { name: 'Note' })).toBeInTheDocument()
    }
    expect(screen.getByText(/saved together as one review of the whole report/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument()
  })

  it('saves nothing until every finding has a decision and a note', async () => {
    const backend = openReview()
    const user = userEvent.setup()
    await screen.findByRole('group', { name: hypothesisLegend })

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    expect(screen.getByRole('alert')).toHaveTextContent('5 things are missing before the review can be saved.')
    expect(within(finding(hypothesisLegend)).getByText('Pick a decision for this finding.')).toBeInTheDocument()
    expect(within(finding(techniqueLegend)).getByRole('textbox', { name: 'Note' })).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Pick an outcome.')).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/review`)).toBe(0)
  })

  it('suggests the outcome from the decisions and lets the analyst pick another', async () => {
    openReview()
    const user = userEvent.setup()
    await screen.findByRole('group', { name: hypothesisLegend })
    const outcome = () => screen.getByRole('group', { name: 'Status' })

    expect(within(outcome()).getByText('Decide every finding to get a suggestion.')).toBeInTheDocument()
    await decide(user, hypothesisLegend, 'Validate', 'ok')
    await decide(user, techniqueLegend, 'Validate', 'ok')
    expect(within(outcome()).getByRole('radio', { name: 'Validated Suggested' })).toBeChecked()

    await user.click(within(finding(techniqueLegend)).getByRole('radio', { name: 'Reject' }))
    expect(within(outcome()).getByRole('radio', { name: 'Corrected Suggested' })).toBeChecked()

    await user.click(within(outcome()).getByRole('radio', { name: 'Rejected' }))
    expect(within(outcome()).getByRole('radio', { name: 'Rejected' })).toBeChecked()
  })

  it('sends one review with every decision in its notes and shows the new status', async () => {
    const backend = openReview({
      [`POST ${base}/review`]: async () => json(200, reviewed((await sentReviews(backend.fetch)).at(-1)!)),
    })
    const user = userEvent.setup()
    await decideAll(user)

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    const [sent] = await sentReviews(backend.fetch)
    expect(sent.status).toBe('corrected')
    expect(sent.analyst).toBe('Test Analyst')
    expect(sent.notes).toContain(`Hypothesis 1: ${report.hypotheses[0].statement}\nDecision: validated\nNote: Both failed logins are real.`)
    expect(sent.notes).toContain('MITRE technique: T1110 Brute Force, Credential Access\nDecision: rejected\nNote: Two attempts are not brute force.')
    expect(await screen.findByRole('heading', { name: 'Analyst review' })).toBeInTheDocument()
    expect(screen.getAllByText('Corrected').length).toBeGreaterThanOrEqual(2)
    expect(screen.queryByRole('button', { name: 'Save review' })).not.toBeInTheDocument()
    expect(localStorage.getItem(`soc.review.${caseId}`)).toBeNull()
  })

  it('takes the analyst from the session and lets it change for this review', async () => {
    const backend = openReview({ [`POST ${base}/review`]: json(200, sampleInvestigation) })
    const user = userEvent.setup()
    await decideAll(user)
    const name = screen.getByRole('textbox', { name: 'Analyst' })
    expect(name).toHaveValue('Test Analyst')

    await user.clear(name)
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    expect(screen.getByText("Write the analyst's name.")).toBeInTheDocument()

    await user.type(name, 'Night shift lead')
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    await vi.waitFor(async () => expect((await sentReviews(backend.fetch))[0]?.analyst).toBe('Night shift lead'))
  })

  it('keeps the decisions after leaving the page', async () => {
    openReview()
    const user = userEvent.setup()
    await decideAll(user)
    cleanup()

    openReview()

    const card = await screen.findByRole('group', { name: hypothesisLegend })
    expect(within(card).getByRole('radio', { name: 'Validate' })).toBeChecked()
    expect(within(finding(techniqueLegend)).getByRole('textbox', { name: 'Note' })).toHaveValue('Two attempts are not brute force.')
  })

  it('offers to investigate again after a backend restart and fills the decisions back in', async () => {
    let restarted = true
    let latest: Investigation = sampleInvestigation
    const backend = openReview({
      [`GET ${base}/investigation`]: () => json(200, latest),
      [`POST ${base}/review`]: async () =>
        restarted
          ? json(409, { detail: 'No resumable investigation in this process' })
          : json(200, reviewed((await sentReviews(backend.fetch)).at(-1)!)),
      [`POST ${base}/investigate`]: () => {
        restarted = false
        latest = { ...sampleInvestigation, run_id: 'second-run' }
        return json(200, latest)
      },
    })
    const user = userEvent.setup()
    await decideAll(user)

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    expect(await screen.findByText(/The backend restarted after this investigation ran/)).toBeInTheDocument()
    expect(screen.getByText(/Your decisions and notes are saved in this browser/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Investigate again' }))

    const card = await screen.findByRole('group', { name: hypothesisLegend })
    expect(within(card).getByRole('radio', { name: 'Validate' })).toBeChecked()
    expect(screen.queryByText(/The backend restarted/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    expect(await screen.findByRole('heading', { name: 'Analyst review' })).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(1)
    expect(backend.calls(`POST ${base}/review`)).toBe(2)
  })

  it('shows the review saved elsewhere instead of running the agent again', async () => {
    let latest: Investigation = sampleInvestigation
    const backend = openReview({
      [`GET ${base}/investigation`]: () => json(200, latest),
      [`POST ${base}/review`]: () => {
        latest = reviewed({ status: 'validated', analyst: 'Other tab', notes: 'Saved first.' })
        return json(409, { detail: 'The investigation is not awaiting review' })
      },
    })
    const user = userEvent.setup()
    await decideAll(user)

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    expect(await screen.findByText('This run already has a review, maybe saved from another tab.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Investigate again' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Show the saved review' }))
    expect(await screen.findByText('Other tab')).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/investigate`)).toBe(0)
  })

  it('saves nothing when another run of the case started after the report loaded', async () => {
    let latest: Investigation = sampleInvestigation
    const backend = openReview({ [`GET ${base}/investigation`]: () => json(200, latest) })
    const user = userEvent.setup()
    await decideAll(user)
    latest = { ...sampleInvestigation, run_id: 'newer-run' }

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    expect(await screen.findByText('There is a newer investigation of this case')).toBeInTheDocument()
    expect(backend.calls(`POST ${base}/review`)).toBe(0)
    await user.click(screen.getByRole('button', { name: 'Load the newer investigation' }))
    await vi.waitFor(() => expect(screen.queryByText('There is a newer investigation of this case')).not.toBeInTheDocument())
    expect(within(finding(hypothesisLegend)).getByRole('radio', { name: 'Validate' })).toBeChecked()
  })

  it('uses the signed in name, not one typed by an analyst who signed out', async () => {
    localStorage.setItem(
      `soc.review.${caseId}`,
      JSON.stringify({ findings: {}, generalNote: '', analyst: 'Previous analyst', analystFor: 'Someone else' }),
    )
    openReview()

    expect(await screen.findByRole('textbox', { name: 'Analyst' })).toHaveValue('Test Analyst')
  })

  it('announces the missing count again on every failed attempt', async () => {
    openReview()
    const user = userEvent.setup()
    await screen.findByRole('group', { name: hypothesisLegend })
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    const first = screen.getByRole('alert')
    expect(first).toHaveFocus()

    await decide(user, hypothesisLegend, 'Validate', 'ok')
    await user.click(screen.getByRole('button', { name: 'Save review' }))

    const second = screen.getByRole('alert')
    expect(second).not.toBe(first)
    expect(second).toHaveFocus()
    expect(second).toHaveTextContent('3 things are missing')
  })

  it('keeps everything when the backend is down', async () => {
    openReview({ [`POST ${base}/review`]: new Response(null, { status: 502 }) })
    const user = userEvent.setup()
    await decideAll(user)

    await user.click(screen.getByRole('button', { name: 'Save review' }))

    expect(await screen.findByText("Can't reach the backend")).toBeInTheDocument()
    expect(screen.getByText(/Your decisions and notes are still here/)).toBeInTheDocument()
    expect(within(finding(hypothesisLegend)).getByRole('radio', { name: 'Validate' })).toBeChecked()
  })

  it('asks for a note on the whole report when there are no findings', async () => {
    const empty = structuredClone(sampleInvestigation)
    empty.report.hypotheses = []
    empty.report.attack_mapping = []
    const backend = openReview({ [`POST ${base}/review`]: json(200, sampleInvestigation) }, empty)
    const user = userEvent.setup()
    await screen.findByRole('heading', { name: 'Review outcome' })

    await user.click(screen.getByRole('radio', { name: 'Rejected' }))
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    expect(screen.getByRole('alert')).toHaveTextContent('1 thing is missing')

    await user.type(screen.getByRole('textbox', { name: 'Note' }), 'Benign admin activity.')
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    await vi.waitFor(async () =>
      expect((await sentReviews(backend.fetch))[0]).toEqual({ status: 'rejected', analyst: 'Test Analyst', notes: 'General note: Benign admin activity.' }),
    )
  })

  it('shows a saved review as it was recorded, with no form', async () => {
    const notes = 'Per finding decisions, sent as one review for the whole report.\n\nGeneral note: done'
    openReview({}, reviewed({ status: 'validated', analyst: 'Ana', notes }))

    expect(await screen.findByRole('heading', { name: 'Analyst review' })).toBeInTheDocument()
    expect(screen.getByText('Ana')).toBeInTheDocument()
    expect(screen.getByText(/General note: done/)).toHaveClass('whitespace-pre-wrap')
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
})
