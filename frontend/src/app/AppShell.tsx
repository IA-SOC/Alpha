import { Outlet } from 'react-router'

import { CaseSidebar } from '../features/cases/CaseSidebar'

// Signed in screens: the case list on the left, the screen on the right. The sidebar is 18rem,
// so at 1440 the content column is 1152 wide before its own padding.
export function AppShell() {
  return (
    <div className="grid flex-1 md:grid-cols-[18rem_minmax(0,1fr)]">
      <CaseSidebar />
      <main id="main" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
        <Outlet />
      </main>
    </div>
  )
}
