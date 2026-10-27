import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderApp as renderAt } from '../test/render'

describe('Layout', () => {
  it('shows the brand and opens New Case in English by default', () => {
    const { router } = renderAt('/')
    expect(screen.getByAltText('ALIGO Defensores Informáticos')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'New case' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/cases/new')
    expect(screen.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches to Spanish and remembers it', async () => {
    renderAt('/')
    await userEvent.click(screen.getByRole('button', { name: 'Español' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Nuevo caso' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('es')
    expect(localStorage.getItem('soc.language')).toBe('es')
  })

  it('shows a not found page for unknown paths', () => {
    renderAt('/nope')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
