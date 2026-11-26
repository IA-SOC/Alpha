import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'

import type { Report } from '../../../api/types'
import { sampleInvestigation } from '../../../test/fixtures'
import { MitreTab } from './MitreTab'

const report = sampleInvestigation.report

function renderTab(attack_mapping: Report['attack_mapping']) {
  render(
    <MemoryRouter initialEntries={['/cases/demo?tab=mitre']}>
      <MitreTab report={{ ...report, attack_mapping }} />
    </MemoryRouter>,
  )
}

it('shows the technique status, source and a link to each cited alert', () => {
  const [technique] = report.attack_mapping
  renderTab([{ ...technique, source_version: 'Synthetic catalog v1' }])

  const card = within(screen.getByRole('article'))
  expect(card.getByRole('heading', { name: 'T1110 Brute Force' })).toBeVisible()
  expect(card.getByText('Credential Access')).toBeVisible()
  expect(card.getByText('Candidate')).toBeVisible()
  expect(card.getByText('Technique source: Synthetic catalog v1')).toBeVisible()
  expect(card.getByRole('heading', { name: '2 pieces of evidence' })).toBeVisible()
  expect(card.getByRole('link', { name: 'Open alert ecs-auth-001 in Evidence' }))
    .toHaveAttribute('href', '/cases/demo?tab=evidence&alert=ecs-auth-001')
  expect(card.getByRole('link', { name: 'Open alert wazuh-auth-002 in Evidence' }))
    .toHaveAttribute('href', '/cases/demo?tab=evidence&alert=wazuh-auth-002')
})

it('keeps a technique visible when the tactic and source are unavailable', () => {
  const [technique] = report.attack_mapping
  renderTab([{ ...technique, tactic: null, source_version: null, status: 'unknown', evidence: [technique.evidence[0]] }])

  const card = within(screen.getByRole('article'))
  expect(card.getByText('Unknown')).toBeVisible()
  expect(card.getByText('No tactic given')).toBeVisible()
  expect(card.getByText('No technique source given')).toBeVisible()
  expect(card.getByRole('heading', { name: '1 piece of evidence' })).toBeVisible()
})

it('explains when there are no ATT&CK mappings', () => {
  renderTab([])
  expect(screen.getByText('The agent mapped no ATT&CK techniques for this case.')).toBeVisible()
  expect(screen.queryByRole('article')).not.toBeInTheDocument()
})
