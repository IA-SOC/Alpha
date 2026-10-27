import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Investigation } from '../../../api/types'
import { fakeBackend, json } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'

const caseId = sampleInvestigation.case_id
const report = sampleInvestigation.report

function openTab(tab: string, investigation: Investigation = sampleInvestigation) {
  fakeBackend({
    [`GET /api/v1/cases/${caseId}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET /api/v1/cases/${caseId}/investigation`]: json(200, investigation),
  })
  return renderApp(`/cases/${caseId}?tab=${tab}`)
}

const section = async (heading: string) => (await screen.findByRole('heading', { name: heading })).closest('section')!
const alertsIn = (element: HTMLElement) =>
  within(element)
    .getAllByRole('listitem')
    .map((item) => within(item).queryAllByRole('link').map((link) => link.textContent))
    .filter((links) => links.length > 0)

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Timeline', () => {
  it('orders events by UTC time and keeps the time as it was sent', async () => {
    openTab('timeline')

    const story = await section('3 events in order')
    // The Wazuh alert was sent at 07:02 at -05:00, which is 12:02 UTC.
    expect(alertsIn(story)).toEqual([['ecs-auth-001'], ['wazuh-auth-002'], ['ecs-uncertain-004']])
    expect(within(story).getByText('2026-10-09 12:02:00 UTC')).toBeInTheDocument()
    expect(within(story).getByText('Sent as 2026-10-09T07:02:00-05:00')).toBeInTheDocument()
    expect(within(story).getByText('Uncertain link')).toBeInTheDocument()
  })

  it('moves unrelated alerts out of the chronology without dropping them', async () => {
    openTab('timeline')

    expect(alertsIn(await section('3 events in order')).flat()).not.toContain('ecs-noise-003')
    expect(alertsIn(await section('1 unrelated event'))).toEqual([['ecs-noise-003']])
  })

  it('keeps undated events apart and marks inferred ones', async () => {
    const copy = structuredClone(sampleInvestigation)
    copy.report.timeline[3] = { ...copy.report.timeline[3], timestamp_utc: null, timezone_unknown: true, timestamp_original: '09/10/2026 12:03' }
    copy.report.timeline[0] = { ...copy.report.timeline[0], certainty: 'inferred' }
    openTab('timeline', copy)

    const undated = await section('1 event without a usable time')
    expect(alertsIn(undated)).toEqual([['ecs-uncertain-004']])
    expect(within(undated).getByText('Time zone unknown')).toBeInTheDocument()
    expect(within(undated).getByText('Sent as 09/10/2026 12:03')).toBeInTheDocument()
    expect(within(await section('2 events in order')).getByText('Inferred')).toBeInTheDocument()
  })

  it('shows the related groups and the alerts left out of them', async () => {
    openTab('timeline')

    const panel = await section('How the alerts relate')
    const group = within(panel).getByText('Group 1').parentElement!
    expect(within(group).getAllByRole('link').map((link) => link.textContent)).toEqual(sampleInvestigation.correlation.related_groups[0])
    expect(within(panel).getByRole('heading', { name: '1 uncertain alert' })).toBeInTheDocument()
    expect(within(panel).getByRole('heading', { name: '1 unrelated alert' })).toBeInTheDocument()
  })
})

describe('Affected assets', () => {
  it('lists assets and identities under the label the report gives them', async () => {
    openTab('assets')

    const observed = await section('2 observed assets')
    const web = within(observed).getByText('web-01').closest('tr')!
    expect(within(web).getByText('failed_login; Repeated authentication failures; logon')).toBeInTheDocument()
    expect(within(web).getAllByRole('link')).toHaveLength(3)

    expect(within(await section('1 suspected asset')).getByText('web-01')).toBeInTheDocument()
    expect(within(await section('0 confirmed assets')).getByText('None.')).toBeInTheDocument()
    expect(within(await section('1 suspected identity')).getByText('demo-user')).toBeInTheDocument()
    expect(screen.getByText(report.blast_radius.unknowns[0])).toBeInTheDocument()
  })
})
