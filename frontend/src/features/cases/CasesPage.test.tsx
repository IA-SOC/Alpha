import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CaseListItem } from '../../api/types'
import { fakeBackend, json } from '../../test/backend'
import { sampleCase, sampleInvestigation } from '../../test/fixtures'
import { renderApp } from '../../test/render'
import { formatCreated } from './format'

const summary = (status: string, review: string) => ({ status, revision: 1, run_id: 'run-1', review_status: review })

// Shaped like GET /api/v1/cases. Three cases: waiting for review, never investigated, and closed.
const cases: CaseListItem[] = [
  {
    case_id: '11111111-1111-4111-8111-111111111111',
    submitted_case_id: 'WAZUH-0001',
    status: 'open',
    created_at: '2026-11-09T10:15:00Z',
    investigation: summary('pending_review', 'pending'),
  },
  {
    case_id: '22222222-2222-4222-8222-222222222222',
    submitted_case_id: 'ELASTIC-0007',
    status: 'open',
    created_at: '2026-11-10T08:30:00Z',
    investigation: null,
  },
  {
    case_id: '33333333-3333-4333-8333-333333333333',
    submitted_case_id: 'WAZUH-0002',
    status: 'closed',
    created_at: '2026-11-08T16:45:00Z',
    investigation: summary('validated', 'validated'),
  },
]

const closedWazuh = { ...cases[0], status: 'closed' as const }

afterEach(() => vi.unstubAllGlobals())

const tableLinks = () => within(screen.getByRole('table')).getAllByRole('link').map((link) => link.textContent)
const rowFor = (name: string) => within(screen.getByRole('table')).getByRole('link', { name }).closest('tr')!
const summaryCounts = () => screen.getAllByRole('definition').map((count) => count.textContent)
const pageFilter = () => screen.getAllByRole('group', { name: 'Filter by status' }).at(-1)!

