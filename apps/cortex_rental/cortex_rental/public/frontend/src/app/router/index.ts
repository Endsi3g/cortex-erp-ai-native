import { createRouter, createWebHistory, createMemoryHistory, type Router } from 'vue-router'
import { routes } from './routes'
import { setupRouterGuards } from './guards'

export function createAppRouter(isTesting = false): Router {
  const history = isTesting || typeof window === 'undefined'
    ? createMemoryHistory()
    : createWebHistory()

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
