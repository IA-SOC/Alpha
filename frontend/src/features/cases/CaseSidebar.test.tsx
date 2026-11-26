import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import type { CaseListItem } from '../../api/types'
import { fakeBackend, json, pending } from '../../test/backend'
import { CaseSidebar } from './CaseSidebar'

const cases: CaseListItem[] = [
  { case_id: 'open-auth', submitted_case_id: 'AUTH-OPEN', status: 'open', created_at: '2026-11-26T10:00:00Z', investigation: null },
  { case_id: 'closed-auth', submitted_case_id: 'AUTH-CLOSED', status: 'closed', created_at: '2026-11-26T11:00:00Z', investigation: null },
  { case_id: 'open-dns', submitted_case_id: 'DNS-OPEN', status: 'open', created_at: '2026-11-26T12:00:00Z', investigation: null },
]

function renderSidebar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/cases/open-auth']}>
        <CaseSidebar />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return within(screen.getByRole('navigation', { name: 'Cases' }))
}

afterEach(() => vi.unstubAllGlobals())

it('combines the status and ID filters and updates the active case on navigation', async () => {
  fakeBackend({ 'GET /api/v1/cases': json(200, cases) })
  const user = userEvent.setup()
  const sidebar = renderSidebar()

  expect(await sidebar.findByRole('link', { name: /AUTH-OPEN/ })).toHaveAttribute('aria-current', 'page')
  await user.click(sidebar.getByRole('button', { name: /^Closed\s*1$/ }))
  const search = sidebar.getByRole('searchbox', { name: 'Search by case ID' })
  await user.type(search, 'dns')
  expect(sidebar.getByText('No cases match.')).toBeVisible()
  await user.clear(search)
  await user.type(search, 'auth')
  expect(sidebar.queryByRole('link', { name: /AUTH-OPEN/ })).not.toBeInTheDocument()
  const closed = sidebar.getByRole('link', { name: /AUTH-CLOSED/ })
  expect(closed).toHaveTextContent('Closed, Not investigated')
  expect(closed).toHaveAttribute('href', '/cases/closed-auth')
  await user.click(closed)
  expect(closed).toHaveAttribute('aria-current', 'page')
  await user.click(sidebar.getByRole('button', { name: /^All\s*3$/ }))
  expect(sidebar.getByRole('link', { name: /AUTH-OPEN/ })).not.toHaveAttribute('aria-current')
  expect(sidebar.queryByRole('link', { name: /DNS-OPEN/ })).not.toBeInTheDocument()
})

it('shows loading, then lets the analyst retry a failed list request', async () => {
  const first = pending()
  const response = vi.fn()
    .mockReturnValueOnce(first.promise)
    .mockImplementation(() => json(200, cases))
  const backend = fakeBackend({ 'GET /api/v1/cases': response })
  const user = userEvent.setup()
  const sidebar = renderSidebar()

  expect(sidebar.getByText('Loading the cases')).toBeVisible()
  expect(sidebar.queryByRole('searchbox')).not.toBeInTheDocument()
  first.settle(json(503, { detail: 'Test service unavailable' }))
  const error = await sidebar.findByRole('status')
  await user.click(within(error).getByRole('button', { name: 'Retry' }))

  expect(await sidebar.findByRole('link', { name: /AUTH-OPEN/ })).toBeVisible()
  expect(backend.calls('GET /api/v1/cases')).toBe(2)
  expect(sidebar.queryByRole('status')).not.toBeInTheDocument()
})
