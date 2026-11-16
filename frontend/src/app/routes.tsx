import type { RouteObject } from 'react-router'

import { CaseRoute } from '../features/case/CasePage'
import { CasesPage } from '../features/cases/CasesPage'
import { NewCasePage } from '../features/new-case/NewCasePage'
import { EntryPage } from '../session/EntryPage'
import { RequireSession } from '../session/RequireSession'
import { AppShell } from './AppShell'
import { Layout } from './Layout'
import { NotFoundPage } from './NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      {
        index: true,
        element: (
          <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
            <EntryPage />
          </main>
        ),
      },
      {
        element: <RequireSession />,
        children: [
          {
            element: <AppShell />,
            children: [
              { path: 'cases', element: <CasesPage /> },
              { path: 'cases/new', element: <NewCasePage /> },
              { path: 'cases/:caseId', element: <CaseRoute /> },
              { path: '*', element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]
