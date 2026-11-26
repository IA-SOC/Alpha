import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'

import type { CaseListItem } from '../../api/types'
import { FilterButtons } from './StatusFilter'

const first: CaseListItem = {
  case_id: 'case-a',
  submitted_case_id: 'CASE-A',
  status: 'open',
  created_at: '2026-11-26T16:00:00Z',
  investigation: null,
}

it('keeps whole-list counts while changing the selected filter', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  const cases: CaseListItem[] = [first, { ...first, case_id: 'case-b' }, { ...first, case_id: 'case-c', status: 'closed' }]
  const { rerender } = render(<FilterButtons cases={cases} value="all" onChange={onChange} />)
  const filters = within(screen.getByRole('group', { name: 'Filter by status' }))

  expect(filters.getByRole('button', { name: /^All\s*3$/, pressed: true })).toBeVisible()
  await user.click(filters.getByRole('button', { name: /^Closed\s*1$/, pressed: false }))
  expect(onChange).toHaveBeenLastCalledWith('closed')

  rerender(<FilterButtons cases={cases} value="closed" onChange={onChange} />)
  expect(filters.getByRole('button', { name: /^Closed\s*1$/, pressed: true })).toBeVisible()
  expect(filters.getByRole('button', { name: /^All\s*3$/, pressed: false })).toBeVisible()
  await user.click(filters.getByRole('button', { name: /^Open\s*2$/, pressed: false }))
  expect(onChange).toHaveBeenLastCalledWith('open')
  await user.click(filters.getByRole('button', { name: /^All\s*3$/, pressed: false }))
  expect(onChange.mock.calls).toEqual([['closed'], ['open'], ['all']])
})

it('shows zero for each choice when the case list is empty', () => {
  render(<FilterButtons cases={[]} value="open" onChange={vi.fn()} />)
  const filters = within(screen.getByRole('group', { name: 'Filter by status' }))
  expect(filters.getByRole('button', { name: /^All\s*0$/, pressed: false })).toBeVisible()
  expect(filters.getByRole('button', { name: /^Open\s*0$/, pressed: true })).toBeVisible()
  expect(filters.getByRole('button', { name: /^Closed\s*0$/, pressed: false })).toBeVisible()
})
