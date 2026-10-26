import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'

import { routes } from './routes'

function renderAt(path: string) {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

describe('Layout', () => {
  it('shows the brand and the start page in English by default', () => {
    renderAt('/')
    expect(screen.getByAltText('ALIGO Defensores Informáticos')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Investigate a security case' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches to Spanish and remembers it', async () => {
    renderAt('/')
    await userEvent.click(screen.getByRole('button', { name: 'Español' }))
    expect(screen.getByRole('heading', { name: 'Investiga un caso de seguridad' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('es')
    expect(localStorage.getItem('soc.language')).toBe('es')
  })

  it('shows a not found page for unknown paths', () => {
    renderAt('/nope')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
