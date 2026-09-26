import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/app/App.vue'
import { router } from '@/app/router'
import { i18n } from '@/app/i18n'
import '@/design-system/styles/index.css'

export function bootstrapApp() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  app.use(i18n)

  return { app, pinia, router, i18n }
}

const { app } = bootstrapApp()

// Mount if running in browser environment
if (typeof document !== 'undefined' && document.getElementById('app')) {
  app.mount('#app')
}

export default app
