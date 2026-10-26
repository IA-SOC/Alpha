import { Navigate, Outlet, useLocation } from 'react-router'

import { useSession } from './session'

// Every screen except the entry screen needs a session. After signing in, the analyst lands
// on the page they first asked for.
export function RequireSession() {
  const session = useSession()
  const location = useLocation()

  if (!session) return <Navigate to="/" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}
