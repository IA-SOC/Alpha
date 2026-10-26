import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { sampleCase } from '../../test/fixtures'
import { renderApp } from '../../test/render'

// Bodies copied from the real backend's answers to the same requests.
const accepted = {
  case_id: '1b5f7505-6433-430d-9f1f-aba1da31d5a2',
  submitted_case_id: 'SPRINT2-DEMO-001',
  status: 'accepted',
}
const duplicate = {
  detail: [
    { rule: 'VR-04', loc: ['body', 'case_id'], msg: 'This submitted case_id has already been accepted', type: 'case_id_conflict' },
  ],
}

function backendAnswers(status: number, body: unknown) {
  const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  )
  vi.stubGlobal('fetch', fetch)
  return fetch
}

async function pasteAndSubmit(text: string) {
  const user = userEvent.setup()
  renderApp('/cases/new')
  await user.click(screen.getByLabelText('Case JSON'))
  await user.paste(text)
  await user.click(screen.getByRole('button', { name: 'Submit case' }))
  return user
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('New case', () => {
  it('lists what the backend requires before anything is submitted', () => {
    renderApp('/cases/new')
    expect(screen.getByRole('heading', { name: 'What the backend checks' })).toBeInTheDocument()
    expect(screen.getByText('schema_version')).toBeInTheDocument()
    expect(screen.getByText('raw_alert')).toBeInTheDocument()
  })

  it('sends a valid case and shows its application ID on 201', async () => {
    const fetch = backendAnswers(201, accepted)

    await pasteAndSubmit(JSON.stringify(sampleCase, null, 2))

    expect(await screen.findByRole('heading', { name: 'Case accepted' })).toHaveFocus()
    expect(screen.getByText(accepted.case_id)).toBeInTheDocument()
    expect(screen.getByText(/SPRINT2-DEMO-001 is stored/)).toBeInTheDocument()
    expect(await (fetch.mock.calls[0][0] as Request).json()).toEqual(sampleCase)
  })

  it('explains a duplicate on 409', async () => {
    backendAnswers(409, duplicate)

    await pasteAndSubmit(JSON.stringify(sampleCase))

    expect(await screen.findByRole('heading', { name: 'This case was already submitted' })).toBeInTheDocument()
  })

  it('lists every 422 issue with its rule and field, and shows it in the JSON', async () => {
    const text = '{\n  "schema_version": "1.0",\n  "case_id": "X-1",\n  "alerts": [\n    { "alert_id": "a", "source_system": "splunk", "raw_alert": {} }\n  ]\n}'
    backendAnswers(422, {
      detail: [
        { rule: 'VR-05', loc: ['body', 'submitted_at'], msg: 'Field required', type: 'missing' },
        { rule: 'VR-13', loc: ['body', 'alerts', 0, 'source_system'], msg: "Input should be 'elastic' or 'wazuh'", type: 'enum' },
      ],
    })

    const user = await pasteAndSubmit(text)

    expect(await screen.findByRole('heading', { name: '2 problems to fix' })).toBeInTheDocument()
    const issues = screen.getAllByRole('listitem').filter((item) => item.textContent?.includes('VR-'))
    expect(issues).toHaveLength(2)
    expect(within(issues[1]).getByText('alerts[0].source_system')).toBeInTheDocument()

    await user.click(within(issues[1]).getByRole('button', { name: 'Show in JSON' }))
    const editor = screen.getByLabelText<HTMLTextAreaElement>('Case JSON')
    expect(editor).toHaveFocus()
    expect(text.slice(editor.selectionStart, editor.selectionEnd)).toBe('"source_system": "splunk"')
  })

  it('stops invalid JSON before it reaches the backend', async () => {
    const fetch = backendAnswers(201, accepted)

    await pasteAndSubmit('{\n  "case_id": "X-1",\n}')

    expect(screen.getByText('This is not valid JSON. Check line 3, column 1.')).toBeInTheDocument()
    expect(screen.getByLabelText('Case JSON')).toHaveAttribute('aria-invalid', 'true')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('asks for a case when the editor is empty', async () => {
    const fetch = backendAnswers(201, accepted)

    await pasteAndSubmit('')

    expect(screen.getByText('Paste or upload a case first.')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('says the backend is down when the request never gets an answer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await pasteAndSubmit(JSON.stringify(sampleCase))

    expect(await screen.findByRole('heading', { name: "Can't reach the backend" })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('loads an uploaded file into the editor', async () => {
    const user = userEvent.setup()
    renderApp('/cases/new')
    const file = new File([JSON.stringify(sampleCase)], 'case.json', { type: 'application/json' })

    await user.upload(screen.getByLabelText('Upload JSON file'), file)

    expect(screen.getByLabelText<HTMLTextAreaElement>('Case JSON').value).toBe(JSON.stringify(sampleCase))
    expect(screen.getByText('Loaded case.json')).toBeInTheDocument()
  })
})
