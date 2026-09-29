import { createApp, type App } from 'vue'
import { createPinia } from 'pinia'
import type { Router } from 'vue-router'
import { createAppRouter } from '@/app/router'
import { i18n } from '@/app/i18n'
import DeskApp from './DeskApp.vue'
import './desk.css'

export interface MountOptions {
  /** Initial SPA path, for example `/app/cortex-rental/CR-TRX-2026-00001?tab=finance`. */
  path: string
  /** Called when a screen links to another page: the Desk host turns it into `frappe.set_route`. */
  navigate: (path: string) => void
}

export interface MountedScreen {
  unmount: () => void
}

/**
 * Mounts one Cortex screen inside a Desk Page. Navigation inside the same page (query changes,
 * tabs) stays in the memory router; anything that changes the page path is handed back to the
 * Desk so the URL, the breadcrumbs and the workspace sidebar stay correct.
 */
export async function mountCortexScreen(el: HTMLElement, options: MountOptions): Promise<MountedScreen> {
  const app: App = createApp(DeskApp)
  const router: Router = createAppRouter(true)
  let ready = false

  router.beforeEach((to, from) => {
    if (!ready) return true
    if (to.path === from.path) return true
    options.navigate(to.fullPath)
    return false
  })

  app.use(createPinia())
  app.use(router)
  app.use(i18n)

  await router.replace(options.path)
  ready = true
  app.mount(el)
  return { unmount: () => app.unmount() }
}
