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
import { useCopilotStore } from '@/stores/copilot'
import type { ChatBlock, SendChatInput, SendChatResult } from '@/api/contracts/ai'
import '@/design-system/styles/index.css'

LatencySimulator.setEnabled(false)
/**
 * Preview only: a scripted assistant so the conversation screens can be
 * compared visually. The app's own mock never answers (see MockCortexApiClient).
 */
class PreviewAssistantClient extends MockCortexApiClient {
  override async decideAiAction(actionId: string, decision: 'confirm' | 'cancel') {
    return decision === 'confirm'
      ? { action_id: actionId, status: 'executed' as const, result: { rental: 'DEMO-TRX-2026-003', route: '/rentals/DEMO-TRX-2026-003' }, error: null }
      : { action_id: actionId, status: 'cancelled' as const, result: null, error: null }
  }
  override async getAssistantStatus() {
    return { available: true, provider: 'mock' as const, model_name: 'Aperçu (réponses scriptées)' }
  }
  override async listChatSessions() {
    const now = new Date().toISOString().slice(0, 19).replace('T', ' ')
    return [
      { name: 'PRV-1', agent_profile: 'cortex-assistant', state: 'Active' as const, started_at: now, last_message_at: now, title: 'Départs et retours du jour' },
      { name: 'PRV-2', agent_profile: 'cortex-assistant', state: 'Active' as const, started_at: '2026-09-21 10:00:00', last_message_at: '2026-09-21 10:05:00', title: 'Soumission Production Nord' }
    ]
  }
  override async sendChatMessage(_input: SendChatInput): Promise<SendChatResult> {
    const blocks: ChatBlock[] = [
        { type: 'assistant_text' as const, source_ids: [], text: `Voici ce que je vois pour **aujourd’hui** :\n\n- **3 départs** : DEMO-TRX-2026-002 (Studio Lumière), DEMO-TRX-2026-006 (Production Nord) et un kit éclairage.\n- **2 retours** attendus, dont un **en retard** depuis hier (DEMO-TRX-2026-001).\n\nVoulez-vous que je prépare un rappel au client en retard ?` },
        { type: 'widget' as const, tool: 'operations_overview', view: { type: 'kpis', entity: 'operations' }, data: { day: '2026-09-25', kpis: { departures: 3, returns: 2, overdue: 1, exceptions: 1 } } },
        { type: 'widget' as const, tool: 'check_availability', view: { type: 'availability', items: ['DEMO-ITM-ALX35', 'DEMO-ITM-CKE-S4'], starts_at: '2026-10-01T08:00', ends_at: '2026-10-04T18:00' }, data: [
          { item_id: 'DEMO-ITM-ALX35', requested_quantity: 2, available_quantity: 1, total_fleet_quantity: 3, is_available: false },
          { item_id: 'DEMO-ITM-CKE-S4', requested_quantity: 1, available_quantity: 2, total_fleet_quantity: 2, is_available: true }
        ] },
        { type: 'page_link' as const, route: '/operations', label: 'Ouvrir l’aperçu du jour' }
        ,{ type: 'action_proposal', action_id: 'PRV-ACT-1', tool: 'create_quote', title: 'Créer une soumission pour Production Nord Inc.', impact: ['Période : 1 oct. → 4 oct. 2026', 'Articles : 1 × DEMO-ITM-CKE-S4'], effect: 'Crée une location à l’état Soumission. Les prix viennent du catalogue. Rien n’est réservé.', arguments: {}, status: 'proposed' }
      ]
    return { message_id: `PRV-${Date.now()}`, chat_session_id: 'PRV-1', status: 'completed', blocks }
  }
}
setCortexApiClient(new PreviewAssistantClient())

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
const params = new URLSearchParams(window.location.search)
router.push(target).then(async () => {
  app.mount('#app')
  // ?ask=… sends a first message; ?drawer=1 opens the ⌘J panel (visual checks only).
  const copilot = useCopilotStore()
  if (params.get('drawer')) copilot.open()
  const ask = params.get('ask')
  if (ask) {
    await copilot.loadStatus()
    await copilot.sendMessage(ask)
  }
})
