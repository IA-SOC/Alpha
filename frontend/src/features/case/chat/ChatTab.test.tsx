import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import i18n from 'i18next'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChatEvidenceItem, ChatMessage } from '../../../api/types'
import { type Answer, fakeBackend, json, pending } from '../../../test/backend'
import { sampleCase, sampleInvestigation } from '../../../test/fixtures'
import { renderApp } from '../../../test/render'
import { describeRef } from './evidence'

const caseId = sampleInvestigation.case_id
const runId = sampleInvestigation.run_id
const base = `/api/v1/cases/${caseId}`
const hypothesisKey = `mcp:${runId}:hypotheses:0`

// The catalog as app/services/chat_service.py builds it, cut down to what the tests read.
const catalog: Record<string, ChatEvidenceItem> = {
  'alert:wazuh-auth-002': {
    source: 'submitted_case',
    alert_id: 'wazuh-auth-002',
    data: { alert_id: 'wazuh-auth-002', raw_alert: { rule: { description: 'Repeated authentication failures' } } },
  },
  [hypothesisKey]: {
    source: 'investigation',
    section: 'hypotheses',
    data: { rank: 1, statement: 'Brute force against web-01' },
  },
}

const question: ChatMessage = {
  role: 'user',
  analyst_id: 'Test Analyst',
  content: 'Is this really a brute force?',
  evidence_refs: [hypothesisKey],
  created_at: '2026-11-13T09:00:00+00:00',
}
const reply: ChatMessage = {
  role: 'assistant',
  content: 'Only two failures are recorded.\nThat is weak for a brute force.',
  evidence_refs: ['alert:wazuh-auth-002', 'mcp:old-run:timeline:0'],
  created_at: '2026-11-13T09:00:00+00:00',
}

function open(messages: () => Answer, extra: Record<string, Answer | (() => Answer)> = {}) {
  const backend = fakeBackend({
    [`GET ${base}`]: json(200, { case_id: caseId, submitted_case: sampleCase }),
    [`GET ${base}/investigation`]: json(200, sampleInvestigation),
    [`GET ${base}/messages`]: messages,
    [`GET ${base}/chat-evidence`]: json(200, { case_id: caseId, evidence: catalog }),
    ...extra,
  })
  return { backend, ...renderApp(`/cases/${caseId}?tab=chat`) }
}

