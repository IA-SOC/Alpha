import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'

import type { Report } from '../../../api/types'
import { sampleInvestigation } from '../../../test/fixtures'
import { AssetsTab } from './AssetsTab'

const report = sampleInvestigation.report

function renderTab(blast_radius: Report['blast_radius']) {
  render(
    <MemoryRouter initialEntries={['/cases/demo?tab=assets']}>
      <AssetsTab report={{ ...report, blast_radius }} />
    </MemoryRouter>,
  )
}

function panel(name: string) {
  return within(screen.getByRole('heading', { name }).closest('section')!)
}

it('keeps observed activity and its evidence attached to the correct asset', () => {
  renderTab(report.blast_radius)

  const web = within(screen.getByRole('row', { name: /web-01/ }))
  expect(web.getByRole('cell', { name: /failed_login/ })).toBeVisible()
  expect(web.getByRole('link', { name: 'Open alert ecs-auth-001 in Evidence' }))
    .toHaveAttribute('href', '/cases/demo?tab=evidence&alert=ecs-auth-001')
  const dns = within(screen.getByRole('row', { name: /dns-02/ }))
  expect(dns.getByRole('link', { name: 'Open alert ecs-noise-003 in Evidence' })).toBeVisible()
  expect(dns.queryByRole('link', { name: /ecs-auth-001/ })).not.toBeInTheDocument()
})

it('lists suspected and confirmed assets and identities under their own headings', () => {
  renderTab({
    ...report.blast_radius,
    confirmed_assets: [{ asset: 'confirmed-server', basis_alert_ids: ['ecs-uncertain-004'] }],
    confirmed_identities: [{ identity: 'confirmed-user', basis_alert_ids: ['ecs-noise-003'] }],
  })

  const suspected = panel('1 suspected asset')
  expect(suspected.getByText('web-01')).toBeVisible()
  expect(suspected.queryByText('confirmed-server')).not.toBeInTheDocument()
  const confirmed = panel('1 confirmed asset')
  expect(confirmed.getByText('confirmed-server')).toBeVisible()
  expect(confirmed.getByRole('link', { name: /ecs-uncertain-004/ })).toBeVisible()
  expect(confirmed.queryByText('web-01')).not.toBeInTheDocument()

  const suspectedIdentities = panel('1 suspected identity')
  expect(suspectedIdentities.getByText('demo-user')).toBeVisible()
  expect(suspectedIdentities.queryByText('confirmed-user')).not.toBeInTheDocument()
  const confirmedIdentities = panel('1 confirmed identity')
  expect(confirmedIdentities.getByText('confirmed-user')).toBeVisible()
  expect(confirmedIdentities.getByRole('link', { name: /ecs-noise-003/ })).toBeVisible()
  expect(confirmedIdentities.queryByText('demo-user')).not.toBeInTheDocument()
})

it('handles reports with empty asset lists and omitted identity lists', () => {
  renderTab({ observed_assets: [], suspected_assets: [], confirmed_assets: [], unknowns: [] })

  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  for (const title of [
    '0 observed assets', '0 suspected assets', '0 confirmed assets', '0 suspected identities', '0 confirmed identities',
  ]) {
    expect(panel(title).getByText('None.')).toBeVisible()
  }
  expect(screen.getByText('None listed.')).toBeVisible()
})
