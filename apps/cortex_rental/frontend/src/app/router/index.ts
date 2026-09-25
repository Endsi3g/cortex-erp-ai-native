import { createRouter, createWebHistory, createMemoryHistory, type Router } from 'vue-router'
import { routes, ROUTER_BASE } from './routes'
import { setupRouterGuards } from './guards'

export function createAppRouter(isTesting = false): Router {
  const history = isTesting || typeof window === 'undefined'
    ? createMemoryHistory()
    : createWebHistory(ROUTER_BASE)

  const router = createRouter({
    history,
    routes,
    scrollBehavior(_to, _from, savedPosition) {
      if (savedPosition) {
        return savedPosition
      } else {
        return { top: 0 }
      }
    }
  })

  setupRouterGuards(router)
  return router
}

export const router = createAppRouter()
export * from './types'
export * from './routes'
export * from './guards'
