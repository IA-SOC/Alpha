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
