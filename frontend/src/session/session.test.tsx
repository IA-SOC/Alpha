import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderApp } from '../test/render'
import { currentSession, signIn, signOut } from './session'

describe('session module', () => {
  it('stores only the trimmed analyst name', () => {
    signIn('  Ana Pérez  ')
    expect(currentSession()).toEqual({ analyst: 'Ana Pérez' })
    expect(JSON.parse(localStorage.getItem('soc.session')!)).toEqual({ analyst: 'Ana Pérez' })
  })

  it('refuses an empty name', () => {
    expect(() => signIn('   ')).toThrow()
    expect(currentSession()).toBeNull()
  })

  it('ignores a stored value that is not a session', () => {
    localStorage.setItem('soc.session', '{"analyst": "  "}')
    expect(currentSession()).toBeNull()
    localStorage.setItem('soc.session', 'not json')
    expect(currentSession()).toBeNull()
  })

  it('forgets the analyst on sign out', () => {
    signIn('Ana')
    signOut()
    expect(currentSession()).toBeNull()
    expect(localStorage.getItem('soc.session')).toBeNull()
  })
})

describe('entry screen', () => {
  it('asks for a name when there is no session and then opens New Case', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/', { analyst: null })

    expect(screen.getByRole('heading', { level: 1, name: 'Who is investigating?' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Your name'), 'Ana Pérez')
    await user.click(screen.getByRole('button', { name: 'Continue' }))

    expect(router.state.location.pathname).toBe('/cases/new')
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument()
  })

  it('does not continue without a name', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/', { analyst: null })

    await user.type(screen.getByLabelText('Your name'), '   ')
    await user.click(screen.getByRole('button', { name: 'Continue' }))

    expect(screen.getByText('Enter your name to continue.')).toBeInTheDocument()
    expect(screen.getByLabelText('Your name')).toHaveAttribute('aria-invalid', 'true')
    expect(router.state.location.pathname).toBe('/')
  })

  it('sends a deep link without a session to the entry screen and back after signing in', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/cases/new', { analyst: null })

    expect(router.state.location.pathname).toBe('/')
    await user.type(screen.getByLabelText('Your name'), 'Ana')
    await user.click(screen.getByRole('button', { name: 'Continue' }))

    expect(router.state.location.pathname).toBe('/cases/new')
  })

  it('skips the entry screen when a session already exists', () => {
    const { router } = renderApp('/', { analyst: 'Ana' })
    expect(router.state.location.pathname).toBe('/cases/new')
  })

  it('signs out from the header and goes back to the entry screen', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/cases/new', { analyst: 'Ana' })

    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(router.state.location.pathname).toBe('/')
    expect(screen.getByRole('heading', { level: 1, name: 'Who is investigating?' })).toBeInTheDocument()
    expect(currentSession()).toBeNull()
  })
})
