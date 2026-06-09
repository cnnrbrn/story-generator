import { Outlet, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <>
      {/* Shared shell for every page; <Outlet /> renders the matched child route. */}
      <Outlet />
      <TanStackRouterDevtools />
    </>
  )
}
