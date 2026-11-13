import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Investigation } from '../../../api/types'
import i18n from '../../../i18n'
import { fakeBackend, json } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'

const caseId = sampleInvestigation.case_id
const report = sampleInvestigation.report

function openReport(investigation: Investigation = sampleInvestigation, search = '') {
  fakeBackend({
    [`GET /api/v1/cases/${caseId}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET /api/v1/cases/${caseId}/investigation`]: json(200, investigation),
  })
  return renderApp(`/cases/${caseId}${search}`)
}

// The demo report has no evidence against, so this copy adds one to check it is never hidden.
function withEvidenceAgainst(): Investigation {
  const copy = structuredClone(sampleInvestigation)
  const hypothesis = copy.report.hypotheses[0]
  hypothesis.confidence = 'baja'
  hypothesis.evidence_against = [
    {
      alert_id: 'ecs-uncertain-004',
      role: 'contradicting',
      observation: 'logon en web-01 (usuario other-user)',
      relevance: 'Inicio de sesión correcto de otro usuario.',
    },
  ]
  return copy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Case report', () => {
  it('shows the report header facts', async () => {
    openReport()

    expect(await screen.findByText('Mixed sources')).toBeInTheDocument()
    expect(screen.getByText('4 of 4 processed')).toBeInTheDocument()
    expect(screen.getByText('Time window').nextElementSibling).toHaveTextContent('2026-10-09 12:00:00 to 12:03:00 UTC')
    expect(screen.getAllByText('Waiting for review').length).toBeGreaterThan(0)
  })

  it('shows the Gemini model and UTC time for a completed second opinion', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'ok',
      model: 'gemini-3.6-flash',
      primary_model: 'gemini-3.6-flash',
      analyzed_at: '2026-11-13T00:30:00Z',
      fallback_used: false,
      attempts: [{ model: 'gemini-3.6-flash', outcome: 'ok', latency_ms: 250 }],
    }
    openReport(investigation)

    expect(await screen.findByText(/Second opinion: gemini-3\.6-flash/)).toBeInTheDocument()
    expect(screen.getByText('Second opinion: gemini-3.6-flash · 2026-11-13 00:30:00 UTC')).toBeInTheDocument()
    expect(screen.queryByText(/was used because/)).not.toBeInTheDocument()
  })

  it('explains a Gemini 504 fallback in the active language', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'ok',
      model: 'gemini-3.5-flash',
      primary_model: 'gemini-3.6-flash',
      analyzed_at: '2026-11-13T15:30:00Z',
      fallback_used: true,
      attempts: [
        { model: 'gemini-3.6-flash', outcome: 'http_504', latency_ms: 1000 },
        { model: 'gemini-3.5-flash', outcome: 'ok', latency_ms: 250 },
      ],
    }
    openReport(investigation)

    expect(await screen.findByText('gemini-3.5-flash was used because gemini-3.6-flash did not answer in time (504).')).toBeInTheDocument()

    await i18n.changeLanguage('es')

    expect(screen.getByText('Se us\u00f3 gemini-3.5-flash porque gemini-3.6-flash no respondi\u00f3 a tiempo (504).')).toBeInTheDocument()
  })

  it('uses the unknown fallback copy without a failed primary attempt', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'ok',
      model: 'gemini-3.5-flash',
      primary_model: 'gemini-3.6-flash',
      fallback_used: true,
      attempts: [{ model: 'gemini-3.5-flash', outcome: 'ok', latency_ms: 250 }],
    }
    openReport(investigation)

    expect(await screen.findByRole('status')).toHaveTextContent('gemini-3.5-flash was used as a fallback.')
  })

  it('explains server errors and falls back from unknown outcomes without exposing translation keys', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'ok',
      model: 'gemini-3.5-flash',
      primary_model: 'gemini-3.6-flash',
      fallback_used: true,
      attempts: [{ model: 'gemini-3.6-flash', outcome: 'http_500', latency_ms: 1000 }],
    }
    openReport(investigation)

    expect(await screen.findByText('gemini-3.5-flash was used because gemini-3.6-flash had a server error (500).')).toBeInTheDocument()

    investigation.report.model_review.attempts![0].outcome = 'unexpected' as never
    openReport(investigation)

    expect(await screen.findByText('gemini-3.5-flash was used because gemini-3.6-flash was unavailable.')).toBeInTheDocument()
    expect(screen.queryByText(/report\.modelReview\.outcomes/)).not.toBeInTheDocument()
  })

  it('keeps the model visible when the second-opinion date is invalid', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'ok',
      model: 'gemini-3.6-flash',
      analyzed_at: 'not-a-date',
      fallback_used: false,
    }
    openReport(investigation)

    expect(await screen.findByText('Second opinion: gemini-3.6-flash')).toBeInTheDocument()
    expect(screen.queryByText('not-a-date')).not.toBeInTheDocument()
  })

  it('does not show second-opinion details when model review is null or absent', async () => {
    const nullReview = structuredClone(sampleInvestigation)
    Object.assign(nullReview.report, { model_review: null }) // the API omits it, but be safe
    openReport(nullReview)

    expect(await screen.findByText('Mixed sources')).toBeInTheDocument()
    expect(screen.queryByText(/Second opinion:/)).not.toBeInTheDocument()

    const absentReview = structuredClone(sampleInvestigation)
    delete absentReview.report.model_review
    openReport(absentReview)

    expect(await screen.findByText('Mixed sources')).toBeInTheDocument()
    expect(screen.queryByText(/Second opinion:/)).not.toBeInTheDocument()
  })

  it('keeps the existing warning when the second opinion fails', async () => {
    const investigation = structuredClone(sampleInvestigation)
    investigation.report.model_review = {
      status: 'error',
      attempts: [{ model: 'gemini-3.6-flash', outcome: 'http_503', latency_ms: 1000 }],
    }
    openReport(investigation)

    expect(await screen.findByRole('status')).toHaveTextContent("The rules-based report is available. Gemini’s second opinion could not be completed.")
  })

  it('shows each hypothesis with its confidence word and no percentage', async () => {
    openReport()

    const card = (await screen.findByRole('heading', { name: `1. ${report.hypotheses[0].statement}` })).closest('article')!
    expect(within(card).getByText('Medium')).toBeInTheDocument()
    expect(within(card).getByText(report.hypotheses[0].confidence_basis)).toBeInTheDocument()
    expect(within(card).getByText('2 pieces of evidence for')).toBeInTheDocument()
    expect(within(card).getByText('No evidence against was recorded.')).toBeInTheDocument()
    expect(screen.getByRole('main').textContent).not.toMatch(/\d\s?%/)
  })

  it('never hides the evidence against', async () => {
    openReport(withEvidenceAgainst())

    const card = (await screen.findByRole('heading', { name: /^1\. / })).closest('article')!
    expect(within(card).getByText('Low')).toBeInTheDocument()
    expect(within(card).getByText('1 piece of evidence against')).toBeInTheDocument()
    expect(within(card).getByText('Inicio de sesión correcto de otro usuario.')).toBeInTheDocument()
  })

  it('flags every recommended action that needs human approval', async () => {
    openReport()

    expect(await screen.findByRole('heading', { name: '2 recommended actions' })).toBeInTheDocument()
    expect(screen.getByText(report.recommended_actions[0].action)).toBeInTheDocument()
    expect(screen.getAllByText("Needs an analyst's approval before anyone acts on it.")).toHaveLength(2)
  })

  it('shows MITRE techniques with their status and no confidence', async () => {
    const user = userEvent.setup()
    const { router } = openReport()
    await user.click(await screen.findByRole('tab', { name: 'Summary' }))

    await user.keyboard('{Home}{ArrowRight}{ArrowRight}{ArrowRight}')

    expect(screen.getByRole('tab', { name: 'MITRE ATT&CK' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'MITRE ATT&CK' })).toHaveFocus()
    expect(router.state.location.search).toBe('?tab=mitre')
    const panel = screen.getByRole('tabpanel')
    expect(within(panel).getByRole('heading', { name: 'T1110 Brute Force' })).toBeInTheDocument()
    expect(within(panel).getByText('Candidate')).toBeInTheDocument()
    expect(within(panel).getByText(`Technique source: ${report.attack_mapping[0].source_version}`)).toBeInTheDocument()
    expect(within(panel).queryByText('Confidence')).not.toBeInTheDocument()
  })

  it('opens the tab named in the address', async () => {
    openReport(sampleInvestigation, '?tab=review')

    expect(await screen.findByRole('heading', { name: 'Review outcome' })).toBeInTheDocument()
  })

  it('translates the labels and leaves the report text as it came', async () => {
    await i18n.changeLanguage('es')
    openReport()

    expect(await screen.findByText('Qué encontró el agente')).toBeInTheDocument()
    expect(screen.getByText('Media')).toBeInTheDocument()
    expect(screen.getByText(report.executive_summary)).toBeInTheDocument()
  })
})


it('offers the server JSON export for the current case', async () => {
  openReport()
  const link = await screen.findByRole('link', { name: 'Export JSON' })
  expect(link).toHaveAttribute('href', `/api/v1/cases/${caseId}/export`)
})
