/**
 * Development-only visual preview: renders the real app shell and screens
 * against the explicit DEMO mock client, with a fixed demo session, so
 * screens can be compared with inspiration/image.png without a bench.
 *
 * Not part of the production build (vite builds index.html only) and
 * never served by Frappe. Open /preview/?route=/finance/profit-and-loss
 * on the Vite dev server.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/app/App.vue'
import { createAppRouter } from '@/app/router'
import { i18n } from '@/app/i18n'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { useSessionStore } from '@/stores/session'
import '@/design-system/styles/index.css'

LatencySimulator.setEnabled(false)
setCortexApiClient(new MockCortexApiClient())

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

const session = useSessionStore()
session.currentUser = {
  id: 'demo@cortex.local',
  email: 'demo@cortex.local',
  full_name: 'Démo Cortex',
  roles: ['System Manager'],
  permissions: []
}
session.userCompanies = [{ id: 'DEMO Cortex Cinema Rentals', name: 'DEMO Cortex Cinema Rentals', code: 'CCR', is_default: true, currency: 'CAD' }]
session.activeCompanyId = 'DEMO Cortex Cinema Rentals'
session.isAuthenticated = true

const router = createAppRouter(true)
app.use(router)
app.use(i18n)

const target = new URLSearchParams(window.location.search).get('route') || '/operations'
router.push(target).then(() => app.mount('#app'))
