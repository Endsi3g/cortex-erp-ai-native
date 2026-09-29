import { createRouter, createWebHistory, createMemoryHistory, type Router } from 'vue-router'
import { routes } from './routes'
import { setupRouterGuards } from './guards'
import { STANDALONE_BASE, setupStandalonePaths, standaloneRoutes } from './standalone'

export { STANDALONE_BASE }

export function createAppRouter(isTesting = false): Router {
  const memory = isTesting || typeof window === 'undefined'
  const history = memory ? createMemoryHistory() : createWebHistory(STANDALONE_BASE)

  const router = createRouter({
    history,
    // Memory history = Desk host and tests (canonical /app/cortex-* paths); browser history = standalone /cortex.
    routes: memory ? routes : standaloneRoutes(routes),
    scrollBehavior(_to, _from, savedPosition) {
      if (savedPosition) {
        return savedPosition
      } else {
        return { top: 0 }
      }
    }
  })

  if (!memory) setupStandalonePaths(router)
  setupRouterGuards(router)
  return router
}

export const router = createAppRouter()
export * from './types'
export * from './routes'
export * from './guards'