describe('Cases dashboard', () => {
  it('lists the stored cases, newest first, with where each one stands', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    renderApp('/cases')

    expect(await screen.findByRole('heading', { level: 1, name: 'Cases' })).toBeInTheDocument()
    expect(await screen.findByText('3 cases')).toBeInTheDocument()
    expect(tableLinks()).toEqual(['ELASTIC-0007', 'WAZUH-0001', 'WAZUH-0002'])
    expect(within(rowFor('ELASTIC-0007')).getByText('Not investigated')).toBeInTheDocument()
    expect(within(rowFor('WAZUH-0001')).getByText('Waiting for review')).toBeInTheDocument()
    expect(within(rowFor('WAZUH-0002')).getByText('Validated')).toBeInTheDocument()
    expect(within(rowFor('WAZUH-0002')).getByText('Closed')).toBeInTheDocument()
    expect(within(rowFor('WAZUH-0001')).getByText('2026-11-09 10:15')).toBeInTheDocument()
  })

  it('splits the open cases into waiting for review and not investigated', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    renderApp('/cases')

    await screen.findByRole('table')
    expect(summaryCounts()).toEqual(['2', '1', '1'])
  })

  it('prints zeros when every case is closed', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, [cases[2]]) })
    renderApp('/cases')

    await screen.findByRole('table')
    expect(summaryCounts()).toEqual(['0', '0', '0'])
  })

  it('opens a case from its ID', async () => {
    fakeBackend({
      'GET /api/v1/cases': json(200, cases),
      [`GET /api/v1/cases/${cases[0].case_id}`]: json(200, { case_id: cases[0].case_id, submitted_case: sampleCase }),
      [`GET /api/v1/cases/${cases[0].case_id}/investigation`]: json(404, { detail: 'No completed investigation found' }),
    })
    const user = userEvent.setup()
    const { router } = renderApp('/cases')

    await screen.findByRole('table')
    await user.click(within(screen.getByRole('table')).getByRole('link', { name: 'WAZUH-0001' }))

    expect(router.state.location.pathname).toBe(`/cases/${cases[0].case_id}`)
  })

  it('filters by status and keeps the counts of the whole list', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    const user = userEvent.setup()
    const { router } = renderApp('/cases')
    await screen.findByRole('table')

    await user.click(within(pageFilter()).getByRole('button', { name: /Closed/ }))

    expect(router.state.location.search).toBe('?status=closed')
    expect(tableLinks()).toEqual(['WAZUH-0002'])
    expect(within(pageFilter()).getByRole('button', { name: /All/ })).toHaveTextContent('3')
    expect(within(pageFilter()).getByRole('button', { name: /Open/ })).toHaveTextContent('2')
  })

  it('opens already filtered from the address', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    renderApp('/cases?status=open')

    await screen.findByRole('table')
    expect(tableLinks()).toEqual(['ELASTIC-0007', 'WAZUH-0001'])
    expect(within(pageFilter()).getByRole('button', { name: /Open/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('says so when a filter matches nothing', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, [cases[0]]) })
    renderApp('/cases?status=closed')

    expect(await screen.findByText('No closed cases.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('closes a case and then offers to reopen it', async () => {
    const backend = fakeBackend({
      'GET /api/v1/cases': json(200, cases),
      [`PATCH /api/v1/cases/${cases[0].case_id}`]: json(200, closedWazuh),
    })
    const user = userEvent.setup()
    renderApp('/cases')

    await user.click(await screen.findByRole('button', { name: 'Close case: WAZUH-0001' }))

    expect(await screen.findByRole('button', { name: 'Reopen case: WAZUH-0001' })).toBeInTheDocument()
    const sent = backend.fetch.mock.calls.map(([input]) => input as Request).find((request) => request.method === 'PATCH')!
    expect(await sent.json()).toEqual({ status: 'closed' })
    expect(summaryCounts()).toEqual(['1', '0', '1'])
  })

  it('keeps the case as it was and says so when the status change fails', async () => {
    fakeBackend({
      'GET /api/v1/cases': json(200, cases),
      [`PATCH /api/v1/cases/${cases[0].case_id}`]: json(404, { detail: 'Case not found' }),
    })
    const user = userEvent.setup()
    renderApp('/cases')

    await user.click(await screen.findByRole('button', { name: 'Close case: WAZUH-0001' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('The case status was not updated')
    expect(screen.getByRole('button', { name: 'Close case: WAZUH-0001' })).toBeEnabled()
  })

  it('keeps its frame and offers the first action when there are no cases', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, []) })
    renderApp('/cases')

    expect(await screen.findByRole('heading', { name: 'No cases yet' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Cases' })).toBeInTheDocument()
    expect(summaryCounts()).toEqual(['0', '0', '0'])
  })

  it('explains a failed load inside the block and retries', async () => {
    let answer = json(500, { detail: 'boom' })
    fakeBackend({ 'GET /api/v1/cases': () => answer.clone() })
    const user = userEvent.setup()
    renderApp('/cases')

    expect(await screen.findByRole('heading', { name: "Couldn't load the cases" })).toBeInTheDocument()
    answer = json(200, cases)
    await user.click(screen.getAllByRole('button', { name: 'Retry' })[0])

    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

  it('shows the same screen in Spanish', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    const user = userEvent.setup()
    renderApp('/cases')
    await screen.findByRole('table')

    await user.click(screen.getByRole('button', { name: 'Español' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Casos' })).toBeInTheDocument()
    expect(within(rowFor('WAZUH-0001')).getByText('Pendiente de revisión')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar caso: WAZUH-0001' })).toBeInTheDocument()
  })
})

describe('Case list sidebar', () => {
  const caseId = sampleInvestigation.case_id
  const mine: CaseListItem = { ...cases[0], case_id: caseId, submitted_case_id: sampleCase.case_id }
  const route = {
    [`GET /api/v1/cases/${caseId}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET /api/v1/cases/${caseId}/investigation`]: json(200, sampleInvestigation),
  }

  it('lists the cases next to the open one and marks it as current', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, [mine, cases[1], cases[2]]), ...route })
    renderApp(`/cases/${caseId}`)

    const nav = await screen.findByRole('navigation', { name: 'Cases' })
    const current = await within(nav).findByRole('link', { name: new RegExp(sampleCase.case_id) })
    expect(current).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: /ELASTIC-0007/ })).not.toHaveAttribute('aria-current')
    expect(within(nav).getByRole('link', { name: /WAZUH-0002/ })).toHaveTextContent('Closed, Validated')
  })

  it('filters by status and searches by case ID', async () => {
    fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
    const user = userEvent.setup()
    renderApp('/cases/new')
    const nav = await screen.findByRole('navigation', { name: 'Cases' })
    await within(nav).findByRole('link', { name: /WAZUH-0001/ })

    await user.click(within(nav).getByRole('button', { name: /Closed/ }))
    expect(within(nav).queryByRole('link', { name: /WAZUH-0001/ })).not.toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /WAZUH-0002/ })).toBeInTheDocument()

    await user.click(within(nav).getByRole('button', { name: /All/ }))
    await user.type(within(nav).getByRole('searchbox'), 'elastic')
    expect(within(nav).getByRole('link', { name: /ELASTIC-0007/ })).toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: /WAZUH/ })).not.toBeInTheDocument()

    await user.clear(within(nav).getByRole('searchbox'))
    await user.type(within(nav).getByRole('searchbox'), 'nothing like it')
    expect(within(nav).getByText('No cases match.')).toBeInTheDocument()
  })

  it('shows a new case in the list as soon as it is accepted', async () => {
    let list: CaseListItem[] = []
    fakeBackend({
      'GET /api/v1/cases': () => json(200, list),
      'POST /api/v1/cases': () => {
        list = [{ ...mine, investigation: null }]
        return json(201, { case_id: caseId, submitted_case_id: sampleCase.case_id, status: 'accepted' })
      },
    })
    const user = userEvent.setup()
    renderApp('/cases/new')
    const nav = await screen.findByRole('navigation', { name: 'Cases' })
    expect(await within(nav).findByText('No cases match.')).toBeInTheDocument()

    await user.click(screen.getByLabelText('Case JSON'))
    await user.paste(JSON.stringify(sampleCase))
    await user.click(screen.getByRole('button', { name: 'Submit case' }))

    expect(await within(nav).findByRole('link', { name: new RegExp(sampleCase.case_id) })).toBeInTheDocument()
  })

  it('closes and reopens the open case from its header', async () => {
    let status: CaseListItem['status'] = 'open'
    const backend = fakeBackend({
      'GET /api/v1/cases': () => json(200, [{ ...mine, status }]),
      [`PATCH /api/v1/cases/${caseId}`]: () => {
        status = status === 'open' ? 'closed' : 'open'
        return json(200, { ...mine, status })
      },
      ...route,
    })
    const user = userEvent.setup()
    renderApp(`/cases/${caseId}`)

    await user.click(await screen.findByRole('button', { name: 'Close case' }))
    expect(await screen.findByRole('button', { name: 'Reopen case' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reopen case' }))
    expect(await screen.findByRole('button', { name: 'Close case' })).toBeInTheDocument()
    expect(backend.calls(`PATCH /api/v1/cases/${caseId}`)).toBe(2)
    // The stored report is still there: closing never touches the findings.
    expect(screen.getByText(sampleInvestigation.report.executive_summary)).toBeInTheDocument()
  })
})

describe('formatCreated', () => {
  it('prints UTC to the minute', () => {
    expect(formatCreated('2026-11-10T08:30:45.123456Z')).toBe('2026-11-10 08:30')
    expect(formatCreated('2026-11-10T08:30:00+02:00')).toBe('2026-11-10 06:30')
  })

  it('reads a time without an offset as UTC, and leaves nonsense alone', () => {
    expect(formatCreated('2026-11-10T08:30:00')).toBe('2026-11-10 08:30')
    expect(formatCreated('later')).toBe('later')
  })
})
