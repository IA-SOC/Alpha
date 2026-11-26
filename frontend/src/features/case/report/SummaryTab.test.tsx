import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'

import type { Report } from '../../../api/types'
import { sampleInvestigation } from '../../../test/fixtures'
import { SummaryTab } from './SummaryTab'

const report = sampleInvestigation.report
const [hypothesis] = report.hypotheses

function renderTab(overrides: Partial<Report>) {
  render(
    <MemoryRouter initialEntries={['/cases/demo?tab=summary']}>
      <SummaryTab report={{ ...report, ...overrides }} />
    </MemoryRouter>,
  )
}

it('sorts findings by rank and keeps supporting and contradicting evidence separate', () => {
  const firstFinding = { ...hypothesis, rank: 1, statement: 'First finding' }
  firstFinding.evidence_for = [
    { alert_id: 'ecs-auth-001', role: 'supporting', observation: 'Repeated failures', relevance: 'Supports the finding.' },
  ]
  firstFinding.evidence_against = [
    { alert_id: 'ecs-uncertain-004', role: 'contradicting', observation: 'A separate successful login', relevance: 'Weakens the finding.' },
  ]
  renderTab({ hypotheses: [{ ...hypothesis, rank: 2, statement: 'Second finding' }, firstFinding] })

  const [first, second] = screen.getAllByRole('article').map((card) => within(card))
  expect(first.getByRole('heading', { name: '1. First finding' })).toBeVisible()
  expect(second.getByRole('heading', { name: '2. Second finding' })).toBeVisible()

  const supports = within(first.getByRole('heading', { name: /evidence for/ }).parentElement!)
  const contradicts = within(first.getByRole('heading', { name: /evidence against/ }).parentElement!)
  expect(supports.getByRole('link', { name: /ecs-auth-001/ })).toBeVisible()
  expect(supports.queryByRole('link', { name: /ecs-uncertain-004/ })).not.toBeInTheDocument()
  expect(contradicts.getByRole('link', { name: /ecs-uncertain-004/ })).toBeVisible()
  expect(contradicts.queryByRole('link', { name: /ecs-auth-001/ })).not.toBeInTheDocument()
})

it('shows each action’s own priority and evidence and flags both for approval', () => {
  renderTab({
    recommended_actions: [
      { priority: 'high', action: 'Rotate credentials', rationale: 'Review the affected accounts.', evidence_ids: ['ecs-auth-001'], requires_human_approval: true, approval_status: 'pending', hypothesis_ranks: [1] },
      { priority: 'low', action: 'Read the case notes', rationale: 'Gather context.', evidence_ids: ['ecs-uncertain-004'], requires_human_approval: true, approval_status: 'pending', hypothesis_ranks: [1] },
    ],
  })

  const rotate = within(screen.getByText('Rotate credentials').closest('li')!)
  expect(rotate.getByText('High')).toBeVisible()
  expect(rotate.getByRole('link', { name: /ecs-auth-001/ })).toBeVisible()
  expect(rotate.getByText(/Needs an analyst's approval/)).toBeVisible()

  const read = within(screen.getByText('Read the case notes').closest('li')!)
  expect(read.getByText('Low')).toBeVisible()
  expect(read.getByText(/Needs an analyst's approval/)).toBeVisible()
  expect(read.getByRole('link', { name: /ecs-uncertain-004/ })).toBeVisible()
  expect(read.queryByRole('link', { name: /ecs-auth-001/ })).not.toBeInTheDocument()
})

it('renders report limitations and missing fields with no hypotheses or actions', () => {
  renderTab({
    executive_summary: 'The available alerts do not settle the finding.',
    hypotheses: [],
    recommended_actions: [],
    limitations: ['Endpoint telemetry is missing.'],
    input: { ...report.input, missing_fields: ['process.command_line'] },
  })

  expect(screen.getByText('The available alerts do not settle the finding.')).toBeVisible()
  expect(screen.getByRole('heading', { name: '0 hypotheses' })).toBeVisible()
  expect(screen.getByText('The agent formed no hypothesis for this case.')).toBeVisible()
  expect(screen.getByText('The agent recommended no actions.')).toBeVisible()
  expect(screen.getByText('Endpoint telemetry is missing.')).toBeVisible()
  expect(screen.getByText('process.command_line')).toBeVisible()
})
