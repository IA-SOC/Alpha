import '@fontsource/poppins/latin-300.css'
import '@fontsource/poppins/latin-500.css'
import '@fontsource/poppins/latin-500-italic.css'
import '@fontsource/poppins/latin-700.css'
import './index.css'
import './i18n'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import { routes } from './app/routes'

const queryClient = new QueryClient()
const router = createBrowserRouter(routes)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
