import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, type InitialEntry, RouterProvider } from 'react-router'

import { routes } from '../app/routes'
import { signIn } from '../session/session'

// Signed in by default, since every screen but the entry screen needs a session.
export function renderApp(path: InitialEntry, { analyst = 'Test Analyst' }: { analyst?: string | null } = {}) {
  if (analyst) signIn(analyst)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { router, queryClient }
}