const history = (...messages: ChatMessage[]) => () => json(200, { case_id: caseId, messages })

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Case chat', () => {
  it('shows the saved conversation with the evidence each answer cites', async () => {
    open(history(question, reply))

    const thread = await screen.findByRole('list', { name: 'Conversation' })
    const [asked, answered] = within(thread).getAllByRole('article')
    expect(within(asked).getByText('Test Analyst')).toBeInTheDocument()
    expect(within(asked).getByText('Asked about 1 piece of evidence')).toBeInTheDocument()
    expect(within(answered).getByText('Gemini')).toBeInTheDocument()
    expect(within(answered).getByText(/Only two failures are recorded\.\s+That is weak/)).toBeInTheDocument()
    expect(within(answered).getByRole('button', { name: 'Inspect Alert wazuh-auth-002' })).toBeInTheDocument()
  })

  it('opens what Gemini cited, with a way to the alert on the Evidence tab', async () => {
    const user = userEvent.setup()
    open(history(question, reply))
    const answered = within(await screen.findByRole('list', { name: 'Conversation' })).getAllByRole('article')[1]

    await user.click(within(answered).getByRole('button', { name: 'Inspect Alert wazuh-auth-002' }))

    const inspector = screen.getByRole('heading', { level: 2, name: 'Alert wazuh-auth-002' })
    expect(inspector).toHaveFocus()
    const panel = inspector.closest('section')!
    expect(within(panel).getByText('From the submitted case')).toBeInTheDocument()
    expect(within(panel).getByText(/"description": "Repeated authentication failures"/)).toBeInTheDocument()
    expect(within(panel).getByRole('link', { name: 'Open alert wazuh-auth-002 in Evidence' })).toBeInTheDocument()
  })

  it('says when a cited piece of evidence belongs to an earlier run', async () => {
    const user = userEvent.setup()
    open(history(question, reply))
    const answered = within(await screen.findByRole('list', { name: 'Conversation' })).getAllByRole('article')[1]

    await user.click(within(answered).getByRole('button', { name: 'Inspect Timeline event 1' }))

    expect(screen.getByText(/comes from an earlier run of the investigation/)).toBeInTheDocument()
  })

  it('sends a question with the attached evidence and shows the answer', async () => {
    let saved = history()
    const answer = pending()
    const { backend } = open(() => saved(), {
      [`POST ${base}/messages`]: () => answer.promise,
    })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('checkbox', { name: 'Attach Hypothesis 1: Brute force against web-01 to the question' }))
    await user.type(screen.getByLabelText('Your question'), 'Is this really a brute force?')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Gemini is answering')
    expect(screen.getByRole('button', { name: 'Sending' })).toBeDisabled()
    const post = backend.fetch.mock.calls.map(([input]) => input as Request).find((request) => request.method === 'POST')!
    expect(post.headers.get('X-Analyst-Id')).toBe('Test Analyst')
    expect(await post.clone().json()).toEqual({
      analyst_id: 'Test Analyst',
      message: 'Is this really a brute force?',
      evidence_refs: [hypothesisKey],
    })

    saved = history(question, reply)
    answer.settle(json(200, { case_id: caseId, message: reply }))

    expect(await screen.findByText(/Only two failures are recorded/)).toBeInTheDocument()
    expect(screen.getByLabelText('Your question')).toHaveValue('')
    expect(screen.queryByText('1 piece of evidence attached')).not.toBeInTheDocument()
  })

  it('does not send twice after leaving the chat and coming back while Gemini answers', async () => {
    const answer = pending()
    const { backend } = open(history(), { [`POST ${base}/messages`]: () => answer.promise })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Your question'), 'Is this really a brute force?')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Gemini is answering')

    await user.click(screen.getByRole('tab', { name: 'Summary' }))
    await user.click(await screen.findByRole('tab', { name: 'Chat' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Gemini is answering')
    expect(screen.getByRole('button', { name: 'Sending' })).toBeDisabled()
    await user.type(screen.getByLabelText('Your question'), 'Is this really a brute force?{Control>}{Enter}{/Control}')
    expect(backend.calls(`POST ${base}/messages`)).toBe(1)

    answer.settle(json(200, { case_id: caseId, message: reply }))
    expect(await screen.findByRole('button', { name: 'Send' })).toBeEnabled()
  })

  it('keeps the question when Gemini is not set up', async () => {
    open(history(), { [`POST ${base}/messages`]: json(503, { detail: 'Gemini is not configured' }) })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Your question'), 'Anything odd here?')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Gemini is not set up on the backend')
    expect(screen.getByLabelText('Your question')).toHaveValue('Anything odd here?')
  })

  it('explains a rejected answer with the backend reason', async () => {
    open(history(), { [`POST ${base}/messages`]: json(502, { detail: 'Gemini cited evidence outside its context' }) })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Your question'), 'Which alerts matter?')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Gemini didn’t give a usable answer, so nothing was saved.')
    expect(alert).toHaveTextContent('Gemini cited evidence outside its context')
  })

  it('does not send an empty question', async () => {
    const { backend } = open(history())
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Your question'), '   ')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(screen.getByRole('alert')).toHaveTextContent('Write a question first.')
    expect(backend.calls(`POST ${base}/messages`)).toBe(0)
  })

  it('offers starting questions on an empty conversation', async () => {
    open(history())
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'What would change the conclusion of this report?' }))

    expect(screen.getByLabelText('Your question')).toHaveValue('What would change the conclusion of this report?')
  })
})

describe('describeRef', () => {
  const t = i18n.getFixedT('en')

  it('names each kind of key the backend builds', () => {
    expect(describeRef('alert:a-1', catalog, runId, t).label).toBe('Alert a-1')
    expect(describeRef(hypothesisKey, catalog, runId, t).label).toBe('Hypothesis 1: Brute force against web-01')
    expect(describeRef(`mcp:${runId}:attack_mapping:0`, undefined, runId, t).label).toBe('ATT&CK technique 1')
    expect(describeRef('something-else', catalog, runId, t).label).toBe('something-else')
  })

  it('marks keys from another run, or missing from the catalog, as stale', () => {
    expect(describeRef(hypothesisKey, catalog, runId, t).stale).toBe(false)
    expect(describeRef('mcp:old-run:hypotheses:0', catalog, runId, t).stale).toBe(true)
    expect(describeRef('alert:gone', catalog, runId, t).stale).toBe(true)
  })
})
