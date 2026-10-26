import { Navigate, type RouteObject } from 'react-router'

import { NewCasePage } from '../features/new-case/NewCasePage'
import { Layout } from './Layout'
import { NotFoundPage } from './NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/cases/new" replace /> },
      { path: 'cases/new', element: <NewCasePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
