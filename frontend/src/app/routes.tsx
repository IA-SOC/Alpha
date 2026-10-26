import type { RouteObject } from 'react-router'

import { CasePage } from '../features/case/CasePage'
import { NewCasePage } from '../features/new-case/NewCasePage'
import { EntryPage } from '../session/EntryPage'
import { RequireSession } from '../session/RequireSession'
import { Layout } from './Layout'
import { NotFoundPage } from './NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <EntryPage /> },
      {
        element: <RequireSession />,
        children: [
          { path: 'cases/new', element: <NewCasePage /> },
          { path: 'cases/:caseId', element: <CasePage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
]
