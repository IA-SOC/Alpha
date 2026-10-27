import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Evidence, Investigation } from '../../../api/types'
import { fakeBackend, json } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'

const caseId = sampleInvestigation.case_id

function openReport(search = '', investigation: Investigation = sampleInvestigation) {
  fakeBackend({
    [`GET /api/v1/cases/${caseId}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET /api/v1/cases/${caseId}/investigation`]: json(200, investigation),
  })
  return renderApp(`/cases/${caseId}${search}`)
}

const alertCard = async (id: string) => (await screen.findByRole('heading', { name: id })).closest('article')!

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Evidence', () => {
  it('opens the source fields of a piece of evidence, checked against the submitted case', async () => {
    const user = userEvent.setup()
    openReport()
    const card = (await screen.findByRole('heading', { name: /^1\. / })).closest('article')!

    await user.click(within(card).getAllByText('Show the 6 source fields')[0])

    const table = within(card).getAllByRole('table')[0]
    const row = within(table).getByText('/alerts/0/raw_alert/event/action').closest('tr')!
    expect(within(row).getByText('failed_login')).toBeInTheDocument()
    expect(within(row).getByText('Matches')).toBeInTheDocument()
  })

  it('takes an alert link to that alert on the Evidence tab', async () => {
    const user = userEvent.setup()
    const { router } = openReport()

    await user.click((await screen.findAllByRole('link', { name: 'Open alert wazuh-auth-002 in Evidence' }))[0])

    expect(router.state.location.search).toBe('?tab=evidence&alert=wazuh-auth-002')
    expect(screen.getByRole('tab', { name: 'Evidence' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: 'wazuh-auth-002' })).toHaveFocus()
  })

  it('shows the severity only as the alert sent it, with its field', async () => {
    openReport('?tab=evidence')

    const wazuh = await alertCard('wazuh-auth-002')
    expect(within(wazuh).getByText('8')).toBeInTheDocument()
    expect(within(wazuh).getByText('from rule.level')).toBeInTheDocument()
    expect(within(await alertCard('ecs-auth-001')).getByText('The alert carries no severity')).toBeInTheDocument()
  })

  it('keeps unrelated alerts visible and says how each one correlates', async () => {
    openReport('?tab=evidence')

    const noise = await alertCard('ecs-noise-003')
    expect(within(noise).getByText('Unrelated')).toBeInTheDocument()
    expect(within(noise).getByText('Timeline')).toBeInTheDocument()
    expect(within(await alertCard('ecs-auth-001')).getByText('Hypothesis 1, for')).toBeInTheDocument()
  })

  it('says when a cited path is missing from the case or holds another value', async () => {
    const copy = structuredClone(sampleInvestigation)
    const evidence = copy.report.hypotheses[0].evidence_for[0] as Evidence
    evidence.source_fields = [
      { alert_id: 'ecs-auth-001', path: '/alerts/0/raw_alert/event/nothing', value: 'x' },
      { alert_id: 'ecs-auth-001', path: '/alerts/0/raw_alert/host/name', value: 'web-99' },
    ]
    const user = userEvent.setup()
    openReport('', copy)
    const card = (await screen.findByRole('heading', { name: /^1\. / })).closest('article')!

    await user.click(within(card).getByText('Show the 2 source fields'))

    expect(within(card).getByText('Not found in the submitted case')).toBeInTheDocument()
    const differs = within(card).getByText('The case holds this value. The report cites web-99').closest('tr')!
    expect(within(differs).getByText('web-01')).toBeInTheDocument()
  })

  it("shows each IoC's provider result as sent, with no verdict of its own", async () => {
    openReport('?tab=evidence')

    const panel = (await screen.findByRole('heading', { name: '3 IoCs' })).closest('section')!
    expect(within(panel).getByText('Provided with the case')).toBeInTheDocument()
    expect(within(panel).getByText('verdict: suspicious')).toBeInTheDocument()
    // The report drops raw_result from this item, so it comes from the submitted case.
    expect(within(panel).getByText('note: Explicit association supplied; observable not present in alert fields')).toBeInTheDocument()
    expect(within(panel).getByText('The provider sent no result.')).toBeInTheDocument()
    expect(panel.textContent).not.toMatch(/malicious/i)
  })
})
